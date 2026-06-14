from django.shortcuts import render, redirect
from django.contrib.auth import login, logout
from django.contrib.auth.hashers import check_password
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_http_methods
from django.utils import timezone
from django.db import transaction
from django.db.models import Sum, Q, Case, When, Value, IntegerField
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from .forms import (
    RegistrationForm, LoginForm, DefaultProfileForm, UserEditForm,
    ProfileEditForm, ProductForm, DishForm, ExerciseForm
)
from .models import (
    app_user, food_catalogue, FoodCatalogueIngredient, exercise_catalogue,
    Meal, MealItem, ExerciseRecord
)
from datetime import datetime, timedelta
from .utils import get_targets_for_date, update_future_daily_targets
import json


def register_view(request):
    # Регистрация нового пользователя
    if request.user.is_authenticated:
        return redirect('training_django_app:dashboard')

    if request.method == 'POST':
        form = RegistrationForm(request.POST)

        if form.is_valid():
            user = form.save()
            login(request, user)
            # После регистрации сразу на страницу заполнения профиля
            messages.info(
                request,
                'Пожалуйста, заполните ваш профиль для расчёта дневной нормы КБЖУ.'
            )
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
    # Вход через прямую проверку пароля (без authenticate)
    if request.user.is_authenticated:
        return redirect('training_django_app:dashboard')

    if request.method == 'POST':
        form = LoginForm(request.POST)
        if form.is_valid():
            username = form.cleaned_data['username']
            password = form.cleaned_data['password']

            # Поиск пользователя по username или email
            user = None
            try:
                if '@' in username:
                    user = app_user.objects.get(email=username)
                else:
                    user = app_user.objects.get(username=username)
            except app_user.DoesNotExist:
                user = None

            # Прямая проверка пароля (минуя authenticate)
            if user and check_password(password, user.password):
                login(request, user)
                messages.success(request, f'С возвращением, {user.full_name}!')
                next_url = request.GET.get('next', 'training_django_app:dashboard')
                return redirect(next_url)
            else:
                messages.error(
                    request,
                    'Неверное имя пользователя/email или пароль ❌'
                )
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
    # Выход из системы
    logout(request)
    messages.info(request, 'Вы вышли из аккаунта')
    return redirect('training_django_app:login')


def profile_setup_view(request):
    # Первоначальное заполнение профиля после регистрации
    if not request.user.is_authenticated:
        return redirect('training_django_app:login')

    profile = request.user.profile
    # Если профиль уже заполнен (не значения по умолчанию)
    if profile.weight != 70 and profile.height != 170:
        return redirect('training_django_app:dashboard')

    if request.method == 'POST':
        form = DefaultProfileForm(request.POST, instance=profile)
        if form.is_valid():
            form.save()
            profile.calculate_daily_targets()
            profile.save()
            messages.success(
                request,
                'Отлично! Профиль заполнен. Рассчитана ваша дневная норма КБЖУ.'
            )
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
    # Страница профиля пользователя
    if not request.user.is_authenticated:
        return redirect('training_django_app:login')

    profile = request.user.profile
    user = request.user

    # Обработка POST-запросов
    if request.method == 'POST':
        if 'edit_user' in request.POST:
            # Редактирование личной информации
            user_form = UserEditForm(request.POST, instance=user)
            if user_form.is_valid():
                user_form.save()
                messages.success(request, 'Личная информация обновлена!')
                return redirect('training_django_app:profile')
            else:
                messages.error(request, 'Пожалуйста, исправьте ошибки в форме')

        elif 'update_custom_targets' in request.POST:
            # Сохранение ручных целей (калории рассчитываются из БЖУ)
            profile.custom_targets_enabled = True

            if request.POST.get('target_protein'):
                profile.target_protein = float(request.POST.get('target_protein'))
            if request.POST.get('target_fat'):
                profile.target_fat = float(request.POST.get('target_fat'))
            if request.POST.get('target_carb'):
                profile.target_carb = float(request.POST.get('target_carb'))

            # Расчёт калорий из БЖУ
            protein = profile.target_protein or 0
            fat = profile.target_fat or 0
            carb = profile.target_carb or 0
            profile.custom_calories = round(
                (protein * 4) + (fat * 9) + (carb * 4), 1
            )
            profile.save()
            messages.success(request, 'Ручные цели сохранены!')
            update_future_daily_targets(request.user)
            return redirect('training_django_app:profile')

        else:
            # Редактирование антропометрии
            form = ProfileEditForm(request.POST, instance=profile)
            if form.is_valid():
                form.save()
                profile.calculate_daily_targets()
                profile.save()
                messages.success(request, 'Профиль успешно обновлён!')
                update_future_daily_targets(request.user)
                return redirect('training_django_app:profile')
            else:
                messages.error(request, 'Пожалуйста, исправьте ошибки в форме')

    # GET-запрос: показываем формы
    user_form = UserEditForm(instance=user)
    profile_form = ProfileEditForm(instance=profile)

    # Расчёт целевых КБЖУ
    targets = profile.calculate_daily_targets()

    # Продукты: только свои (созданные пользователем)
    user_products = food_catalogue.objects.filter(
        created_by=request.user,
        is_dish=False
    ).order_by('-last_used', '-created_at')

    # Блюда: только свои
    user_dishes = food_catalogue.objects.filter(
        created_by=request.user,
        is_dish=True
    ).order_by('-last_used', '-created_at')

    # Упражнения: только свои
    user_exercises = exercise_catalogue.objects.filter(
        created_by=request.user
    ).order_by('name')

    context = {
        'user_form': user_form,
        'profile_form': profile_form,
        'profile': profile,
        'user': user,
        'targets': targets,
        'user_products': user_products,
        'user_dishes': user_dishes,
        'user_exercises': user_exercises,
        'title': 'Мой профиль',
    }
    return render(request, 'training_django_app/profile.html', context)


