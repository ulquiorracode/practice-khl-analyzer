"""Точка входа приложения. Парсинг CLI и запуск задач."""

import argparse
import sys
from typing import Dict, Callable
import pandas as pd
from analyzer import KHLSeasonAnalyzer
from printers import BasePrinter, PlainPrinter, PrettyConsolePrinter, HtmlPrinter


def main() -> None:
    """Точка входа."""
    # Реконфигурация кодировки вывода для кириллицы
    sys.stdout.reconfigure(encoding='utf-8')

    parser = argparse.ArgumentParser(description="Аналитическая система КХЛ")
    parser.add_argument(
        "csv_file",
        type=str,
        help="Путь к файлу регулярного сезона"
    )
    parser.add_argument(
        "--task",
        type=str,
        choices=["standings", "points_plot", "points_hist", "diff_plot", "goals_hist"],
        default="standings",
        help="Режим выполнения"
    )
    parser.add_argument(
        "--standings-mode",
        type=str,
        choices=["both", "championship", "conferences"],
        default="both",
        help="Режим вывода таблиц: both (чемпионат+конференции), championship (только общая), conferences (только конференции)"
    )
    parser.add_argument("--team", type=str, default="", help="Целевая команда")
    parser.add_argument(
        "--format",
        type=str,
        choices=["text", "pretty", "html"],
        default="text",
        help="Формат вывода таблиц"
    )
    # Добавляем новый аргумент для вывода напрямую в файл
    parser.add_argument(
        "--output",
        type=str,
        default="",
        help="Путь к файлу для сохранения вывода (позволяет избежать проблем с кодировкой консоли)"
    )
    args = parser.parse_args()

    analyzer = KHLSeasonAnalyzer(args.csv_file)

    # Диспетчеризация выбора принтера
    printer_map: Dict[str, BasePrinter] = {
        "text": PlainPrinter(),
        "pretty": PrettyConsolePrinter(),
        "html": HtmlPrinter()
    }
    printer: BasePrinter = printer_map[args.format]

    # Валидация аргументов
    is_team_required: bool = pd.Series([args.task]).isin(["points_plot", "diff_plot"]).iloc[0]
    is_team_empty: bool = pd.Series([args.team]).isin(["", None]).iloc[0]

    (is_team_required and is_team_empty) and sys.exit("Ошибка: Параметр --team обязателен для этого режима.")

    # Выбираем поток вывода
    stream_resolver: Dict[bool, Callable[[], any]] = {
        True: lambda: open(args.output, "w", encoding="utf-8"),
        False: lambda: sys.stdout
    }
    output_stream = stream_resolver[bool(args.output)]()

    def run_standings() -> None:
        """Запуск построения турнирной таблицы с диспетчеризацией режимов вывода."""
        
        # Функция вывода общей таблицы чемпионата
        def print_championship() -> None:
            printer.print_table(analyzer.get_champion_table(), "Итоговая таблица чемпионата", output_stream)

        # Функция вывода таблиц конференций
        def print_conferences() -> None:
            conf_tables = analyzer.get_conference_tables()
            pd.Series(list(conf_tables.keys())).apply(
                lambda name: printer.print_table(
                    conf_tables[name], 
                    f"Регулярный чемпионат. Конференция «{name}»", 
                    output_stream
                )
            )

        # Функциональный диспетчер режимов (вместо конструкции if/else)
        mode_dispatcher: Dict[str, Callable[[], None]] = {
            "championship": print_championship,
            "conferences": print_conferences,
            "both": lambda: (print_championship(), print_conferences())
        }

        # Вызываем функцию, соответствующую переданному значению standings-mode
        mode_dispatcher.get(args.standings_mode, lambda: None)()
        
        # Закрываем поток, если это файл (sys.stdout закрывать нельзя)
        is_file: bool = output_stream != sys.stdout
        is_file and output_stream.close()

    # Диспетчеризация задач
    dispatch_map: Dict[str, Callable[[], None]] = {
        "standings": run_standings,
        "points_plot": lambda: analyzer.plot_team_points(args.team),
        "points_hist": analyzer.plot_points_histogram,
        "diff_plot": lambda: analyzer.plot_team_goal_diff(args.team),
        "goals_hist": analyzer.plot_goals_histogram
    }

    dispatch_map[args.task]()


# Точка входа, если запускаем этот файл
if __name__ == "__main__":
    main()
