"""Точка входа приложения. Парсинг CLI и запуск задач."""

import argparse
from sys import exit
import pandas as pd
from typing import Dict, Callable
from analyzer import KHLSeasonAnalyzer
from printers import BasePrinter, PlainPrinter, PrettyConsolePrinter


# Функция, которую вызываем при запуске скрипта
def main() -> None:
    """Точка входа."""
    # Инициализируем парсер аргументов командной строки
    parser = argparse.ArgumentParser(description="Аналитическая система КХЛ")
    
    # Обязательный первый аргумент — путь к CSV-файлу с матчами
    parser.add_argument("csv_file", type=str, help="Путь к файлу регулярного сезона")
    
    # Режим работы программы (по умолчанию — вывод таблиц)
    parser.add_argument(
        "--task",
        type=str,
        choices=["standings", "points_plot", "points_hist", "diff_plot", "goals_hist"],
        default="standings",
        help="Режим выполнения"
    )
    
    # Имя команды (нужно только для индивидуальных графиков)
    parser.add_argument("--team", type=str, default="", help="Целевая команда")
    # Флаг для красивого вывода таблиц в рамке
    parser.add_argument("--pretty", action="store_true", help="Красивый вывод таблиц")
    args = parser.parse_args()

    # Создаем экземпляр нашего аналитического класса
    analyzer = KHLSeasonAnalyzer(args.csv_file)

    # Выбираем способ печати таблиц в консоль на основании флага --pretty
    # Это паттерн "Стратегия": подменяем логику вывода без изменения основного кода
    printer_map: Dict[bool, BasePrinter] = {
        True: PrettyConsolePrinter(),
        False: PlainPrinter()
    }
    printer: BasePrinter = printer_map[args.pretty]

    # Валидация аргументов: если пользователь выбрал график по команде,
    # но саму команду не указал, прекращаем работу программы с сообщением об ошибке
    is_team_required: bool = pd.Series([args.task]).isin(["points_plot", "diff_plot"]).iloc[0]
    is_team_empty: bool = pd.Series([args.team]).isin(["", None]).iloc[0]
    (is_team_required and is_team_empty) and exit("Ошибка: Параметр --team обязателен для этого режима.")

    def run_standings() -> None:
        """Локальная функция для вывода общей таблицы и таблиц конференций."""
        # Печатаем общую таблицу регулярки
        printer.print_table(analyzer.get_champion_table(), "Итоговая таблица чемпионата")
        # Получаем и печатаем таблицы по конференциям
        conf_tables = analyzer.get_conference_tables()
        pd.Series(conf_tables).apply(
            lambda table: printer.print_table(table, "Таблица конференции")
        )

    # Словарь сопоставления строкового названия задачи и реального Python-метода (Диспетчеризация)
    dispatch_map: Dict[str, Callable[[], None]] = {
        "standings": run_standings,
        "points_plot": lambda: analyzer.plot_team_points(args.team),
        "points_hist": analyzer.plot_points_histogram,
        "diff_plot": lambda: analyzer.plot_team_goal_diff(args.team),
        "goals_hist": analyzer.plot_goals_histogram
    }

    # Достаем нужную функцию из словаря по ключу и вызываем ее
    dispatch_map[args.task]()


# Точка в ходу в программу, вызываем main
if __name__ == "__main__":
    main()