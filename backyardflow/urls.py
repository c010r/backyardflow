"""BackyardFlow POS URL Configuration"""
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.contrib.auth import views as auth_views
from . import views

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('accounts/login/', auth_views.LoginView.as_view(template_name='registration/login.html'), name='login'),
    path('accounts/logout/', auth_views.LogoutView.as_view(), name='logout'),
    path('inventory/', include('inventory.urls', namespace='inventory')),
    path('menu/', include('menu.urls', namespace='menu')),
    path('tables/', include('tables.urls', namespace='tables')),
    path('orders/', include('orders.urls', namespace='orders')),
    path('cash-register/', include('cash_register.urls', namespace='cash_register')),
    path('staff/', include('staff.urls', namespace='staff')),
    path('qr-menu/', include('qr_menu.urls', namespace='qr_menu')),
    path('admin-panel/', include('config.urls', namespace='config')),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT) \
  + static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
