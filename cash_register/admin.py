from django.contrib import admin
from .models import CashRegister, CashSession, CashMovement, Payment


@admin.register(CashRegister)
class CashRegisterAdmin(admin.ModelAdmin):
    list_display = ['name', 'location', 'active']
    list_filter = ['active']


@admin.register(CashSession)
class CashSessionAdmin(admin.ModelAdmin):
    list_display = ['cash_register', 'operator', 'status', 'opening_amount', 'opened_at', 'closed_at']
    list_filter = ['status', 'cash_register']
    readonly_fields = ['opened_at', 'closed_at']


@admin.register(CashMovement)
class CashMovementAdmin(admin.ModelAdmin):
    list_display = ['session', 'movement_type', 'amount', 'description', 'created_at']
    list_filter = ['movement_type', 'created_at']


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ['order', 'session', 'payment_method', 'amount', 'created_at']
    list_filter = ['payment_method', 'created_at']
    search_fields = ['order__order_number']
