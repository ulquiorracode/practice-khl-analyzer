"""Модель готовой выходной турнирной таблицы."""

import pandas as pd

class StandingsTable:
    """Модель данных турнирной таблицы, инкапсулирующая DataFrame КХЛ."""
    
    def __init__(self, df: pd.DataFrame) -> None:
        self._display_columns = ["Место", "Клуб", "И", "В", "ВО", "ВБ", "ПБ", "ПО", "П", "Ш", "О"]
        self.data: pd.DataFrame = df[self._display_columns].reset_index(drop=True)

    def to_dataframe(self) -> pd.DataFrame:
        return self.data
