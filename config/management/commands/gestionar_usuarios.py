"""
Comando Django: gestionar_usuarios
Permite crear y modificar usuarios desde la línea de comandos.

Uso:
  python manage.py gestionar_usuarios
"""
import getpass
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError

ROLES = ['MANAGER', 'WAITER', 'BARTENDER', 'CHEF', 'CASHIER', 'CLEANER']

SEP = '─' * 52


def ask(prompt, default=None, required=True):
    """Pide input al usuario, con valor por defecto opcional."""
    hint = f' [{default}]' if default else ''
    while True:
        val = input(f'  {prompt}{hint}: ').strip()
        if not val and default is not None:
            return default
        if val:
            return val
        if not required:
            return ''
        print('  [!] Este campo no puede estar vacío.')


def ask_password(prompt='Contraseña'):
    """Pide contraseña dos veces y valida que coincidan."""
    while True:
        p1 = getpass.getpass(f'  {prompt}: ')
        if not p1:
            print('  [!] La contraseña no puede estar vacía.')
            continue
        p2 = getpass.getpass(f'  Confirmar contraseña: ')
        if p1 != p2:
            print('  [!] Las contraseñas no coinciden. Intentá de nuevo.')
            continue
        try:
            validate_password(p1)
        except ValidationError as e:
            print(f'  [!] Contraseña débil: {", ".join(e.messages)}')
            override = input('  ¿Usar de todos modos? (s/N): ').strip().lower()
            if override != 's':
                continue
        return p1


def print_users():
    """Muestra tabla de usuarios actuales."""
    users = User.objects.all().order_by('username')
    print(f'\n  {"Usuario":<20} {"Nombre":<25} {"Rol":<12} {"Staff"}')
    print(f'  {SEP}')
    for u in users:
        try:
            role = u.staff_profile.role
        except Exception:
            role = 'MANAGER' if (u.is_staff or u.is_superuser) else '—'
        fullname = u.get_full_name() or '—'
        staff_mark = '✓' if u.is_staff else ''
        print(f'  {u.username:<20} {fullname:<25} {role:<12} {staff_mark}')
    print()


