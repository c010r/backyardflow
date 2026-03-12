from django.db import models
from decimal import Decimal


class MenuCategory(models.Model):
    name = models.CharField(max_length=100, verbose_name='Nombre')
    description = models.TextField(blank=True, verbose_name='Descripcion')
    icon = models.ImageField(upload_to='menu/categories/', null=True, blank=True, verbose_name='Icono')
    display_order = models.PositiveIntegerField(default=0, verbose_name='Orden')
    active = models.BooleanField(default=True, verbose_name='Activo')

    class Meta:
        verbose_name = 'Categoria del Menu'
        verbose_name_plural = 'Categorias del Menu'
        ordering = ['display_order', 'name']

    def __str__(self):
        return self.name


class MenuItem(models.Model):
    ITEM_TYPES = [
        ('FOOD', 'Comida'),
        ('DRINK', 'Bebida'),
        ('DESSERT', 'Postre'),
        ('OTHER', 'Otro'),
    ]

    name = models.CharField(max_length=200, verbose_name='Nombre')
    category = models.ForeignKey(
        MenuCategory, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='items', verbose_name='Categoria'
    )
    description = models.TextField(blank=True, verbose_name='Descripcion')
    item_type = models.CharField(max_length=20, choices=ITEM_TYPES, default='FOOD', verbose_name='Tipo')
    price = models.DecimalField(max_digits=10, decimal_places=2, verbose_name='Precio de Venta')
    image = models.ImageField(upload_to='menu/items/', null=True, blank=True, verbose_name='Imagen')
    available = models.BooleanField(default=True, verbose_name='Disponible')
    featured = models.BooleanField(default=False, verbose_name='Destacado')
    preparation_time = models.PositiveIntegerField(default=15, verbose_name='Tiempo de Preparacion (min)')
    display_order = models.PositiveIntegerField(default=0, verbose_name='Orden')
    active = models.BooleanField(default=True, verbose_name='Activo')

    class Meta:
        verbose_name = 'Item del Menu'
        verbose_name_plural = 'Items del Menu'
        ordering = ['display_order', 'name']

    def __str__(self):
        return self.name

    @property
    def cost(self):
        """Calculate cost from recipe ingredients"""
        try:
            recipe = self.recipe
            total_cost = sum(ri.calculate_cost() for ri in recipe.ingredients.all())
            return total_cost
        except Exception:
            return Decimal('0')

    @property
    def profit_margin(self):
        """Calculate profit margin percentage"""
        cost = self.cost
        if cost and cost > 0 and self.price > 0:
            return ((self.price - cost) / self.price) * 100
        return Decimal('100') if self.price > 0 else Decimal('0')

    @property
    def gross_profit(self):
        return self.price - self.cost


class Recipe(models.Model):
    menu_item = models.OneToOneField(
        MenuItem, on_delete=models.CASCADE,
        related_name='recipe', verbose_name='Item del Menu'
    )
    instructions = models.TextField(blank=True, verbose_name='Instrucciones')
    servings = models.PositiveIntegerField(default=1, verbose_name='Porciones')
    preparation_time = models.PositiveIntegerField(default=15, verbose_name='Tiempo de Preparacion (min)')
    notes = models.TextField(blank=True, verbose_name='Notas')

    class Meta:
        verbose_name = 'Receta'
        verbose_name_plural = 'Recetas'

    def __str__(self):
        return f"Receta: {self.menu_item.name}"

    @property
    def total_cost(self):
        return sum(ri.calculate_cost() for ri in self.ingredients.all())


class RecipeIngredient(models.Model):
    UNIT_CHOICES = [
        ('kg', 'Kilogramos'),
        ('g', 'Gramos'),
        ('l', 'Litros'),
        ('ml', 'Mililitros'),
        ('units', 'Unidades'),
        ('portions', 'Porciones'),
    ]

    recipe = models.ForeignKey(
        Recipe, on_delete=models.CASCADE,
        related_name='ingredients', verbose_name='Receta'
    )
    ingredient = models.ForeignKey(
        'inventory.Ingredient', on_delete=models.PROTECT,
        related_name='recipe_usages', verbose_name='Ingrediente'
    )
    quantity = models.DecimalField(max_digits=10, decimal_places=3, verbose_name='Cantidad')
    unit = models.CharField(max_length=20, choices=UNIT_CHOICES, verbose_name='Unidad')
    notes = models.CharField(max_length=200, blank=True, verbose_name='Notas')

    class Meta:
        verbose_name = 'Ingrediente de Receta'
        verbose_name_plural = 'Ingredientes de Receta'

    def __str__(self):
        return f"{self.ingredient.name} - {self.quantity} {self.unit}"

    def calculate_cost(self):
        """Calculate cost for this ingredient line"""
        # Convert units if needed (simple implementation)
        qty = self.quantity
        unit_cost = self.ingredient.cost_per_unit
        ingredient_unit = self.ingredient.unit
        recipe_unit = self.unit

        # Unit conversions
        conversion = Decimal('1')
        if ingredient_unit == 'kg' and recipe_unit == 'g':
            conversion = Decimal('0.001')
        elif ingredient_unit == 'g' and recipe_unit == 'kg':
            conversion = Decimal('1000')
        elif ingredient_unit == 'l' and recipe_unit == 'ml':
            conversion = Decimal('0.001')
        elif ingredient_unit == 'ml' and recipe_unit == 'l':
            conversion = Decimal('1000')

        return qty * unit_cost * conversion
