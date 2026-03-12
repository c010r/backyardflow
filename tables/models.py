from django.db import models
from django.conf import settings
import os
import io


class TableArea(models.Model):
    name = models.CharField(max_length=100, verbose_name='Nombre')
    description = models.TextField(blank=True, verbose_name='Descripcion')
    active = models.BooleanField(default=True, verbose_name='Activo')

    class Meta:
        verbose_name = 'Area'
        verbose_name_plural = 'Areas'
        ordering = ['name']

    def __str__(self):
        return self.name


class Table(models.Model):
    STATUS_CHOICES = [
        ('FREE', 'Libre'),
        ('OCCUPIED', 'Ocupada'),
        ('RESERVED', 'Reservada'),
        ('CLEANING', 'Limpieza'),
    ]

    number = models.PositiveIntegerField(verbose_name='Numero')
    area = models.ForeignKey(
        TableArea, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='tables', verbose_name='Area'
    )
    capacity = models.PositiveIntegerField(default=4, verbose_name='Capacidad')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='FREE', verbose_name='Estado')
    qr_code = models.ImageField(upload_to='tables/qr/', null=True, blank=True, verbose_name='Codigo QR')
    active = models.BooleanField(default=True, verbose_name='Activo')

    class Meta:
        verbose_name = 'Mesa'
        verbose_name_plural = 'Mesas'
        ordering = ['number']
        unique_together = [['number', 'area']]

    def __str__(self):
        area_name = self.area.name if self.area else 'Sin Area'
        return f"Mesa {self.number} - {area_name}"

    def generate_qr(self):
        """Generate QR code image for this table"""
        try:
            import qrcode
            from django.core.files.base import ContentFile

            # URL for the table's virtual menu
            url = f"/qr-menu/table/{self.pk}/"

            qr = qrcode.QRCode(version=1, box_size=10, border=5)
            qr.add_data(url)
            qr.make(fit=True)

            img = qr.make_image(fill_color='black', back_color='white')

            buffer = io.BytesIO()
            img.save(buffer, format='PNG')
            buffer.seek(0)

            filename = f'table_{self.number}_qr.png'
            self.qr_code.save(filename, ContentFile(buffer.read()), save=True)
            return True
        except Exception as e:
            return False

    @property
    def status_color(self):
        colors = {
            'FREE': 'success',
            'OCCUPIED': 'danger',
            'RESERVED': 'warning',
            'CLEANING': 'info',
        }
        return colors.get(self.status, 'secondary')


class Reservation(models.Model):
    STATUS_CHOICES = [
        ('PENDING', 'Pendiente'),
        ('CONFIRMED', 'Confirmada'),
        ('SEATED', 'Sentado'),
        ('CANCELLED', 'Cancelada'),
        ('NO_SHOW', 'No se presento'),
    ]

    table = models.ForeignKey(
        Table, on_delete=models.CASCADE,
        related_name='reservations', verbose_name='Mesa'
    )
    customer_name = models.CharField(max_length=200, verbose_name='Nombre del Cliente')
    customer_phone = models.CharField(max_length=50, blank=True, verbose_name='Telefono')
    date = models.DateField(verbose_name='Fecha')
    time = models.TimeField(verbose_name='Hora')
    party_size = models.PositiveIntegerField(default=2, verbose_name='Numero de Personas')
    notes = models.TextField(blank=True, verbose_name='Notas')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING', verbose_name='Estado')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Reserva'
        verbose_name_plural = 'Reservas'
        ordering = ['date', 'time']

    def __str__(self):
        return f"{self.customer_name} - Mesa {self.table.number} - {self.date} {self.time}"
