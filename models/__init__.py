"""Модели данных турнирной системы КХЛ"""

from .match_schema import MatchSchema
from .standings import StandingsTable

# Экспортируем наружу только то, что нужно другим модулям
# Иначе при импорте * из models в analyzer.py
# Мы будем импортировать всё, что есть в папке models
__all__ = ["MatchSchema", "StandingsTable"]
