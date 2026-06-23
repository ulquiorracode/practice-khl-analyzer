"""Модели данных турнирной системы КХЛ"""

from .match_schema import MatchSchema
from .standings import StandingsTable

__all__ = ["MatchSchema", "StandingsTable"]
