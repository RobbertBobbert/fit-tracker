from django.contrib import admin
from .models import (
    app_user, UserProfile, food_catalogue, FoodCatalogueIngredient, 
    exercise_catalogue, ExerciseRecord, Meal, MealItem, DailyTarget
)

# ========== ПОЛЬЗОВАТЕЛИ И ПРОФИЛИ ==========
@admin.register(app_user)
class AppUserAdmin(admin.ModelAdmin):
    list_display = ('username', 'email', 'full_name', 'birth_date', 'gender', 'is_active', 'date_joined')
    list_filter = ('is_active', 'gender', 'date_joined')
    search_fields = ('username', 'email', 'full_name')
    readonly_fields = ('date_joined', 'last_login')
    fieldsets = (
        ('Основная информация', {
            'fields': ('username', 'email', 'full_name', 'birth_date', 'gender')
        }),
        ('Права доступа', {
            'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')
        }),
        ('Важные даты', {
            'fields': ('last_login', 'date_joined')
        }),
    )

@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'weight', 'height', 'body_fat', 'goal', 'activity_level', 'maintenance_calories')
    list_filter = ('goal', 'activity_level')
    search_fields = ('user__username', 'user__email')
    readonly_fields = ('bmi', 'bmr', 'maintenance_calories')
    fieldsets = (
        ('Пользователь', {
            'fields': ('user',)
        }),
        ('Антропометрия', {
            'fields': ('weight', 'height', 'body_fat')
        }),
        ('Цели и активность', {
            'fields': ('goal', 'activity_level')
        }),
        ('Целевые БЖУ', {
            'fields': ('target_protein', 'target_fat', 'target_carb', 'custom_targets_enabled', 'custom_calories')
        }),
        ('Рассчитанные показатели', {
            'fields': ('bmi', 'bmr', 'maintenance_calories'),
            'classes': ('collapse',)
        }),
    )


# ========== КАТАЛОГ (ПРОДУКТЫ И БЛЮДА) ==========
@admin.register(food_catalogue)
class FoodCatalogueAdmin(admin.ModelAdmin):
    list_display = ('name', 'is_dish', 'created_by', 'protein', 'carb', 'fat', 'calories', 'created_at', 'last_used')
    list_filter = ('is_dish', 'created_at', 'last_used')
    search_fields = ('name', 'created_by__username')
    readonly_fields = ('calories', 'created_at', 'updated_at')
    fieldsets = (
        ('Основное', {
            'fields': ('name', 'is_dish', 'created_by')
        }),
        ('Пищевая ценность (на 100г)', {
            'fields': ('protein', 'carb', 'fat', 'calories')
        }),
        ('Метаданные', {
            'fields': ('last_used', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('created_by')


@admin.register(FoodCatalogueIngredient)
class FoodCatalogueIngredientAdmin(admin.ModelAdmin):
    list_display = ('dish', 'ingredient', 'weight_grams', 'created_at')
    list_filter = ('created_at',)
    search_fields = ('dish__name', 'ingredient__name')
    raw_id_fields = ('dish', 'ingredient')
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('dish', 'ingredient')


# ========== УПРАЖНЕНИЯ ==========
@admin.register(exercise_catalogue)
class ExerciseCatalogueAdmin(admin.ModelAdmin):
    list_display = ('name', 'created_by', 'met', 'calories_per_hour', 'is_shared', 'created_at')
    list_filter = ('is_shared', 'created_at')
    search_fields = ('name', 'created_by__username')
    fieldsets = (
        ('Основное', {
            'fields': ('name', 'created_by', 'is_shared')
        }),
        ('Параметры расчёта', {
            'fields': ('met', 'calories_per_hour')
        }),
        ('Метаданные', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(ExerciseRecord)
class ExerciseRecordAdmin(admin.ModelAdmin):
    list_display = ('user', 'exercise', 'date', 'time', 'duration_minutes', 'calories_burned', 'created_at')
    list_filter = ('date', 'exercise')
    search_fields = ('user__username', 'exercise__name')
    readonly_fields = ('calories_burned', 'created_at')
    date_hierarchy = 'date'
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('user', 'exercise')


# ========== ПРИЁМЫ ПИЩИ ==========
@admin.register(Meal)
class MealAdmin(admin.ModelAdmin):
    list_display = ('user', 'date', 'time', 'created_at', 'total_calories')
    list_filter = ('date',)
    search_fields = ('user__username',)
    date_hierarchy = 'date'
    
    def total_calories(self, obj):
        return obj.total_calories()
    total_calories.short_description = 'Калории'
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('user').prefetch_related('items')


@admin.register(MealItem)
class MealItemAdmin(admin.ModelAdmin):
    list_display = ('meal', 'food', 'weight_grams', 'protein', 'carb', 'fat', 'calories')
    list_filter = ('meal__date',)
    search_fields = ('meal__user__username', 'food__name')
    raw_id_fields = ('meal', 'food')
    readonly_fields = ('protein', 'carb', 'fat', 'calories')
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('meal', 'meal__user', 'food')


# ========== ДНЕВНЫЕ ЦЕЛИ ==========
@admin.register(DailyTarget)
class DailyTargetAdmin(admin.ModelAdmin):
    list_display = ('user', 'date', 'calories', 'protein', 'fat', 'carb', 'is_custom')
    list_filter = ('date', 'is_custom')
    search_fields = ('user__username',)
    date_hierarchy = 'date'
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('user')