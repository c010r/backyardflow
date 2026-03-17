from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.models import User
from django.contrib import messages
from django.db.models import Count, Sum
from django.utils import timezone
from .models import SystemSettings
from .forms import UserCreateForm, UserEditForm, ChangePasswordForm, SystemSettingsForm

staff_required = user_passes_test(lambda u: u.is_staff, login_url='/')


@login_required
@staff_required
def dashboard(request):
    from orders.models import Order
    from inventory.models import Ingredient
    from cash_register.models import CashSession, Payment
    from staff.models import StaffMember
    from tables.models import Table
    from menu.models import MenuItem

    today = timezone.now().date()

    stats = {
        'total_users': User.objects.filter(is_active=True).count(),
        'total_staff': StaffMember.objects.filter(active=True).count(),
        'total_tables': Table.objects.filter(active=True).count(),
        'total_menu_items': MenuItem.objects.filter(active=True).count(),
        'total_ingredients': Ingredient.objects.filter(active=True).count(),
        'low_stock': Ingredient.objects.filter(active=True, stock_quantity__lte=models_low_stock()).count(),
        'open_sessions': CashSession.objects.filter(status='OPEN').count(),
        'today_orders': Order.objects.filter(created_at__date=today).count(),
        'today_sales': Payment.objects.filter(created_at__date=today).aggregate(t=Sum('amount'))['t'] or 0,
    }
    users = User.objects.all().order_by('-date_joined')[:10]
    settings_obj = SystemSettings.get()
    return render(request, 'config/dashboard.html', {'stats': stats, 'users': users, 'settings': settings_obj})


def models_low_stock():
    from django.db import connection
    return 0  # placeholder — comparison done in queryset below


@login_required
@staff_required
def user_list(request):
    users = User.objects.all().order_by('username')
    return render(request, 'config/user_list.html', {'users': users})


@login_required
@staff_required
def user_create(request):
    if request.method == 'POST':
        form = UserCreateForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Usuario creado correctamente.')
            return redirect('config:user_list')
    else:
        form = UserCreateForm()
    return render(request, 'config/user_form.html', {'form': form, 'title': 'Nuevo Usuario'})


@login_required
@staff_required
def user_edit(request, pk):
    user = get_object_or_404(User, pk=pk)
    if request.method == 'POST':
        form = UserEditForm(request.POST, instance=user)
        if form.is_valid():
            form.save()
            messages.success(request, 'Usuario actualizado.')
            return redirect('config:user_list')
    else:
        form = UserEditForm(instance=user)
    return render(request, 'config/user_form.html', {'form': form, 'title': f'Editar: {user.username}', 'edit_user': user})


@login_required
@staff_required
def user_change_password(request, pk):
    user = get_object_or_404(User, pk=pk)
    if request.method == 'POST':
        form = ChangePasswordForm(user, request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, f'Contraseña de {user.username} actualizada.')
            return redirect('config:user_list')
    else:
        form = ChangePasswordForm(user)
    return render(request, 'config/user_form.html', {'form': form, 'title': f'Cambiar contraseña: {user.username}', 'edit_user': user})


@login_required
@staff_required
def user_toggle_active(request, pk):
    user = get_object_or_404(User, pk=pk)
    if user == request.user:
        messages.error(request, 'No podés desactivar tu propio usuario.')
    else:
        user.is_active = not user.is_active
        user.save()
        estado = 'activado' if user.is_active else 'desactivado'
        messages.success(request, f'Usuario {user.username} {estado}.')
    return redirect('config:user_list')


@login_required
@staff_required
def user_delete(request, pk):
    user = get_object_or_404(User, pk=pk)
    if user == request.user:
        messages.error(request, 'No podés eliminar tu propio usuario.')
        return redirect('config:user_list')
    if request.method == 'POST':
        username = user.username
        user.delete()
        messages.success(request, f'Usuario {username} eliminado.')
        return redirect('config:user_list')
    return render(request, 'config/user_confirm_delete.html', {'edit_user': user})


@login_required
@staff_required
def system_settings(request):
    settings_obj = SystemSettings.get()
    if request.method == 'POST':
        form = SystemSettingsForm(request.POST, request.FILES, instance=settings_obj)
        if form.is_valid():
            form.save()
            messages.success(request, 'Configuración guardada.')
            return redirect('config:settings')
    else:
        form = SystemSettingsForm(instance=settings_obj)
    return render(request, 'config/settings.html', {'form': form, 'settings': settings_obj})


@login_required
@staff_required
def cash_register_list(request):
    from cash_register.models import CashRegister
    from django.db.models import Q
    registers = CashRegister.objects.annotate(
        open_sessions=Count('sessions', filter=Q(sessions__status='OPEN'))
    ).order_by('name')
    return render(request, 'config/cash_register_list.html', {'registers': registers})


@login_required
@staff_required
def cash_register_create(request):
    from cash_register.forms import CashRegisterForm
    if request.method == 'POST':
        form = CashRegisterForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Caja creada.')
            return redirect('config:cash_register_list')
    else:
        form = CashRegisterForm()
    return render(request, 'config/cash_register_form.html', {'form': form, 'title': 'Nueva Caja'})


@login_required
@staff_required
def cash_register_edit(request, pk):
    from cash_register.models import CashRegister
    from cash_register.forms import CashRegisterForm
    register = get_object_or_404(CashRegister, pk=pk)
    if request.method == 'POST':
        form = CashRegisterForm(request.POST, instance=register)
        if form.is_valid():
            form.save()
            messages.success(request, 'Caja actualizada.')
            return redirect('config:cash_register_list')
    else:
        form = CashRegisterForm(instance=register)
    return render(request, 'config/cash_register_form.html', {'form': form, 'title': f'Editar: {register.name}'})


@login_required
@staff_required
def table_area_list(request):
    from tables.models import TableArea, Table
    areas = TableArea.objects.annotate(table_count=Count('table')).order_by('name')
    return render(request, 'config/table_area_list.html', {'areas': areas})


@login_required
@staff_required
def table_area_create(request):
    from tables.forms import TableAreaForm
    if request.method == 'POST':
        form = TableAreaForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Área creada.')
            return redirect('config:table_area_list')
    else:
        form = TableAreaForm()
    return render(request, 'config/area_form.html', {'form': form, 'title': 'Nueva Área'})


@login_required
@staff_required
def table_area_edit(request, pk):
    from tables.models import TableArea
    from tables.forms import TableAreaForm
    area = get_object_or_404(TableArea, pk=pk)
    if request.method == 'POST':
        form = TableAreaForm(request.POST, instance=area)
        if form.is_valid():
            form.save()
            messages.success(request, 'Área actualizada.')
            return redirect('config:table_area_list')
    else:
        form = TableAreaForm(instance=area)
    return render(request, 'config/area_form.html', {'form': form, 'title': f'Editar: {area.name}'})
