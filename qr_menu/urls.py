from django.urls import path
from . import views

app_name = 'qr_menu'

urlpatterns = [
    path('', views.public_menu, name='public_menu'),
    path('table/<int:table_pk>/', views.table_menu, name='table_menu'),
    path('qr-codes/', views.menu_qr_codes, name='qr_codes'),
]