@login_required
@require_http_methods(['POST'])
def api_toggle_custom_targets(request):
    # Переключение ручного/автоматического режима целей
    try:
        data = json.loads(request.body)
        enabled = data.get('enabled', False)

        profile = request.user.profile
        profile.custom_targets_enabled = enabled

        # Если включаем ручной режим, но нет сохранённых целей
        if enabled and not profile.custom_calories:
            targets = profile.calculate_daily_targets()
            profile.custom_calories = targets['calories']
            profile.target_protein = targets['protein']
            profile.target_fat = targets['fat']
            profile.target_carb = targets['carb']

        profile.save()
        update_future_daily_targets(request.user)

        return JsonResponse({'success': True})

    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@login_required
@require_http_methods(['GET'])
def dashboard(request):
    # Главная страница дашборд
    # Получаем дату из GET-параметра или сегодня
    date_str = request.GET.get('date')
    if date_str:
        try:
            current_date = datetime.strptime(date_str, '%Y-%m-%d').date()
        except ValueError:
            current_date = timezone.now().date()
    else:
        current_date = timezone.now().date()

    prev_date = current_date - timedelta(days=1)   # Предыдущий день
    next_date = current_date + timedelta(days=1)   # Следующий день

    # Приёмы пищи за выбранную дату
    meals = Meal.objects.filter(
        user=request.user,
        date=current_date
    ).prefetch_related('items__food')

    # Тренировки за выбранную дату
    exercises = ExerciseRecord.objects.filter(
        user=request.user,
        date=current_date
    ).select_related('exercise')

    # Подсчёт итогов за день (еда)
    total_calories = 0
    total_protein = 0
    total_fat = 0
    total_carb = 0

    for meal in meals:
        total_calories += meal.total_calories()
        total_protein += meal.total_protein()
        total_fat += meal.total_fat()
        total_carb += meal.total_carb()

    # Сожжённые калории (тренировки)
    calories_burned = sum(ex.calories_burned for ex in exercises)

    balance = total_calories - calories_burned   # Баланс калорий

    # Цели для этой даты (из DailyTarget или текущие)
    targets = get_targets_for_date(request.user, current_date)

    # Проверка наличия записей
    has_entries = meals.exists() or exercises.exists()

    # Разницы для сообщений
    protein_diff = total_protein - targets['protein']
    carb_diff = total_carb - targets['carb']
    fat_diff = total_fat - targets['fat']
    calories_diff = total_calories - targets['calories']

    context = {
        'current_date': current_date,
        'prev_date': prev_date,
        'next_date': next_date,
        'meals': meals,
        'exercises': exercises,
        'total_calories': round(total_calories, 1),
        'total_protein': round(total_protein, 1),
        'total_fat': round(total_fat, 1),
        'total_carb': round(total_carb, 1),
        'calories_burned': round(calories_burned, 1),
        'balance': round(balance, 1),
        'target_calories': targets['calories'],
        'target_protein': targets['protein'],
        'target_fat': targets['fat'],
        'target_carb': targets['carb'],
        'is_custom_targets': targets.get('is_custom', False),
        'has_entries': has_entries,
        'protein_diff': protein_diff,
        'carb_diff': carb_diff,
        'fat_diff': fat_diff,
        'calories_diff': calories_diff,
    }
    return render(request, 'training_django_app/dashboard.html', context)


