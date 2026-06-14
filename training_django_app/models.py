from django.db import models
from django.db.models.signals import post_save
from django.contrib.auth.models import AbstractUser
from datetime import date
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone
from django.dispatch import receiver


class app_user(AbstractUser):
    # Кастомная модель пользователя с входом по email
    # Выбор пола для пользователя
    GENDER_CHOICES = [
        ('male', 'Мужской'),
        ('female', 'Женский'),
    ]

    # Уникальный email используется как основной идентификатор
    email = models.EmailField(unique=True)
    # Полное имя пользователя
    full_name = models.CharField(max_length=255, verbose_name='ФИО')
    # Дата рождения для расчёта возраста
    birth_date = models.DateField(verbose_name='Дата рождения')
    # Пол пользователя
    gender = models.CharField(
        max_length=10,
        choices=GENDER_CHOICES,
        verbose_name='Пол',
        default='other'
    )

    # Поле для входа (email вместо username)
    USERNAME_FIELD = 'email'
    # Обязательные поля при создании суперпользователя
    REQUIRED_FIELDS = ['username', 'full_name', 'birth_date', 'gender']

    class Meta:
        verbose_name = 'Пользователь'
        verbose_name_plural = 'Пользователи'

    def __str__(self):
        return self.full_name

    @property
    def age(self):
        # Расчёт возраста на основе даты рождения
        today = date.today()
        return today.year - self.birth_date.year - (
            (today.month, today.day) < (self.birth_date.month, self.birth_date.day)
        )


class UserProfile(models.Model):
    # Профиль пользователя с антропометрическими данными и целями
    # Варианты целей пользователя
    GOAL_CHOICES = [
        ('weight_loss', 'Похудение'),
        ('maintenance', 'Поддержание веса'),
        ('muscle_gain', 'Набор массы'),
    ]

    # Коэффициенты активности для расчёта калорий
    ACTIVITY_LEVELS = [
        (1.2, 'Сидячий образ жизни'),
        (1.375, 'Лёгкая активность (1-3 дня/неделю)'),
        (1.55, 'Умеренная активность (3-5 дней/неделю)'),
        (1.725, 'Высокая активность (6-7 дней/неделю)'),
        (1.9, 'Экстремальная активность'),
    ]

    # Связь один-к-одному с пользователем
    user = models.OneToOneField(
        app_user,
        on_delete=models.CASCADE,
        related_name='profile',
        verbose_name='Пользователь'
    )

    # Антропометрические данные
    weight = models.FloatField(
        verbose_name='Вес (кг)',
        validators=[MinValueValidator(20, 'Вес должен быть > 20 кг')]
    )
    height = models.PositiveIntegerField(
        verbose_name='Рост (см)',
        validators=[MinValueValidator(100, 'Рост должен быть > 100 см')]
    )
    # Процент жира (опционально, для точного расчёта)
    body_fat = models.FloatField(
        null=True,
        blank=True,
        verbose_name='Процент жира (%)',
        validators=[MinValueValidator(5), MaxValueValidator(60)]
    )

    # Цели и уровень активности
    goal = models.CharField(
        max_length=20,
        choices=GOAL_CHOICES,
        default='maintenance',
        verbose_name='Цель'
    )
    activity_level = models.FloatField(
        choices=ACTIVITY_LEVELS,
        default=1.375,
        verbose_name='Уровень активности'
    )

    # Целевые значения КБЖУ (могут быть переопределены вручную)
    target_protein = models.FloatField(
        blank=True,
        null=True,
        verbose_name='Целевой белок (г/день)'
    )
    target_fat = models.FloatField(
        blank=True,
        null=True,
        verbose_name='Целевые жиры (г/день)'
    )
    target_carb = models.FloatField(
        blank=True,
        null=True,
        verbose_name='Целевые углеводы (г/день)'
    )
    # Флаг ручной настройки целей
    custom_targets_enabled = models.BooleanField(
        default=False,
        verbose_name="Ручная настройка целей"
    )
    # Пользовательские целевые калории
    custom_calories = models.FloatField(
        blank=True,
        null=True,
        verbose_name="Целевые калории (своё значение)"
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Профиль пользователя'
        verbose_name_plural = 'Профили пользователей'

    def __str__(self):
        return f'Профиль {self.user.full_name}'

    def get_lean_mass(self):
        # Возвращает безжировую массу тела (кг)
        # Если процент жира не указан — используется среднее значение по полу
        if self.body_fat and self.body_fat > 0:
            return self.weight * (1 - self.body_fat / 100)
        else:
            # Предполагаем средний процент жира по полу
            if self.user.gender == 'male':
                estimated_body_fat = 0.15  # 15% для мужчин
            else:
                estimated_body_fat = 0.22  # 22% для женщин
            return self.weight * (1 - estimated_body_fat)

    @property
    def bmi(self):
        # Индекс массы тела (ИМТ)
        if self.height > 0:
            height_m = self.height / 100
            return round(self.weight / (height_m ** 2), 1)
        return 0

    @property
    def bmr(self):
        # Базальный метаболизм (BMR)
        # Если есть процент жира — формула Кэтча-МакАрдла (точнее)
        # Иначе — формула Миффлина-Сан-Жеора
        if self.body_fat and self.body_fat > 0:
            # Формула Кэтча-МакАрдла (на основе безжировой массы)
            lean_mass = self.get_lean_mass()
            return round(370 + (21.6 * lean_mass), 1)
        else:
            # Формула Миффлина-Сан-Жеора (на основе веса, роста, возраста)
            age = self.user.age
            if self.user.gender == 'male':
                return round(10 * self.weight + 6.25 * self.height - 5 * age + 5, 1)
            else:
                return round(10 * self.weight + 6.25 * self.height - 5 * age - 161, 1)

    @property
    def lean_mass(self):
        # Безжировая масса (кг) для отображения в профиле
        return round(self.get_lean_mass(), 1)

    @property
    def maintenance_calories(self):
        # Калории для поддержания веса (BMR * активность)
        calories = round(self.bmr * self.activity_level)

        # Корректировка для высокого ИМТ (только если нет процента жира)
        if not self.body_fat and self.bmi > 30:
            calories = int(calories * 0.85)

        return max(calories, 1500)

    def calculate_daily_targets(self):
        # Расчёт целевых КБЖУ на день
        # Если ручная настройка включена — возвращаем ручные значения
        if self.custom_targets_enabled and self.custom_calories:
            protein = self.target_protein or 0
            fat = self.target_fat or 0
            carb = self.target_carb or 0
            calories = self.custom_calories

            # Если калории не указаны, рассчитываем из БЖУ
            if not self.custom_calories and protein and fat and carb:
                calories = round(protein * 4 + fat * 9 + carb * 4, 1)

            return {
                'calories': int(calories),
                'protein': protein,
                'fat': fat,
                'carb': carb,
                'is_custom': True
            }

        # Автоматический расчёт
        lean_mass = self.get_lean_mass()

        # Целевые калории на основе поддержания веса и цели
        calories = self.maintenance_calories

        # Корректировка калорий под цель (дефицит/профицит)
        if self.goal == 'weight_loss':
            calories = int(calories * 0.8)  # Дефицит 20% для похудения
        elif self.goal == 'muscle_gain':
            calories = int(calories * 1.1)  # Профицит 10% для набора массы

        # Коэффициенты БЖУ в зависимости от цели
        if self.goal == 'weight_loss':
            protein_coef = 2.2      # Выше, чтобы сохранить мышцы
            fat_coef = 0.8          # Чуть режем жиры
        elif self.goal == 'muscle_gain':
            protein_coef = 2.4      # Больше для роста мышц
            fat_coef = 1.0          # Норма
        else:  # maintenance
            protein_coef = 2.0
            fat_coef = 1.0

        # Расчёт БЖУ от безжировой массы
        target_protein = round(lean_mass * protein_coef, 1)
        target_fat = round(lean_mass * fat_coef, 1)

        # Углеводы: остаток калорий после вычета белков и жиров
        protein_calories = target_protein * 4
        fat_calories = target_fat * 9
        carb_calories = calories - protein_calories - fat_calories
        target_carb = round(carb_calories / 4, 1)

        # Если углеводы получились отрицательными — корректируем жиры
        if target_carb < 0:
            target_fat = round((calories - protein_calories) / 9, 1)
            target_carb = 0

        return {
            'calories': calories,
            'protein': target_protein,
            'fat': target_fat,
            'carb': target_carb,
            'is_custom': False
        }


class DailyTarget(models.Model):
    # Сохранённые цели пользователя на конкретную дату
    # Нужны для отображения старых целей при просмотре истории
    user = models.ForeignKey(
        app_user,
        on_delete=models.CASCADE,
        verbose_name="Пользователь"
    )
    date = models.DateField(verbose_name="Дата")
    calories = models.FloatField(verbose_name="Целевые калории")
    protein = models.FloatField(verbose_name="Целевой белок")
    fat = models.FloatField(verbose_name="Целевые жиры")
    carb = models.FloatField(verbose_name="Целевые углеводы")
    is_custom = models.BooleanField(
        default=False,
        verbose_name="Ручная настройка"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Дневная цель"
        verbose_name_plural = "Дневные цели"
        unique_together = ['user', 'date']  # Один пользователь — одна запись на дату
        ordering = ['-date']

    def __str__(self):
        return f"{self.user.username} - {self.date}: {self.calories} ккал"


class food_catalogue(models.Model):
    # Единый каталог продуктов и блюд
    # Продукты общие для всех пользователей (нет поля user)
    name = models.CharField(max_length=200, verbose_name="Название")
    # True = блюдо (составное), False = продукт (базовый)
    is_dish = models.BooleanField(
        default=False,
        verbose_name="Это блюдо? (если нет - продукт)"
    )
    # Кто создал (для продуктов и блюд)
    created_by = models.ForeignKey(
        app_user,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name="Кто создал",
        related_name='created_products'
    )
    # БЖУ на 100г
    protein = models.FloatField(default=0, verbose_name="Белки (г/100г)")
    carb = models.FloatField(default=0, verbose_name="Углеводы (г/100г)")
    fat = models.FloatField(default=0, verbose_name="Жиры (г/100г)")
    # Калории на 100г (рассчитывается автоматически)
    calories = models.FloatField(
        default=0,
        editable=False,
        verbose_name="Калории (на 100г)"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    # Время последнего использования (для сортировки недавних)
    last_used = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Последнее использование"
    )

    def save(self, *args, **kwargs):
        # Переопределяем сохранение для автоматического расчёта калорий
        is_new = self.pk is None  # Проверяем, новый ли объект

        if not self.is_dish:
            # Для продуктов — рассчитываем калории из БЖУ
            self.calories = round(self.protein * 4 + self.carb * 4 + self.fat * 9, 2)
        else:
            # Для новых блюд обнуляем БЖУ (потом пересчитаются из ингредиентов)
            if is_new:
                self.protein = 0
                self.carb = 0
                self.fat = 0
                self.calories = 0
            # Для существующих блюд — не трогаем (БЖУ уже рассчитаны)

        super().save(*args, **kwargs)

    def update_from_ingredients(self):
        # Пересчитывает КБЖУ блюда на основе ингредиентов (для is_dish=True)
        if not self.is_dish:
            return  # Только для блюд

        ingredients = self.ingredients.all()

        if not ingredients.exists():
            # Нет ингредиентов — обнуляем
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
        # Рассчитывает КБЖУ для указанного веса (в граммах)
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
    # Ингредиент в составе блюда
    # Связывает блюдо с продуктом/блюдом, которое входит в его состав
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
        # Расчет КБЖУ для ингредиента на его вес
        return self.ingredient.calculate_for_weight(self.weight_grams)

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        # После сохранения ингредиента пересчитываем блюдо
        self.dish.update_from_ingredients()

    def delete(self, *args, **kwargs):
        dish = self.dish
        super().delete(*args, **kwargs)
        # После удаления ингредиента пересчитываем блюдо
        dish.update_from_ingredients()

    def __str__(self):
        return f"{self.ingredient.name} - {self.weight_grams}г в {self.dish.name}"

    class Meta:
        verbose_name = "Ингредиент"
        verbose_name_plural = "Ингредиенты"


class exercise_catalogue(models.Model):
    # Каталог упражнений (общая база)
    name = models.CharField(max_length=100, verbose_name="Название упражнения")
    # Кто создал упражнение
    created_by = models.ForeignKey(
        app_user,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name="Кто создал",
        related_name='created_exercises'
    )
    # Калорийность в час (упрощённый расчёт)
    calories_per_hour = models.IntegerField(
        null=True,
        blank=True,
        verbose_name="Калорий в час"
    )
    # MET (метаболический эквивалент) — более точный расчёт
    met = models.FloatField(
        null=True,
        blank=True,
        verbose_name="MET (коэффициент интенсивности)"
    )
    # Общее упражнение (доступно всем) или личное
    is_shared = models.BooleanField(default=True, verbose_name="Общее упражнение")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Упражнение"
        verbose_name_plural = "Упражнения"
        ordering = ['name']

    def __str__(self):
        return self.name


class ExerciseRecord(models.Model):
    # Запись о выполненной тренировке
    user = models.ForeignKey(
        app_user,
        on_delete=models.CASCADE,
        verbose_name="Пользователь"
    )
    exercise = models.ForeignKey(
        exercise_catalogue,
        on_delete=models.CASCADE,
        verbose_name="Упражнение"
    )
    date = models.DateField(default=date.today, verbose_name="Дата")
    time = models.TimeField(default=timezone.now, verbose_name="Время")
    duration_minutes = models.PositiveIntegerField(
        verbose_name="Длительность (минуты)"
    )
    # Рассчитывается автоматически при сохранении
    calories_burned = models.FloatField(
        verbose_name="Сожжено калорий",
        editable=False,
        default=0
    )
    created_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        # Расчёт калорий с приоритетом MET (с учётом BMR пользователя)
        if self.exercise.met:
            # BMR пользователя в минуту (24ч * 60мин = 1440 минут)
            bmr_per_minute = self.user.profile.bmr / 1440
            self.calories_burned = round(
                self.exercise.met * bmr_per_minute * self.duration_minutes,
                2
            )
        elif self.exercise.calories_per_hour:
            # Старый расчёт (если нет MET)
            self.calories_burned = round(
                (self.exercise.calories_per_hour / 60) * self.duration_minutes,
                2
            )
        else:
            self.calories_burned = 0

        super().save(*args, **kwargs)

    class Meta:
        verbose_name = "Запись тренировки"
        verbose_name_plural = "Записи тренировок"
        ordering = ['-date', '-created_at']

    def __str__(self):
        return f"{self.user.username} - {self.exercise.name} - {self.date}"


class Meal(models.Model):
    # Приём пищи (группа продуктов)
    user = models.ForeignKey(
        app_user,
        on_delete=models.CASCADE,
        verbose_name="Пользователь"
    )
    date = models.DateField(default=date.today, verbose_name="Дата")
    time = models.TimeField(default=timezone.now, verbose_name="Время приёма")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Приём пищи"
        verbose_name_plural = "Приёмы пищи"
        ordering = ['-date', '-time', '-created_at']

    def __str__(self):
        return f"{self.user.username} - {self.date} {self.time}"

    def is_empty(self):
        # Проверяет, есть ли продукты в приёме
        return not self.items.exists()

    def total_calories(self):
        # Сумма калорий всех продуктов в приёме
        return sum(item.calories for item in self.items.all())

    def total_protein(self):
        # Сумма белков всех продуктов в приёме
        return sum(item.protein for item in self.items.all())

    def total_fat(self):
        # Сумма жиров всех продуктов в приёме
        return sum(item.fat for item in self.items.all())

    def total_carb(self):
        # Сумма углеводов всех продуктов в приёме
        return sum(item.carb for item in self.items.all())

    def total_weight(self):
        # Общий вес всех продуктов в приёме
        return sum(item.weight_grams for item in self.items.all())


class MealItem(models.Model):
    # Продукт в приёме пищи
    meal = models.ForeignKey(
        Meal,
        on_delete=models.CASCADE,
        related_name='items',
        verbose_name="Приём пищи"
    )
    food = models.ForeignKey(
        food_catalogue,
        on_delete=models.CASCADE,
        verbose_name="Продукт"
    )
    weight_grams = models.FloatField(
        default=100,
        verbose_name="Вес (г)",
        validators=[MinValueValidator(1)]
    )

    # Кэшированные значения (сохраняются в БД для быстрых запросов)
    protein = models.FloatField(default=0, verbose_name="Белки (г)")
    fat = models.FloatField(default=0, verbose_name="Жиры (г)")
    carb = models.FloatField(default=0, verbose_name="Углеводы (г)")
    calories = models.FloatField(default=0, verbose_name="Калории")

    class Meta:
        verbose_name = "Продукт в приёме"
        verbose_name_plural = "Продукты в приёме"

    def save(self, *args, **kwargs):
        # Расчёт КБЖУ на основе веса порции
        factor = self.weight_grams / 100
        self.protein = round(self.food.protein * factor, 2)
        self.fat = round(self.food.fat * factor, 2)
        self.carb = round(self.food.carb * factor, 2)
        self.calories = round(self.food.calories * factor, 2)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.food.name} - {self.weight_grams}г"


@receiver(post_save, sender=Meal)
@receiver(post_save, sender=ExerciseRecord)
def update_daily_target(sender, instance, created, **kwargs):
    # Сигнал: при сохранении приёма пищи или тренировки
    # создаём/обновляем цели на этот день
    # Импорт внутри функции, чтобы избежать циклического импорта
    from .utils import get_or_create_daily_target
    get_or_create_daily_target(instance.user, instance.date)