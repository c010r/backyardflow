"""Main dashboard view for BackyardFlow POS"""
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from decimal import Decimal


@login_required
def dashboard(request):
    from tables.models import Table
    from orders.models import Order
    from inventory.models import Ingredient
    from cash_register.models import CashSession
    from staff.models import StaffMember

    # Open tables count
    open_tables = Table.objects.filter(status='OCCUPIED', active=True).count()
    free_tables = Table.objects.filter(status='FREE', active=True).count()
    total_tables = Table.objects.filter(active=True).count()

    # Pending orders
    pending_orders = Order.objects.filter(
        status__in=['PENDING', 'IN_PROGRESS', 'READY']
    ).count()

    # Recent orders
    recent_orders = Order.objects.filter(
        status__in=['PENDING', 'IN_PROGRESS', 'READY', 'DELIVERED']
    ).order_by('-created_at')[:5]

    # Low stock items
    low_stock = Ingredient.objects.filter(active=True).extra(
        where=['stock_quantity <= min_stock']
    ).count()

    # Today's sales
    today = timezone.now().date()
    from cash_register.models import Payment
    today_payments = Payment.objects.filter(created_at__date=today)
    today_sales = sum(p.amount for p in today_payments) if today_payments.exists() else Decimal('0')

    # Active cash session
    active_session = CashSession.objects.filter(status='OPEN').first()

    # Staff count
    total_staff = StaffMember.objects.filter(active=True).count()

    context = {
        'open_tables': open_tables,
        'free_tables': free_tables,
        'total_tables': total_tables,
        'pending_orders': pending_orders,
        'recent_orders': recent_orders,
        'low_stock': low_stock,
        'today_sales': today_sales,
        'active_session': active_session,
        'total_staff': total_staff,
        'today': today,
    }
    return render(request, 'dashboard.html', context)