@login_required
@require_http_methods(['GET'])
def api_dashboard_totals(request):
    # API для получения актуальных итогов за день
    date_str = request.GET.get('date')
    if date_str:
        target_date = datetime.strptime(date_str, '%Y-%m-%d').date()
    else:
        target_date = timezone.now().date()

    # Приёмы пищи
    meals = Meal.objects.filter(
        user=request.user,
        date=target_date
    ).prefetch_related('items__food')

    total_calories = 0
    total_protein = 0
    total_fat = 0
    total_carb = 0

    for meal in meals:
        total_calories += meal.total_calories()
        total_protein += meal.total_protein()
        total_fat += meal.total_fat()
        total_carb += meal.total_carb()

    # Тренировки
    trainings = ExerciseRecord.objects.filter(
        user=request.user,
        date=target_date
    )
    total_calories_burned = sum(t.calories_burned for t in trainings)

    balance = total_calories - total_calories_burned

    # Целевые нормы из профиля
    targets = request.user.profile.calculate_daily_targets()

    return JsonResponse({
        'success': True,
        'total_calories': round(total_calories, 1),
        'total_protein': round(total_protein, 1),
        'total_fat': round(total_fat, 1),
        'total_carb': round(total_carb, 1),
        'total_calories_burned': round(total_calories_burned, 1),
        'balance': round(balance, 1),
        'target_calories': targets['calories'],
        'target_protein': targets['protein'],
        'target_fat': targets['fat'],
        'target_carb': targets['carb'],
    })


@login_required
def product_form(request, product_id=None):
    # Универсальная форма для создания/редактирования продукта
    if product_id:
        # Режим редактирования
        product = get_object_or_404(
            food_catalogue,
            id=product_id,
            is_dish=False
        )
        if product.created_by != request.user:
            messages.error(request, 'Вы можете редактировать только свои продукты')
            return redirect('training_django_app:profile')
        title = 'Редактировать продукт'
        submit_text = 'Сохранить изменения'
    else:
        # Режим создания
        product = None
        title = 'Добавить продукт'
        submit_text = 'Добавить продукт'

    if request.method == 'POST':
        form = ProductForm(request.POST, instance=product)
        if form.is_valid():
            new_product = form.save(commit=False)
            new_product.created_by = request.user
            new_product.is_dish = False
            new_product.save()
            messages.success(request, f'Продукт "{new_product.name}" сохранён!')
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
    product = get_object_or_404(
        food_catalogue,
        id=product_id,
        is_dish=False
    )
    if product.created_by != request.user:
        messages.error(request, 'Вы можете удалять только свои продукты')
        return redirect('training_django_app:profile')

    product_name = product.name
    product.delete()
    messages.success(request, f'Продукт "{product_name}" удалён!')
    return redirect('training_django_app:profile')


