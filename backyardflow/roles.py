"""
Helpers de roles para BackyardFlow POS.
Cada rol define qué secciones puede ver.
"""
from functools import wraps
from django.shortcuts import redirect
from django.contrib import messages

# Mapa de permisos por rol
ROLE_PERMISSIONS = {
    'MANAGER': {
        'tables', 'orders', 'kitchen', 'menu', 'inventory',
        'cash_register', 'staff', 'qr_menu', 'config',
    },
    'WAITER': {
        'tables', 'orders', 'qr_menu',
    },
    'BARTENDER': {
        'tables', 'orders', 'kitchen', 'qr_menu',
    },
    'CHEF': {
        'kitchen', 'orders',
    },
    'CASHIER': {
        'cash_register', 'orders', 'tables',
    },
    'CLEANER': {
        'tables',
    },
}

# Dashboard de inicio por rol
ROLE_HOME = {
    'MANAGER':   '/',
    'WAITER':    '/tables/',
    'BARTENDER': '/orders/kitchen/',
    'CHEF':      '/orders/kitchen/',
    'CASHIER':   '/cash-register/',
    'CLEANER':   '/tables/',
}


def get_role(user):
    """Retorna el rol del usuario o None si es admin/superuser."""
    if not user.is_authenticated:
        return None
    if user.is_staff or user.is_superuser:
        return 'MANAGER'
    try:
        return user.staff_profile.role
    except Exception:
        return None


def has_permission(user, section):
    role = get_role(user)
    if role is None:
        return False
    return section in ROLE_PERMISSIONS.get(role, set())


def role_required(*sections):
    """Decorador: requiere que el usuario tenga acceso a alguna de las secciones."""
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            if not request.user.is_authenticated:
                return redirect('/accounts/login/')
            role = get_role(request.user)
            allowed = ROLE_PERMISSIONS.get(role, set())
            if any(s in allowed for s in sections):
                return view_func(request, *args, **kwargs)
            messages.error(request, 'No tenés permiso para acceder a esta sección.')
            home = ROLE_HOME.get(role, '/')
            return redirect(home)
        return wrapper
    return decorator
