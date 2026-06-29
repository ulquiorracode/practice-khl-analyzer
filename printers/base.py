"""Базовый интерфейс для принтеров"""

import sys
from abc import ABC, abstractmethod
from models import StandingsTable
from typing import Callable

class BasePrinter(ABC):
    """
    Абстрактный класс. Создает обязательный шаблон (интерфейс)
    для всех будущих классов вывода таблиц.
    """
    @abstractmethod
    def print_table(self, table: StandingsTable, title: str, stream=sys.stdout, formatter: Callable[[], str] = lambda text: text) -> None:
        """Любой наследник обязан реализовать этот метод."""
        pass
