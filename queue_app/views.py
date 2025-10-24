from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from django.contrib.auth.decorators import user_passes_test
from django.utils import timezone
from datetime import timedelta
from django.db import connection
from django.conf import settings
from twilio.rest import Client
import logging

from .models import Token, ServiceCounter
from .forms import TokenForm, CounterForm

logger = logging.getLogger(__name__)

def home(request):
    form = TokenForm()
    return render(request, 'index.html', {'form': form})

def generate_token(request):
    if request.method == 'POST':
        form = TokenForm(request.POST)
        if form.is_valid():
            customer_name = form.cleaned_data['customer_name']
            phone_number = form.cleaned_data.get('phone_number')
            token = Token.objects.create(customer_name=customer_name, phone_number=phone_number)
            # Calculate estimated wait and send a friendly initial SMS
            tokens_ahead = Token.objects.filter(is_served=False, token_number__lt=token.token_number).count()
            per_token = getattr(settings, 'PER_TOKEN_MINUTES', 2)
            # Minimum wait for a newly created token should be one slot * per_token
            est_wait = (tokens_ahead + 1) * per_token  # minutes per token estimate
            try:
                init_msg = (
                    f"Hi {customer_name}, your token #{token.token_number} is confirmed. "
#                    f"Counters will be allotted soon. Estimated wait: {est_wait} minutes. "
                    f"You will receive an update when a counter is assigned."
                    f"Track your status at /status/{token.token_number}/"
                )
                send_sms(phone_number, init_msg)
            except Exception:
                # don't block token creation if SMS fails
                pass
            return render(request, 'token.html', {
                'token': token,
                'tokens_ahead': tokens_ahead,
                'est_wait': est_wait,
            })
    return redirect('home')


def send_sms(phone_number, message):
    """Send SMS using Twilio"""
    if not phone_number or not settings.SMS_ENABLED:
        return False

    # Format Indian numbers automatically (optional)
    if phone_number.isdigit() and len(phone_number) == 10:
        phone_number = '+91' + phone_number

    try:
        client = Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)
        # Prefer messaging service SID if configured, otherwise use a Twilio phone number
        msg_kwargs = {
            'body': message,
            'to': phone_number,
        }
        if getattr(settings, 'TWILIO_MESSAGING_SERVICE_SID', ''):
            msg_kwargs['messaging_service_sid'] = settings.TWILIO_MESSAGING_SERVICE_SID
        else:
            msg_kwargs['from_'] = settings.TWILIO_PHONE_NUMBER

        client.messages.create(**msg_kwargs)
        print(f"SMS sent to {phone_number}")  # Debug
        return True
    except Exception as e:
        logger.error(f"SMS sending failed: {e}")
        print(f"SMS failed: {e}")  # Debug
        return False

def queue_status(request, token_number):
    token = get_object_or_404(Token, token_number=token_number)
    current_serving = Token.objects.filter(is_served=False).order_by('token_number').first()
    tokens_ahead = Token.objects.filter(is_served=False, token_number__lt=token.token_number).count()
    per_token = getattr(settings, 'PER_TOKEN_MINUTES', 2)
    est_wait = (tokens_ahead + 1) * per_token
    # Support both modern header check and Django's is_ajax fallback
    is_ajax = request.headers.get('x-requested-with') == 'XMLHttpRequest' or getattr(request, 'is_ajax', lambda: False)()
    if is_ajax:
        return JsonResponse({
            'current_serving': current_serving.token_number if current_serving else None,
            'tokens_ahead': tokens_ahead,
            'est_wait': est_wait,
        })

    return render(request, 'queue_status.html', {
        'token': token,
        'current_serving': current_serving,
        'tokens_ahead': tokens_ahead,
        'est_wait': est_wait,
    })

def admin_check(user):
    return user.is_staff or user.is_superuser

@user_passes_test(admin_check)
def admin_dashboard(request):
    active_tokens = Token.objects.filter(is_served=False).order_by('token_number')
    served_tokens = Token.objects.filter(is_served=True).order_by('-issued_at')[:20]
    counters = ServiceCounter.objects.all()
    counter_form = CounterForm()
    return render(request, 'admin_dashboard.html', {
        'active_tokens': active_tokens,
        'served_tokens': served_tokens,
        'counters': counters,
        'counter_form': counter_form,
    })


@user_passes_test(admin_check)
def create_counter(request):
    if request.method == 'POST':
        form = CounterForm(request.POST)
        if form.is_valid():
            name = form.cleaned_data['name']
            ServiceCounter.objects.create(name=name, is_available=True)
    return redirect('admin_dashboard')

