from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from decimal import Decimal
from datetime import timedelta


class StaffMember(models.Model):
    ROLE_CHOICES = [
        ('MANAGER', 'Gerente'),
        ('WAITER', 'Mozo'),
        ('BARTENDER', 'Bartender'),
        ('CHEF', 'Cocinero'),
        ('CASHIER', 'Cajero'),
        ('CLEANER', 'Limpieza'),
    ]
    PAYMENT_TYPES = [
        ('MONTHLY', 'Mensual'),
        ('HOURLY', 'Por Hora'),
    ]

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='staff_profile', verbose_name='Usuario')
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, verbose_name='Rol')
    phone = models.CharField(max_length=50, blank=True, verbose_name='Telefono')
    address = models.TextField(blank=True, verbose_name='Direccion')
    hire_date = models.DateField(default=timezone.now, verbose_name='Fecha de Ingreso')
    birth_date = models.DateField(null=True, blank=True, verbose_name='Fecha de Nacimiento')
    base_salary = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name='Salario Base')
    hourly_rate = models.DecimalField(max_digits=8, decimal_places=2, default=0, verbose_name='Tarifa por Hora')
    payment_type = models.CharField(max_length=20, choices=PAYMENT_TYPES, default='MONTHLY', verbose_name='Tipo de Pago')
    dni = models.CharField(max_length=20, blank=True, verbose_name='DNI')
    emergency_contact = models.CharField(max_length=200, blank=True, verbose_name='Contacto de Emergencia')
    active = models.BooleanField(default=True, verbose_name='Activo')

    class Meta:
        verbose_name = 'Miembro del Personal'
        verbose_name_plural = 'Personal'
        ordering = ['user__last_name', 'user__first_name']

    def __str__(self):
        return f"{self.user.get_full_name() or self.user.username} ({self.get_role_display()})"

    @property
    def full_name(self):
        return self.user.get_full_name() or self.user.username

    def total_hours_in_period(self, start_date, end_date):
        """Calculate total hours worked in a period"""
        shifts = self.shifts.filter(date__gte=start_date, date__lte=end_date)
        total = sum(s.hours_worked for s in shifts if s.hours_worked)
        return total


class WorkShift(models.Model):
    SHIFT_TYPES = [
        ('MORNING', 'Manana'),
        ('AFTERNOON', 'Tarde'),
        ('NIGHT', 'Noche'),
        ('FULL', 'Jornada Completa'),
    ]

    staff_member = models.ForeignKey(
        StaffMember, on_delete=models.CASCADE,
        related_name='shifts', verbose_name='Personal'
    )
    date = models.DateField(verbose_name='Fecha')
    start_time = models.TimeField(verbose_name='Hora de Entrada')
    end_time = models.TimeField(null=True, blank=True, verbose_name='Hora de Salida')
    hours_worked = models.DecimalField(max_digits=5, decimal_places=2, default=0, verbose_name='Horas Trabajadas')
    shift_type = models.CharField(max_length=20, choices=SHIFT_TYPES, default='MORNING', verbose_name='Tipo de Turno')
    notes = models.CharField(max_length=300, blank=True, verbose_name='Notas')

    class Meta:
        verbose_name = 'Turno de Trabajo'
        verbose_name_plural = 'Turnos de Trabajo'
        ordering = ['-date', 'start_time']

    def __str__(self):
        return f"{self.staff_member} - {self.date} {self.get_shift_type_display()}"

    def save(self, *args, **kwargs):
        if self.start_time and self.end_time:
            from datetime import datetime, date
            start_dt = datetime.combine(date.today(), self.start_time)
            end_dt = datetime.combine(date.today(), self.end_time)
            if end_dt < start_dt:
                end_dt += timedelta(days=1)
            diff = end_dt - start_dt
            self.hours_worked = Decimal(str(round(diff.total_seconds() / 3600, 2)))
        super().save(*args, **kwargs)


class SalaryAdvance(models.Model):
    staff_member = models.ForeignKey(
        StaffMember, on_delete=models.CASCADE,
        related_name='advances', verbose_name='Personal'
    )
    amount = models.DecimalField(max_digits=10, decimal_places=2, verbose_name='Monto')
    date = models.DateField(default=timezone.now, verbose_name='Fecha')
    reason = models.CharField(max_length=300, blank=True, verbose_name='Motivo')
    approved_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True,
        verbose_name='Aprobado por'
    )
    settled = models.BooleanField(default=False, verbose_name='Liquidado')

    class Meta:
        verbose_name = 'Adelanto de Salario'
        verbose_name_plural = 'Adelantos de Salario'
        ordering = ['-date']

    def __str__(self):
        return f"{self.staff_member} - ${self.amount} ({self.date})"


class SalarySettlement(models.Model):
    STATUS_CHOICES = [
        ('DRAFT', 'Borrador'),
        ('APPROVED', 'Aprobado'),
        ('PAID', 'Pagado'),
    ]
    PAYMENT_METHODS = [
        ('CASH', 'Efectivo'),
        ('TRANSFER', 'Transferencia'),
    ]

    staff_member = models.ForeignKey(
        StaffMember, on_delete=models.CASCADE,
        related_name='settlements', verbose_name='Personal'
    )
    period_start = models.DateField(verbose_name='Inicio del Periodo')
    period_end = models.DateField(verbose_name='Fin del Periodo')
    base_amount = models.DecimalField(max_digits=10, decimal_places=2, verbose_name='Monto Base')
    bonuses = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name='Bonificaciones')
    deductions = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name='Deducciones')
    advances_deducted = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name='Adelantos Descontados')
    total_amount = models.DecimalField(max_digits=10, decimal_places=2, verbose_name='Total a Pagar')
    payment_date = models.DateField(null=True, blank=True, verbose_name='Fecha de Pago')
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHODS, default='CASH', verbose_name='Metodo de Pago')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='DRAFT', verbose_name='Estado')
    notes = models.TextField(blank=True, verbose_name='Notas')
    generated_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, verbose_name='Generado por')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Liquidacion de Salario'
        verbose_name_plural = 'Liquidaciones de Salario'
        ordering = ['-period_end']

    def __str__(self):
        return f"{self.staff_member} - {self.period_start} a {self.period_end}"

    def calculate_total(self):
        self.total_amount = self.base_amount + self.bonuses - self.deductions - self.advances_deducted
        return self.total_amount


class SalaryItem(models.Model):
    ITEM_TYPES = [
        ('EARNING', 'Haberes'),
        ('DEDUCTION', 'Descuento'),
    ]

    settlement = models.ForeignKey(
        SalarySettlement, on_delete=models.CASCADE,
        related_name='items', verbose_name='Liquidacion'
    )
    concept = models.CharField(max_length=200, verbose_name='Concepto')
    item_type = models.CharField(max_length=20, choices=ITEM_TYPES, verbose_name='Tipo')
    amount = models.DecimalField(max_digits=10, decimal_places=2, verbose_name='Monto')

    class Meta:
        verbose_name = 'Item de Liquidacion'
        verbose_name_plural = 'Items de Liquidacion'

    def __str__(self):
        return f"{self.concept} - ${self.amount}"
