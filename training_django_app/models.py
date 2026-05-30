from django.db import models
from django.contrib.auth.models import AbstractUser
from datetime import date
from django.core.validators import MinValueValidator, MaxValueValidator


class app_user(AbstractUser):
    GENDER_CHOICES = [
        ('male', 'Мужской'),
        ('female', 'Женский'),
    ]

    email = models.EmailField(unique=True)
    full_name = models.CharField(max_length=255, verbose_name='ФИО')
    birth_date = models.DateField(verbose_name='Дата рождения')
    gender = models.CharField(max_length=10, choices=GENDER_CHOICES, verbose_name='Пол', default='other')
    
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username', 'full_name', 'birth_date', 'gender']
    
    class Meta:
        verbose_name = 'Пользователь'
        verbose_name_plural = 'Пользователи'
    
    def __str__(self):
        return self.full_name
    
    @property
    def age(self):
        today = date.today()
        return today.year - self.birth_date.year - (
            (today.month, today.day) < (self.birth_date.month, self.birth_date.day)
        )


class UserProfile(models.Model):
    GOAL_CHOICES = [
        ('weight_loss', 'Похудение'),
        ('maintenance', 'Поддержание веса'),
        ('muscle_gain', 'Набор массы'),
    ]
    
    ACTIVITY_LEVELS = [
        (1.2, 'Сидячий образ жизни'),
        (1.375, 'Лёгкая активность (1-3 дня/неделю)'),
        (1.55, 'Умеренная активность (3-5 дней/неделю)'),
        (1.725, 'Высокая активность (6-7 дней/неделю)'),
        (1.9, 'Экстремальная активность'),
    ]
    
    user = models.OneToOneField(
        app_user, 
        on_delete=models.CASCADE,
        related_name='profile',
        verbose_name='Пользователь'
    )
    
    # Антропометрия
    weight = models.FloatField(verbose_name='Вес (кг)', validators=[MinValueValidator(20, 'Вес должен быть > 20 кг')])
    height = models.PositiveIntegerField(verbose_name='Рост (см)', validators=[MinValueValidator(100, 'Рост должен быть > 100 см')])
    
    # Цели и активность
    goal = models.CharField(max_length=20, choices=GOAL_CHOICES, default='maintenance', verbose_name='Цель')
    activity_level = models.FloatField(choices=ACTIVITY_LEVELS, default=1.375, verbose_name='Уровень активности')
    
    # Целевые БЖУ 
    target_protein = models.FloatField(blank=True, null=True, verbose_name='Целевой белок (г/день)')
    target_fat = models.FloatField(blank=True, null=True, verbose_name='Целевые жиры (г/день)')
    target_carb = models.FloatField(blank=True, null=True, verbose_name='Целевые углеводы (г/день)')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Профиль пользователя'
        verbose_name_plural = 'Профили пользователей'
    
    def __str__(self):
        return f'Профиль {self.user.full_name}'
    
    @property
    # Расчет ИМТ, только для статистики, чтобы смотреть и радоваться)
    def bmi(self):
        if self.height > 0:
            height_m = self.height / 100
            return round(self.weight / (height_m ** 2), 1)
        return 0
    
    @property
    # Расчсет базового метаболизма
    def bmr(self):
        age = self.user.age
        if self.user.gender == 'male':
            return 10 * self.weight + 6.25 * self.height - 5 * age + 5
        else:
            return 10 * self.weight + 6.25 * self.height - 5 * age - 161
    
    @property
    def maintenance_calories(self):
        calories = round(self.bmr * self.activity_level)
        
        # Корректировка для высокого ИМТ
        if self.bmi > 30:
            calories = int(calories * 0.85)
        
        return max(calories, 1500)
    
    # Рассчет БЖУшечки
    def calculate_daily_targets(self):
        calories = self.maintenance_calories
        
        if self.goal == 'weight_loss':
            calories = int(calories * 0.8)  # Дефицит 20%
        elif self.goal == 'muscle_gain':
            calories = int(calories * 1.1)  # Профицит 10%
        
        # Базовое распределение: белки 30%, жиры 25%, углеводы 45%
        self.target_protein = round((calories * 0.30) / 4)  # 4 ккал/г
        self.target_fat = round((calories * 0.25) / 9)     # 9 ккал/г
        self.target_carb = round((calories * 0.45) / 4)    # 4 ккал/г
        
        return {
            'calories': calories,
            'protein': self.target_protein,
            'fat': self.target_fat,
            'carb': self.target_carb
        }


