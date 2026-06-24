"""Реализация принтера для вывода таблиц в формате HTML."""

import sys
from .base import BasePrinter
from models import StandingsTable

class HtmlPrinter(BasePrinter):
    """
    Принтер для генерации HTML-кода турнирных таблиц.
    
    Использует встроенные векторные возможности Pandas для рендеринга HTML,
    что исключает ручную конкатенацию строк и использование циклов.
    """
    def print_table(self, table: StandingsTable, title: str, stream=sys.stdout) -> None:
        # Выводим заголовок в теге h2 и генерируем таблицу
        stream.write(f"\n<h2>{title}</h2>\n")
        
        # Метод .to_html() преобразует DataFrame в готовую HTML-таблицу.
        # border=1 добавляет стандартную рамку, а index=False убирает колонку индексов Pandas.
        html_code = table.to_dataframe().to_html(
            index=False,
            border=1,
            classes="khl-standings-table"
        )

        stream.write(html_code + "\n")
        