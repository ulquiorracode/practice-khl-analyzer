"""Модель готовой выходной турнирной таблицы."""

import pandas as pd

class StandingsTable:
    """
    Класс-обертка над DataFrame, хранящим итоговую таблицу.
    Гарантирует, что наружу будут отданы только строго определенные
    регламентом КХЛ колонки и в правильном порядке.
    """
    
    def __init__(self, df: pd.DataFrame) -> None:
        # Список столбцов, которые мы хотим выводить на экран
        self._display_columns = ["Место", "Клуб", "И", "В", "ВО", "ВБ", "ПБ", "ПО", "П", "Ш", "О"]
        # Фильтруем исходный DataFrame, оставляя только нужные колонки, и сбрасываем индексы строк
        self.data: pd.DataFrame = df[self._display_columns].reset_index(drop=True)

    def to_dataframe(self) -> pd.DataFrame:
        """Возвращает отфильтрованные данные обратно в виде Pandas DataFrame."""
        return self.data
