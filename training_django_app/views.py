from django.shortcuts import render, redirect
from django.contrib.auth import login, logout
from django.contrib.auth.hashers import check_password
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_http_methods
from django.utils import timezone
from django.db import transaction
from django.db.models import Sum
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from .forms import RegistrationForm, LoginForm, DefaultProfileForm, UserEditForm, ProfileEditForm, ProductForm, DishForm
from .models import app_user, food_catalogue, FoodCatalogueIngredient, exercise_entry, Meal, MealItem
from datetime import date
import json


def register_view(request):
    # регистрация нового пользователя
    
    if request.user.is_authenticated:
        return redirect('training_django_app:dashboard')
    
    if request.method == 'POST':
        form = RegistrationForm(request.POST)
        
        if form.is_valid():
            user = form.save()
            login(request, user)
            # После регистрации сразу на страницу заполнения профиля
            messages.info(request, 'Пожалуйста, заполните ваш профиль для расчёта дневной нормы КБЖУ.')
            return redirect('training_django_app:profile_setup')
        else:
            messages.error(request, 'Пожалуйста, исправьте ошибки в форме')
    else:
        form = RegistrationForm()
    
    context = {
        'form': form,
        'title': 'Регистрация'
    }
    return render(request, 'training_django_app/register.html', context)


def login_view(request):
    #вход через чекпссворд, аутентификейт сосать!
    if request.user.is_authenticated:
        return redirect('training_django_app:dashboard')
    
    if request.method == 'POST':
        form = LoginForm(request.POST)
        if form.is_valid():
            username = form.cleaned_data['username']
            password = form.cleaned_data['password']
            
            # Пытаемся найти пользователя по username или email
            user = None
            try:
                if '@' in username:
                    user = app_user.objects.get(email=username)
                else:
                    user = app_user.objects.get(username=username)
            except app_user.DoesNotExist:
                user = None
            
            # Прямая проверка пароля (минуя ебаный забаговавший authenticate)
            if user and check_password(password, user.password):
                login(request, user)
                messages.success(request, f'С возвращением, {user.full_name}! 👋')
                next_url = request.GET.get('next', 'training_django_app:dashboard')
                return redirect(next_url)
            else:
                messages.error(request, 'Неверное имя пользователя/email или пароль ❌')
        else:
            messages.error(request, 'Пожалуйста, заполните все поля')
    else:
        form = LoginForm()
    
    context = {
        'form': form,
        'title': 'Вход'
    }
    return render(request, 'training_django_app/login.html', context)


@require_http_methods(['POST'])
def logout_view(request):
    
    # Выхд из системы
    
    logout(request)
    messages.info(request, 'Вы вышли из аккаунта 👋')
    return redirect('training_django_app:login')


def profile_setup_view(request):
   # после реги заполняем профиль
    if not request.user.is_authenticated:
        return redirect('training_django_app:login')
    
    profile = request.user.profile
    
    # Если профиль уже заполнен (не значения по умолчанию), перенаправляем на дашборд
    if profile.weight != 70 and profile.height != 170:
        return redirect('training_django_app:dashboard')
    
    if request.method == 'POST':
        form = DefaultProfileForm(request.POST, instance=profile)
        if form.is_valid():
            form.save()
            profile.calculate_daily_targets()
            profile.save()
            
            messages.success(request, '🎉 Отлично! Профиль заполнен. Рассчитана ваша дневная норма КБЖУ.')
            return redirect('training_django_app:dashboard')
        else:
            messages.error(request, 'Пожалуйста, исправьте ошибки в форме')
    else:
        form = DefaultProfileForm(instance=profile)
    
    context = {
        'form': form,
        'title': 'Заполнение профиля'
    }
    return render(request, 'training_django_app/profile_setup.html', context)


def profile_view(request):
    #профиль
    if not request.user.is_authenticated:
        return redirect('training_django_app:login')
    
    profile = request.user.profile
    user = request.user
    
    # Обработка формы редактирования пользователя
    if request.method == 'POST':
        if 'edit_user' in request.POST:
            user_form = UserEditForm(request.POST, instance=user)
            if user_form.is_valid():
                user_form.save()
                messages.success(request, 'Личная информация обновлена! ✅')
                return redirect('training_django_app:profile')
            else:
                messages.error(request, 'Пожалуйста, исправьте ошибки в форме')
        else:
            form = ProfileEditForm(request.POST, instance=profile)
            if form.is_valid():
                form.save()
                profile.calculate_daily_targets()
                profile.save()
                messages.success(request, 'Профиль успешно обновлён! ✅')
                return redirect('training_django_app:profile')
            else:
                messages.error(request, 'Пожалуйста, исправьте ошибки в форме')
    
    # GET — показываем формы
    user_form = UserEditForm(instance=user)
    profile_form = ProfileEditForm(instance=profile)
    
    # Рассчитываем целевую калорийность и БЖУ
    targets = profile.calculate_daily_targets()
    
    # Получаем продукты и блюда пользователя
    user_products = food_catalogue.objects.filter(user=request.user, is_dish=False).order_by('-last_used', '-created_at')
    user_dishes = food_catalogue.objects.filter(user=request.user, is_dish=True).order_by('-last_used', '-created_at')
    
    context = {
        'user_form': user_form,
        'profile_form': profile_form,
        'profile': profile,
        'user': user,
        'targets': targets,
        'user_products': user_products,
        'user_dishes': user_dishes,
        'title': 'Мой профиль'
    }
    return render(request, 'training_django_app/profile.html', context)


