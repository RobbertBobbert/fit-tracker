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
    
    #Спорт
    path('catalogue/exercise/add/', views.exercise_form, name='add_exercise'),
    path('catalogue/exercise/<int:exercise_id>/edit/', views.exercise_form, name='edit_exercise'),
    path('catalogue/exercise/<int:exercise_id>/delete/', views.delete_exercise, name='delete_exercise'),
    path('api/exercises/search/', views.api_search_exercises, name='api_search_exercises'),
]