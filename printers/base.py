"""Базовый интерфейс для принтеров"""

from abc import ABC, abstractmethod
from models import StandingsTable

class BasePrinter(ABC):
    @abstractmethod
    def print_table(self, table: StandingsTable, title: str) -> None:
        pass