class food_catalogue(models.Model):

    user = models.ForeignKey(app_user, on_delete=models.CASCADE, verbose_name="Владелец")
    name = models.CharField(max_length=200, verbose_name="Название")
    is_dish = models.BooleanField(default=False, verbose_name="Это блюдо? (если нет - продукт)")
    protein = models.FloatField(default=0, verbose_name="Белки (г/100г)")
    carb = models.FloatField(default=0, verbose_name="Углеводы (г/100г)")
    fat = models.FloatField(default=0, verbose_name="Жиры (г/100г)")
    calories = models.FloatField(default=0, editable=False, verbose_name="Калории (на 100г)")   
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    last_used = models.DateTimeField(null=True, blank=True, verbose_name="Последнее использование")
    
    def save(self, *args, **kwargs):
        is_new = self.pk is None  # Проверяем, новый ли объект
        
        if not self.is_dish:
            # Для продуктов — рассчитываем калории
            self.calories = round(self.protein * 4 + self.carb * 4 + self.fat * 9, 2)
        else:
            # Для новых блюд обнуляем БЖУ
            if is_new:
                self.protein = 0
                self.carb = 0
                self.fat = 0
                self.calories = 0
            # Для существующих блюд — не трогаем (БЖУ уже рассчитаны из ингредиентов)
        
        super().save(*args, **kwargs)
    
    def update_from_ingredients(self):
        
        if not self.is_dish:
            return  # Только для блюд
        ingredients = self.ingredients.all()

        if not ingredients.exists():
            self.protein = 0
            self.carb = 0
            self.fat = 0
            self.calories = 0
            self.save()
            return
        
        total_protein = 0
        total_carb = 0
        total_fat = 0
        total_calories = 0
        total_weight = 0
        
        for ingredient in ingredients:
            # Получаем КБЖУ ингредиента на его вес
            nutrients = ingredient.get_nutrients()
            total_protein += nutrients['protein']
            total_carb += nutrients['carb']
            total_fat += nutrients['fat']
            total_calories += nutrients['calories']
            total_weight += ingredient.weight_grams
        
        # Пересчитываем на 100г
        if total_weight > 0:
            factor = 100 / total_weight
            self.protein = round(total_protein * factor, 2)
            self.carb = round(total_carb * factor, 2)
            self.fat = round(total_fat * factor, 2)
            self.calories = round(total_calories * factor, 2)
        
        self.save()
    
    def calculate_for_weight(self, weight_grams):

        factor = weight_grams / 100
        return {
            'protein': round(self.protein * factor, 2),
            'carb': round(self.carb * factor, 2),
            'fat': round(self.fat * factor, 2),
            'calories': round(self.calories * factor, 2),
            'weight': weight_grams,
            'name': self.name
        }
    
    def __str__(self):
        return f"{self.name} ({'блюдо' if self.is_dish else 'продукт'})"
    
    class Meta:
        verbose_name = "Элемент каталога"
        verbose_name_plural = "Каталог продуктов и блюд"
        ordering = ['-is_dish', 'name']  # Сначала продукты, потом блюда


