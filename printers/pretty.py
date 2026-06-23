"""Улучшенный вывод таблиц"""

from tabulate import tabulate
from .base import BasePrinter
from models import StandingsTable

class PrettyConsolePrinter(BasePrinter):
    def print_table(self, table: StandingsTable, title: str) -> None:
        print(f"\n==================== {title.upper()} ====================")
        print(tabulate(table.to_dataframe(), headers="keys", tablefmt="fancy_grid", showindex=False))
