from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from decimal import Decimal


class CashRegister(models.Model):
    name = models.CharField(max_length=100, verbose_name='Nombre')
    location = models.CharField(max_length=200, blank=True, verbose_name='Ubicacion')
    active = models.BooleanField(default=True, verbose_name='Activo')

    class Meta:
        verbose_name = 'Caja Registradora'
        verbose_name_plural = 'Cajas Registradoras'
        ordering = ['name']

    def __str__(self):
        return self.name

    @property
    def current_session(self):
        return self.sessions.filter(status='OPEN').first()


class CashSession(models.Model):
    STATUS_CHOICES = [
        ('OPEN', 'Abierta'),
        ('CLOSED', 'Cerrada'),
    ]

    cash_register = models.ForeignKey(
        CashRegister, on_delete=models.PROTECT,
        related_name='sessions', verbose_name='Caja'
    )
    operator = models.ForeignKey(
        User, on_delete=models.PROTECT,
        related_name='cash_sessions', verbose_name='Operador'
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='OPEN', verbose_name='Estado')
    opening_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0, verbose_name='Monto de Apertura')
    closing_amount = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True, verbose_name='Monto de Cierre')
    expected_closing_amount = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True, verbose_name='Monto Esperado')
    difference = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True, verbose_name='Diferencia')
    opened_at = models.DateTimeField(default=timezone.now)
    closed_at = models.DateTimeField(null=True, blank=True)
    notes = models.TextField(blank=True, verbose_name='Notas')

    class Meta:
        verbose_name = 'Sesion de Caja'
        verbose_name_plural = 'Sesiones de Caja'
        ordering = ['-opened_at']

    def __str__(self):
        return f"{self.cash_register.name} - {self.opened_at.strftime('%d/%m/%Y %H:%M')} ({self.get_status_display()})"

    @property
    def total_sales(self):
        return sum(p.amount for p in self.payments.filter(movement_type='SALE') if hasattr(p, 'movement_type')) or \
               sum(p.amount for p in self.payments.all())

    @property
    def calculated_expected_amount(self):
        """Calculate expected closing amount from movements"""
        total = self.opening_amount
        for movement in self.movements.all():
            if movement.movement_type in ('SALE', 'INCOME', 'DEPOSIT'):
                total += movement.amount
            elif movement.movement_type in ('REFUND', 'EXPENSE', 'WITHDRAWAL'):
                total -= movement.amount
        return total


class CashMovement(models.Model):
    MOVEMENT_TYPES = [
        ('SALE', 'Venta'),
        ('REFUND', 'Devolucion'),
        ('EXPENSE', 'Gasto'),
        ('INCOME', 'Ingreso'),
        ('WITHDRAWAL', 'Retiro'),
        ('DEPOSIT', 'Deposito'),
    ]

    session = models.ForeignKey(
        CashSession, on_delete=models.CASCADE,
        related_name='movements', verbose_name='Sesion'
    )
    movement_type = models.CharField(max_length=20, choices=MOVEMENT_TYPES, verbose_name='Tipo')
    amount = models.DecimalField(max_digits=12, decimal_places=2, verbose_name='Monto')
    description = models.CharField(max_length=300, verbose_name='Descripcion')
    reference = models.CharField(max_length=100, blank=True, verbose_name='Referencia')
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, verbose_name='Creado por')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Movimiento de Caja'
        verbose_name_plural = 'Movimientos de Caja'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.get_movement_type_display()} - ${self.amount} ({self.description})"


class Payment(models.Model):
    PAYMENT_METHODS = [
        ('CASH', 'Efectivo'),
        ('CARD', 'Tarjeta'),
        ('TRANSFER', 'Transferencia'),
        ('QR_PAYMENT', 'QR/Billetera'),
        ('MIXED', 'Mixto'),
    ]

    order = models.ForeignKey(
        'orders.Order', on_delete=models.PROTECT,
        related_name='payments', verbose_name='Comanda'
    )
    session = models.ForeignKey(
        CashSession, on_delete=models.PROTECT,
        related_name='payments', verbose_name='Sesion de Caja'
    )
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHODS, verbose_name='Metodo de Pago')
    amount = models.DecimalField(max_digits=12, decimal_places=2, verbose_name='Monto')
    change_given = models.DecimalField(max_digits=12, decimal_places=2, default=0, verbose_name='Vuelto')
    notes = models.CharField(max_length=300, blank=True, verbose_name='Notas')
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, verbose_name='Procesado por')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Pago'
        verbose_name_plural = 'Pagos'
        ordering = ['-created_at']

    def __str__(self):
        return f"Pago {self.order.order_number} - ${self.amount} ({self.get_payment_method_display()})"
