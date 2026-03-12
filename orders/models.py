from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from decimal import Decimal
import uuid


class Order(models.Model):
    ORDER_TYPES = [
        ('DINE_IN', 'En Mesa'),
        ('TAKEOUT', 'Para Llevar'),
        ('DELIVERY', 'Delivery'),
    ]
    WAITER_TYPES = [
        ('HUMAN', 'Mozo'),
        ('VIRTUAL', 'Virtual (QR)'),
    ]
    STATUS_CHOICES = [
        ('PENDING', 'Pendiente'),
        ('IN_PROGRESS', 'En Preparacion'),
        ('READY', 'Listo'),
        ('DELIVERED', 'Entregado'),
        ('PAID', 'Pagado'),
        ('CANCELLED', 'Cancelado'),
    ]

    order_number = models.CharField(max_length=30, unique=True, blank=True, verbose_name='Numero de Comanda')
    table = models.ForeignKey(
        'tables.Table', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='orders', verbose_name='Mesa'
    )
    order_type = models.CharField(max_length=20, choices=ORDER_TYPES, default='DINE_IN', verbose_name='Tipo')
    waiter_type = models.CharField(max_length=20, choices=WAITER_TYPES, default='HUMAN', verbose_name='Tipo de Mozo')
    waiter = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='orders', verbose_name='Mozo'
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING', verbose_name='Estado')
    notes = models.TextField(blank=True, verbose_name='Notas')
    discount_percent = models.DecimalField(max_digits=5, decimal_places=2, default=0, verbose_name='Descuento %')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    closed_at = models.DateTimeField(null=True, blank=True)
    cash_session = models.ForeignKey(
        'cash_register.CashSession', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='orders', verbose_name='Sesion de Caja'
    )

    class Meta:
        verbose_name = 'Comanda'
        verbose_name_plural = 'Comandas'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.order_number} - {self.get_status_display()}"

    def save(self, *args, **kwargs):
        if not self.order_number:
            self.order_number = self.generate_order_number()
        super().save(*args, **kwargs)

    def generate_order_number(self):
        from django.db import transaction
        now = timezone.now()
        date_str = now.strftime('%Y%m%d')
        prefix = f"CMD-{date_str}-"
        with transaction.atomic():
            last = (Order.objects
                    .filter(order_number__startswith=prefix)
                    .order_by('order_number')
                    .values_list('order_number', flat=True)
                    .last())
            if last:
                try:
                    next_num = int(last.split('-')[-1]) + 1
                except (ValueError, IndexError):
                    next_num = 1
            else:
                next_num = 1
            return f"{prefix}{next_num:03d}"

    @property
    def subtotal(self):
        return sum(item.subtotal for item in self.items.filter(status__in=['PENDING', 'PREPARING', 'READY', 'DELIVERED']))

    @property
    def discount_amount(self):
        if self.discount_percent:
            return self.subtotal * (self.discount_percent / 100)
        return Decimal('0')

    @property
    def total(self):
        return self.subtotal - self.discount_amount


class OrderItem(models.Model):
    STATUS_CHOICES = [
        ('PENDING', 'Pendiente'),
        ('PREPARING', 'Preparando'),
        ('READY', 'Listo'),
        ('DELIVERED', 'Entregado'),
        ('CANCELLED', 'Cancelado'),
    ]

    order = models.ForeignKey(
        Order, on_delete=models.CASCADE,
        related_name='items', verbose_name='Comanda'
    )
    menu_item = models.ForeignKey(
        'menu.MenuItem', on_delete=models.PROTECT,
        related_name='order_items', verbose_name='Item del Menu'
    )
    quantity = models.PositiveIntegerField(default=1, verbose_name='Cantidad')
    unit_price = models.DecimalField(max_digits=10, decimal_places=2, verbose_name='Precio Unitario')
    notes = models.CharField(max_length=300, blank=True, verbose_name='Notas')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING', verbose_name='Estado')
    sent_to_kitchen_at = models.DateTimeField(null=True, blank=True)
    ready_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = 'Item de Comanda'
        verbose_name_plural = 'Items de Comanda'

    def __str__(self):
        return f"{self.quantity}x {self.menu_item.name}"

    @property
    def subtotal(self):
        return self.quantity * self.unit_price


class VirtualWaiterSession(models.Model):
    table = models.ForeignKey(
        'tables.Table', on_delete=models.CASCADE,
        related_name='virtual_sessions', verbose_name='Mesa'
    )
    session_token = models.UUIDField(default=uuid.uuid4, unique=True, verbose_name='Token')
    order = models.ForeignKey(
        Order, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='virtual_sessions', verbose_name='Comanda'
    )
    started_at = models.DateTimeField(auto_now_add=True)
    last_activity = models.DateTimeField(auto_now=True)
    active = models.BooleanField(default=True)

    class Meta:
        verbose_name = 'Sesion de Mozo Virtual'
        verbose_name_plural = 'Sesiones de Mozo Virtual'

    def __str__(self):
        return f"Sesion Mesa {self.table.number} - {self.session_token}"
