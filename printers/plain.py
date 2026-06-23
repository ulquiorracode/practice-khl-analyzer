"""Простой вывод таблиц"""

from .base import BasePrinter
from models import StandingsTable

class PlainPrinter(BasePrinter):
    def print_table(self, table: StandingsTable, title: str) -> None:
        print(f"\n=== {title.upper()} ===")
        print(table.to_dataframe().to_string(index=False))
