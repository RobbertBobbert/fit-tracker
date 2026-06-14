# forms.py
from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.core.exceptions import ValidationError
from .models import app_user, UserProfile, food_catalogue, exercise_catalogue
from datetime import date


class RegistrationForm(UserCreationForm):
    # Форма регистрации нового пользователя

    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'example@mail.com'
        }),
        label='Электронная почта'
    )

    full_name = forms.CharField(
        required=True,
        max_length=255,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Иванов Иван Иванович'
        }),
        label='ФИО'
    )

    birth_date = forms.DateField(
        required=True,
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date',
            'placeholder': '1990-01-01'
        }),
        label='Дата рождения',
        help_text='Формат: ГГГГ-ММ-ДД'
    )

    gender = forms.ChoiceField(
        required=True,
        choices=[('male', 'Мужской'), ('female', 'Женский')],
        widget=forms.Select(attrs={
            'class': 'form-control'
        }),
        label='Пол'
    )

    # Переопределяем поля username и password для красивого вида
    username = forms.CharField(
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'nickname'
        }),
        label='Имя пользователя'
    )

    password1 = forms.CharField(
        required=True,
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Минимум 8 символов'
        }),
        label='Пароль'
    )

    password2 = forms.CharField(
        required=True,
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Повторите пароль'
        }),
        label='Подтверждение пароля'
    )

    class Meta:
        # Указываем модель и поля для формы
        model = app_user
        fields = [
            'username', 'email', 'full_name', 'birth_date',
            'gender', 'password1', 'password2'
        ]

    def clean_email(self):
        # Проверка уникальности email
        email = self.cleaned_data.get('email')
        if app_user.objects.filter(email=email).exists():
            raise ValidationError('Пользователь с такой почтой уже существует')
        return email

    def clean_username(self):
        # Проверка уникальности username
        username = self.cleaned_data.get('username')
        if app_user.objects.filter(username=username).exists():
            raise ValidationError('Это имя пользователя уже занято')
        return username

    def save(self, commit=True):
        # Сохраняем пользователя и создаём профиль с значениями по умолчанию
        user = super().save(commit=False)
        user.email = self.cleaned_data['email']
        user.full_name = self.cleaned_data['full_name']
        user.birth_date = self.cleaned_data['birth_date']
        user.gender = self.cleaned_data['gender']

        if commit:
            user.save()
            # Создаём профиль с дефолтными значениями
            UserProfile.objects.create(
                user=user,
                weight=70,
                height=170,
                activity_level=1.375,
                goal='maintenance'
            )

        return user


class LoginForm(forms.Form):
    # Форма входа (простая, без привязки к модели)
    username = forms.CharField(
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Имя пользователя или Email'
        }),
        label='Имя пользователя или Email'
    )

    password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Пароль'
        }),
        label='Пароль'
    )


class ProfileEditForm(forms.ModelForm):
    # Форма редактирования антропометрических данных профиля

    class Meta:
        model = UserProfile
        fields = ['weight', 'height', 'body_fat', 'goal', 'activity_level']
        widgets = {
            'weight': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.1'
            }),
            'height': forms.NumberInput(attrs={
                'class': 'form-control'
            }),
            'body_fat': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.1'
            }),
            'goal': forms.Select(attrs={
                'class': 'form-control'
            }),
            'activity_level': forms.Select(attrs={
                'class': 'form-control'
            }),
        }
        labels = {
            'weight': 'Вес (кг)',
            'height': 'Рост (см)',
            'body_fat': 'Процент жира (%)',
            'goal': 'Цель',
            'activity_level': 'Уровень активности',
        }

    def clean_weight(self):
        # Валидация веса
        weight = self.cleaned_data.get('weight')
        if weight < 20 or weight > 300:
            raise forms.ValidationError('Вес должен быть от 20 до 300 кг')
        return weight

    def clean_height(self):
        # Валидация роста
        height = self.cleaned_data.get('height')
        if height < 100 or height > 250:
            raise forms.ValidationError('Рост должен быть от 100 до 250 см')
        return height

    def clean_body_fat(self):
        # Валидация процента жира
        body_fat = self.cleaned_data.get('body_fat')
        if body_fat and (body_fat < 5 or body_fat > 60):
            raise forms.ValidationError('Процент жира должен быть от 5 до 60%')
        return body_fat


