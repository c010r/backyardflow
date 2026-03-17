from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from backyardflow.roles import role_required
from django.views.generic import ListView, CreateView, DetailView
from django.urls import reverse_lazy
from django.contrib import messages
from django.http import JsonResponse
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.db.models import Sum, Count
from decimal import Decimal
import json
from .models import Order, OrderItem, VirtualWaiterSession
from .forms import OrderForm, OrderItemForm
from menu.models import MenuItem, MenuCategory
from tables.models import Table


@role_required('orders')
def orders_dashboard(request):
    active_orders = Order.objects.filter(
        status__in=['PENDING', 'IN_PROGRESS', 'READY', 'DELIVERED']
    ).select_related('table', 'waiter').prefetch_related('items__menu_item').order_by('created_at')

    pending_count = active_orders.filter(status='PENDING').count()
    in_progress_count = active_orders.filter(status='IN_PROGRESS').count()
    ready_count = active_orders.filter(status='READY').count()

    context = {
        'active_orders': active_orders,
        'pending_count': pending_count,
        'in_progress_count': in_progress_count,
        'ready_count': ready_count,
    }
    return render(request, 'orders/dashboard.html', context)


class OrderListView(LoginRequiredMixin, ListView):
    model = Order
    template_name = 'orders/order_list.html'
    context_object_name = 'orders'
    paginate_by = 20

    def get_queryset(self):
        queryset = Order.objects.select_related('table', 'waiter').order_by('-created_at')
        status = self.request.GET.get('status')
        date = self.request.GET.get('date')
        if status:
            queryset = queryset.filter(status=status)
        if date:
            queryset = queryset.filter(created_at__date=date)
        return queryset

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['statuses'] = Order.STATUS_CHOICES
        ctx['today'] = timezone.now().date()
        return ctx


class OrderDetailView(LoginRequiredMixin, DetailView):
    model = Order
    template_name = 'orders/order_detail.html'
    context_object_name = 'order'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['items'] = self.object.items.select_related('menu_item').all()
        ctx['menu_items'] = MenuItem.objects.filter(active=True, available=True).select_related('category')
        ctx['categories'] = MenuCategory.objects.filter(active=True)
        return ctx


@role_required('orders')
def order_create(request):
    if request.method == 'POST':
        form = OrderForm(request.POST)
        if form.is_valid():
            order = form.save(commit=False)
            if form.cleaned_data.get('waiter_type') == 'HUMAN':
                order.waiter = request.user
            order.save()

            # Mark table as occupied if dine-in
            if order.table and order.order_type == 'DINE_IN':
                order.table.status = 'OCCUPIED'
                order.table.save()

            messages.success(request, f'Comanda {order.order_number} creada.')
            return redirect('orders:order_detail', pk=order.pk)
    else:
        form = OrderForm()

    # Pre-select table if provided
    table_id = request.GET.get('table')
    if table_id:
        form.initial['table'] = table_id

    return render(request, 'orders/order_form.html', {'form': form})


@role_required('orders')
def add_item_to_order(request, order_pk):
    if request.method == 'POST':
        order = get_object_or_404(Order, pk=order_pk)
        if order.status in ('PAID', 'CANCELLED'):
            return JsonResponse({'success': False, 'error': 'Comanda cerrada'}, status=400)

        menu_item_id = request.POST.get('menu_item_id')
        quantity = int(request.POST.get('quantity', 1))
        notes = request.POST.get('notes', '')

        menu_item = get_object_or_404(MenuItem, pk=menu_item_id)

        # Check if item already in order
        existing = order.items.filter(menu_item=menu_item, status='PENDING').first()
        if existing:
            existing.quantity += quantity
            existing.save()
            item = existing
        else:
            item = OrderItem.objects.create(
                order=order,
                menu_item=menu_item,
                quantity=quantity,
                unit_price=menu_item.price,
                notes=notes,
                sent_to_kitchen_at=timezone.now()
            )

        # Update order status
        if order.status == 'PENDING':
            order.status = 'IN_PROGRESS'
            order.save()

        return JsonResponse({
            'success': True,
            'item_id': item.pk,
            'item_name': menu_item.name,
            'quantity': item.quantity,
            'unit_price': str(item.unit_price),
            'subtotal': str(item.subtotal),
            'order_total': str(order.total),
        })
    return JsonResponse({'success': False}, status=400)


