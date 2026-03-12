from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import ListView, CreateView, UpdateView, DeleteView, DetailView
from django.urls import reverse_lazy
from django.contrib import messages
from django.db.models import Q, Sum
from django.utils import timezone
from .models import Ingredient, IngredientCategory, StockMovement, Supplier, PurchaseOrder, PurchaseOrderItem
from .forms import IngredientForm, StockMovementForm, SupplierForm, PurchaseOrderForm, PurchaseOrderItemFormSet


@login_required
def inventory_dashboard(request):
    ingredients = Ingredient.objects.filter(active=True).select_related('category', 'supplier')
    low_stock = [i for i in ingredients if i.is_low_stock]
    recent_movements = StockMovement.objects.select_related('ingredient', 'created_by').order_by('-created_at')[:10]
    pending_orders = PurchaseOrder.objects.filter(status__in=['PENDING', 'ORDERED']).select_related('supplier')
    total_stock_value = sum(i.stock_value for i in ingredients)

    context = {
        'ingredients': ingredients,
        'low_stock': low_stock,
        'low_stock_count': len(low_stock),
        'recent_movements': recent_movements,
        'pending_orders': pending_orders,
        'total_stock_value': total_stock_value,
        'total_ingredients': ingredients.count(),
    }
    return render(request, 'inventory/dashboard.html', context)


class IngredientListView(LoginRequiredMixin, ListView):
    model = Ingredient
    template_name = 'inventory/ingredient_list.html'
    context_object_name = 'ingredients'

    def get_queryset(self):
        queryset = Ingredient.objects.filter(active=True).select_related('category', 'supplier')
        search = self.request.GET.get('search')
        category = self.request.GET.get('category')
        if search:
            queryset = queryset.filter(Q(name__icontains=search))
        if category:
            queryset = queryset.filter(category_id=category)
        return queryset

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['categories'] = IngredientCategory.objects.all()
        ctx['search'] = self.request.GET.get('search', '')
        ctx['selected_category'] = self.request.GET.get('category', '')
        return ctx


class IngredientCreateView(LoginRequiredMixin, CreateView):
    model = Ingredient
    form_class = IngredientForm
    template_name = 'inventory/ingredient_form.html'
    success_url = reverse_lazy('inventory:ingredient_list')

    def form_valid(self, form):
        messages.success(self.request, 'Ingrediente creado exitosamente.')
        return super().form_valid(form)


class IngredientUpdateView(LoginRequiredMixin, UpdateView):
    model = Ingredient
    form_class = IngredientForm
    template_name = 'inventory/ingredient_form.html'
    success_url = reverse_lazy('inventory:ingredient_list')

    def form_valid(self, form):
        messages.success(self.request, 'Ingrediente actualizado exitosamente.')
        return super().form_valid(form)


class IngredientDeleteView(LoginRequiredMixin, DeleteView):
    model = Ingredient
    template_name = 'inventory/ingredient_confirm_delete.html'
    success_url = reverse_lazy('inventory:ingredient_list')

    def form_valid(self, form):
        self.object.active = False
        self.object.save()
        messages.success(self.request, 'Ingrediente desactivado.')
        return redirect(self.success_url)


class StockMovementListView(LoginRequiredMixin, ListView):
    model = StockMovement
    template_name = 'inventory/stock_movement_list.html'
    context_object_name = 'movements'
    paginate_by = 20

    def get_queryset(self):
        queryset = StockMovement.objects.select_related('ingredient', 'created_by').order_by('-created_at')
        ingredient_id = self.request.GET.get('ingredient')
        movement_type = self.request.GET.get('type')
        if ingredient_id:
            queryset = queryset.filter(ingredient_id=ingredient_id)
        if movement_type:
            queryset = queryset.filter(movement_type=movement_type)
        return queryset

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['ingredients'] = Ingredient.objects.filter(active=True)
        ctx['movement_types'] = StockMovement.MOVEMENT_TYPES
        return ctx


