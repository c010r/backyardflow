from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm, SetPasswordForm
from .models import SystemSettings


class UserCreateForm(UserCreationForm):
    first_name = forms.CharField(label='Nombre', max_length=30, required=True)
    last_name = forms.CharField(label='Apellido', max_length=150, required=True)
    email = forms.EmailField(label='Email', required=False)
    is_staff = forms.BooleanField(label='Es administrador', required=False)
    is_active = forms.BooleanField(label='Activo', required=False, initial=True)

    class Meta:
        model = User
        fields = ('username', 'first_name', 'last_name', 'email', 'is_staff', 'is_active', 'password1', 'password2')


class UserEditForm(forms.ModelForm):
    first_name = forms.CharField(label='Nombre', max_length=30, required=True)
    last_name = forms.CharField(label='Apellido', max_length=150, required=True)
    email = forms.EmailField(label='Email', required=False)
    is_staff = forms.BooleanField(label='Es administrador', required=False)
    is_active = forms.BooleanField(label='Activo', required=False)

    class Meta:
        model = User
        fields = ('username', 'first_name', 'last_name', 'email', 'is_staff', 'is_active')


class ChangePasswordForm(SetPasswordForm):
    pass


class SystemSettingsForm(forms.ModelForm):
    class Meta:
        model = SystemSettings
        fields = '__all__'
        widgets = {
            'receipt_footer': forms.Textarea(attrs={'rows': 3}),
        }
