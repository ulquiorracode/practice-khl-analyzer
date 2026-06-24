"""Улучшенный вывод таблиц"""

# Этот импорт для красивой таблички. Делается автоматически
from tabulate import tabulate
from .base import BasePrinter
from models import StandingsTable

# Наследуемся от базового минимума
class PrettyConsolePrinter(BasePrinter):
    """Красивый консольный вывод в виде псевдографической сетки (таблицы)."""
    def print_table(self, table: StandingsTable, title: str) -> None:
        print(f"\n==================== {title.upper()} ====================")
        # Библиотека tabulate превращает DataFrame в готовую сетку с заголовками
        print(tabulate(table.to_dataframe(), headers="keys", tablefmt="fancy_grid", showindex=False))
