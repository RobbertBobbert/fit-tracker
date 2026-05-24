from django.urls import path
from . import views

app_name = 'training_django_app'

urlpatterns = [
    path('',views.dashboard, name='dashboard'),
    path('register/', views.register_view, name='register'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('profile/', views.profile_view, name='profile'),
    path('profile/setup/', views.profile_setup_view, name='profile_setup'), 
    #path('food/add/',views.food_history_view.as_view(), name='food_add'),,
    #path('exercise/add/',views.exercise_add_view.as_view(), name='exercise_add'),
    #path('daily_log/<int:pk>/',views.daily_log.as_view(), name='daily_log'),
]