class FoodCatalogueIngredient(models.Model):
    #Ингредиент в составе блюда
    #(связывает блюдо с продуктом/блюдом, которое входит в его состав)

    dish = models.ForeignKey(
        food_catalogue,
        on_delete=models.CASCADE,
        related_name='ingredients',
        limit_choices_to={'is_dish': True},  # Только блюда могут иметь ингредиенты
        verbose_name="Блюдо"
    )
    ingredient = models.ForeignKey(
        food_catalogue,
        on_delete=models.CASCADE,
        verbose_name="Ингредиент"
    )
    weight_grams = models.FloatField(
        verbose_name="Вес (граммы)",
        validators=[MinValueValidator(0.1)]
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    def get_nutrients(self):
        # Расчет кбжу для ингридиента
        return self.ingredient.calculate_for_weight(self.weight_grams)
    
    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        # После сохранения ингредиента пересчитываем блюдо
        self.dish.update_from_ingredients()
    
    def delete(self, *args, **kwargs):
        dish = self.dish
        super().delete(*args, **kwargs)
        dish.update_from_ingredients()
    
    def __str__(self):
        return f"{self.ingredient.name} - {self.weight_grams}г в {self.dish.name}"
    
    class Meta:
        verbose_name = "Ингредиент"
        verbose_name_plural = "Ингредиенты"



class exercise_entry(models.Model):
    user = models.ForeignKey(app_user, on_delete=models.CASCADE, verbose_name="Автор")
    exercise_name = models.CharField(max_length=50, verbose_name="Наименование упражнения")
    date = models.DateField(auto_now_add=True)
    calories_per_hour = models.IntegerField(verbose_name="Калорий в час")
    exercising_time = models.PositiveIntegerField(verbose_name="Время тренировки")
    calories_exercise = models.FloatField(verbose_name="Сожжено калорий", editable=False, default=0)  # FloatField

    def save(self, *args, **kwargs):
        self.calories_exercise = round((self.calories_per_hour / 60) * self.exercising_time, 2)
        super().save(*args, **kwargs)
    
    class Meta:
        verbose_name = "Внесение упражнения"
        ordering = ['-date', '-id']



class Meal(models.Model):
    #Прием пищи
    MEAL_TYPES = [
        ('breakfast', 'Завтрак'),
        ('lunch', 'Обед'),
        ('dinner', 'Ужин'),
        ('snack', 'Перекус'),
    ]
    
    user = models.ForeignKey(app_user, on_delete=models.CASCADE, verbose_name="Пользователь")
    meal_type = models.CharField(max_length=20, choices=MEAL_TYPES, default='snack', verbose_name="Тип приёма")
    date = models.DateField(default=date.today, verbose_name="Дата")
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = "Приём пищи"
        verbose_name_plural = "Приёмы пищи"
        ordering = ['date', 'meal_type', 'created_at']
    
    def __str__(self):
        return f"{self.user.username} - {self.get_meal_type_display()} - {self.date}"
    
    def total_calories(self):
        #Каллории за прием 
        return sum(item.calories for item in self.items.all())
    
    def total_protein(self):
        return sum(item.protein for item in self.items.all())
    
    def total_fat(self):
        return sum(item.fat for item in self.items.all())
    
    def total_carb(self):
        return sum(item.carb for item in self.items.all())


class MealItem(models.Model):
    # Продукт в приеме
    meal = models.ForeignKey(Meal, on_delete=models.CASCADE, related_name='items', verbose_name="Приём пищи")
    food = models.ForeignKey(food_catalogue, on_delete=models.CASCADE, verbose_name="Продукт")
    weight_grams = models.FloatField(default=100, verbose_name="Вес (г)", validators=[MinValueValidator(1)])
    
    # Кэшированные значения
    protein = models.FloatField(default=0, verbose_name="Белки (г)")
    fat = models.FloatField(default=0, verbose_name="Жиры (г)")
    carb = models.FloatField(default=0, verbose_name="Углеводы (г)")
    calories = models.FloatField(default=0, verbose_name="Калории")
    
    class Meta:
        verbose_name = "Продукт в приёме"
        verbose_name_plural = "Продукты в приёме"
    
    def save(self, *args, **kwargs):
        factor = self.weight_grams / 100
        self.protein = round(self.food.protein * factor, 2)
        self.fat = round(self.food.fat * factor, 2)
        self.carb = round(self.food.carb * factor, 2)
        self.calories = round(self.food.calories * factor, 2)
        super().save(*args, **kwargs)
    
    def __str__(self):
        return f"{self.food.name} - {self.weight_grams}г"