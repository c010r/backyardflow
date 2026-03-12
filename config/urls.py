from django.urls import path
from . import views

app_name = 'config'

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('usuarios/', views.user_list, name='user_list'),
    path('usuarios/nuevo/', views.user_create, name='user_create'),
    path('usuarios/<int:pk>/editar/', views.user_edit, name='user_edit'),
    path('usuarios/<int:pk>/password/', views.user_change_password, name='user_change_password'),
    path('usuarios/<int:pk>/activar/', views.user_toggle_active, name='user_toggle_active'),
    path('usuarios/<int:pk>/eliminar/', views.user_delete, name='user_delete'),
    path('ajustes/', views.system_settings, name='settings'),
    path('cajas/', views.cash_register_list, name='cash_register_list'),
    path('cajas/nueva/', views.cash_register_create, name='cash_register_create'),
    path('cajas/<int:pk>/editar/', views.cash_register_edit, name='cash_register_edit'),
    path('areas/', views.table_area_list, name='table_area_list'),
    path('areas/nueva/', views.table_area_create, name='table_area_create'),
    path('areas/<int:pk>/editar/', views.table_area_edit, name='table_area_edit'),
]
