from django.urls import path
from . import views

app_name = 'training_django_app'

urlpatterns = [
    # Основные страницы
    path('', views.dashboard, name='dashboard'),
    path('register/', views.register_view, name='register'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('profile/', views.profile_view, name='profile'),
    path('profile/setup/', views.profile_setup_view, name='profile_setup'), 
    
    # Продукты
    path('catalogue/product/add/', views.product_form, name='add_product'),
    path('catalogue/product/<int:product_id>/edit/', views.product_form, name='edit_product'),
    path('catalogue/product/<int:product_id>/delete/', views.delete_product, name='delete_product'),
    path('catalogue/dish/add/', views.dish_form, name='add_dish'),
    path('catalogue/dish/<int:dish_id>/edit/', views.dish_form, name='edit_dish'),
    path('catalogue/dish/<int:dish_id>/delete/', views.delete_dish, name='delete_dish'),
    
    # API
    path('api/dish/save/', views.api_save_dish, name='api_save_dish'),
    path('api/user/products/', views.api_search_user_products, name='api_user_products'),
    path('api/toggle_custom_targets/', views.api_toggle_custom_targets, name='api_toggle_custom_targets'),
    path('api/dashboard/totals/', views.api_dashboard_totals, name='api_dashboard_totals'),

    #Спорт
    path('catalogue/exercise/add/', views.exercise_form, name='add_exercise'),
    path('catalogue/exercise/<int:exercise_id>/edit/', views.exercise_form, name='edit_exercise'),
    path('catalogue/exercise/<int:exercise_id>/delete/', views.delete_exercise, name='delete_exercise'),
    path('training/add/', views.add_training, name='add_training'),

    # API спорт
    path('api/exercises/search/', views.api_search_exercises, name='api_search_exercises'),
    path('api/training/save/', views.api_training_save, name='api_training_save'),
    path('training/<int:training_id>/edit/', views.edit_training, name='edit_training'),
    path('api/training/<int:training_id>/delete/', views.api_delete_training, name='api_delete_training'),
    path('api/training/<int:training_id>/update/', views.api_update_training, name='api_update_training'),

    # API для приёмов пищи
    path('meal/', views.meal_form, name='meal_form'),
    path('api/meal/save/', views.api_meal_save, name='api_meal_save'),
    path('api/meal/<int:meal_id>/delete/', views.api_delete_meal, name='api_delete_meal'),
    path('api/meal/<int:meal_id>/update_time/', views.api_meal_update_time, name='api_meal_update_time'),
    path('api/meal/item/add/', views.api_add_meal_item, name='api_add_meal_item'),
    path('api/meal/item/<int:item_id>/delete/', views.api_delete_meal_item, name='api_delete_meal_item'),
    path('api/meal/item/<int:item_id>/update/', views.api_update_meal_item_weight, name='api_update_meal_item_weight'),
    path('api/meal/<int:meal_id>/totals/', views.api_meal_totals, name='api_meal_totals'),
]