"""Принтер форматированной консольной сетки."""

import sys
from tabulate import tabulate
from .base import BasePrinter
from models import StandingsTable

# Наследуемся от базового минимума
class PrettyConsolePrinter(BasePrinter):
    """Красивый консольный вывод в виде псевдографической сетки (таблицы)."""
    def print_table(self, table: StandingsTable, title: str, stream=sys.stdout) -> None:
        stream.write(f"\n==================== {title.upper()} ====================\n")
        # Библиотека tabulate превращает DataFrame в готовую сетку с заголовками
        grid = tabulate(table.to_dataframe(), headers="keys", tablefmt="fancy_grid", showindex=False)
        stream.write(grid + "\n")
