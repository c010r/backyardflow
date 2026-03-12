from django.db import models


class SystemSettings(models.Model):
    restaurant_name = models.CharField('Nombre del local', max_length=100, default='BackyardFlow POS')
    address = models.CharField('Dirección', max_length=200, blank=True)
    phone = models.CharField('Teléfono', max_length=30, blank=True)
    email = models.EmailField('Email', blank=True)
    currency_symbol = models.CharField('Símbolo de moneda', max_length=5, default='$')
    tax_percent = models.DecimalField('IVA %', max_digits=5, decimal_places=2, default=0)
    logo = models.ImageField('Logo', upload_to='system/', blank=True, null=True)
    receipt_footer = models.TextField('Pie de ticket', blank=True)

    class Meta:
        verbose_name = 'Configuración del sistema'

    def __str__(self):
        return self.restaurant_name

    @classmethod
    def get(cls):
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj
