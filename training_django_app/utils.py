# utils.py
from .models import DailyTarget
from django.utils import timezone


def get_or_create_daily_target(user, date):
    # Получить или создать цели пользователя на конкретную дату
    try:
        return DailyTarget.objects.get(user=user, date=date)
    except DailyTarget.DoesNotExist:
        # Берём текущие цели пользователя
        profile = user.profile
        targets = profile.calculate_daily_targets()

        return DailyTarget.objects.create(
            user=user,
            date=date,
            calories=targets['calories'],
            protein=targets['protein'],
            fat=targets['fat'],
            carb=targets['carb'],
            is_custom=targets.get('is_custom', False)
        )


def get_targets_for_date(user, date):
    # Получить цели для отображения на дашборде
    try:
        target = DailyTarget.objects.get(user=user, date=date)
        return {
            'calories': target.calories,
            'protein': target.protein,
            'fat': target.fat,
            'carb': target.carb,
            'is_custom': target.is_custom
        }
    except DailyTarget.DoesNotExist:
        # Если целей на эту дату нет — создаём из текущих целей
        profile = user.profile
        targets = profile.calculate_daily_targets()

        # Создаём запись в DailyTarget для этой даты
        DailyTarget.objects.create(
            user=user,
            date=date,
            calories=targets['calories'],
            protein=targets['protein'],
            fat=targets['fat'],
            carb=targets['carb'],
            is_custom=targets.get('is_custom', False)
        )

        return targets


def update_future_daily_targets(user):
    # Обновить DailyTarget для сегодня и всех будущих дат
    today = timezone.now().date()
    profile = user.profile
    targets = profile.calculate_daily_targets()

    # Обновляем или создаём для сегодня и всех будущих дней
    future_targets = DailyTarget.objects.filter(
        user=user,
        date__gte=today
    )

    for future in future_targets:
        future.calories = targets['calories']
        future.protein = targets['protein']
        future.fat = targets['fat']
        future.carb = targets['carb']
        future.is_custom = targets.get('is_custom', False)
        future.save()

    # Если нет записи на сегодня — создаём
    DailyTarget.objects.update_or_create(
        user=user,
        date=today,
        defaults={
            'calories': targets['calories'],
            'protein': targets['protein'],
            'fat': targets['fat'],
            'carb': targets['carb'],
            'is_custom': targets.get('is_custom', False)
        }
    )