@login_required
@require_http_methods(['POST'])
def api_save_dish(request):
    # API для сохранения блюда с ингредиентами
    try:
        data = json.loads(request.body)
        dish_name = data.get('name', '').strip()
        ingredients_data = data.get('ingredients', [])
        dish_id = data.get('dish_id')

        if not dish_name:
            return JsonResponse({'error': 'Название блюда обязательно'}, status=400)

        if not ingredients_data:
            return JsonResponse({'error': 'Добавьте хотя бы один ингредиент'}, status=400)

        # Проверка существования блюда с таким названием
        existing = food_catalogue.objects.filter(
            created_by=request.user,
            name__iexact=dish_name,
            is_dish=True
        )
        if dish_id:
            existing = existing.exclude(id=dish_id)

        if existing.exists():
            return JsonResponse(
                {'error': 'Блюдо с таким названием уже существует'},
                status=400
            )

        with transaction.atomic():
            if dish_id:
                # Обновление существующего блюда
                dish = get_object_or_404(
                    food_catalogue,
                    id=dish_id,
                    created_by=request.user,
                    is_dish=True
                )
                dish.name = dish_name
                dish.save()
                # Удаляем старые ингредиенты
                FoodCatalogueIngredient.objects.filter(dish=dish).delete()
            else:
                # Создание нового блюда
                dish = food_catalogue.objects.create(
                    created_by=request.user,
                    name=dish_name,
                    is_dish=True,
                    protein=0,
                    fat=0,
                    carb=0,
                    calories=0
                )

            # Создаём новые ингредиенты
            for item in ingredients_data:
                product_id = item.get('product_id')
                weight_grams = item.get('weight_grams', 0)

                if not product_id or weight_grams <= 0:
                    continue

                try:
                    product = food_catalogue.objects.get(
                        id=product_id,
                        is_dish=False
                    )
                    FoodCatalogueIngredient.objects.create(
                        dish=dish,
                        ingredient=product,
                        weight_grams=weight_grams
                    )
                except food_catalogue.DoesNotExist:
                    continue

            # Пересчитываем КБЖУ блюда
            dish.update_from_ingredients()

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
    # API для поиска продуктов и блюд с пагинацией
    query = request.GET.get('q', '').strip()
    offset = int(request.GET.get('offset', 0))
    limit = int(request.GET.get('limit', 10))

    # Базовый запрос: общие продукты и созданные пользователем
    products = food_catalogue.objects.filter(
        Q(created_by=request.user) | Q(created_by__isnull=True)
    )

    if query:
        products = products.filter(name__icontains=query)

    # Пагинация
    total = products.count()
    products = products.order_by(
        '-last_used', '-created_at'
    )[offset:offset + limit]

    data = [{
        'id': p.id,
        'name': p.name,
        'protein': p.protein,
        'fat': p.fat,
        'carb': p.carb,
        'calories': p.calories,
        'is_dish': p.is_dish,
    } for p in products]

    return JsonResponse({
        'items': data,
        'total': total,
        'offset': offset,
        'has_more': offset + limit < total
    }, safe=False)


@login_required
def dish_form(request, dish_id=None):
    # Универсальная форма для создания/редактирования блюда
    if dish_id:
        # Режим редактирования
        dish = get_object_or_404(
            food_catalogue,
            id=dish_id,
            created_by=request.user,
            is_dish=True
        )
        title = 'Редактировать блюдо'
        submit_text = 'Сохранить изменения'
    else:
        # Режим создания
        dish = None
        title = 'Создать блюдо'
        submit_text = 'Создать блюдо'

    # Обработка POST-запроса (сохранение названия)
    if request.method == 'POST':
        form = DishForm(request.POST, instance=dish)
        if form.is_valid():
            new_dish = form.save(commit=False)
            new_dish.created_by = request.user
            new_dish.is_dish = True
            new_dish.save()
            messages.success(request, f'Блюдо "{new_dish.name}" сохранено!')
            return redirect('training_django_app:edit_dish', dish_id=new_dish.id)
        else:
            messages.error(request, 'Пожалуйста, исправьте ошибки в форме')
    else:
        form = DishForm(instance=dish)

    # Получаем ингредиенты для редактирования
    ingredients = []
    if dish:
        ingredients = FoodCatalogueIngredient.objects.filter(
            dish=dish
        ).select_related('ingredient')

    context = {
        'form': form,
        'title': title,
        'submit_text': submit_text,
        'is_edit': dish_id is not None,
        'dish_id': dish_id,
        'dish': dish,
        'ingredients': ingredients,
    }
    return render(request, 'training_django_app/dish_form.html', context)


@login_required
@require_http_methods(['POST'])
def delete_dish(request, dish_id):
    # Удаление блюда
    dish = get_object_or_404(
        food_catalogue,
        id=dish_id,
        created_by=request.user,
        is_dish=True
    )
    dish_name = dish.name
    dish.delete()
    messages.success(request, f'Блюдо "{dish_name}" удалено!')
    return redirect('training_django_app:profile')


@login_required
def exercise_form(request, exercise_id=None):
    # Универсальная форма для создания/редактирования упражнения
    if exercise_id:
        # Режим редактирования
        exercise = get_object_or_404(exercise_catalogue, id=exercise_id)
        if exercise.created_by != request.user:
            messages.error(request, 'Вы можете редактировать только свои упражнения')
            return redirect('training_django_app:profile')
        title = 'Редактировать упражнение'
        submit_text = 'Сохранить изменения'
    else:
        # Режим создания
        exercise = None
        title = 'Добавить упражнение'
        submit_text = 'Добавить упражнение'

    if request.method == 'POST':
        form = ExerciseForm(request.POST, instance=exercise)
        if form.is_valid():
            new_exercise = form.save(commit=False)
            new_exercise.created_by = request.user
            new_exercise.save()
            messages.success(request, f'Упражнение "{new_exercise.name}" сохранено!')
            return redirect('training_django_app:profile')
        else:
            messages.error(request, 'Пожалуйста, исправьте ошибки в форме')
    else:
        form = ExerciseForm(instance=exercise)

    context = {
        'form': form,
        'title': title,
        'submit_text': submit_text,
        'is_edit': exercise_id is not None,
        'exercise_id': exercise_id,
    }
    return render(request, 'training_django_app/exercise_form.html', context)


