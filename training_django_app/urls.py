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
    #path('catalogue/dish/add/', views.add_dish, name='add_dish'),
    
    # API
    path('api/dish/save/', views.api_save_dish, name='api_save_dish'),
    path('api/user/products/', views.api_search_user_products, name='api_user_products'),
    
    # Закомментированные старые маршруты 
    # path('food/add/', views.add_food_entry, name='add_food_entry'),
    # path('api/food/search/', views.api_search_food, name='api_search_food'),
    # path('api/food/add/', views.api_add_food_item, name='api_add_food_item'),
    # path('api/food/save/', views.api_save_meal, name='api_save_meal'),
]