class DefaultProfileForm(forms.ModelForm):
    # Форма для первоначального заполнения профиля после регистрации

    class Meta:
        model = UserProfile
        fields = ['weight', 'height', 'body_fat', 'goal', 'activity_level']
        widgets = {
            'weight': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.1',
                'placeholder': '75.5'
            }),
            'height': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': '175'
            }),
            'body_fat': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.1',
                'placeholder': '15'
            }),
            'goal': forms.Select(attrs={
                'class': 'form-control'
            }),
            'activity_level': forms.Select(attrs={
                'class': 'form-control'
            }),
        }
        labels = {
            'weight': 'Вес (кг)',
            'height': 'Рост (см)',
            'body_fat': 'Процент жира (%) — опционально',
            'goal': 'Ваша цель',
            'activity_level': 'Уровень активности',
        }
        help_texts = {
            'body_fat': 'Если не знаете — оставьте пустым',
            'goal': 'Какую цель вы преследуете?',
            'activity_level': 'Насколько вы активны в повседневной жизни?',
        }

    def clean_weight(self):
        # Валидация веса
        weight = self.cleaned_data.get('weight')
        if weight < 20 or weight > 300:
            raise forms.ValidationError('Вес должен быть от 20 до 300 кг')
        return weight

    def clean_height(self):
        # Валидация роста
        height = self.cleaned_data.get('height')
        if height < 100 or height > 250:
            raise forms.ValidationError('Рост должен быть от 100 до 250 см')
        return height

    def clean_body_fat(self):
        # Валидация процента жира
        body_fat = self.cleaned_data.get('body_fat')
        if body_fat and (body_fat < 5 or body_fat > 60):
            raise forms.ValidationError('Процент жира должен быть от 5 до 60%')
        return body_fat


class UserEditForm(forms.ModelForm):
    # Форма редактирования личной информации пользователя

    birth_date = forms.DateField(
        required=True,
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date'
        }),
        label='Дата рождения'
    )

    class Meta:
        model = app_user
        fields = ['full_name', 'birth_date', 'gender']
        widgets = {
            'full_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Иванов Иван Иванович'
            }),
            'gender': forms.Select(attrs={
                'class': 'form-control'
            }),
        }
        labels = {
            'full_name': 'ФИО',
            'birth_date': 'Дата рождения',
            'gender': 'Пол',
        }

    def clean_full_name(self):
        # Валидация ФИО (минимум 3 символа)
        full_name = self.cleaned_data.get('full_name')
        if len(full_name) < 3:
            raise forms.ValidationError('ФИО должно содержать минимум 3 символа')
        return full_name


class ProductForm(forms.ModelForm):
    # Форма для добавления простого продукта в каталог

    class Meta:
        model = food_catalogue
        fields = ['name', 'protein', 'fat', 'carb']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Например: Куриная грудка'
            }),
            'protein': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.1',
                'placeholder': 'Белки на 100г'
            }),
            'fat': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.1',
                'placeholder': 'Жиры на 100г'
            }),
            'carb': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.1',
                'placeholder': 'Углеводы на 100г'
            }),
        }
        labels = {
            'name': 'Название продукта',
            'protein': 'Белки (г/100г)',
            'fat': 'Жиры (г/100г)',
            'carb': 'Углеводы (г/100г)',
        }


class DishForm(forms.ModelForm):
    # Форма для создания нового блюда (только название)
    # БЖУ будут рассчитаны автоматически после добавления ингредиентов

    class Meta:
        model = food_catalogue
        fields = ['name']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Например: Овсянка с яблоком'
            }),
        }
        labels = {
            'name': 'Название блюда',
        }

    def clean_name(self):
        # Проверка уникальности названия блюда для пользователя
        name = self.cleaned_data.get('name')
        user = self.instance.created_by if self.instance.pk else None

        if self.instance.pk:
            # Режим редактирования — исключаем текущее блюдо из проверки
            if food_catalogue.objects.filter(
                created_by=user,
                name__iexact=name,
                is_dish=True
            ).exclude(pk=self.instance.pk).exists():
                raise forms.ValidationError('У вас уже есть блюдо с таким названием')
        else:
            # Режим создания — проверяем все блюда пользователя
            if food_catalogue.objects.filter(
                created_by=user,
                name__iexact=name,
                is_dish=True
            ).exists():
                raise forms.ValidationError('У вас уже есть блюдо с таким названием')

        return name


class ExerciseForm(forms.ModelForm):
    # Форма для создания/редактирования упражнения

    class Meta:
        model = exercise_catalogue
        fields = ['name', 'calories_per_hour', 'met', 'is_shared']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Например: Бег'
            }),
            'calories_per_hour': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '1',
                'placeholder': 'Калорий в час (опционально)'
            }),
            'met': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.1',
                'placeholder': 'MET (опционально)'
            }),
            'is_shared': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
        }
        labels = {
            'name': 'Название упражнения',
            'calories_per_hour': 'Калорий в час',
            'met': 'MET (коэффициент интенсивности)',
            'is_shared': 'Общее упражнение (доступно всем)',
        }

    def clean(self):
        # Проверка: должно быть указано хотя бы одно из полей (calories_per_hour или met)
        cleaned_data = super().clean()
        calories_per_hour = cleaned_data.get('calories_per_hour')
        met = cleaned_data.get('met')

        if not calories_per_hour and not met:
            raise forms.ValidationError('Укажите либо калории в час, либо MET')

        return cleaned_data