@role_required('orders')
def remove_item_from_order(request, order_pk, item_pk):
    if request.method == 'POST':
        order = get_object_or_404(Order, pk=order_pk)
        item = get_object_or_404(OrderItem, pk=item_pk, order=order)
        item.status = 'CANCELLED'
        item.save()
        return JsonResponse({
            'success': True,
            'order_total': str(order.total)
        })
    return JsonResponse({'success': False}, status=400)


@role_required('orders')
def update_item_quantity(request, order_pk, item_pk):
    if request.method == 'POST':
        order = get_object_or_404(Order, pk=order_pk)
        item = get_object_or_404(OrderItem, pk=item_pk, order=order)
        quantity = int(request.POST.get('quantity', 1))
        if quantity <= 0:
            item.status = 'CANCELLED'
        else:
            item.quantity = quantity
        item.save()
        return JsonResponse({
            'success': True,
            'quantity': item.quantity,
            'subtotal': str(item.subtotal),
            'order_total': str(order.total)
        })
    return JsonResponse({'success': False}, status=400)


@role_required('orders')
def update_order_status(request, pk):
    if request.method == 'POST':
        order = get_object_or_404(Order, pk=pk)
        new_status = request.POST.get('status')
        valid_statuses = [s[0] for s in Order.STATUS_CHOICES]
        if new_status in valid_statuses:
            order.status = new_status
            if new_status in ('PAID', 'CANCELLED'):
                order.closed_at = timezone.now()
                # Free the table
                if order.table:
                    # Check if table has other active orders
                    other_orders = Order.objects.filter(
                        table=order.table,
                        status__in=['PENDING', 'IN_PROGRESS', 'READY', 'DELIVERED']
                    ).exclude(pk=order.pk).exists()
                    if not other_orders:
                        order.table.status = 'FREE'
                        order.table.save()
            order.save()
            return JsonResponse({'success': True, 'status': order.status, 'status_display': order.get_status_display()})
    return JsonResponse({'success': False}, status=400)


@role_required('kitchen', 'orders')
def update_item_status(request, item_pk):
    if request.method == 'POST':
        item = get_object_or_404(OrderItem, pk=item_pk)
        new_status = request.POST.get('status')
        valid_statuses = [s[0] for s in OrderItem.STATUS_CHOICES]
        if new_status in valid_statuses:
            item.status = new_status
            if new_status == 'READY':
                item.ready_at = timezone.now()
            item.save()
            return JsonResponse({'success': True, 'status': item.status})
    return JsonResponse({'success': False}, status=400)


@role_required('kitchen')
def kitchen_display(request):
    items = OrderItem.objects.filter(
        status__in=['PENDING', 'PREPARING']
    ).select_related('order__table', 'menu_item').order_by('sent_to_kitchen_at')

    orders_with_items = {}
    for item in items:
        order = item.order
        if order.pk not in orders_with_items:
            orders_with_items[order.pk] = {
                'order': order,
                'items': []
            }
        orders_with_items[order.pk]['items'].append(item)

    context = {
        'orders_with_items': list(orders_with_items.values()),
        'total_pending': items.filter(status='PENDING').count(),
        'total_preparing': items.filter(status='PREPARING').count(),
    }
    return render(request, 'orders/kitchen_display.html', context)


@role_required('orders', 'cash_register')
def close_order(request, pk):
    order = get_object_or_404(Order, pk=pk)
    if request.method == 'POST':
        order.status = 'DELIVERED'
        order.save()
        messages.success(request, f'Comanda {order.order_number} lista para cobrar.')
        return redirect('cash_register:process_payment', order_pk=order.pk)
    return render(request, 'orders/close_order_confirm.html', {'order': order})


def virtual_waiter_menu(request, token):
    """Customer-facing menu via QR code - no auth required"""
    session = get_object_or_404(VirtualWaiterSession, session_token=token, active=True)
    table = session.table
    categories = MenuCategory.objects.filter(active=True).prefetch_related(
        'items'
    )
    available_categories = []
    for cat in categories:
        items = cat.items.filter(active=True, available=True)
        if items.exists():
            available_categories.append({'category': cat, 'items': items})

    cart = request.session.get(f'cart_{token}', {})
    cart_items = []
    cart_total = 0
    for item_id, qty in cart.items():
        try:
            item = MenuItem.objects.get(pk=item_id)
            subtotal = item.price * qty
            cart_items.append({'item': item, 'quantity': qty, 'subtotal': subtotal})
            cart_total += subtotal
        except MenuItem.DoesNotExist:
            pass

    context = {
        'session': session,
        'table': table,
        'categories': available_categories,
        'cart_items': cart_items,
        'cart_total': cart_total,
    }
    return render(request, 'orders/virtual_menu.html', context)


