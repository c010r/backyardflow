from .roles import get_role, ROLE_PERMISSIONS, ROLE_HOME


def user_role(request):
    if not request.user.is_authenticated:
        return {}
    role = get_role(request.user)
    perms = ROLE_PERMISSIONS.get(role, set())
    return {
        'user_role': role,
        'user_home': ROLE_HOME.get(role, '/'),
        'can_tables':        'tables'        in perms,
        'can_orders':        'orders'        in perms,
        'can_kitchen':       'kitchen'       in perms,
        'can_menu':          'menu'          in perms,
        'can_inventory':     'inventory'     in perms,
        'can_cash_register': 'cash_register' in perms,
        'can_staff':         'staff'         in perms,
        'can_qr_menu':       'qr_menu'       in perms,
        'can_config':        'config'        in perms,
    }
