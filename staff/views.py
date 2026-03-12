from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from backyardflow.roles import role_required
from django.views.generic import ListView, CreateView, UpdateView, DetailView, DeleteView
from django.urls import reverse_lazy
from django.contrib import messages
from django.utils import timezone
from django.contrib.auth.models import User
from decimal import Decimal
from datetime import date, timedelta
from .models import StaffMember, WorkShift, SalaryAdvance, SalarySettlement, SalaryItem
from .forms import (StaffMemberForm, WorkShiftForm, SalaryAdvanceForm,
                    SalarySettlementForm, UserCreationWithStaffForm)


@role_required('staff')
def staff_dashboard(request):
    staff = StaffMember.objects.filter(active=True).select_related('user')
    today = timezone.now().date()

    # This month's shifts
    start_of_month = today.replace(day=1)
    recent_shifts = WorkShift.objects.filter(
        date__gte=start_of_month
    ).select_related('staff_member__user').order_by('-date')[:10]

    # Pending settlements
    pending_settlements = SalarySettlement.objects.filter(
        status='DRAFT'
    ).select_related('staff_member__user')

    # Recent advances
    recent_advances = SalaryAdvance.objects.filter(
        settled=False
    ).select_related('staff_member__user').order_by('-date')[:5]

    context = {
        'staff': staff,
        'total_staff': staff.count(),
        'recent_shifts': recent_shifts,
        'pending_settlements': pending_settlements,
        'recent_advances': recent_advances,
        'today': today,
    }
    return render(request, 'staff/dashboard.html', context)


class StaffMemberListView(LoginRequiredMixin, ListView):
    model = StaffMember
    template_name = 'staff/member_list.html'
    context_object_name = 'members'

    def get_queryset(self):
        return StaffMember.objects.filter(active=True).select_related('user').order_by('role', 'user__last_name')


class StaffMemberDetailView(LoginRequiredMixin, DetailView):
    model = StaffMember
    template_name = 'staff/member_detail.html'
    context_object_name = 'member'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        today = timezone.now().date()
        start_of_month = today.replace(day=1)

        ctx['recent_shifts'] = self.object.shifts.filter(
            date__gte=start_of_month
        ).order_by('-date')

        ctx['pending_advances'] = self.object.advances.filter(settled=False).order_by('-date')

        ctx['settlements'] = self.object.settlements.order_by('-period_end')[:5]

        # Calculate monthly hours
        total_hours = self.object.total_hours_in_period(start_of_month, today)
        ctx['monthly_hours'] = total_hours

        return ctx


@role_required('staff')
def staff_member_create(request):
    if request.method == 'POST':
        user_form = UserCreationWithStaffForm(request.POST)
        staff_form = StaffMemberForm(request.POST)
        if user_form.is_valid() and staff_form.is_valid():
            user = user_form.save()
            staff = staff_form.save(commit=False)
            staff.user = user
            staff.save()
            messages.success(request, f'Personal {staff} creado exitosamente.')
            return redirect('staff:member_list')
    else:
        user_form = UserCreationWithStaffForm()
        staff_form = StaffMemberForm()

    return render(request, 'staff/member_create.html', {
        'user_form': user_form,
        'staff_form': staff_form
    })


class StaffMemberUpdateView(LoginRequiredMixin, UpdateView):
    model = StaffMember
    form_class = StaffMemberForm
    template_name = 'staff/member_form.html'
    success_url = reverse_lazy('staff:member_list')

    def form_valid(self, form):
        messages.success(self.request, 'Personal actualizado.')
        return super().form_valid(form)


class StaffMemberDeleteView(LoginRequiredMixin, DeleteView):
    model = StaffMember
    template_name = 'staff/member_confirm_delete.html'
    success_url = reverse_lazy('staff:member_list')

    def form_valid(self, form):
        self.object.active = False
        self.object.save()
        messages.success(self.request, f'{self.object.full_name} desactivado del sistema.')
        return redirect(self.success_url)


class WorkShiftDeleteView(LoginRequiredMixin, DeleteView):
    model = WorkShift
    template_name = 'staff/shift_confirm_delete.html'

    def get_success_url(self):
        return reverse_lazy('staff:shift_list', kwargs={'member_pk': self.object.staff_member.pk})

    def form_valid(self, form):
        messages.success(self.request, 'Turno eliminado.')
        return super().form_valid(form)


