# forms.py
from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.core.exceptions import ValidationError
from .models import app_user, UserProfile, food_catalogue
from datetime import date


class RegistrationForm(UserCreationForm):

    
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
        model = app_user  # Указываем, с какой моделью работаем
        fields = ['username', 'email', 'full_name', 'birth_date', 'gender', 'password1', 'password2']
    
    def clean_email(self):
        
        #Проверка: email должен быть уникальным
        
        email = self.cleaned_data.get('email')
        if app_user.objects.filter(email=email).exists():
            raise ValidationError('Пользователь с такой почтой уже существует')
        return email
    
    def clean_username(self):
        
        # Проверка: username должен быть уникальным
        
        username = self.cleaned_data.get('username')
        if app_user.objects.filter(username=username).exists():
            raise ValidationError('Это имя пользователя уже занято')
        return username
    
    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data['email']
        user.full_name = self.cleaned_data['full_name']
        user.birth_date = self.cleaned_data['birth_date']
        user.gender = self.cleaned_data['gender']
        
        if commit:
            user.save()
            # ✅ СОЗДАЁМ ПРОФИЛЬ
            UserProfile.objects.create(
                user=user,
                weight=70,
                height=170,
                activity_level=1.375,
                goal='maintenance'
            )
        
        return user


class LoginForm(forms.Form):
    
    # Форма входа (простая, без модели)
    
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
    
    # Форма редактирования профиля пользователя
    
    class Meta:
        model = UserProfile
        fields = ['weight', 'height', 'goal', 'activity_level']
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
            'goal': 'Цель',
            'activity_level': 'Уровень активности',
        }
    
    def clean_weight(self):
        weight = self.cleaned_data.get('weight')
        if weight < 20 or weight > 300:
            raise forms.ValidationError('Вес должен быть от 20 до 300 кг')
        return weight
    
    def clean_height(self):
        height = self.cleaned_data.get('height')
        if height < 100 or height > 250:
            raise forms.ValidationError('Рост должен быть от 100 до 250 см')
        return height
    


class DefaultProfileForm(forms.ModelForm):
    
    # Форма для первоначального заполнения профиля
    
    class Meta:
        model = UserProfile
        fields = ['weight', 'height', 'goal', 'activity_level']
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
            'goal': 'Ваша цель',
            'activity_level': 'Уровень активности',
        }
        help_texts = {
            'goal': 'Какую цель вы преследуете?',
            'activity_level': 'Насколько вы активны в повседневной жизни?',
        }
    
    def clean_weight(self):
        weight = self.cleaned_data.get('weight')
        if weight < 20 or weight > 300:
            raise forms.ValidationError('Вес должен быть от 20 до 300 кг')
        return weight
    
    def clean_height(self):
        height = self.cleaned_data.get('height')
        if height < 100 or height > 250:
            raise forms.ValidationError('Рост должен быть от 100 до 250 см')
        return height
    

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
        full_name = self.cleaned_data.get('full_name')
        if len(full_name) < 3:
            raise forms.ValidationError('ФИО должно содержать минимум 3 символа')
        return full_name
    

class ProductForm(forms.ModelForm):
    #Форма для добавления простого продукта
    class Meta:
        model = food_catalogue
        fields = ['name', 'protein', 'fat', 'carb']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Например: Куриная грудка'}),
            'protein': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.1', 'placeholder': 'Белки на 100г'}),
            'fat': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.1', 'placeholder': 'Жиры на 100г'}),
            'carb': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.1', 'placeholder': 'Углеводы на 100г'}),
        }
        labels = {
            'name': 'Название продукта',
            'protein': 'Белки (г/100г)',
            'fat': 'Жиры (г/100г)',
            'carb': 'Углеводы (г/100г)',
        }


class DishForm(forms.ModelForm):
    
    # Форма для создания нового блюда 
    # БЖУ будут рассчитаны автоматически после добавления ингредиентов
    
    class Meta:
        model = food_catalogue
        fields = ['name']  # Пока только название
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
        # Проверка: нет ли уже такого блюда у пользователя
        name = self.cleaned_data.get('name')
        user = self.instance.user if self.instance.pk else None
        
        # Проверяем есть ли  уже такое блюдо у текущего пользователя
        if food_catalogue.objects.filter(
            user=user, 
            name__iexact=name,  # регистронезависимое сравнение
            is_dish=True  # только блюда, не продукты
        ).exists():
            raise forms.ValidationError('У вас уже есть блюдо с таким названием')
        
        return name