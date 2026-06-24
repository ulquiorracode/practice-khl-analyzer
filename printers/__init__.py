"""Пакет для вывода таблиц"""

from .base import BasePrinter
from .plain import PlainPrinter
from .pretty import PrettyConsolePrinter

__all__ = ["BasePrinter", "PlainPrinter", "PrettyConsolePrinter"]