class WorkShiftCreateView(LoginRequiredMixin, CreateView):
    model = WorkShift
    form_class = WorkShiftForm
    template_name = 'staff/shift_form.html'

    def get_success_url(self):
        return reverse_lazy('staff:member_detail', kwargs={'pk': self.object.staff_member.pk})

    def get_initial(self):
        initial = super().get_initial()
        member_pk = self.kwargs.get('member_pk')
        if member_pk:
            initial['staff_member'] = member_pk
        initial['date'] = timezone.now().date()
        return initial

    def form_valid(self, form):
        messages.success(self.request, 'Turno registrado.')
        return super().form_valid(form)


class WorkShiftListView(LoginRequiredMixin, ListView):
    model = WorkShift
    template_name = 'staff/shift_list.html'
    context_object_name = 'shifts'
    paginate_by = 20

    def get_queryset(self):
        member_pk = self.kwargs.get('member_pk')
        if member_pk:
            return WorkShift.objects.filter(
                staff_member_id=member_pk
            ).select_related('staff_member__user').order_by('-date')
        return WorkShift.objects.select_related('staff_member__user').order_by('-date')

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        member_pk = self.kwargs.get('member_pk')
        if member_pk:
            ctx['member'] = get_object_or_404(StaffMember, pk=member_pk)
        return ctx


class SalaryAdvanceCreateView(LoginRequiredMixin, CreateView):
    model = SalaryAdvance
    form_class = SalaryAdvanceForm
    template_name = 'staff/advance_form.html'
    success_url = reverse_lazy('staff:dashboard')

    def form_valid(self, form):
        form.instance.approved_by = self.request.user
        messages.success(self.request, 'Adelanto registrado.')
        return super().form_valid(form)


@role_required('staff')
def generate_settlement(request, member_pk):
    member = get_object_or_404(StaffMember, pk=member_pk)

    if request.method == 'POST':
        period_start_str = request.POST.get('period_start')
        period_end_str = request.POST.get('period_end')
        bonuses = Decimal(request.POST.get('bonuses', '0') or '0')
        deductions = Decimal(request.POST.get('deductions', '0') or '0')
        notes = request.POST.get('notes', '')

        from datetime import datetime
        period_start = datetime.strptime(period_start_str, '%Y-%m-%d').date()
        period_end = datetime.strptime(period_end_str, '%Y-%m-%d').date()

        # Calculate base amount
        if member.payment_type == 'MONTHLY':
            # Pro-rate monthly salary
            days_in_period = (period_end - period_start).days + 1
            days_in_month = 30
            base_amount = member.base_salary * Decimal(str(days_in_period)) / Decimal(str(days_in_month))
        else:
            # Hourly
            total_hours = member.total_hours_in_period(period_start, period_end)
            base_amount = Decimal(str(total_hours)) * member.hourly_rate

        # Get unsettled advances
        advances = member.advances.filter(settled=False, date__lte=period_end)
        advances_total = sum(a.amount for a in advances)

        settlement = SalarySettlement.objects.create(
            staff_member=member,
            period_start=period_start,
            period_end=period_end,
            base_amount=base_amount,
            bonuses=bonuses,
            deductions=deductions,
            advances_deducted=advances_total,
            total_amount=base_amount + bonuses - deductions - advances_total,
            status='DRAFT',
            notes=notes,
            generated_by=request.user
        )

        # Mark advances as settled
        advances.update(settled=True)

        # Add salary items
        SalaryItem.objects.create(
            settlement=settlement,
            concept='Salario Base',
            item_type='EARNING',
            amount=base_amount
        )
        if bonuses > 0:
            SalaryItem.objects.create(
                settlement=settlement,
                concept='Bonificaciones',
                item_type='EARNING',
                amount=bonuses
            )
        if deductions > 0:
            SalaryItem.objects.create(
                settlement=settlement,
                concept='Deducciones',
                item_type='DEDUCTION',
                amount=deductions
            )
        if advances_total > 0:
            SalaryItem.objects.create(
                settlement=settlement,
                concept='Adelantos descontados',
                item_type='DEDUCTION',
                amount=advances_total
            )

        messages.success(request, f'Liquidacion generada: ${settlement.total_amount}')
        return redirect('staff:settlement_detail', pk=settlement.pk)

    # Default period: current month
    today = timezone.now().date()
    period_start = today.replace(day=1)
    period_end = today

    # Calculate preview
    if member.payment_type == 'MONTHLY':
        days_in_period = (period_end - period_start).days + 1
        preview_base = member.base_salary * Decimal(str(days_in_period)) / Decimal('30')
    else:
        total_hours = member.total_hours_in_period(period_start, period_end)
        preview_base = Decimal(str(total_hours)) * member.hourly_rate

    pending_advances = member.advances.filter(settled=False)
    advances_total = sum(a.amount for a in pending_advances)

    context = {
        'member': member,
        'period_start': period_start,
        'period_end': period_end,
        'preview_base': preview_base,
        'pending_advances': pending_advances,
        'advances_total': advances_total,
    }
    return render(request, 'staff/generate_settlement.html', context)


