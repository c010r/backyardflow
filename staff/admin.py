from django.contrib import admin
from .models import StaffMember, WorkShift, SalaryAdvance, SalarySettlement, SalaryItem


@admin.register(StaffMember)
class StaffMemberAdmin(admin.ModelAdmin):
    list_display = ['user', 'role', 'phone', 'payment_type', 'base_salary', 'active']
    list_filter = ['role', 'payment_type', 'active']
    search_fields = ['user__username', 'user__first_name', 'user__last_name', 'dni']


@admin.register(WorkShift)
class WorkShiftAdmin(admin.ModelAdmin):
    list_display = ['staff_member', 'date', 'start_time', 'end_time', 'hours_worked', 'shift_type']
    list_filter = ['shift_type', 'date']
    search_fields = ['staff_member__user__username']


@admin.register(SalaryAdvance)
class SalaryAdvanceAdmin(admin.ModelAdmin):
    list_display = ['staff_member', 'amount', 'date', 'settled', 'approved_by']
    list_filter = ['settled', 'date']


class SalaryItemInline(admin.TabularInline):
    model = SalaryItem
    extra = 0


@admin.register(SalarySettlement)
class SalarySettlementAdmin(admin.ModelAdmin):
    list_display = ['staff_member', 'period_start', 'period_end', 'total_amount', 'status']
    list_filter = ['status']
    inlines = [SalaryItemInline]
