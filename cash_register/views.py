from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from backyardflow.roles import role_required
from django.views.generic import ListView, CreateView, UpdateView, DeleteView
from django.urls import reverse_lazy
from django.contrib import messages
from django.utils import timezone
from django.db.models import Sum
from decimal import Decimal
from .models import CashRegister, CashSession, CashMovement, Payment
from .forms import OpenSessionForm, CloseSessionForm, CashMovementForm, PaymentForm, CashRegisterForm
from orders.models import Order


@role_required('cash_register')
def cash_register_dashboard(request):
    registers = CashRegister.objects.filter(active=True)
    open_sessions = CashSession.objects.filter(status='OPEN').select_related('cash_register', 'operator')
    today = timezone.now().date()

    today_payments = Payment.objects.filter(created_at__date=today)
    today_total = today_payments.aggregate(total=Sum('amount'))['total'] or Decimal('0')

    recent_payments = today_payments.select_related('order', 'session').order_by('-created_at')[:10]

    # Sales by method
    sales_by_method = {}
    for method_code, method_name in Payment.PAYMENT_METHODS:
        total = today_payments.filter(payment_method=method_code).aggregate(
            total=Sum('amount')
        )['total'] or Decimal('0')
        if total > 0:
            sales_by_method[method_name] = total

    context = {
        'registers': registers,
        'open_sessions': open_sessions,
        'today_total': today_total,
        'recent_payments': recent_payments,
        'sales_by_method': sales_by_method,
        'today': today,
    }
    return render(request, 'cash_register/dashboard.html', context)


@role_required('cash_register')
def open_session(request):
    # Check if current user already has open session
    existing = CashSession.objects.filter(operator=request.user, status='OPEN').first()
    if existing:
        messages.warning(request, f'Ya tienes una sesion abierta: {existing}')
        return redirect('cash_register:dashboard')

    if request.method == 'POST':
        form = OpenSessionForm(request.POST)
        if form.is_valid():
            session = form.save(commit=False)
            # Check if register already has open session
            register = form.cleaned_data['cash_register']
            if register.current_session:
                messages.error(request, f'La caja {register.name} ya tiene una sesion abierta.')
                return render(request, 'cash_register/open_session.html', {'form': form})
            session.operator = request.user
            session.status = 'OPEN'
            session.save()
            messages.success(request, f'Sesion de caja abierta: {session}')
            return redirect('cash_register:dashboard')
    else:
        form = OpenSessionForm()

    return render(request, 'cash_register/open_session.html', {'form': form})


@role_required('cash_register')
def close_session(request, pk):
    session = get_object_or_404(CashSession, pk=pk, status='OPEN')

    # Calculate expected amount
    expected = session.calculated_expected_amount

    if request.method == 'POST':
        form = CloseSessionForm(request.POST, instance=session)
        if form.is_valid():
            session = form.save(commit=False)
            session.status = 'CLOSED'
            session.closed_at = timezone.now()
            session.expected_closing_amount = expected
            closing = form.cleaned_data.get('closing_amount') or Decimal('0')
            session.closing_amount = closing
            session.difference = closing - expected
            session.save()
            messages.success(request, f'Sesion cerrada. Diferencia: ${session.difference}')
            return redirect('cash_register:session_report', pk=session.pk)
    else:
        form = CloseSessionForm(instance=session)

    # Recent movements
    movements = session.movements.order_by('-created_at')[:20]
    payments = session.payments.order_by('-created_at')[:20]

    context = {
        'session': session,
        'form': form,
        'expected': expected,
        'movements': movements,
        'payments': payments,
    }
    return render(request, 'cash_register/close_session.html', context)


class CashMovementCreateView(LoginRequiredMixin, CreateView):
    model = CashMovement
    form_class = CashMovementForm
    template_name = 'cash_register/movement_form.html'
    success_url = reverse_lazy('cash_register:dashboard')

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        return kwargs

    def form_valid(self, form):
        form.instance.created_by = self.request.user
        messages.success(self.request, 'Movimiento registrado.')
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['open_sessions'] = CashSession.objects.filter(status='OPEN')
        return ctx