def virtual_waiter_order(request, token):
    """Customer places order via QR"""
    session = get_object_or_404(VirtualWaiterSession, session_token=token, active=True)

    if request.method == 'POST':
        action = request.POST.get('action')

        if action == 'add_to_cart':
            item_id = request.POST.get('item_id')
            qty = int(request.POST.get('quantity', 1))
            cart = request.session.get(f'cart_{token}', {})
            cart[item_id] = cart.get(item_id, 0) + qty
            request.session[f'cart_{token}'] = cart
            return JsonResponse({'success': True, 'cart_count': sum(cart.values())})

        elif action == 'remove_from_cart':
            item_id = request.POST.get('item_id')
            cart = request.session.get(f'cart_{token}', {})
            if item_id in cart:
                del cart[item_id]
            request.session[f'cart_{token}'] = cart
            return JsonResponse({'success': True})

        elif action == 'place_order':
            cart = request.session.get(f'cart_{token}', {})
            if not cart:
                return JsonResponse({'success': False, 'error': 'Carrito vacio'})

            # Create or get existing order
            if session.order and session.order.status not in ('PAID', 'CANCELLED'):
                order = session.order
            else:
                order = Order.objects.create(
                    table=session.table,
                    order_type='DINE_IN',
                    waiter_type='VIRTUAL',
                    status='PENDING'
                )
                session.order = order
                session.save()
                # Mark table occupied
                session.table.status = 'OCCUPIED'
                session.table.save()

            # Add items to order
            for item_id, qty in cart.items():
                try:
                    menu_item = MenuItem.objects.get(pk=item_id, available=True)
                    OrderItem.objects.create(
                        order=order,
                        menu_item=menu_item,
                        quantity=qty,
                        unit_price=menu_item.price,
                        sent_to_kitchen_at=timezone.now()
                    )
                except MenuItem.DoesNotExist:
                    pass

            # Clear cart
            request.session[f'cart_{token}'] = {}
            order.status = 'IN_PROGRESS'
            order.save()

            return JsonResponse({'success': True, 'order_number': order.order_number})

    return redirect('orders:virtual_waiter_menu', token=token)


# ─────────────────────────────────────────────
#  BAR EVENT POS
# ─────────────────────────────────────────────

@role_required('orders')
def bar_event_pos(request):
    categories = MenuCategory.objects.filter(active=True).order_by('order')
    menu_items = (MenuItem.objects
                  .filter(available=True)
                  .select_related('category')
                  .order_by('category__order', 'name'))
    open_tabs = (Order.objects
                 .filter(
                     status__in=['PENDING', 'IN_PROGRESS', 'READY', 'DELIVERED'],
                     table__isnull=True,
                     created_at__date=timezone.now().date(),
                 )
                 .prefetch_related('items__menu_item')
                 .order_by('created_at'))
    context = {
        'categories': categories,
        'menu_items': menu_items,
        'open_tabs': open_tabs,
    }
    return render(request, 'orders/bar_event.html', context)


@role_required('orders')
def bar_event_new_tab(request):
    if request.method != 'POST':
        return JsonResponse({'success': False}, status=405)
    label = request.POST.get('label', '').strip() or f"Tab {timezone.now().strftime('%H:%M:%S')}"
    order = Order.objects.create(
        order_type='TAKEOUT',
        waiter=request.user,
        status='PENDING',
        notes=label,
    )
    return JsonResponse({
        'success': True,
        'tab_id': order.pk,
        'tab_number': order.order_number,
        'label': label,
    })


