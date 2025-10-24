from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from django.contrib.auth.decorators import user_passes_test
from django.utils import timezone
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
            # placeholder: send SMS (implement provider integration later)
            try:
                send_sms(phone_number, f"Your token is {token.token_number}. Visit /status/{token.token_number}/ to see updates.")
            except Exception:
                # don't block token creation if SMS fails
                pass
            tokens_ahead = Token.objects.filter(is_served=False, token_number__lt=token.token_number).count()
            est_wait = tokens_ahead * 2
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

    try:
        client = Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)
        client.messages.create(
            body=message,
            messaging_service_sid=settings.TWILIO_MESSAGING_SERVICE_SID,
            to=phone_number
        )
        return True
    except Exception as e:
        logger.error(f"SMS sending failed: {e}")
        return False

def queue_status(request, token_number):
    token = get_object_or_404(Token, token_number=token_number)
    current_serving = Token.objects.filter(is_served=False).order_by('token_number').first()
    tokens_ahead = Token.objects.filter(is_served=False, token_number__lt=token.token_number).count()
    est_wait = tokens_ahead * 2
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

@user_passes_test(admin_check)
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
                # Send SMS notification
                if next_token.phone_number:
                    message = f"Your token #{next_token.token_number} is now being served at counter {counter.name}."
                    send_sms(next_token.phone_number, message)
                    
        except (ServiceCounter.DoesNotExist, ValueError):
            pass
            
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
            message = f"Your token #{next_possible.token_number} will be served soon. Please proceed to the waiting area."
            send_sms(next_possible.phone_number, message)
            
    return redirect('admin_dashboard')


@user_passes_test(admin_check)
def reset_queue(request):
    """Admin-only: clear all tokens (for testing / reset)"""
    if request.method == 'POST':
        Token.objects.all().delete()
        # mark all counters available
        ServiceCounter.objects.update(is_available=True)
    return redirect('admin_dashboard')