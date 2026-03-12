"""
BackyardFlow POS - Demo Data Setup Script
Run with: python manage.py shell < setup_demo.py
Or: python setup_demo.py (from project root with manage.py)
"""
import os
import sys
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backyardflow.settings')
django.setup()

from django.contrib.auth.models import User
from decimal import Decimal
from datetime import date, time

print("=== BackyardFlow POS - Setup Demo Data ===\n")

# Create superuser
if not User.objects.filter(username='admin').exists():
    admin = User.objects.create_superuser('admin', 'admin@backyardflow.com', 'admin123')
    print("Superuser creado: admin / admin123")
else:
    admin = User.objects.get(username='admin')
    print("Superuser ya existe: admin")

# Create waiter users
waiter_data = [
    {'username': 'carlos', 'first_name': 'Carlos', 'last_name': 'Garcia', 'password': 'mozo123'},
    {'username': 'maria', 'first_name': 'Maria', 'last_name': 'Lopez', 'password': 'mozo123'},
]
waiters = []
for wd in waiter_data:
    if not User.objects.filter(username=wd['username']).exists():
        u = User.objects.create_user(
            username=wd['username'],
            first_name=wd['first_name'],
            last_name=wd['last_name'],
            password=wd['password']
        )
        waiters.append(u)
        print(f"Usuario creado: {wd['username']} / {wd['password']}")
    else:
        waiters.append(User.objects.get(username=wd['username']))

# Inventory
from inventory.models import IngredientCategory, Ingredient, Supplier

# Supplier
if not Supplier.objects.filter(name='Distribuidora Central').exists():
    sup = Supplier.objects.create(
        name='Distribuidora Central',
        contact_name='Roberto Mendez',
        phone='011-4567-8900',
        email='ventas@distribuidora.com'
    )
    print("Proveedor creado: Distribuidora Central")
else:
    sup = Supplier.objects.get(name='Distribuidora Central')

# Ingredient categories
cat_data = ['Carnes', 'Verduras', 'Bebidas', 'Lacteos', 'Condimentos', 'Harinas y Masas']
ing_cats = {}
for cat_name in cat_data:
    cat, created = IngredientCategory.objects.get_or_create(name=cat_name)
    ing_cats[cat_name] = cat
    if created:
        print(f"Categoria de ingrediente: {cat_name}")

# Ingredients
ingredients_data = [
    ('Carne Vacuna', 'Carnes', 'kg', Decimal('1.5'), Decimal('5'), Decimal('2800')),
    ('Pollo', 'Carnes', 'kg', Decimal('2.0'), Decimal('3'), Decimal('1800')),
    ('Papa', 'Verduras', 'kg', Decimal('3.0'), Decimal('2'), Decimal('300')),
    ('Tomate', 'Verduras', 'kg', Decimal('1.0'), Decimal('1'), Decimal('400')),
    ('Lechuga', 'Verduras', 'units', Decimal('5'), Decimal('3'), Decimal('200')),
    ('Queso Mozzarella', 'Lacteos', 'kg', Decimal('0.5'), Decimal('1'), Decimal('3500')),
    ('Manteca', 'Lacteos', 'kg', Decimal('0.3'), Decimal('0.5'), Decimal('2000')),
    ('Cerveza (botella)', 'Bebidas', 'units', Decimal('24'), Decimal('12'), Decimal('350')),
    ('Gaseosa Cola (2L)', 'Bebidas', 'units', Decimal('12'), Decimal('6'), Decimal('450')),
    ('Agua Mineral', 'Bebidas', 'units', Decimal('20'), Decimal('10'), Decimal('150')),
    ('Vino Tinto (750ml)', 'Bebidas', 'units', Decimal('6'), Decimal('3'), Decimal('1200')),
    ('Harina 000', 'Harinas y Masas', 'kg', Decimal('2.0'), Decimal('1'), Decimal('200')),
    ('Aceite de Girasol', 'Condimentos', 'l', Decimal('1.5'), Decimal('1'), Decimal('600')),
    ('Sal', 'Condimentos', 'kg', Decimal('0.5'), Decimal('0.2'), Decimal('100')),
    ('Pimienta Negra', 'Condimentos', 'g', Decimal('50'), Decimal('20'), Decimal('5')),
]

for name, cat_name, unit, stock, min_stock, cost in ingredients_data:
    ing, created = Ingredient.objects.get_or_create(
        name=name,
        defaults={
            'category': ing_cats[cat_name],
            'unit': unit,
            'stock_quantity': stock,
            'min_stock': min_stock,
            'cost_per_unit': cost,
            'supplier': sup,
        }
    )
    if created:
        print(f"Ingrediente: {name}")

# Menu
from menu.models import MenuCategory, MenuItem, Recipe, RecipeIngredient

menu_cats_data = [
    ('Entradas', 0),
    ('Parrilla', 1),
    ('Sandwiches', 2),
    ('Ensaladas', 3),
    ('Cervezas', 4),
    ('Bebidas sin Alcohol', 5),
    ('Vinos', 6),
    ('Postres', 7),
]
menu_cats = {}
for cat_name, order in menu_cats_data:
    cat, created = MenuCategory.objects.get_or_create(
        name=cat_name,
        defaults={'display_order': order}
    )
    menu_cats[cat_name] = cat
    if created:
        print(f"Categoria del menu: {cat_name}")

