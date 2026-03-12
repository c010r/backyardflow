from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import ListView, CreateView, UpdateView, DeleteView, DetailView
from django.urls import reverse_lazy
from django.contrib import messages
from django.db.models import Q
from .models import MenuItem, MenuCategory, Recipe, RecipeIngredient
from .forms import MenuItemForm, MenuCategoryForm, RecipeForm, RecipeIngredientFormSet


@login_required
def menu_dashboard(request):
    items = MenuItem.objects.filter(active=True).select_related('category')
    categories = MenuCategory.objects.filter(active=True)
    featured = items.filter(featured=True)

    # Profitability analysis
    profitable_items = []
    for item in items:
        cost = item.cost
        if cost > 0:
            margin = item.profit_margin
            profitable_items.append({
                'item': item,
                'cost': cost,
                'margin': margin,
                'profit': item.gross_profit
            })

    profitable_items.sort(key=lambda x: x['margin'], reverse=True)

    context = {
        'items': items,
        'categories': categories,
        'featured': featured,
        'profitable_items': profitable_items[:10],
        'total_items': items.count(),
        'available_items': items.filter(available=True).count(),
    }
    return render(request, 'menu/dashboard.html', context)


class MenuItemListView(LoginRequiredMixin, ListView):
    model = MenuItem
    template_name = 'menu/item_list.html'
    context_object_name = 'items'

    def get_queryset(self):
        queryset = MenuItem.objects.filter(active=True).select_related('category')
        search = self.request.GET.get('search')
        category = self.request.GET.get('category')
        item_type = self.request.GET.get('type')
        if search:
            queryset = queryset.filter(Q(name__icontains=search) | Q(description__icontains=search))
        if category:
            queryset = queryset.filter(category_id=category)
        if item_type:
            queryset = queryset.filter(item_type=item_type)
        return queryset

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['categories'] = MenuCategory.objects.filter(active=True)
        ctx['item_types'] = MenuItem.ITEM_TYPES
        ctx['search'] = self.request.GET.get('search', '')
        return ctx


class MenuItemCreateView(LoginRequiredMixin, CreateView):
    model = MenuItem
    form_class = MenuItemForm
    template_name = 'menu/item_form.html'
    success_url = reverse_lazy('menu:item_list')

    def form_valid(self, form):
        messages.success(self.request, 'Item del menu creado exitosamente.')
        return super().form_valid(form)


class MenuItemUpdateView(LoginRequiredMixin, UpdateView):
    model = MenuItem
    form_class = MenuItemForm
    template_name = 'menu/item_form.html'
    success_url = reverse_lazy('menu:item_list')

    def form_valid(self, form):
        messages.success(self.request, 'Item del menu actualizado.')
        return super().form_valid(form)


class MenuItemDeleteView(LoginRequiredMixin, DeleteView):
    model = MenuItem
    template_name = 'menu/item_confirm_delete.html'
    success_url = reverse_lazy('menu:item_list')

    def form_valid(self, form):
        self.object.active = False
        self.object.save()
        messages.success(self.request, 'Item desactivado.')
        return redirect(self.success_url)


class MenuCategoryListView(LoginRequiredMixin, ListView):
    model = MenuCategory
    template_name = 'menu/category_list.html'
    context_object_name = 'categories'

    def get_queryset(self):
        return MenuCategory.objects.all().order_by('display_order', 'name')


class MenuCategoryCreateView(LoginRequiredMixin, CreateView):
    model = MenuCategory
    form_class = MenuCategoryForm
    template_name = 'menu/category_form.html'
    success_url = reverse_lazy('menu:category_list')

    def form_valid(self, form):
        messages.success(self.request, 'Categoria creada exitosamente.')
        return super().form_valid(form)


class MenuCategoryUpdateView(LoginRequiredMixin, UpdateView):
    model = MenuCategory
    form_class = MenuCategoryForm
    template_name = 'menu/category_form.html'
    success_url = reverse_lazy('menu:category_list')

    def form_valid(self, form):
        messages.success(self.request, 'Categoria actualizada.')
        return super().form_valid(form)


class RecipeDetailView(LoginRequiredMixin, DetailView):
    model = Recipe
    template_name = 'menu/recipe_detail.html'
    context_object_name = 'recipe'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['ingredients'] = self.object.ingredients.select_related('ingredient').all()
        ctx['total_cost'] = self.object.total_cost
        return ctx


@login_required
def recipe_create(request, item_pk):
    menu_item = get_object_or_404(MenuItem, pk=item_pk)

    # Check if recipe already exists
    if hasattr(menu_item, 'recipe'):
        return redirect('menu:recipe_update', pk=menu_item.recipe.pk)

    if request.method == 'POST':
        form = RecipeForm(request.POST)
        formset = RecipeIngredientFormSet(request.POST, prefix='ingredients')
        if form.is_valid() and formset.is_valid():
            recipe = form.save(commit=False)
            recipe.menu_item = menu_item
            recipe.save()
            instances = formset.save(commit=False)
            for instance in instances:
                instance.recipe = recipe
                instance.save()
            for obj in formset.deleted_objects:
                obj.delete()
            messages.success(request, 'Receta guardada exitosamente.')
            return redirect('menu:recipe_detail', pk=recipe.pk)
    else:
        form = RecipeForm(initial={'preparation_time': menu_item.preparation_time})
        formset = RecipeIngredientFormSet(prefix='ingredients')

    return render(request, 'menu/recipe_form.html', {
        'form': form,
        'formset': formset,
        'menu_item': menu_item,
        'action': 'Crear'
    })


@login_required
def recipe_update(request, pk):
    recipe = get_object_or_404(Recipe, pk=pk)
    if request.method == 'POST':
        form = RecipeForm(request.POST, instance=recipe)
        formset = RecipeIngredientFormSet(request.POST, instance=recipe, prefix='ingredients')
        if form.is_valid() and formset.is_valid():
            form.save()
            instances = formset.save(commit=False)
            for instance in instances:
                instance.recipe = recipe
                instance.save()
            for obj in formset.deleted_objects:
                obj.delete()
            messages.success(request, 'Receta actualizada exitosamente.')
            return redirect('menu:recipe_detail', pk=recipe.pk)
    else:
        form = RecipeForm(instance=recipe)
        formset = RecipeIngredientFormSet(instance=recipe, prefix='ingredients')

    return render(request, 'menu/recipe_form.html', {
        'form': form,
        'formset': formset,
        'menu_item': recipe.menu_item,
        'recipe': recipe,
        'action': 'Actualizar'
    })
