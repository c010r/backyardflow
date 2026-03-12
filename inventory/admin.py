from django.contrib import admin
from .models import Supplier, IngredientCategory, Ingredient, StockMovement, PurchaseOrder, PurchaseOrderItem


@admin.register(Supplier)
class SupplierAdmin(admin.ModelAdmin):
    list_display = ['name', 'contact_name', 'phone', 'email', 'active']
    list_filter = ['active']
    search_fields = ['name', 'contact_name', 'email']


@admin.register(IngredientCategory)
class IngredientCategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'description']
    search_fields = ['name']


@admin.register(Ingredient)
class IngredientAdmin(admin.ModelAdmin):
    list_display = ['name', 'category', 'unit', 'stock_quantity', 'min_stock', 'cost_per_unit', 'supplier', 'active']
    list_filter = ['category', 'unit', 'active']
    search_fields = ['name']
    list_editable = ['stock_quantity', 'min_stock']


@admin.register(StockMovement)
class StockMovementAdmin(admin.ModelAdmin):
    list_display = ['ingredient', 'movement_type', 'quantity', 'unit_cost', 'reason', 'created_by', 'created_at']
    list_filter = ['movement_type', 'created_at']
    search_fields = ['ingredient__name', 'reason']
    readonly_fields = ['created_at']


class PurchaseOrderItemInline(admin.TabularInline):
    model = PurchaseOrderItem
    extra = 1


@admin.register(PurchaseOrder)
class PurchaseOrderAdmin(admin.ModelAdmin):
    list_display = ['pk', 'supplier', 'order_date', 'expected_delivery', 'status', 'total_amount']
    list_filter = ['status', 'order_date']
    search_fields = ['supplier__name']
    inlines = [PurchaseOrderItemInline]
