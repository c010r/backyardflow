from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from menu.models import MenuCategory, MenuItem
from tables.models import Table
from orders.models import VirtualWaiterSession
import uuid


def public_menu(request):
    """Public-facing full menu, no auth required"""
    categories = MenuCategory.objects.filter(active=True).prefetch_related(
        'items'
    ).order_by('display_order')

    available_categories = []
    for cat in categories:
        items = cat.items.filter(active=True, available=True).order_by('display_order', 'name')
        if items.exists():
            available_categories.append({
                'category': cat,
                'items': items,
            })

    featured_items = MenuItem.objects.filter(
        active=True, available=True, featured=True
    ).select_related('category')

    context = {
        'categories': available_categories,
        'featured_items': featured_items,
    }
    return render(request, 'qr_menu/public_menu.html', context)


def table_menu(request, table_pk):
    """Table-specific menu via QR code, allows adding to order"""
    table = get_object_or_404(Table, pk=table_pk, active=True)

    # Create or get virtual session
    session = VirtualWaiterSession.objects.filter(
        table=table, active=True
    ).first()

    if not session:
        session = VirtualWaiterSession.objects.create(
            table=table,
            session_token=uuid.uuid4()
        )

    categories = MenuCategory.objects.filter(active=True).prefetch_related('items')
    available_categories = []
    for cat in categories:
        items = cat.items.filter(active=True, available=True).order_by('display_order')
        if items.exists():
            available_categories.append({'category': cat, 'items': items})

    # Get cart from session
    token = str(session.session_token)
    cart = request.session.get(f'cart_{token}', {})
    cart_items = []
    cart_total = 0
    for item_id_str, qty in cart.items():
        try:
            item = MenuItem.objects.get(pk=int(item_id_str))
            subtotal = item.price * qty
            cart_items.append({'item': item, 'quantity': qty, 'subtotal': subtotal})
            cart_total += subtotal
        except (MenuItem.DoesNotExist, ValueError):
            pass

    context = {
        'table': table,
        'session': session,
        'categories': available_categories,
        'cart_items': cart_items,
        'cart_total': cart_total,
        'token': token,
    }
    return render(request, 'qr_menu/table_menu.html', context)


@login_required
def menu_qr_codes(request):
    """Admin view to show printable QR codes for all tables"""
    tables = Table.objects.filter(active=True).select_related('area').order_by('area__name', 'number')

    # Generate QR codes for tables that don't have one
    for table in tables:
        if not table.qr_code:
            table.generate_qr()

    context = {
        'tables': tables,
    }
    return render(request, 'qr_menu/qr_codes.html', context)