# Menu items
menu_items_data = [
    ('Tabla de Picada', 'Entradas', 'FOOD', Decimal('3500'), 30, True),
    ('Bife de Chorizo 300g', 'Parrilla', 'FOOD', Decimal('6500'), 25, True),
    ('Pollo a la Plancha', 'Parrilla', 'FOOD', Decimal('4500'), 20, False),
    ('Choripan', 'Sandwiches', 'FOOD', Decimal('1800'), 10, False),
    ('Hamburguesa Clasica', 'Sandwiches', 'FOOD', Decimal('2800'), 15, True),
    ('Ensalada Mixta', 'Ensaladas', 'FOOD', Decimal('1500'), 10, False),
    ('Ensalada Caesar', 'Ensaladas', 'FOOD', Decimal('2200'), 12, False),
    ('Cerveza Quilmes 1L', 'Cervezas', 'DRINK', Decimal('1200'), 2, True),
    ('Cerveza Quilmes 500cc', 'Cervezas', 'DRINK', Decimal('700'), 2, True),
    ('Coca-Cola 500cc', 'Bebidas sin Alcohol', 'DRINK', Decimal('600'), 2, False),
    ('Agua Mineral 500cc', 'Bebidas sin Alcohol', 'DRINK', Decimal('400'), 2, False),
    ('Vino Tinto Copa', 'Vinos', 'DRINK', Decimal('900'), 2, False),
    ('Vino Tinto Botella', 'Vinos', 'DRINK', Decimal('3500'), 5, False),
    ('Helado 2 Gustos', 'Postres', 'DESSERT', Decimal('1200'), 5, False),
    ('Flan Casero', 'Postres', 'DESSERT', Decimal('800'), 10, False),
]

menu_items = {}
for name, cat_name, item_type, price, prep_time, featured in menu_items_data:
    item, created = MenuItem.objects.get_or_create(
        name=name,
        defaults={
            'category': menu_cats[cat_name],
            'item_type': item_type,
            'price': price,
            'preparation_time': prep_time,
            'featured': featured,
        }
    )
    menu_items[name] = item
    if created:
        print(f"Item del menu: {name}")

# Simple recipe for bife
bife = menu_items.get('Bife de Chorizo 300g')
if bife and not hasattr(bife, 'recipe'):
    recipe = Recipe.objects.create(
        menu_item=bife,
        instructions='Sellar a fuego alto por 3 minutos cada lado. Condimentar con sal y pimienta.',
        preparation_time=25
    )
    try:
        carne = Ingredient.objects.get(name='Carne Vacuna')
        RecipeIngredient.objects.get_or_create(
            recipe=recipe, ingredient=carne,
            defaults={'quantity': Decimal('0.35'), 'unit': 'kg'}
        )
        sal = Ingredient.objects.get(name='Sal')
        RecipeIngredient.objects.get_or_create(
            recipe=recipe, ingredient=sal,
            defaults={'quantity': Decimal('5'), 'unit': 'g'}
        )
        print("Receta creada: Bife de Chorizo")
    except Ingredient.DoesNotExist:
        pass

# Tables
from tables.models import TableArea, Table

areas_data = [
    ('Salon Principal', 'Area interior climatizada'),
    ('Terraza', 'Area exterior con vista al jardin'),
    ('Barra', 'Asientos en la barra'),
]
areas = {}
for area_name, desc in areas_data:
    area, created = TableArea.objects.get_or_create(name=area_name, defaults={'description': desc})
    areas[area_name] = area
    if created:
        print(f"Area creada: {area_name}")

tables_data = [
    (1, 'Salon Principal', 4),
    (2, 'Salon Principal', 4),
    (3, 'Salon Principal', 6),
    (4, 'Salon Principal', 2),
    (5, 'Salon Principal', 8),
    (6, 'Terraza', 4),
    (7, 'Terraza', 4),
    (8, 'Terraza', 6),
    (9, 'Barra', 2),
    (10, 'Barra', 2),
]
for num, area_name, capacity in tables_data:
    table, created = Table.objects.get_or_create(
        number=num,
        area=areas[area_name],
        defaults={'capacity': capacity}
    )
    if created:
        print(f"Mesa {num} - {area_name}")

# Cash Register
from cash_register.models import CashRegister

reg, created = CashRegister.objects.get_or_create(
    name='Caja Principal',
    defaults={'location': 'Frente al salon'}
)
if created:
    print("Caja registradora creada: Caja Principal")

reg2, created = CashRegister.objects.get_or_create(
    name='Caja Barra',
    defaults={'location': 'En la barra'}
)
if created:
    print("Caja registradora creada: Caja Barra")

# Staff
from staff.models import StaffMember

staff_data = [
    (waiters[0], 'WAITER', 'MONTHLY', Decimal('180000'), Decimal('0')),
    (waiters[1] if len(waiters) > 1 else waiters[0], 'BARTENDER', 'HOURLY', Decimal('0'), Decimal('1500')),
]

for user, role, payment_type, salary, hourly in staff_data:
    member, created = StaffMember.objects.get_or_create(
        user=user,
        defaults={
            'role': role,
            'payment_type': payment_type,
            'base_salary': salary,
            'hourly_rate': hourly,
            'hire_date': date.today(),
        }
    )
    if created:
        print(f"Personal creado: {user.get_full_name()} - {role}")

print("\n=== Setup completado exitosamente! ===")
print("\nCredenciales:")
print("  Admin: admin / admin123")
print("  Mozo:  carlos / mozo123")
print("  Barra: maria / mozo123")
print("\nEjecutar el servidor con: python manage.py runserver")
print("Acceder a: http://127.0.0.1:8000/")
print("Admin Django: http://127.0.0.1:8000/admin/")
