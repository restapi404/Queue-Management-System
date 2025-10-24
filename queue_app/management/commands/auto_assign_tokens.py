from django.core.management.base import BaseCommand
from django.utils import timezone
from queue_app.models import Token, ServiceCounter
import time
from django.conf import settings

class Command(BaseCommand):
    help = 'Automatically assign tokens to available counters'

    def handle(self, *args, **kwargs):
        while True:
            self.assign_tokens()
            time.sleep(settings.AUTO_ASSIGN_INTERVAL)

    def assign_tokens(self):
        # Get available counters
        counters = ServiceCounter.objects.filter(is_available=True)
        if not counters.exists():
            return

        # Get unassigned tokens that can be served
        for counter in counters:
            next_token = Token.get_next_servable()
            if next_token:
                if next_token.start_serving(counter):
                    self.stdout.write(
                        self.style.SUCCESS(
                            f'Assigned token #{next_token.token_number} to counter {counter.name}'
                        )
                    )

        # Auto-complete tokens that have been serving too long
        serving_tokens = Token.objects.filter(
            is_served=False,
            started_serving__isnull=False
        )
        
        for token in serving_tokens:
            serve_duration = timezone.now() - token.started_serving
            if serve_duration.total_seconds() > settings.MAX_SERVING_TIME:
                token.complete_serving()
                self.stdout.write(
                    self.style.WARNING(
                        f'Auto-completed token #{token.token_number} due to timeout'
                    )
                )