@role_required('cash_register')
def process_payment(request, order_pk):
    order = get_object_or_404(Order, pk=order_pk)

    if order.status == 'PAID':
        messages.info(request, 'Esta comanda ya fue pagada.')
        return redirect('orders:order_detail', pk=order_pk)

    # Get active session
    active_session = CashSession.objects.filter(
        status='OPEN', operator=request.user
    ).first()

    if not active_session:
        active_session = CashSession.objects.filter(status='OPEN').first()

    if not active_session:
        messages.error(request, 'No hay sesion de caja abierta. Abre una sesion primero.')
        return redirect('cash_register:open_session')

    if request.method == 'POST':
        form = PaymentForm(request.POST)
        if form.is_valid():
            payment = form.save(commit=False)
            payment.order = order
            payment.session = active_session
            payment.created_by = request.user

            # Calculate change
            if payment.payment_method == 'CASH':
                amount_received = form.cleaned_data.get('amount_received') or payment.amount
                payment.change_given = max(amount_received - order.total, Decimal('0'))
                payment.amount = order.total

            payment.save()

            # Register as sale movement
            CashMovement.objects.create(
                session=active_session,
                movement_type='SALE',
                amount=payment.amount,
                description=f'Venta comanda {order.order_number}',
                reference=order.order_number,
                created_by=request.user
            )

            # Mark order as paid
            order.status = 'PAID'
            order.closed_at = timezone.now()
            order.cash_session = active_session
            order.save()

            # Free table
            if order.table:
                other_active = Order.objects.filter(
                    table=order.table,
                    status__in=['PENDING', 'IN_PROGRESS', 'READY', 'DELIVERED']
                ).exclude(pk=order.pk).exists()
                if not other_active:
                    order.table.status = 'FREE'
                    order.table.save()

            messages.success(request, f'Pago procesado. Cambio: ${payment.change_given}')
            return redirect('orders:order_detail', pk=order.pk)
    else:
        form = PaymentForm(initial={'amount': order.total})

    context = {
        'form': form,
        'order': order,
        'active_session': active_session,
    }
    return render(request, 'cash_register/payment_form.html', context)


@role_required('cash_register')
def session_report(request, pk):
    session = get_object_or_404(CashSession, pk=pk)
    movements = session.movements.order_by('created_at')
    payments = session.payments.select_related('order').order_by('created_at')

    total_sales = payments.aggregate(total=Sum('amount'))['total'] or Decimal('0')
    total_by_method = {}
    for method_code, method_name in Payment.PAYMENT_METHODS:
        total = payments.filter(payment_method=method_code).aggregate(
            total=Sum('amount')
        )['total'] or Decimal('0')
        if total > 0:
            total_by_method[method_name] = total

    context = {
        'session': session,
        'movements': movements,
        'payments': payments,
        'total_sales': total_sales,
        'total_by_method': total_by_method,
    }
    return render(request, 'cash_register/session_report.html', context)


class CashRegisterListView(LoginRequiredMixin, ListView):
    model = CashRegister
    template_name = 'cash_register/register_list.html'
    context_object_name = 'registers'


class CashRegisterCreateView(LoginRequiredMixin, CreateView):
    model = CashRegister
    form_class = CashRegisterForm
    template_name = 'cash_register/register_form.html'
    success_url = reverse_lazy('cash_register:register_list')

    def form_valid(self, form):
        messages.success(self.request, 'Caja creada exitosamente.')
        return super().form_valid(form)


class CashRegisterUpdateView(LoginRequiredMixin, UpdateView):
    model = CashRegister
    form_class = CashRegisterForm
    template_name = 'cash_register/register_form.html'
    success_url = reverse_lazy('cash_register:register_list')

    def form_valid(self, form):
        messages.success(self.request, 'Caja actualizada.')
        return super().form_valid(form)


class CashRegisterDeleteView(LoginRequiredMixin, DeleteView):
    model = CashRegister
    template_name = 'cash_register/register_confirm_delete.html'
    success_url = reverse_lazy('cash_register:register_list')

    def form_valid(self, form):
        if self.object.sessions.filter(status='OPEN').exists():
            messages.error(self.request, 'No se puede eliminar una caja con sesión abierta.')
            return redirect(self.success_url)
        messages.success(self.request, f'Caja "{self.object.name}" eliminada.')
        return super().form_valid(form)


@role_required('cash_register')
def daily_sales_report(request):
    from django.db.models import Count
    date_str = request.GET.get('date')
    if date_str:
        from datetime import datetime
        try:
            report_date = datetime.strptime(date_str, '%Y-%m-%d').date()
        except ValueError:
            report_date = timezone.now().date()
    else:
        report_date = timezone.now().date()

    payments = Payment.objects.filter(
        created_at__date=report_date
    ).select_related('order', 'session__cash_register')

    total_amount = payments.aggregate(total=Sum('amount'))['total'] or Decimal('0')
    total_orders = payments.values('order').distinct().count()

    by_method = {}
    for method_code, method_name in Payment.PAYMENT_METHODS:
        total = payments.filter(payment_method=method_code).aggregate(
            total=Sum('amount')
        )['total'] or Decimal('0')
        count = payments.filter(payment_method=method_code).count()
        if total > 0 or count > 0:
            by_method[method_name] = {'total': total, 'count': count}

    by_session = {}
    for payment in payments:
        session_key = str(payment.session)
        if session_key not in by_session:
            by_session[session_key] = Decimal('0')
        by_session[session_key] += payment.amount

    context = {
        'report_date': report_date,
        'payments': payments,
        'total_amount': total_amount,
        'total_orders': total_orders,
        'by_method': by_method,
        'by_session': by_session,
    }
    return render(request, 'cash_register/daily_report.html', context)