class SalarySettlementListView(LoginRequiredMixin, ListView):
    model = SalarySettlement
    template_name = 'staff/settlement_list.html'
    context_object_name = 'settlements'
    paginate_by = 20

    def get_queryset(self):
        return SalarySettlement.objects.select_related(
            'staff_member__user', 'generated_by'
        ).order_by('-period_end')


class SalarySettlementDetailView(LoginRequiredMixin, DetailView):
    model = SalarySettlement
    template_name = 'staff/settlement_detail.html'
    context_object_name = 'settlement'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['items'] = self.object.items.all()
        ctx['earnings'] = self.object.items.filter(item_type='EARNING')
        ctx['deduction_items'] = self.object.items.filter(item_type='DEDUCTION')
        return ctx


@role_required('staff')
def approve_settlement(request, pk):
    settlement = get_object_or_404(SalarySettlement, pk=pk, status='DRAFT')
    if request.method == 'POST':
        settlement.status = 'APPROVED'
        settlement.save()
        messages.success(request, 'Liquidacion aprobada.')
    return redirect('staff:settlement_detail', pk=pk)


@role_required('staff')
def mark_settlement_paid(request, pk):
    settlement = get_object_or_404(SalarySettlement, pk=pk, status='APPROVED')
    if request.method == 'POST':
        settlement.status = 'PAID'
        settlement.payment_date = timezone.now().date()
        payment_method = request.POST.get('payment_method', 'CASH')
        settlement.payment_method = payment_method
        settlement.save()
        messages.success(request, f'Liquidacion marcada como pagada via {settlement.get_payment_method_display()}.')
    return redirect('staff:settlement_detail', pk=pk)


@role_required('staff')
def work_schedule(request):
    """Weekly calendar view of work schedule"""
    today = timezone.now().date()
    week_start_str = request.GET.get('week_start')

    if week_start_str:
        from datetime import datetime
        try:
            week_start = datetime.strptime(week_start_str, '%Y-%m-%d').date()
        except ValueError:
            week_start = today - timedelta(days=today.weekday())
    else:
        week_start = today - timedelta(days=today.weekday())

    week_end = week_start + timedelta(days=6)

    staff = StaffMember.objects.filter(active=True).select_related('user')
    shifts = WorkShift.objects.filter(
        date__gte=week_start,
        date__lte=week_end
    ).select_related('staff_member__user')

    # Build schedule matrix
    schedule = {}
    week_days = [week_start + timedelta(days=i) for i in range(7)]

    # days_dict[member_pk][day] = [shift, ...]
    days_dict = {}
    for member in staff:
        days_dict[member.pk] = {day: [] for day in week_days}

    for shift in shifts:
        if shift.staff_member.pk in days_dict:
            if shift.date in days_dict[shift.staff_member.pk]:
                days_dict[shift.staff_member.pk][shift.date].append(shift)

    # Build list of (member, day_rows) where day_rows is an ordered list
    # of (day, shifts_list) tuples so the template can iterate without
    # dict-key lookups (which don't work with date objects in DTL).
    schedule_rows = []
    for member in staff:
        day_cells = [(day, days_dict[member.pk][day]) for day in week_days]
        schedule_rows.append({'member': member, 'day_cells': day_cells})

    context = {
        'schedule': schedule_rows,
        'week_days': week_days,
        'week_start': week_start,
        'week_end': week_end,
        'prev_week': week_start - timedelta(days=7),
        'next_week': week_start + timedelta(days=7),
        'today': today,
    }
    return render(request, 'staff/work_schedule.html', context)