'''@user_passes_test(admin_check)
def serve_next(request):
    """Serve next token with fairness rules"""
    if request.method == 'POST':
        counter_id = request.POST.get('counter_id')
        if not counter_id:
            return redirect('admin_dashboard')
            
        try:
            counter = ServiceCounter.objects.get(id=int(counter_id))
            if not counter.is_available:
                return redirect('admin_dashboard')
                
            # Get next token that can be fairly served
            next_token = Token.get_next_servable()
            if next_token and next_token.start_serving(counter):
                tokens_ahead = Token.objects.filter(is_served=False, token_number__lt=next_token.token_number).count()
                per_token = getattr(settings, 'PER_TOKEN_MINUTES', 2)
                est_wait = (tokens_ahead + 1) * per_token

                # Send SMS notification
                if next_token.phone_number:
                    start_time = timezone.localtime(next_token.started_serving).strftime('%H:%M') if next_token.started_serving else timezone.localtime(timezone.now()).strftime('%H:%M')
                    message = (
                        f"Good news — your token #{next_token.token_number} is now being served at counter {counter.name}. "
                        f"Please collect your order. Started at {start_time}."
                    )
                    send_sms(next_token.phone_number, message)
                    
        except (ServiceCounter.DoesNotExist, ValueError):
            pass
            
    return redirect('admin_dashboard')'''

@user_passes_test(admin_check)
def serve_next(request):
    """Serve next token with fairness rules"""
    if request.method == 'POST':
        counter_id = request.POST.get('counter_id')
        if not counter_id:
            return redirect('admin_dashboard')

        # ✅ Step 1: Check if any counters are available
        available_counters = ServiceCounter.objects.filter(is_available=True)
        if not available_counters.exists():
            # No free counters — notify waiting users
            waiting_tokens = Token.objects.filter(is_served=False, started_serving__isnull=True)
            for t in waiting_tokens:
                if t.phone_number:
                    send_sms(
                        t.phone_number,
                        f"Dear {t.customer_name}, all counters are currently busy. "
                        f"You’ll be notified once a counter is free."
                    )
            # Return without trying to allocate
            return redirect('admin_dashboard')

        # ✅ Step 2: Proceed to assign the next token
        try:
            counter = ServiceCounter.objects.get(id=int(counter_id))
            if not counter.is_available:
                return redirect('admin_dashboard')

            next_token = Token.get_next_servable()
            if next_token and next_token.start_serving(counter):
                # Calculate estimated wait for clarity
                tokens_ahead = Token.objects.filter(is_served=False, token_number__lt=next_token.token_number).count()
                per_token = getattr(settings, 'PER_TOKEN_MINUTES', 2)
                est_wait = (tokens_ahead + 1) * per_token

                # ✅ Step 3: Send SMS about counter assignment
                if next_token.phone_number:
                    start_time = timezone.localtime(timezone.now()).strftime('%H:%M')
                    message = (
                        f"Hi {next_token.customer_name}, your token #{next_token.token_number} "
                        f"is now being served at counter {counter.name}. "
                        f"Estimated service start time: {start_time}. Please proceed soon."
                    )
                    send_sms(next_token.phone_number, message)

        except (ServiceCounter.DoesNotExist, ValueError) as e:
            logger.error(f"Serve next error: {e}")

    return redirect('admin_dashboard')


@user_passes_test(admin_check)
def mark_served(request, token_number):
    """Complete serving a token and free its counter"""
    token = get_object_or_404(Token, token_number=token_number)
    if request.method == 'POST':
        token.complete_serving()  # This handles counter availability too
        
        # Notify next in line if within threshold
        next_possible = Token.get_next_servable()
        if next_possible and next_possible.phone_number:
            # Estimate wait time for the next_possible token and attach expected time
            tokens_ahead_np = Token.objects.filter(is_served=False, token_number__lt=next_possible.token_number).count()
            per_token = getattr(settings, 'PER_TOKEN_MINUTES', 2)
            est_wait_np = (tokens_ahead_np + 1) * per_token
            expected_time = (timezone.localtime(timezone.now()) + timedelta(minutes=est_wait_np)).strftime('%H:%M')
            message = (
                f"Update for token #{next_possible.token_number}: a counter will be allotted soon. "
                f"Estimated wait: {est_wait_np} minutes (approx at {expected_time}). Please be ready to proceed to the waiting area."
            )
            send_sms(next_possible.phone_number, message)

        # Notify the token owner that their order has been served/collected
        if token.phone_number:
            completed_time = timezone.localtime(token.completed_serving or timezone.now()).strftime('%H:%M')
            collected_msg = (
                f"Your token #{token.token_number} has been served and collected at {completed_time}. "
                f"Thank you for visiting!"
            )
            send_sms(token.phone_number, collected_msg)
            
    return redirect('admin_dashboard')


@user_passes_test(admin_check)
def reset_queue(request):
    """Admin-only: clear all tokens (for testing / reset)"""
    if request.method == 'POST':
        Token.objects.all().delete()
        # mark all counters available
        ServiceCounter.objects.update(is_available=True)
        # Reset SQLite autoincrement sequence so token numbers start back at 1
        try:
            if connection.vendor == 'sqlite':
                with connection.cursor() as cursor:
                    cursor.execute("DELETE FROM sqlite_sequence WHERE name='queue_app_token';")
        except Exception:
            # Non-fatal; leave as-is for other DB backends
            pass
    return redirect('admin_dashboard')