class Command(BaseCommand):
    help = 'Gestionar usuarios: crear, cambiar contraseña, asignar rol, activar/desactivar'

    def handle(self, *args, **options):
        self.stdout.write('\n')
        self.stdout.write(f'  ╔{"═"*50}╗\n')
        self.stdout.write(f'  ║{"BackyardFlow POS — Gestión de Usuarios":^50}║\n')
        self.stdout.write(f'  ╚{"═"*50}╝\n\n')

        while True:
            self.stdout.write(f'  {SEP}\n')
            self.stdout.write('  1. Listar usuarios\n')
            self.stdout.write('  2. Crear usuario\n')
            self.stdout.write('  3. Cambiar contraseña\n')
            self.stdout.write('  4. Editar nombre / email\n')
            self.stdout.write('  5. Cambiar rol\n')
            self.stdout.write('  6. Activar / desactivar usuario\n')
            self.stdout.write('  7. Eliminar usuario\n')
            self.stdout.write('  0. Salir\n')
            self.stdout.write(f'  {SEP}\n')

            opcion = input('  Opción: ').strip()

            if opcion == '0':
                self.stdout.write('\n  Hasta luego.\n\n')
                break
            elif opcion == '1':
                print_users()
            elif opcion == '2':
                self._crear_usuario()
            elif opcion == '3':
                self._cambiar_password()
            elif opcion == '4':
                self._editar_nombre()
            elif opcion == '5':
                self._cambiar_rol()
            elif opcion == '6':
                self._toggle_activo()
            elif opcion == '7':
                self._eliminar_usuario()
            else:
                self.stdout.write('  [!] Opción inválida.\n')

    # ── Operaciones ───────────────────────────────────────────────────────

    def _crear_usuario(self):
        self.stdout.write(f'\n  {SEP}\n  CREAR USUARIO\n  {SEP}\n')

        username = ask('Nombre de usuario')
        if User.objects.filter(username=username).exists():
            self.stdout.write(f'  [!] El usuario "{username}" ya existe.\n\n')
            return

        first_name = ask('Nombre', required=False)
        last_name  = ask('Apellido', required=False)
        email      = ask('Email', required=False)

        self.stdout.write(f'\n  Roles disponibles: {", ".join(ROLES)}\n')
        role = ask('Rol', default='WAITER').upper()
        while role not in ROLES:
            self.stdout.write(f'  [!] Rol inválido. Opciones: {", ".join(ROLES)}\n')
            role = ask('Rol', default='WAITER').upper()

        is_staff = role == 'MANAGER'
        if not is_staff:
            resp = input('  ¿Dar acceso de staff/admin? (s/N): ').strip().lower()
            is_staff = resp == 's'

        password = ask_password()

        user = User.objects.create_user(
            username=username,
            password=password,
            first_name=first_name,
            last_name=last_name,
            email=email,
            is_staff=is_staff,
            is_superuser=(role == 'MANAGER' and is_staff),
        )

        # Asignar rol via StaffMember si no es MANAGER puro
        if role != 'MANAGER':
            try:
                from staff.models import StaffMember
                StaffMember.objects.get_or_create(
                    user=user,
                    defaults={'role': role, 'active': True}
                )
            except Exception as e:
                self.stdout.write(f'  [!] Advertencia: no se pudo asignar perfil de staff: {e}\n')

        self.stdout.write(f'\n  [OK] Usuario "{username}" creado con rol {role}.\n\n')

    def _cambiar_password(self):
        self.stdout.write(f'\n  {SEP}\n  CAMBIAR CONTRASEÑA\n  {SEP}\n')
        print_users()

        username = ask('Usuario')
        try:
            user = User.objects.get(username=username)
        except User.DoesNotExist:
            self.stdout.write(f'  [!] Usuario "{username}" no encontrado.\n\n')
            return

        password = ask_password('Nueva contraseña')
        user.set_password(password)
        user.save()
        self.stdout.write(f'\n  [OK] Contraseña de "{username}" actualizada.\n\n')

    def _editar_nombre(self):
        self.stdout.write(f'\n  {SEP}\n  EDITAR NOMBRE / EMAIL\n  {SEP}\n')
        print_users()

        username = ask('Usuario')
        try:
            user = User.objects.get(username=username)
        except User.DoesNotExist:
            self.stdout.write(f'  [!] Usuario "{username}" no encontrado.\n\n')
            return

        user.first_name = ask('Nombre', default=user.first_name or '', required=False)
        user.last_name  = ask('Apellido', default=user.last_name or '', required=False)
        user.email      = ask('Email', default=user.email or '', required=False)
        user.save()
        self.stdout.write(f'\n  [OK] Datos de "{username}" actualizados.\n\n')

    def _cambiar_rol(self):
        self.stdout.write(f'\n  {SEP}\n  CAMBIAR ROL\n  {SEP}\n')
        print_users()

        username = ask('Usuario')
        try:
            user = User.objects.get(username=username)
        except User.DoesNotExist:
            self.stdout.write(f'  [!] Usuario "{username}" no encontrado.\n\n')
            return

        self.stdout.write(f'  Roles disponibles: {", ".join(ROLES)}\n')
        role = ask('Nuevo rol').upper()
        while role not in ROLES:
            self.stdout.write(f'  [!] Rol inválido.\n')
            role = ask('Nuevo rol').upper()

        # Actualizar is_staff / is_superuser
        user.is_staff = role == 'MANAGER'
        user.is_superuser = role == 'MANAGER'
        user.save()

        # Actualizar o crear StaffMember
        try:
            from staff.models import StaffMember
            profile, _ = StaffMember.objects.get_or_create(user=user, defaults={'role': role})
            profile.role = role
            profile.save()
        except Exception as e:
            self.stdout.write(f'  [!] Advertencia al actualizar perfil: {e}\n')

        self.stdout.write(f'\n  [OK] Rol de "{username}" actualizado a {role}.\n\n')

    def _toggle_activo(self):
        self.stdout.write(f'\n  {SEP}\n  ACTIVAR / DESACTIVAR USUARIO\n  {SEP}\n')
        print_users()

        username = ask('Usuario')
        try:
            user = User.objects.get(username=username)
        except User.DoesNotExist:
            self.stdout.write(f'  [!] Usuario "{username}" no encontrado.\n\n')
            return

        estado_actual = 'activo' if user.is_active else 'desactivado'
        accion = 'desactivar' if user.is_active else 'activar'
        self.stdout.write(f'  Usuario "{username}" está {estado_actual}.\n')
        conf = input(f'  ¿{accion.capitalize()}? (s/N): ').strip().lower()

        if conf == 's':
            user.is_active = not user.is_active
            user.save()
            nuevo = 'activado' if user.is_active else 'desactivado'
            self.stdout.write(f'\n  [OK] Usuario "{username}" {nuevo}.\n\n')
        else:
            self.stdout.write('  Cancelado.\n\n')

    def _eliminar_usuario(self):
        self.stdout.write(f'\n  {SEP}\n  ELIMINAR USUARIO\n  {SEP}\n')
        print_users()

        username = ask('Usuario a eliminar')
        try:
            user = User.objects.get(username=username)
        except User.DoesNotExist:
            self.stdout.write(f'  [!] Usuario "{username}" no encontrado.\n\n')
            return

        if user.is_superuser:
            self.stdout.write('  [!] No se puede eliminar un superusuario desde aquí.\n\n')
            return

        conf = input(f'  ¿Eliminar "{username}" permanentemente? (s/N): ').strip().lower()
        if conf == 's':
            user.delete()
            self.stdout.write(f'\n  [OK] Usuario "{username}" eliminado.\n\n')
        else:
            self.stdout.write('  Cancelado.\n\n')
