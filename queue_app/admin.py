from django.contrib import admin
from .models import ServiceCounter, Token

@admin.register(ServiceCounter)
class ServiceCounterAdmin(admin.ModelAdmin):
    list_display = ('name', 'is_available')
    list_editable = ('is_available',)
    search_fields = ('name',)

@admin.register(Token)
class TokenAdmin(admin.ModelAdmin):
    list_display = ('token_number', 'customer_name', 'issued_at', 'is_served', 'counter')
    list_filter = ('is_served', 'counter')
    search_fields = ('customer_name',)