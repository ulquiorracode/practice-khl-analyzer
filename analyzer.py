"""Аналитический движок расчета очков КХЛ."""

from typing import Dict, List, Tuple
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from config import CONFERENCES, DIVISIONS
from models import MatchSchema, StandingsTable

POINTS_MAP: pd.Series = pd.Series({"В": 3, "ВО": 2, "ВБ": 2, "ПБ": 1, "ПО": 1, "П": 0})
SORT_COLUMNS: List[str] = ["О", "В", "ВО", "ВБ", "Разница", "Забито"]
SORT_ASCENDING: List[bool] = [False, False, False, False, False, False]


class KHLSeasonAnalyzer:
    """Анализатор, работающий строго со схемой данных MatchSchema."""
    
    def __init__(self, csv_path: str) -> None:
        self.csv_path: str = csv_path
        self.season_key: str = pd.Series([csv_path]).str.replace(r"\\", "/", regex=True).str.split("/").str[-1].iloc[0]
        # Читаем CSV-файл с указанием парсинга даты по схеме
        self.matches_df: pd.DataFrame = pd.read_csv(self.csv_path, parse_dates=[MatchSchema.DATE])
        self.team_games_df: pd.DataFrame = self._process_match_outcomes()
        self.global_standings_raw: pd.DataFrame = self._build_global_standings()

    def _parse_score(self, score_series: pd.Series) -> Tuple[pd.Series, pd.Series]:
        filled: pd.Series = score_series.fillna(":").astype(str).str.strip()
        cleaned: pd.Series = filled.mask(filled.eq(":"), "0:0")
        split_scores: pd.DataFrame = cleaned.str.split(":", expand=True)
        
        home_goals: pd.Series = pd.to_numeric(split_scores[0], errors="coerce").fillna(0).astype(int)
        away_goals: pd.Series = pd.to_numeric(split_scores[1], errors="coerce").fillna(0).astype(int)
        return home_goals, away_goals

    def _process_match_outcomes(self) -> pd.DataFrame:
        # Обращаемся к колонкам сырого CSV исключительно через MatchSchema
        p1_h, p1_a = self._parse_score(self.matches_df[MatchSchema.PERIOD_1])
        p2_h, p2_a = self._parse_score(self.matches_df[MatchSchema.PERIOD_2])
        p3_h, p3_a = self._parse_score(self.matches_df[MatchSchema.PERIOD_3])
        ot_h, ot_a = self._parse_score(self.matches_df[MatchSchema.OVERTIME])
        so_h, so_a = self._parse_score(self.matches_df[MatchSchema.BULLETS])

        reg_h: pd.Series = p1_h + p2_h + p3_h
        reg_a: pd.Series = p1_a + p2_a + p3_a
        total_h: pd.Series = reg_h + ot_h
        total_a: pd.Series = reg_a + ot_a

        reg_home_win: pd.Series = reg_h.gt(reg_a)
        reg_away_win: pd.Series = reg_h.lt(reg_a)
        reg_tie: pd.Series = reg_h.eq(reg_a)

        ot_home_win: pd.Series = reg_tie & ot_h.gt(ot_a)
        ot_away_win: pd.Series = reg_tie & ot_h.lt(ot_a)
        ot_tie: pd.Series = reg_tie & ot_h.eq(ot_a)

        so_home_win: pd.Series = ot_tie & so_h.gt(so_a)
        so_away_win: pd.Series = ot_tie & so_h.lt(so_a)

        home_code: pd.Series = pd.Series("П", index=self.matches_df.index)
        home_code = home_code.mask(reg_home_win, "В").mask(ot_home_win, "ВО").mask(so_home_win, "ВБ")
        home_code = home_code.mask(so_away_win, "ПБ").mask(ot_away_win, "ПО")

        away_code: pd.Series = pd.Series("П", index=self.matches_df.index)
        away_code = away_code.mask(reg_away_win, "В").mask(ot_away_win, "ВО").mask(so_away_win, "ВБ")
        away_code = away_code.mask(so_home_win, "ПБ").mask(ot_home_win, "ПО")

        home_pts: pd.Series = home_code.map(POINTS_MAP).astype(int)
        away_pts: pd.Series = away_code.map(POINTS_MAP).astype(int)

        h_goals: pd.Series = total_h + so_home_win.astype(int)
        a_goals: pd.Series = total_a + so_away_win.astype(int)

        home_df: pd.DataFrame = pd.DataFrame({
            "Дата": self.matches_df[MatchSchema.DATE], "Команда": self.matches_df[MatchSchema.TEAM_1],
            "Забито": h_goals, "Пропущено": a_goals, "Очки_матч": home_pts, "Исход": home_code
        })
        away_df: pd.DataFrame = pd.DataFrame({
            "Дата": self.matches_df[MatchSchema.DATE], "Команда": self.matches_df[MatchSchema.TEAM_2],
            "Забито": a_goals, "Пропущено": h_goals, "Очки_матч": away_pts, "Исход": away_code
        })
        return pd.concat([home_df, away_df], ignore_index=True)

    def _build_global_standings(self) -> pd.DataFrame:
        outcomes_pivot: pd.DataFrame = self.team_games_df.pivot_table(
            index="Команда", columns="Исход", values="Очки_матч", aggfunc="count", fill_value=0
        ).reindex(columns=["В", "ВО", "ВБ", "ПБ", "ПО", "П"], fill_value=0).astype(int)

        aggregations: pd.DataFrame = self.team_games_df.groupby("Команда").agg(
            Забито=("Забито", "sum"), Пропущено=("Пропущено", "sum"), О=("Очки_матч", "sum")
        )

        standings: pd.DataFrame = outcomes_pivot.join(aggregations)
        standings["И"] = standings[["В", "ВО", "ВБ", "ПБ", "ПО", "П"]].sum(axis=1)
        standings["Разница"] = standings["Забито"] - standings["Пропущено"]
        standings["Ш"] = standings["Забито"].astype(str) + "-" + standings["Пропущено"].astype(str)
        standings = standings.rename_axis("Клуб").reset_index()
        standings = standings.sort_values(by=SORT_COLUMNS, ascending=SORT_ASCENDING)
        standings["Место"] = np.arange(1, len(standings) + 1)
        return standings

    def get_champion_table(self) -> StandingsTable:
        return StandingsTable(self.global_standings_raw)

    def get_conference_tables(self) -> Dict[str, StandingsTable]:
        conf_dict: Dict[str, List[str]] = CONFERENCES.get(self.season_key, {})
        div_dict: Dict[str, List[List[str]]] = DIVISIONS.get(self.season_key, {})

        conf_mapping: pd.Series = pd.DataFrame(
            {"Конференция": list(conf_dict.keys()), "Клуб": list(conf_dict.values())}
        ).explode("Клуб").set_index("Клуб")["Конференция"]

        mapped_standings: pd.DataFrame = self.global_standings_raw.copy()
        mapped_standings["Конференция"] = mapped_standings["Клуб"].map(conf_mapping)

        div_list_west: List[List[str]] = div_dict.get("Запад", [])
        div_list_east: List[List[str]] = div_dict.get("Восток", [])

        div_mapping_west: pd.Series = pd.DataFrame({"Дивизион": [0, 1], "Клуб": div_list_west}).explode("Клуб").set_index("Клуб")["Дивизион"] if div_list_west else pd.Series(dtype=int)
        div_mapping_east: pd.Series = pd.DataFrame({"Дивизион": [2, 3], "Клуб": div_list_east}).explode("Клуб").set_index("Клуб")["Дивизион"] if div_list_east else pd.Series(dtype=int)
        
        div_mapping: pd.Series = pd.concat([div_mapping_west, div_mapping_east])
        mapped_standings["Дивизион"] = mapped_standings["Клуб"].map(div_mapping).fillna(-1)

        division_leaders_idx: pd.Series = mapped_standings.groupby("Дивизион")["О"].idxmax()
        valid_leaders_idx: pd.Series = division_leaders_idx.drop(labels=[-1], errors="ignore")
        mapped_standings["Лидер_Дивизиона"] = mapped_standings.index.isin(valid_leaders_idx).astype(int)

        def process_sub_conf(conf_name: str) -> StandingsTable:
            sub_df: pd.DataFrame = mapped_standings[mapped_standings["Конференция"] == conf_name].copy()
            sub_df = sub_df.sort_values(by=["Лидер_Дивизиона"] + SORT_COLUMNS, ascending=[False] + SORT_ASCENDING)
            sub_df["Место"] = np.arange(1, len(sub_df) + 1)
            return StandingsTable(sub_df)

        return {name: process_sub_conf(name) for name in conf_dict.keys()}

    def plot_team_points(self, team_name: str) -> None:
        team_data: pd.DataFrame = self.team_games_df[self.team_games_df["Команда"] == team_name].sort_values("Дата").copy()
        team_data["Очки_кум"] = team_data["Очки_матч"].cumsum()

        fig, ax = plt.subplots(figsize=(10, 5))
        ax.plot(team_data["Дата"], team_data["Очки_кум"], marker="o", color="royalblue", linewidth=2)
        ax.set_title(f"Динамика набора очков команды «{team_name}»", fontsize=12)
        ax.set_xlabel("Дата")
        ax.set_ylabel("Очки (нарастающим итогом)")
        ax.grid(True, linestyle="--", alpha=0.5)
        fig.autofmt_xdate()
        plt.tight_layout()
        plt.show()

    def plot_points_histogram(self) -> None:
        fig, ax = plt.subplots(figsize=(10, 5))
        ax.hist(self.global_standings_raw["О"], bins=10, color="forestgreen", edgecolor="black", alpha=0.7)
        ax.set_title("Гистограмма распределения набранных очков", fontsize=12)
        ax.set_xlabel("Количество набранных очков")
        ax.set_ylabel("Число команд")
        ax.grid(True, linestyle="--", alpha=0.5)
        plt.tight_layout()
        plt.show()

    def plot_team_goal_diff(self, team_name: str) -> None:
        team_data: pd.DataFrame = self.team_games_df[self.team_games_df["Команда"] == team_name].sort_values("Дата").copy()
        team_data["Разница_матча"] = team_data["Забито"] - team_data["Пропущено"]
        team_data["Разница_кум"] = team_data["Разница_матча"].cumsum()

        fig, ax = plt.subplots(figsize=(10, 5))
        ax.plot(team_data["Дата"], team_data["Разница_кум"], marker="s", color="crimson", linewidth=2)
        ax.axhline(0, color="black", linestyle="-.", linewidth=1)
        ax.set_title(f"Разница забитых и пропущенных шайб команды «{team_name}»", fontsize=12)
        ax.set_xlabel("Дата")
        ax.set_ylabel("Суммарная разница шайб")
        ax.grid(True, linestyle="--", alpha=0.5)
        fig.autofmt_xdate()
        plt.tight_layout()
        plt.show()

    def plot_goals_histogram(self) -> None:
        fig, ax = plt.subplots(figsize=(10, 5))
        ax.hist(self.global_standings_raw["Забито"], bins=10, color="darkorange", edgecolor="black", alpha=0.7)
        ax.set_title("Гистограмма распределения заброшенных шайб", fontsize=12)
        ax.set_xlabel("Заброшенные шайбы")
        ax.set_ylabel("Число команд")
        ax.grid(True, linestyle="--", alpha=0.5)
        plt.tight_layout()
        plt.show()
