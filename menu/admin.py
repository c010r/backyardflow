from django.contrib import admin
from .models import MenuCategory, MenuItem, Recipe, RecipeIngredient


@admin.register(MenuCategory)
class MenuCategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'display_order', 'active']
    list_filter = ['active']
    search_fields = ['name']
    list_editable = ['display_order', 'active']


class RecipeIngredientInline(admin.TabularInline):
    model = RecipeIngredient
    extra = 2


class RecipeInline(admin.StackedInline):
    model = Recipe
    extra = 0


@admin.register(MenuItem)
class MenuItemAdmin(admin.ModelAdmin):
    list_display = ['name', 'category', 'item_type', 'price', 'available', 'featured', 'active']
    list_filter = ['category', 'item_type', 'available', 'featured', 'active']
    search_fields = ['name', 'description']
    list_editable = ['available', 'featured']
    inlines = [RecipeInline]


@admin.register(Recipe)
class RecipeAdmin(admin.ModelAdmin):
    list_display = ['menu_item', 'servings', 'preparation_time']
    search_fields = ['menu_item__name']
    inlines = [RecipeIngredientInline]
