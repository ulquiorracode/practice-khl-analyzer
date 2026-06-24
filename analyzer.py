"""Аналитический движок расчета очков КХЛ."""

from typing import Dict, List, Tuple
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from config import CONFERENCES, DIVISIONS
from models import MatchSchema, StandingsTable

# Словарь для начисления очков в КХЛ (система: 3 очка за победу в основное время)
# В - победа (3 очка), ВО/ВБ - победа в овертайме/буллитах (2 очка)
# ПО/ПБ - поражение в овертайме/буллитах (1 очко), П - поражение (0 очков)
POINTS_MAP: pd.Series = pd.Series({"В": 3, "ВО": 2, "ВБ": 2, "ПБ": 1, "ПО": 1, "П": 0})

# Колонки, по которым КХЛ сортирует команды при равенстве очков
SORT_COLUMNS: List[str] = ["О", "В", "ВО", "ВБ", "Разница", "Забито"]
# Сортировка по всем показателям идет по убыванию (False означает убывание)
SORT_ASCENDING: List[bool] = [False, False, False, False, False, False]


class KHLSeasonAnalyzer:
    """Анализатор, работающий строго со схемой данных MatchSchema."""
    
    def __init__(self, csv_path: str) -> None:
        self.csv_path: str = csv_path
        
        # Выделяем имя файла из пути (например, "khl_2017_18.csv"), чтобы понять, какой это сезон
        # и подгрузить для него правильные конференции из config.py
        self.season_key: str = pd.Series([csv_path]).str.replace(r"\\", "/", regex=True).str.split("/").str[-1].iloc[0]
        
        # Читаем CSV-файл, при этом Pandas сразу преобразует колонку с датой в формат datetime
        self.matches_df: pd.DataFrame = pd.read_csv(self.csv_path, parse_dates=[MatchSchema.DATE])
        
        # Преобразуем матчи в плоскую таблицу: одна строка — одна игра одной команды
        self.team_games_df: pd.DataFrame = self._process_match_outcomes()
        
        # Строим общую турнирную таблицу чемпионата
        self.global_standings_raw: pd.DataFrame = self._build_global_standings()

    def _parse_score(self, score_series: pd.Series) -> Tuple[pd.Series, pd.Series]:
        """
        Парсит строковый счет матча или периода (например, "3:2") в два числовых столбца.
        """
        # Заменяем пустые значения (NaN) на двоеточие ":" и приводим к строке
        filled: pd.Series = score_series.fillna(":").astype(str).str.strip()
        # Если счет отсутствует (просто ":"), заменяем его на "0:0"
        cleaned: pd.Series = filled.mask(filled.eq(":"), "0:0")
        # Разделяем строку по символу ":" на две колонки (голы хозяев и гостей)
        split_scores: pd.DataFrame = cleaned.str.split(":", expand=True)
        
        # Преобразуем строки в целые числа. Ошибки парсинга заменяем на 0
        home_goals: pd.Series = pd.to_numeric(split_scores[0], errors="coerce").fillna(0).astype(int)
        away_goals: pd.Series = pd.to_numeric(split_scores[1], errors="coerce").fillna(0).astype(int)
        return home_goals, away_goals

    def _process_match_outcomes(self) -> pd.DataFrame:
        """
        Рассчитывает исходы каждого матча для обеих команд.
        Превращает "матч между А и Б" в две записи: "команда А сыграла матч" и "команда Б сыграла матч".
        """
        # Извлекаем голы по периодам, овертаймам и буллитам
        p1_h, p1_a = self._parse_score(self.matches_df[MatchSchema.PERIOD_1])
        p2_h, p2_a = self._parse_score(self.matches_df[MatchSchema.PERIOD_2])
        p3_h, p3_a = self._parse_score(self.matches_df[MatchSchema.PERIOD_3])
        ot_h, ot_a = self._parse_score(self.matches_df[MatchSchema.OVERTIME])
        so_h, so_a = self._parse_score(self.matches_df[MatchSchema.BULLETS])

        # Считаем голы в основное время (первые 3 периода)
        reg_h: pd.Series = p1_h + p2_h + p3_h
        reg_a: pd.Series = p1_a + p2_a + p3_a
        
        # Считаем голы с учетом овертайма
        total_h: pd.Series = reg_h + ot_h
        total_a: pd.Series = reg_a + ot_a

        # Определяем логические маски (True/False) для исходов в основное время
        reg_home_win: pd.Series = reg_h.gt(reg_a)  # Победа хозяев в осн. время
        reg_away_win: pd.Series = reg_h.lt(reg_a)  # Победа гостей в осн. время
        reg_tie: pd.Series = reg_h.eq(reg_a)       # Ничья в осн. время

        # Определяем исходы в овертайме
        ot_home_win: pd.Series = reg_tie & ot_h.gt(ot_a)
        ot_away_win: pd.Series = reg_tie & ot_h.lt(ot_a)
        ot_tie: pd.Series = reg_tie & ot_h.eq(ot_a)

        # Определяем исходы в серии буллитов
        so_home_win: pd.Series = ot_tie & so_h.gt(so_a)
        so_away_win: pd.Series = ot_tie & so_h.lt(so_a)

        # Определяем буквенный код исхода для хозяев поля (по умолчанию "П" - поражение)
        # И последовательно заменяем (маскируем) значение в зависимости от условий
        home_code: pd.Series = pd.Series("П", index=self.matches_df.index)
        home_code = home_code.mask(reg_home_win, "В").mask(ot_home_win, "ВО").mask(so_home_win, "ВБ")
        home_code = home_code.mask(so_away_win, "ПБ").mask(ot_away_win, "ПО")

        # Аналогично определяем буквенный код исхода для гостей
        away_code: pd.Series = pd.Series("П", index=self.matches_df.index)
        away_code = away_code.mask(reg_away_win, "В").mask(ot_away_win, "ВО").mask(so_away_win, "ВБ")
        away_code = away_code.mask(so_home_win, "ПБ").mask(ot_home_win, "ПО")

        # Переводим буквенные коды в очки с помощью словаря POINTS_MAP
        home_pts: pd.Series = home_code.map(POINTS_MAP).astype(int)
        away_pts: pd.Series = away_code.map(POINTS_MAP).astype(int)

        # Полное количество шайб (в КХЛ победный буллит идет в общий зачет как +1 гол)
        h_goals: pd.Series = total_h + so_home_win.astype(int)
        a_goals: pd.Series = total_a + so_away_win.astype(int)

        # Создаем плоские датафреймы для хозяев и для гостей
        home_df: pd.DataFrame = pd.DataFrame({
            "Дата": self.matches_df[MatchSchema.DATE], "Команда": self.matches_df[MatchSchema.TEAM_1],
            "Забито": h_goals, "Пропущено": a_goals, "Очки_матч": home_pts, "Исход": home_code
        })
        away_df: pd.DataFrame = pd.DataFrame({
            "Дата": self.matches_df[MatchSchema.DATE], "Команда": self.matches_df[MatchSchema.TEAM_2],
            "Забито": a_goals, "Пропущено": h_goals, "Очки_матч": away_pts, "Исход": away_code
        })
        
        # Объединяем их по вертикали (строка под строкой) в один большой реестр сыгранных матчей
        return pd.concat([home_df, away_df], ignore_index=True)

    def _build_global_standings(self) -> pd.DataFrame:
        """
        Строит итоговую сводную таблицу чемпионата на основе реестра матчей.
        """
        # С помощью сводной таблицы (pivot_table) подсчитываем количество каждого исхода ("В", "ВО" и т.д.) для команд.
        # index="Команда" группирует по клубам, columns="Исход" создает столбцы для каждого типа исхода.
        outcomes_pivot: pd.DataFrame = self.team_games_df.pivot_table(
            index="Команда", columns="Исход", values="Очки_матч", aggfunc="count", fill_value=0
        ).reindex(columns=["В", "ВО", "ВБ", "ПБ", "ПО", "П"], fill_value=0).astype(int)

        # Группируем игры по командам и суммируем забитые/пропущенные шайбы, а также набранные очки
        aggregations: pd.DataFrame = self.team_games_df.groupby("Команда").agg(
            Забито=("Забито", "sum"), Пропущено=("Пропущено", "sum"), О=("Очки_матч", "sum")
        )

        # Объединяем сводную таблицу исходов и таблицу суммарных показателей по индексу (названию клуба)
        standings: pd.DataFrame = outcomes_pivot.join(aggregations)
        
        # Считаем количество проведенных игр ("И") как сумму всех возможных исходов
        standings["И"] = standings[["В", "ВО", "ВБ", "ПБ", "ПО", "П"]].sum(axis=1)
        # Считаем разницу шайб
        standings["Разница"] = standings["Забито"] - standings["Пропущено"]
        # Формируем строковое представление забитых и пропущенных шайб (например, "150-120")
        standings["Ш"] = standings["Забито"].astype(str) + "-" + standings["Пропущено"].astype(str)
        
        # Сбрасываем индекс, превращая "Клуб" из индекса в обычную колонку
        standings = standings.rename_axis("Клуб").reset_index()
        # Сортируем таблицу согласно регламенту КХЛ (Очки -> Победы -> Разница -> Забито)
        standings = standings.sort_values(by=SORT_COLUMNS, ascending=SORT_ASCENDING)
        # Проставляем места командам от 1 до N
        standings["Sub_Место"] = np.arange(1, len(standings) + 1) # Временное поле
        standings["Место"] = standings["Sub_Место"]
        standings = standings.drop(columns=["Sub_Место"])
        return standings

    def get_champion_table(self) -> StandingsTable:
        """Возвращает общую таблицу регулярного чемпионата."""
        return StandingsTable(self.global_standings_raw)

    def get_conference_tables(self) -> Dict[str, StandingsTable]:
        """
        Формирует таблицы конференций с учетом лидерства в дивизионах.
        По регламенту КХЛ лидеры дивизионов автоматически занимают первые 2 места в конференции.
        """
        # Получаем структуру конференций и дивизионов для конкретного сезона из config.py
        conf_dict: Dict[str, List[str]] = CONFERENCES.get(self.season_key, {})
        div_dict: Dict[str, List[List[str]]] = DIVISIONS.get(self.season_key, {})

        # Строим соответствие "Клуб -> Конференция" с помощью Pandas
        conf_mapping: pd.Series = pd.DataFrame(
            {"Конференция": list(conf_dict.keys()), "Клуб": list(conf_dict.values())}
        ).explode("Клуб").set_index("Клуб")["Конференция"]
        
        mapped_standings: pd.DataFrame = self.global_standings_raw.copy()
        # Прикрепляем к каждой команде её конференцию
        mapped_standings["Конференция"] = mapped_standings["Клуб"].map(conf_mapping)

        # То же самое делаем для дивизионов (если они описаны для этого сезона в конфиге)
        div_list_west: List[List[str]] = div_dict.get("Запад", [])
        div_list_east: List[List[str]] = div_dict.get("Восток", [])

        # Разносим клубы по числовым номерам дивизионов (0, 1 для Запада; 2, 3 для Востока)
        div_mapping_west: pd.Series = pd.DataFrame({"Дивизион": [0, 1], "Клуб": div_list_west}).explode("Клуб").set_index("Клуб")["Дивизион"] if div_list_west else pd.Series(dtype=int)
        div_mapping_east: pd.Series = pd.DataFrame({"Дивизион": [2, 3], "Клуб": div_list_east}).explode("Клуб").set_index("Клуб")["Дивизион"] if div_list_east else pd.Series(dtype=int)
        
        div_mapping: pd.Series = pd.concat([div_mapping_west, div_mapping_east])
        # Записываем дивизион в общую таблицу, отсутствующим ставим -1
        mapped_standings["Дивизион"] = mapped_standings["Клуб"].map(div_mapping).fillna(-1)

        # Находим лидеров дивизионов (группируем по дивизиону и берем строку с максимальными очками "О")
        division_leaders_idx: pd.Series = mapped_standings.groupby("Дивизион")["О"].idxmax()
        # Игнорируем тех, у кого дивизион не определен (-1)
        valid_leaders_idx: pd.Series = division_leaders_idx.drop(labels=[-1], errors="ignore")
        # Помечаем лидеров флагом 1, остальных — 0
        mapped_standings["Лидер_Дивизиона"] = mapped_standings.index.isin(valid_leaders_idx).astype(int)

        def process_sub_conf(conf_name: str) -> StandingsTable:
            """Внутренняя функция для фильтрации и сортировки отдельной конференции."""
            # Оставляем только команды выбранной конференции
            sub_df: pd.DataFrame = mapped_standings[mapped_standings["Конференция"] == conf_name].copy()
            # Сортируем: сначала идут лидеры дивизионов (по убыванию флага Лидер_Дивизиона), затем все остальные
            sub_df = sub_df.sort_values(by=["Лидер_Дивизиона"] + SORT_COLUMNS, ascending=[False] + SORT_ASCENDING)
            # Присваиваем места внутри конференции от 1 до N
            sub_df["Место"] = np.arange(1, len(sub_df) + 1)
            return StandingsTable(sub_df)

        # Возвращаем словарь с готовыми таблицами для каждой конференции
        return {name: process_sub_conf(name) for name in conf_dict.keys()}

    def plot_team_points(self, team_name: str) -> None:
        """Строит линейный график набора очков конкретной команды во времени."""
        # Фильтруем матчи только для нужной команды и сортируем по дате
        team_data: pd.DataFrame = self.team_games_df[self.team_games_df["Команда"] == team_name].sort_values("Дата").copy()
        # Считаем сумму очков нарастающим итогом (кумулятивная сумма)
        team_data["Очки_кум"] = team_data["Очки_матч"].cumsum()

        # Инициализируем полотно графика с помощью Matplotlib
        fig, ax = plt.subplots(figsize=(10, 5))
        # Строим линию графика с круглыми маркерами на точках матчей
        ax.plot(team_data["Дата"], team_data["Очки_кум"], marker="o", color="royalblue", linewidth=2)
        
        ax.set_title(f"Динамика набора очков команды «{team_name}»", fontsize=12)
        ax.set_xlabel("Дата")
        ax.set_ylabel("Очки (нарастающим итогом)")
        ax.grid(True, linestyle="--", alpha=0.5) # Добавляем полупрозрачную сетку
        fig.autofmt_xdate() # Красиво наклоняем даты на оси X, чтобы не перекрывались
        plt.tight_layout()
        plt.show()

    def plot_points_histogram(self) -> None:
        """Строит гистограмму распределения итоговых очков среди всех команд."""
        fig, ax = plt.subplots(figsize=(10, 5))
        # Строим гистограмму распределения очков (делим диапазон на 10 интервалов)
        ax.hist(self.global_standings_raw["О"], bins=10, color="forestgreen", edgecolor="black", alpha=0.7)
        
        ax.set_title("Гистограмма распределения набранных очков", fontsize=12)
        ax.set_xlabel("Количество набранных очков")
        ax.set_ylabel("Число команд")
        ax.grid(True, linestyle="--", alpha=0.5)
        plt.tight_layout()
        plt.show()

    def plot_team_goal_diff(self, team_name: str) -> None:
        """Строит кумулятивный график разницы забитых/пропущенных шайб команды."""
        # Выбираем матчи конкретной команды
        team_data: pd.DataFrame = self.team_games_df[self.team_games_df["Команда"] == team_name].sort_values("Дата").copy()
        # Считаем разницу шайб в отдельно взятом матче
        team_data["Разница_матча"] = team_data["Забито"] - team_data["Пропущено"]
        # Считаем разницу нарастающим итогом
        team_data["Разница_кум"] = team_data["Разница_матча"].cumsum()

        fig, ax = plt.subplots(figsize=(10, 5))
        # Строим линию разницы шайб (с квадратными маркерами)
        ax.plot(team_data["Дата"], team_data["Разница_кум"], marker="s", color="crimson", linewidth=2)
        # Проводим горизонтальную черту на уровне нуля (баланс забитых/пропущенных)
        ax.axhline(0, color="black", linestyle="-.", linewidth=1)
        
        ax.set_title(f"Разница забитых и пропущенных шайб команды «{team_name}»", fontsize=12)
        ax.set_xlabel("Дата")
        ax.set_ylabel("Суммарная разница шайб")
        ax.grid(True, linestyle="--", alpha=0.5)
        fig.autofmt_xdate()
        plt.tight_layout()
        plt.show()

    def plot_goals_histogram(self) -> None:
        """Строит гистограмму забитых шайб командами в лиге."""
        fig, ax = plt.subplots(figsize=(10, 5))
        # Строим гистограмму распределения суммарно заброшенных шайб по командам
        ax.hist(self.global_standings_raw["Забито"], bins=10, color="darkorange", edgecolor="black", alpha=0.7)
        
        ax.set_title("Гистограмма распределения заброшенных шайб", fontsize=12)
        ax.set_xlabel("Заброшенные шайбы")
        ax.set_ylabel("Число команд")
        ax.grid(True, linestyle="--", alpha=0.5)
        plt.tight_layout()
        plt.show()