@login_required
@require_http_methods(['GET'])
def dashboard(request):
    #НеДамБорд
    today = timezone.now().date()
    
    # Получаем все приёмы пищи за сегодня
    meals = Meal.objects.filter(user=request.user, date=today).prefetch_related('items__food')
    
    # Подсчёт итогов за день
    total_calories = 0
    total_protein = 0
    total_fat = 0
    total_carb = 0
    
    for meal in meals:
        total_calories += meal.total_calories()
        total_protein += meal.total_protein()
        total_fat += meal.total_fat()
        total_carb += meal.total_carb()
    
    # Сожжённые калории
    calories_burnt_agg = exercise_entry.objects.filter(
        user=request.user, date=today
    ).aggregate(total_burnt=Sum('calories_exercise'))
    calories_burnt_agg_value = calories_burnt_agg['total_burnt'] or 0
    
    balance = total_calories - calories_burnt_agg_value
    
    context = {
        'today': today,
        'meals': meals,
        'total_calories': round(total_calories, 1),
        'total_protein': round(total_protein, 1),
        'total_fat': round(total_fat, 1),
        'total_carb': round(total_carb, 1),
        'calories_burnt_agg_value': round(calories_burnt_agg_value, 1),
        'balance': round(balance, 1),
    }
    return render(request, 'training_django_app/dashboard.html', context)


@login_required
def product_form(request, product_id=None):
    
    # Универсальная форма для создания и редактирования продукта
    # - Если product_id передан: редактируем существующий продукт
    # - Если нет: создаём новый
    
    if product_id:
        # Режим редактирования
        product = get_object_or_404(food_catalogue, id=product_id, user=request.user, is_dish=False)
        title = 'Редактировать продукт'
        submit_text = '💾 Сохранить изменения'
    else:
        # Режим создания
        product = None
        title = 'Добавить продукт'
        submit_text = '➕ Добавить продукт'
    
    if request.method == 'POST':
        form = ProductForm(request.POST, instance=product)
        if form.is_valid():
            new_product = form.save(commit=False)
            new_product.user = request.user
            new_product.is_dish = False
            new_product.save()
            messages.success(request, f'✅ Продукт "{new_product.name}" сохранён!')
            return redirect('training_django_app:profile')
        else:
            messages.error(request, 'Пожалуйста, исправьте ошибки в форме')
    else:
        form = ProductForm(instance=product)
    
    context = {
        'form': form,
        'title': title,
        'submit_text': submit_text,
        'is_edit': product_id is not None,
        'product_id': product_id,
    }
    return render(request, 'training_django_app/product_form.html', context)


@login_required
@require_http_methods(['POST'])
def delete_product(request, product_id):
    
    # Удаление продукта
    
    product = get_object_or_404(food_catalogue, id=product_id, user=request.user, is_dish=False)
    product_name = product.name
    product.delete()
    messages.success(request, f'🗑️ Продукт "{product_name}" удалён!')
    return redirect('training_django_app:profile')


@login_required
@require_http_methods(['POST'])
def api_save_dish(request):
    
    # API для сохранения блюда с ингредиентами
    # Принимает JSON: { "name": "Название", "ingredients": [{"product_id": 1, "weight_grams": 100}, ...] }
    
    try:
        data = json.loads(request.body)
        dish_name = data.get('name', '').strip()
        ingredients_data = data.get('ingredients', [])
        
        # Проверка названия
        if not dish_name:
            return JsonResponse({'error': 'Название блюда обязательно'}, status=400)
        
        # Проверка: есть ли ингредиенты
        if not ingredients_data:
            return JsonResponse({'error': 'Добавьте хотя бы один ингредиент'}, status=400)
        
        # Проверка: нет ли уже блюда с таким названием у пользователя
        if food_catalogue.objects.filter(user=request.user, name__iexact=dish_name, is_dish=True).exists():
            return JsonResponse({'error': 'Блюдо с таким названием уже существует'}, status=400)
        
        # ВСЁ В ОДНОЙ ТРАНЗАКЦИИ (если что-то упадёт — откатится)
        with transaction.atomic():
            # 1. Создаём блюдо
            dish = food_catalogue.objects.create(
                user=request.user,
                name=dish_name,
                is_dish=True,
                protein=0,
                fat=0,
                carb=0,
                calories=0
            )
            
            # 2. Создаём ингредиенты
            for item in ingredients_data:
                product_id = item.get('product_id')
                weight_grams = item.get('weight_grams', 0)
                
                if not product_id or weight_grams <= 0:
                    continue  # пропускаем некорректные
                
                # Проверяем, существует ли продукт и принадлежит ли пользователю
                try:
                    product = food_catalogue.objects.get(id=product_id, user=request.user)
                except food_catalogue.DoesNotExist:
                    continue  # продукт не найден — пропускаем
                
                # Создаём ингредиент (БЖУ пересчитаются автоматически через save())
                FoodCatalogueIngredient.objects.create(
                    dish=dish,
                    ingredient=product,
                    weight_grams=weight_grams
                )
            
            # 3. После добавления всех ингредиентов БЖУ уже пересчитано
            # (каждый ингредиент при создании вызывал update_from_ingredients)
        
        # Возвращаем данные созданного блюда
        return JsonResponse({
            'success': True,
            'dish_id': dish.id,
            'name': dish.name,
            'protein': dish.protein,
            'fat': dish.fat,
            'carb': dish.carb,
            'calories': dish.calories
        })
        
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Неверный формат данных'}, status=400)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)
    

@login_required
@require_http_methods(['GET'])
def api_search_user_products(request):
    
    # API для получения всех продуктов пользователя (is_dish=False)
    
    products = food_catalogue.objects.filter(
        user=request.user, 
        is_dish=False
    ).order_by('-last_used', '-created_at')
    
    data = [{
        'id': p.id,
        'name': p.name,
        'protein': p.protein,
        'fat': p.fat,
        'carb': p.carb,
        'calories': p.calories
    } for p in products]
    
    return JsonResponse(data, safe=False)