@role_required('orders')
def bar_event_add_item(request, order_pk):
    if request.method != 'POST':
        return JsonResponse({'success': False}, status=405)
    order = get_object_or_404(Order, pk=order_pk)
    if order.status in ('PAID', 'CANCELLED'):
        return JsonResponse({'success': False, 'error': 'Tab cerrado'}, status=400)
    menu_item_id = request.POST.get('menu_item_id')
    quantity = int(request.POST.get('quantity', 1))
    menu_item = get_object_or_404(MenuItem, pk=menu_item_id)
    existing = order.items.filter(menu_item=menu_item, status='PENDING').first()
    if existing:
        existing.quantity += quantity
        existing.save()
        item = existing
    else:
        item = OrderItem.objects.create(
            order=order,
            menu_item=menu_item,
            quantity=quantity,
            unit_price=menu_item.price,
            sent_to_kitchen_at=timezone.now(),
        )
    if order.status == 'PENDING':
        order.status = 'IN_PROGRESS'
        order.save()
    cart_items = _order_cart(order)
    return JsonResponse({'success': True, 'cart': cart_items, 'order_total': str(order.total)})


@role_required('orders')
def bar_event_remove_item(request, order_pk, item_pk):
    if request.method != 'POST':
        return JsonResponse({'success': False}, status=405)
    order = get_object_or_404(Order, pk=order_pk)
    item = get_object_or_404(OrderItem, pk=item_pk, order=order)
    item.status = 'CANCELLED'
    item.save()
    cart_items = _order_cart(order)
    return JsonResponse({'success': True, 'cart': cart_items, 'order_total': str(order.total)})


@role_required('orders')
def bar_event_checkout(request, order_pk):
    if request.method != 'POST':
        return JsonResponse({'success': False}, status=405)
    order = get_object_or_404(Order, pk=order_pk)
    if order.status == 'PAID':
        return JsonResponse({'success': False, 'error': 'Ya cobrado'}, status=400)
    payment_method = request.POST.get('payment_method', 'CASH')
    amount_received = request.POST.get('amount_received')
    discount = Decimal(request.POST.get('discount', '0'))
    if discount > 0:
        order.discount_percent = min(discount, Decimal('100'))
        order.save()
    total = order.total
    change = Decimal('0')
    if payment_method == 'CASH' and amount_received:
        received = Decimal(amount_received)
        change = max(received - total, Decimal('0'))
    try:
        from cash_register.models import CashSession, CashMovement, Payment
        active_session = (CashSession.objects.filter(status='OPEN', operator=request.user).first()
                          or CashSession.objects.filter(status='OPEN').first())
        if active_session:
            Payment.objects.create(
                order=order,
                session=active_session,
                payment_method=payment_method,
                amount=total,
                amount_received=Decimal(amount_received) if amount_received else total,
                change_given=change,
                created_by=request.user,
            )
            CashMovement.objects.create(
                session=active_session,
                movement_type='SALE',
                amount=total,
                description=f'Venta barra {order.order_number}',
                reference=order.order_number,
                created_by=request.user,
            )
            order.cash_session = active_session
    except Exception:
        pass
    order.status = 'PAID'
    order.closed_at = timezone.now()
    order.save()
    return JsonResponse({'success': True, 'order_number': order.order_number, 'total': str(total), 'change': str(change)})


@role_required('orders')
def bar_event_tab_detail(request, order_pk):
    order = get_object_or_404(Order, pk=order_pk)
    return JsonResponse({
        'success': True,
        'tab_id': order.pk,
        'tab_number': order.order_number,
        'label': order.notes or order.order_number,
        'cart': _order_cart(order),
        'order_total': str(order.total),
        'status': order.status,
    })


@role_required('orders')
def bar_event_stats(request):
    today = timezone.now().date()
    paid = Order.objects.filter(status='PAID', closed_at__date=today)
    total_sales = (paid.aggregate(t=Sum('items__unit_price'))['t'] or Decimal('0'))
    top_items = (OrderItem.objects
                 .filter(order__status='PAID', order__closed_at__date=today, status='PENDING')
                 .values('menu_item__name')
                 .annotate(total_qty=Sum('quantity'))
                 .order_by('-total_qty')[:5])
    open_count = Order.objects.filter(
        status__in=['PENDING', 'IN_PROGRESS'],
        table__isnull=True,
        created_at__date=today,
    ).count()
    return JsonResponse({
        'total_sales': str(total_sales),
        'paid_orders': paid.count(),
        'open_tabs': open_count,
        'top_items': list(top_items),
    })


def _order_cart(order):
    return [
        {
            'id': i.pk,
            'name': i.menu_item.name,
            'qty': i.quantity,
            'unit_price': str(i.unit_price),
            'subtotal': str(i.subtotal),
        }
        for i in order.items.filter(status='PENDING').select_related('menu_item')
    ]