@login_required
@require_http_methods(['POST'])
def delete_exercise(request, exercise_id):
    # Удаление упражнения
    exercise = get_object_or_404(exercise_catalogue, id=exercise_id)
    if exercise.created_by != request.user:
        messages.error(request, 'Вы можете удалять только свои упражнения')
        return redirect('training_django_app:profile')

    exercise_name = exercise.name
    exercise.delete()
    messages.success(request, f'Упражнение "{exercise_name}" удалено!')
    return redirect('training_django_app:profile')


@login_required
@require_http_methods(['GET'])
def api_search_exercises(request):
    # API для поиска упражнений с пагинацией
    query = request.GET.get('q', '').strip()
    offset = int(request.GET.get('offset', 0))
    limit = int(request.GET.get('limit', 10))

    exercises = exercise_catalogue.objects.all()

    if query:
        exercises = exercises.filter(name__icontains=query)

    total = exercises.count()
    exercises = exercises.order_by('name')[offset:offset + limit]

    data = [{
        'id': e.id,
        'name': e.name,
        'met': e.met,
        'calories_per_hour': e.calories_per_hour,
    } for e in exercises]

    return JsonResponse({
        'items': data,
        'total': total,
        'has_more': offset + limit < total
    }, safe=False)


@login_required
def edit_training(request, training_id):
    # Страница редактирования тренировки
    training = get_object_or_404(
        ExerciseRecord,
        id=training_id,
        user=request.user
    )

    if request.method == 'POST':
        time_str = request.POST.get('time')
        duration = request.POST.get('duration')

        if time_str and duration:
            try:
                training.time = datetime.strptime(time_str, '%H:%M').time()
                training.duration_minutes = int(duration)
                training.save()
                messages.success(request, 'Тренировка обновлена!')
                return redirect('training_django_app:dashboard')
            except ValueError:
                messages.error(request, 'Неверный формат времени')
        else:
            messages.error(request, 'Пожалуйста, заполните все поля')

    context = {
        'training': training,
        'title': 'Редактировать тренировку'
    }
    return render(request, 'training_django_app/edit_training.html', context)


@login_required
@require_http_methods(['POST'])
def api_delete_training(request, training_id):
    # API для удаления тренировки
    try:
        training = get_object_or_404(
            ExerciseRecord,
            id=training_id,
            user=request.user
        )
        training.delete()
        return JsonResponse({'success': True})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@login_required
@require_http_methods(['POST'])
def api_update_training(request, training_id):
    # API для обновления длительности тренировки
    try:
        data = json.loads(request.body)
        duration_minutes = data.get('duration_minutes')

        training = get_object_or_404(
            ExerciseRecord,
            id=training_id,
            user=request.user
        )
        training.duration_minutes = duration_minutes
        training.save()

        return JsonResponse({
            'success': True,
            'calories_burned': training.calories_burned
        })
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@login_required
def meal_form(request):
    # Страница создания/редактирования приёма пищи
    meal_id = request.GET.get('meal_id')
    meal = None
    items = []

    if meal_id:
        meal = get_object_or_404(Meal, id=meal_id, user=request.user)
        items = MealItem.objects.filter(meal=meal).select_related('food')

    # Дата из GET-параметра или сегодня
    date_str = request.GET.get('date')
    if date_str:
        meal_date = datetime.strptime(date_str, '%Y-%m-%d').date()
    else:
        meal_date = timezone.now().date()

    context = {
        'meal': meal,
        'items': items,
        'date': meal_date,
        'title': 'Редактировать приём пищи' if meal else 'Новый приём пищи'
    }
    return render(request, 'training_django_app/meal_form.html', context)


