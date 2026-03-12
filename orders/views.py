from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import ListView, CreateView, DetailView
from django.urls import reverse_lazy
from django.contrib import messages
from django.http import JsonResponse
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
import json
from .models import Order, OrderItem, VirtualWaiterSession
from .forms import OrderForm, OrderItemForm
from menu.models import MenuItem, MenuCategory
from tables.models import Table


@login_required
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


@login_required
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


@login_required
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


@login_required
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


@login_required
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


@login_required
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


@login_required
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


@login_required
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


@login_required
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
