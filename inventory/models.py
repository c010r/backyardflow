from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone


class Supplier(models.Model):
    name = models.CharField(max_length=200, verbose_name='Nombre')
    contact_name = models.CharField(max_length=200, blank=True, verbose_name='Contacto')
    phone = models.CharField(max_length=50, blank=True, verbose_name='Telefono')
    email = models.EmailField(blank=True, verbose_name='Email')
    address = models.TextField(blank=True, verbose_name='Direccion')
    notes = models.TextField(blank=True, verbose_name='Notas')
    active = models.BooleanField(default=True, verbose_name='Activo')

    class Meta:
        verbose_name = 'Proveedor'
        verbose_name_plural = 'Proveedores'
        ordering = ['name']

    def __str__(self):
        return self.name


class IngredientCategory(models.Model):
    name = models.CharField(max_length=100, verbose_name='Nombre')
    description = models.TextField(blank=True, verbose_name='Descripcion')

    class Meta:
        verbose_name = 'Categoria de Ingrediente'
        verbose_name_plural = 'Categorias de Ingredientes'
        ordering = ['name']

    def __str__(self):
        return self.name


class Ingredient(models.Model):
    UNIT_CHOICES = [
        ('kg', 'Kilogramos'),
        ('g', 'Gramos'),
        ('l', 'Litros'),
        ('ml', 'Mililitros'),
        ('units', 'Unidades'),
        ('portions', 'Porciones'),
    ]

    name = models.CharField(max_length=200, verbose_name='Nombre')
    category = models.ForeignKey(
        IngredientCategory, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='ingredients', verbose_name='Categoria'
    )
    unit = models.CharField(max_length=20, choices=UNIT_CHOICES, default='units', verbose_name='Unidad')
    stock_quantity = models.DecimalField(max_digits=10, decimal_places=3, default=0, verbose_name='Stock Actual')
    min_stock = models.DecimalField(max_digits=10, decimal_places=3, default=0, verbose_name='Stock Minimo')
    cost_per_unit = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name='Costo por Unidad')
    supplier = models.ForeignKey(
        Supplier, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='ingredients', verbose_name='Proveedor'
    )
    last_updated = models.DateTimeField(auto_now=True)
    active = models.BooleanField(default=True, verbose_name='Activo')

    class Meta:
        verbose_name = 'Ingrediente'
        verbose_name_plural = 'Ingredientes'
        ordering = ['name']

    def __str__(self):
        return f"{self.name} ({self.get_unit_display()})"

    @property
    def is_low_stock(self):
        return self.stock_quantity <= self.min_stock

    @property
    def stock_value(self):
        return self.stock_quantity * self.cost_per_unit


class StockMovement(models.Model):
    MOVEMENT_TYPES = [
        ('IN', 'Entrada'),
        ('OUT', 'Salida'),
        ('ADJUSTMENT', 'Ajuste'),
        ('WASTE', 'Merma'),
    ]

    ingredient = models.ForeignKey(
        Ingredient, on_delete=models.CASCADE,
        related_name='movements', verbose_name='Ingrediente'
    )
    movement_type = models.CharField(max_length=20, choices=MOVEMENT_TYPES, verbose_name='Tipo')
    quantity = models.DecimalField(max_digits=10, decimal_places=3, verbose_name='Cantidad')
    unit_cost = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, verbose_name='Costo Unitario')
    reason = models.CharField(max_length=300, blank=True, verbose_name='Motivo')
    reference = models.CharField(max_length=100, blank=True, verbose_name='Referencia')
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, verbose_name='Creado por')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Movimiento de Stock'
        verbose_name_plural = 'Movimientos de Stock'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.get_movement_type_display()} - {self.ingredient.name} ({self.quantity})"

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        # Update ingredient stock
        ingredient = self.ingredient
        if self.movement_type == 'IN':
            ingredient.stock_quantity += self.quantity
        elif self.movement_type in ('OUT', 'WASTE'):
            ingredient.stock_quantity -= self.quantity
        elif self.movement_type == 'ADJUSTMENT':
            ingredient.stock_quantity = self.quantity
        ingredient.save()


class PurchaseOrder(models.Model):
    STATUS_CHOICES = [
        ('PENDING', 'Pendiente'),
        ('ORDERED', 'Pedido'),
        ('RECEIVED', 'Recibido'),
        ('CANCELLED', 'Cancelado'),
    ]

    supplier = models.ForeignKey(
        Supplier, on_delete=models.PROTECT,
        related_name='purchase_orders', verbose_name='Proveedor'
    )
    order_date = models.DateField(default=timezone.now, verbose_name='Fecha de Pedido')
    expected_delivery = models.DateField(null=True, blank=True, verbose_name='Entrega Esperada')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING', verbose_name='Estado')
    notes = models.TextField(blank=True, verbose_name='Notas')
    total_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0, verbose_name='Total')
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, verbose_name='Creado por')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Orden de Compra'
        verbose_name_plural = 'Ordenes de Compra'
        ordering = ['-created_at']

    def __str__(self):
        return f"OC-{self.pk} - {self.supplier.name} ({self.get_status_display()})"

    def calculate_total(self):
        total = sum(item.total_cost for item in self.items.all())
        self.total_amount = total
        self.save(update_fields=['total_amount'])
        return total


class PurchaseOrderItem(models.Model):
    purchase_order = models.ForeignKey(
        PurchaseOrder, on_delete=models.CASCADE,
        related_name='items', verbose_name='Orden de Compra'
    )
    ingredient = models.ForeignKey(
        Ingredient, on_delete=models.PROTECT,
        related_name='purchase_items', verbose_name='Ingrediente'
    )
    quantity_ordered = models.DecimalField(max_digits=10, decimal_places=3, verbose_name='Cantidad Pedida')
    quantity_received = models.DecimalField(max_digits=10, decimal_places=3, default=0, verbose_name='Cantidad Recibida')
    unit_cost = models.DecimalField(max_digits=10, decimal_places=2, verbose_name='Costo Unitario')

    class Meta:
        verbose_name = 'Item de Orden de Compra'
        verbose_name_plural = 'Items de Orden de Compra'

    def __str__(self):
        return f"{self.ingredient.name} x {self.quantity_ordered}"

    @property
    def total_cost(self):
        return self.quantity_ordered * self.unit_cost
