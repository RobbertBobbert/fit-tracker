from django.shortcuts import render, redirect
from django.contrib.auth import login, logout
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_http_methods
from django.utils import timezone
from django.db.models import Sum
from .forms import RegistrationForm, LoginForm, ProfileEditForm, DefaultProfileForm, UserEditForm
from .models import food_catalogue, exercise_entry, app_user, food_entry
from django.contrib.auth.hashers import check_password


def register_view(request):
    """
    Регистрация нового пользователя
    """
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


#переписать на JWT авторизацию:
from django.contrib.auth.hashers import check_password  # Добавь это в начало файла с импортами

def login_view(request):
    """
    Вход пользователя (рабочий вариант без authenticate)
    """
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
    """
    Выход из системы
    """
    logout(request)
    messages.info(request, 'Вы вышли из аккаунта 👋')
    return redirect('training_django_app:login')


def profile_setup_view(request):
    """
    Страница первоначального заполнения профиля (обязательно после регистрации)
    """
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
    """
    Просмотр и редактирование профиля пользователя
    """
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
    
    context = {
        'user_form': user_form,
        'profile_form': profile_form,
        'profile': profile,
        'user': user,
        'targets': targets,
        'title': 'Мой профиль'
    }
    return render(request, 'training_django_app/profile.html', context)


@login_required
@require_http_methods(['GET'])
def dashboard(request):
    """
    Главная страница с отчётами (только для авторизованных)
    """
    today = timezone.now().date()
    
    calories_taken_agg = food_entry.objects.filter(
        user=request.user, date=today
    ).aggregate(total_intake=Sum('calories'))

    calories_taken_agg_value = calories_taken_agg['total_intake'] or 0
    
    calories_burnt_agg = exercise_entry.objects.filter(
        user=request.user, date=today
    ).aggregate(total_burnt=Sum('calories_exercise'))
    calories_burnt_agg_value = calories_burnt_agg['total_burnt'] or 0
    
    balance = calories_taken_agg_value - calories_burnt_agg_value

    protein_taken_agg = food_entry.objects.filter(
        user=request.user, date=today
    ).aggregate(total_protein=Sum('protein'))
    protein_taken_agg_value = protein_taken_agg['total_protein'] or 0

    carb_taken_agg = food_entry.objects.filter(
        user=request.user, date=today
    ).aggregate(total_carb=Sum('carb'))
    carb_taken_agg_value = carb_taken_agg['total_carb'] or 0

    fat_taken_agg = food_entry.objects.filter(
        user=request.user, date=today
    ).aggregate(total_fat=Sum('fat'))
    fat_taken_agg_value = fat_taken_agg['total_fat'] or 0

    context = {
        'today': today,
        'calories_taken_agg_value': round(calories_taken_agg_value, 1),
        'calories_burnt_agg_value': round(calories_burnt_agg_value, 1),
        'balance': round(balance, 1),
        'protein_taken_agg_value': round(protein_taken_agg_value, 1),
        'carb_taken_agg_value': round(carb_taken_agg_value, 1),
        'fat_taken_agg_value': round(fat_taken_agg_value, 1),
        'recent_food': food_entry.objects.filter(
            user=request.user, date=today
        ).order_by('-id'),
    }
    return render(request, 'training_django_app/dashboard.html', context)