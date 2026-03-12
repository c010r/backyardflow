from django.contrib import admin
from .models import TableArea, Table, Reservation


@admin.register(TableArea)
class TableAreaAdmin(admin.ModelAdmin):
    list_display = ['name', 'active']
    list_filter = ['active']


@admin.register(Table)
class TableAdmin(admin.ModelAdmin):
    list_display = ['number', 'area', 'capacity', 'status', 'active']
    list_filter = ['area', 'status', 'active']
    list_editable = ['status']


@admin.register(Reservation)
class ReservationAdmin(admin.ModelAdmin):
    list_display = ['customer_name', 'table', 'date', 'time', 'party_size', 'status']
    list_filter = ['status', 'date']
    search_fields = ['customer_name', 'customer_phone']
