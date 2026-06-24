"""Простой вывод таблиц"""

from .base import BasePrinter
from models import StandingsTable

# Наследуемся от базового минимума
class PlainPrinter(BasePrinter):
    """Обычный вывод данных в виде стандартного текста."""
    def print_table(self, table: StandingsTable, title: str) -> None:
        print(f"\n=== {title.upper()} ===")
        # Преобразуем DataFrame в простую строку без индексов строк
        print(table.to_dataframe().to_string(index=False))