@login_required
@require_http_methods(['POST'])
def api_meal_save(request):
    # API для создания нового приёма пищи с продуктами
    try:
        data = json.loads(request.body)
        date_str = data.get('date')
        time_str = data.get('time')
        items_data = data.get('items', [])

        if not items_data:
            return JsonResponse(
                {'error': 'Добавьте хотя бы один продукт'},
                status=400
            )

        meal_date = datetime.strptime(date_str, '%Y-%m-%d').date()
        meal_time = datetime.strptime(time_str, '%H:%M').time()

        # Создаём приём пищи
        meal = Meal.objects.create(
            user=request.user,
            date=meal_date,
            time=meal_time
        )

        # Добавляем продукты
        for item in items_data:
            product_id = item.get('product_id')
            weight_grams = item.get('weight_grams', 100)

            product = get_object_or_404(food_catalogue, id=product_id)
            MealItem.objects.create(
                meal=meal,
                food=product,
                weight_grams=weight_grams
            )

        return JsonResponse({'success': True, 'meal_id': meal.id})

    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@login_required
@require_http_methods(['POST'])
def api_delete_meal(request, meal_id):
    # API для удаления приёма пищи
    try:
        meal = get_object_or_404(Meal, id=meal_id, user=request.user)
        meal.delete()
        return JsonResponse({'success': True})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@login_required
@require_http_methods(['POST'])
def api_meal_update_time(request, meal_id):
    # API для обновления времени приёма пищи
    try:
        data = json.loads(request.body)
        time_str = data.get('time')
        meal_time = datetime.strptime(time_str, '%H:%M').time()

        meal = get_object_or_404(Meal, id=meal_id, user=request.user)
        meal.time = meal_time
        meal.save()

        return JsonResponse({'success': True})

    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@login_required
@require_http_methods(['POST'])
def api_add_meal_item(request):
    # API для добавления продукта в приём пищи
    try:
        data = json.loads(request.body)
        meal_id = data.get('meal_id')
        product_id = data.get('product_id')
        weight_grams = float(data.get('weight_grams', 100))

        meal = get_object_or_404(Meal, id=meal_id, user=request.user)
        product = get_object_or_404(food_catalogue, id=product_id)

        # Проверяем, есть ли уже такой продукт в приёме
        existing_item = MealItem.objects.filter(
            meal=meal,
            food=product
        ).first()
        if existing_item:
            existing_item.weight_grams = weight_grams
            existing_item.save()
        else:
            MealItem.objects.create(
                meal=meal,
                food=product,
                weight_grams=weight_grams
            )

        return JsonResponse({'success': True})

    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@login_required
@require_http_methods(['POST'])
def api_delete_meal_item(request, item_id):
    # API для удаления продукта из приёма пищи
    try:
        item = get_object_or_404(
            MealItem,
            id=item_id,
            meal__user=request.user
        )
        item.delete()
        return JsonResponse({'success': True})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@login_required
@require_http_methods(['POST'])
def api_update_meal_item_weight(request, item_id):
    # API для обновления веса продукта в приёме пищи
    try:
        data = json.loads(request.body)
        weight_grams = float(data.get('weight_grams', 100))

        item = get_object_or_404(
            MealItem,
            id=item_id,
            meal__user=request.user
        )
        item.weight_grams = weight_grams
        item.save()

        return JsonResponse({
            'success': True,
            'protein': item.protein,
            'fat': item.fat,
            'carb': item.carb,
            'calories': item.calories
        })
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@login_required
@require_http_methods(['GET'])
def api_meal_totals(request, meal_id):
    # API для получения итогов приёма пищи
    meal = get_object_or_404(Meal, id=meal_id, user=request.user)
    return JsonResponse({
        'protein': meal.total_protein(),
        'fat': meal.total_fat(),
        'carb': meal.total_carb(),
        'calories': meal.total_calories()
    })


@login_required
@require_http_methods(['POST'])
def api_training_save(request):
    # API для сохранения тренировки
    try:
        data = json.loads(request.body)
        exercise_id = data.get('exercise_id')
        time_str = data.get('time')
        duration_minutes = data.get('duration_minutes')

        exercise = get_object_or_404(exercise_catalogue, id=exercise_id)
        training_time = datetime.strptime(time_str, '%H:%M').time()

        record = ExerciseRecord.objects.create(
            user=request.user,
            exercise=exercise,
            date=timezone.now().date(),
            time=training_time,
            duration_minutes=duration_minutes
        )

        return JsonResponse({'success': True, 'record_id': record.id})

    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@login_required
def add_training(request):
    # Страница добавления тренировки
    context = {
        'title': 'Добавить тренировку',
        'date': timezone.now().date(),
    }
    return render(request, 'training_django_app/add_training.html', context)