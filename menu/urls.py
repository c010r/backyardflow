from django.urls import path
from . import views

app_name = 'menu'

urlpatterns = [
    path('', views.menu_dashboard, name='dashboard'),
    path('items/', views.MenuItemListView.as_view(), name='item_list'),
    path('items/create/', views.MenuItemCreateView.as_view(), name='item_create'),
    path('items/<int:pk>/edit/', views.MenuItemUpdateView.as_view(), name='item_update'),
    path('items/<int:pk>/delete/', views.MenuItemDeleteView.as_view(), name='item_delete'),
    path('categories/', views.MenuCategoryListView.as_view(), name='category_list'),
    path('categories/create/', views.MenuCategoryCreateView.as_view(), name='category_create'),
    path('categories/<int:pk>/edit/', views.MenuCategoryUpdateView.as_view(), name='category_update'),
    path('recipes/<int:pk>/', views.RecipeDetailView.as_view(), name='recipe_detail'),
    path('recipes/create/<int:item_pk>/', views.recipe_create, name='recipe_create'),
    path('recipes/<int:pk>/edit/', views.recipe_update, name='recipe_update'),
]
