"""Main dashboard view for BackyardFlow POS"""
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from decimal import Decimal
from .roles import get_role


@login_required
def dashboard(request):
    role = get_role(request.user)

    # Roles sin dashboard general → redirigir directo a su pantalla
    if role == 'CHEF':
        return redirect('/orders/kitchen/')
    if role == 'BARTENDER':
        return redirect('/orders/kitchen/')
    if role == 'CLEANER':
        return redirect('/tables/')
    if role == 'CASHIER':
        return redirect('/cash-register/')

    # WAITER → dashboard simplificado
    if role == 'WAITER':
        from tables.models import Table
        from orders.models import Order
        tables = Table.objects.filter(active=True).order_by('number')
        my_orders = Order.objects.filter(
            waiter=request.user,
            status__in=['PENDING', 'IN_PROGRESS', 'READY', 'DELIVERED']
        ).order_by('-created_at')[:10]
        return render(request, 'dashboard_waiter.html', {
            'tables': tables,
            'my_orders': my_orders,
        })

    # MANAGER / admin → dashboard completo
    from tables.models import Table
    from orders.models import Order
    from inventory.models import Ingredient
    from cash_register.models import CashSession, Payment
    from staff.models import StaffMember

    open_tables   = Table.objects.filter(status='OCCUPIED', active=True).count()
    free_tables   = Table.objects.filter(status='FREE', active=True).count()
    total_tables  = Table.objects.filter(active=True).count()

    pending_orders = Order.objects.filter(
        status__in=['PENDING', 'IN_PROGRESS', 'READY']
    ).count()
    recent_orders = Order.objects.filter(
        status__in=['PENDING', 'IN_PROGRESS', 'READY', 'DELIVERED']
    ).order_by('-created_at')[:5]

    low_stock = Ingredient.objects.filter(active=True).extra(
        where=['stock_quantity <= min_stock']
    ).count()

    today = timezone.now().date()
    today_payments = Payment.objects.filter(created_at__date=today)
    today_sales = sum(p.amount for p in today_payments) if today_payments.exists() else Decimal('0')

    active_session = CashSession.objects.filter(status='OPEN').first()
    total_staff    = StaffMember.objects.filter(active=True).count()

    return render(request, 'dashboard.html', {
        'open_tables':    open_tables,
        'free_tables':    free_tables,
        'total_tables':   total_tables,
        'pending_orders': pending_orders,
        'recent_orders':  recent_orders,
        'low_stock':      low_stock,
        'today_sales':    today_sales,
        'active_session': active_session,
        'total_staff':    total_staff,
        'today':          today,
    })