class StockMovementCreateView(LoginRequiredMixin, CreateView):
    model = StockMovement
    form_class = StockMovementForm
    template_name = 'inventory/stock_movement_form.html'
    success_url = reverse_lazy('inventory:stock_movement_list')

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        ingredient_id = self.request.GET.get('ingredient')
        if ingredient_id:
            kwargs['initial'] = {'ingredient': ingredient_id}
        return kwargs

    def form_valid(self, form):
        form.instance.created_by = self.request.user
        messages.success(self.request, 'Movimiento de stock registrado.')
        return super().form_valid(form)


class SupplierListView(LoginRequiredMixin, ListView):
    model = Supplier
    template_name = 'inventory/supplier_list.html'
    context_object_name = 'suppliers'

    def get_queryset(self):
        return Supplier.objects.filter(active=True).order_by('name')


class SupplierCreateView(LoginRequiredMixin, CreateView):
    model = Supplier
    form_class = SupplierForm
    template_name = 'inventory/supplier_form.html'
    success_url = reverse_lazy('inventory:supplier_list')

    def form_valid(self, form):
        messages.success(self.request, 'Proveedor creado exitosamente.')
        return super().form_valid(form)


class SupplierUpdateView(LoginRequiredMixin, UpdateView):
    model = Supplier
    form_class = SupplierForm
    template_name = 'inventory/supplier_form.html'
    success_url = reverse_lazy('inventory:supplier_list')

    def form_valid(self, form):
        messages.success(self.request, 'Proveedor actualizado exitosamente.')
        return super().form_valid(form)


class PurchaseOrderListView(LoginRequiredMixin, ListView):
    model = PurchaseOrder
    template_name = 'inventory/purchase_order_list.html'
    context_object_name = 'orders'
    paginate_by = 20

    def get_queryset(self):
        return PurchaseOrder.objects.select_related('supplier', 'created_by').order_by('-created_at')


class PurchaseOrderCreateView(LoginRequiredMixin, CreateView):
    model = PurchaseOrder
    form_class = PurchaseOrderForm
    template_name = 'inventory/purchase_order_form.html'
    success_url = reverse_lazy('inventory:purchase_order_list')

    def form_valid(self, form):
        form.instance.created_by = self.request.user
        response = super().form_valid(form)
        messages.success(self.request, 'Orden de compra creada.')
        return response


class PurchaseOrderDetailView(LoginRequiredMixin, DetailView):
    model = PurchaseOrder
    template_name = 'inventory/purchase_order_detail.html'
    context_object_name = 'order'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['items'] = self.object.items.select_related('ingredient').all()
        return ctx


@login_required
def receive_purchase_order(request, pk):
    order = get_object_or_404(PurchaseOrder, pk=pk)
    if request.method == 'POST':
        if order.status not in ('ORDERED', 'PENDING'):
            messages.error(request, 'Esta orden ya fue procesada.')
            return redirect('inventory:purchase_order_detail', pk=pk)

        for item in order.items.all():
            received_qty_str = request.POST.get(f'received_{item.pk}', '0')
            try:
                received_qty = float(received_qty_str)
                if received_qty > 0:
                    item.quantity_received = received_qty
                    item.save()
                    # Create stock movement
                    StockMovement.objects.create(
                        ingredient=item.ingredient,
                        movement_type='IN',
                        quantity=received_qty,
                        unit_cost=item.unit_cost,
                        reason=f'Recepcion OC #{order.pk}',
                        reference=str(order.pk),
                        created_by=request.user
                    )
            except (ValueError, TypeError):
                pass

        order.status = 'RECEIVED'
        order.save()
        messages.success(request, 'Orden recibida y stock actualizado.')
        return redirect('inventory:purchase_order_detail', pk=pk)

    return render(request, 'inventory/receive_purchase_order.html', {'order': order})


@login_required
def low_stock_alert(request):
    ingredients = Ingredient.objects.filter(active=True)
    low_stock = [i for i in ingredients if i.is_low_stock]
    return render(request, 'inventory/low_stock_alert.html', {'low_stock': low_stock})
