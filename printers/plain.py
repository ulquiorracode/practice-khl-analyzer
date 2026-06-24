"""Простой вывод таблиц"""

import sys
from .base import BasePrinter
from models import StandingsTable

# Наследуемся от базового минимума
class PlainPrinter(BasePrinter):
    def print_table(self, table: StandingsTable, title: str, stream=sys.stdout) -> None:
        # Пишем напрямую в переданный поток
        stream.write(f"\n=== {title.upper()} ===\n")
        stream.write(table.to_dataframe().to_string(index=False) + "\n")
