from django import forms
from .models import CashRegister, CashSession, CashMovement, Payment
from decimal import Decimal


class OpenSessionForm(forms.ModelForm):
    class Meta:
        model = CashSession
        fields = ['cash_register', 'opening_amount', 'notes']
        widgets = {
            'cash_register': forms.Select(attrs={'class': 'form-select'}),
            'opening_amount': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
        }


class CloseSessionForm(forms.ModelForm):
    class Meta:
        model = CashSession
        fields = ['closing_amount', 'notes']
        widgets = {
            'closing_amount': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }


class CashMovementForm(forms.ModelForm):
    class Meta:
        model = CashMovement
        fields = ['session', 'movement_type', 'amount', 'description', 'reference']
        widgets = {
            'session': forms.Select(attrs={'class': 'form-select'}),
            'movement_type': forms.Select(attrs={'class': 'form-select'}),
            'amount': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'description': forms.TextInput(attrs={'class': 'form-control'}),
            'reference': forms.TextInput(attrs={'class': 'form-control'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['session'].queryset = CashSession.objects.filter(status='OPEN')


class PaymentForm(forms.ModelForm):
    amount_received = forms.DecimalField(
        max_digits=12, decimal_places=2, required=False,
        widget=forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
        label='Monto Recibido (efectivo)'
    )

    class Meta:
        model = Payment
        fields = ['payment_method', 'amount', 'notes']
        widgets = {
            'payment_method': forms.Select(attrs={'class': 'form-select'}),
            'amount': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'notes': forms.TextInput(attrs={'class': 'form-control'}),
        }


class CashRegisterForm(forms.ModelForm):
    class Meta:
        model = CashRegister
        fields = ['name', 'location', 'active']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'location': forms.TextInput(attrs={'class': 'form-control'}),
        }
