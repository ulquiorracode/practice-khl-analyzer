"""Точка входа приложения. Парсинг CLI и запуск задач."""

import argparse
import sys

import pandas as pd

from typing import Dict, Callable
from analyzer import KHLSeasonAnalyzer
from printers import BasePrinter, PlainPrinter, PrettyConsolePrinter


def main() -> None:
    """Точка входа."""
    parser = argparse.ArgumentParser(description="Аналитическая система КХЛ")
    parser.add_argument("csv_file", type=str, help="Путь к файлу регулярного сезона")
    parser.add_argument(
        "--task",
        type=str,
        choices=["standings", "points_plot", "points_hist", "diff_plot", "goals_hist"],
        default="standings",
        help="Режим выполнения"
    )
    parser.add_argument("--team", type=str, default="", help="Целевая команда")
    parser.add_argument("--pretty", action="store_true", help="Красивый вывод таблиц")
    args = parser.parse_args()

    analyzer = KHLSeasonAnalyzer(args.csv_file)

    # Диспетчеризация выбора принтера
    printer_map: Dict[bool, BasePrinter] = {
        True: PrettyConsolePrinter(),
        False: PlainPrinter()
    }
    printer: BasePrinter = printer_map[args.pretty]

    # Валидация аргументов
    is_team_required: bool = pd.Series([args.task]).isin(["points_plot", "diff_plot"]).iloc[0]
    is_team_empty: bool = pd.Series([args.team]).isin(["", None]).iloc[0]
    (is_team_required and is_team_empty) and sys.exit("Ошибка: Параметр --team обязателен для этого режима.")

    def run_standings() -> None:
        printer.print_table(analyzer.get_champion_table(), "Итоговая таблица чемпионата")
        conf_tables = analyzer.get_conference_tables()
        pd.Series(conf_tables).apply(
            lambda table: printer.print_table(table, "Таблица конференции")
        )

    # Диспетчеризация задач
    dispatch_map: Dict[str, Callable[[], None]] = {
        "standings": run_standings,
        "points_plot": lambda: analyzer.plot_team_points(args.team),
        "points_hist": analyzer.plot_points_histogram,
        "diff_plot": lambda: analyzer.plot_team_goal_diff(args.team),
        "goals_hist": analyzer.plot_goals_histogram
    }

    dispatch_map[args.task]()


if __name__ == "__main__":
    main()
