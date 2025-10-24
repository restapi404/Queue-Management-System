from django.db import models
from django.conf import settings
from django.utils import timezone
from twilio.rest import Client
import logging

logger = logging.getLogger(__name__)

class ServiceCounter(models.Model):
    name = models.CharField(max_length=100)
    is_available = models.BooleanField(default=True)
    current_token = models.ForeignKey('Token', null=True, blank=True, on_delete=models.SET_NULL, related_name='serving_at')
    last_token_completed = models.DateTimeField(null=True, blank=True)

    @classmethod
    def get_next_available(cls):
        """Get the counter that's been free the longest"""
        return cls.objects.filter(is_available=True).order_by('last_token_completed').first()

    def __str__(self):
        return self.name

class Token(models.Model):
    token_number = models.AutoField(primary_key=True)
    customer_name = models.CharField(max_length=100)
    phone_number = models.CharField(max_length=20, blank=True, null=True)
    issued_at = models.DateTimeField(auto_now_add=True)
    is_served = models.BooleanField(default=False)
    counter = models.ForeignKey(ServiceCounter, null=True, blank=True, on_delete=models.SET_NULL)
    started_serving = models.DateTimeField(null=True, blank=True)
    completed_serving = models.DateTimeField(null=True, blank=True)

    FAIRNESS_THRESHOLD = 3  # Maximum tokens ahead allowed for parallel serving

    def __str__(self):
        return f"Token {self.token_number} ({self.customer_name})"

    @property
    def can_be_served(self):
        """Check if this token can be served based on fairness rules"""
        if self.is_served:
            return False
        
        # Get the lowest unserved token number that hasn't started serving
        earliest_pending = Token.objects.filter(
            is_served=False, 
            started_serving__isnull=True
        ).order_by('token_number').first()

        if not earliest_pending:
            return True

        # Allow serving if we're within FAIRNESS_THRESHOLD of the earliest pending
        return self.token_number <= earliest_pending.token_number + self.FAIRNESS_THRESHOLD

    def start_serving(self, counter):
        """Mark token as being served at a counter"""
        if not self.can_be_served:
            return False
        
        self.counter = counter
        self.started_serving = timezone.now()
        self.save()
        
        counter.current_token = self
        counter.is_available = False
        counter.save()
        
        return True

    def complete_serving(self):
        """Mark token as completed and free the counter"""
        self.is_served = True
        self.completed_serving = timezone.now()
        if self.counter:
            self.counter.is_available = True
            self.counter.current_token = None
            self.counter.save()
        self.save()

    @classmethod
    def get_next_servable(cls):
        """Get the next token that can be fairly served"""
        unserved = cls.objects.filter(
            is_served=False,
            started_serving__isnull=True
        ).order_by('token_number')
        
        for token in unserved[:cls.FAIRNESS_THRESHOLD + 1]:
            if token.can_be_served:
                return token
        return None