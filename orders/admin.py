from django.contrib import admin
from .models import Order, OrderItem, VirtualWaiterSession


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    readonly_fields = ['subtotal']

    @admin.display(description='Subtotal')
    def subtotal(self, obj):
        return obj.subtotal


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ['order_number', 'table', 'order_type', 'waiter_type', 'status', 'created_at']
    list_filter = ['status', 'order_type', 'waiter_type', 'created_at']
    search_fields = ['order_number']
    inlines = [OrderItemInline]
    readonly_fields = ['order_number', 'created_at', 'updated_at']


@admin.register(VirtualWaiterSession)
class VirtualWaiterSessionAdmin(admin.ModelAdmin):
    list_display = ['table', 'session_token', 'active', 'started_at']
    list_filter = ['active']
