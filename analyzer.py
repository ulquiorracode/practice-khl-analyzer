"""Аналитический движок расчета очков КХЛ."""

from typing import Dict, List, Tuple
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from config import CONFERENCES, DIVISIONS
from models import MatchSchema, StandingsTable

# И   - Количество проведенных матчей
# В   - Выигрыши в основное время (начисляется 3 очка)
# ВО  - Выигрыши в овертайме (начисляется 2 очка)
# ВБ  - Выигрыши в серии послематчевых буллитов (начисляется 2 очка)
# ПБ  - Поражения в серии послематчевых буллитов (начисляется 1 очко)
# ПО  - Поражения в овертайме (начисляется 1 очко)
# П   - Поражения в основное время (очки не начисляются, 0 очков)
# Ш   - Разница заброшенных и пропущенных шайб (в формате "Забито-Пропущено")
# О   - Общее количество набранных очков

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
        
        # Преобразуем матчи в плоскую таблицу: одна строка - одна игра одной команды
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
        # mask для условной замены на основе предиката
        cleaned: pd.Series = filled.mask(filled.eq(":"), "0:0")
        # Разделяем строку по символу ":" на две отдельные колонки (голы хозяев и гостей)
        split_scores: pd.DataFrame = cleaned.str.split(":", expand=True)
        
        # Преобразуем строки в целые числа. Ошибки парсинга заменяем на 0
        # принудительно подавляем исключение ValueError, заменяя некорректные значения на NaN
        home_goals: pd.Series = pd.to_numeric(split_scores[0], errors="coerce").fillna(0).astype(int)
        away_goals: pd.Series = pd.to_numeric(split_scores[1], errors="coerce").fillna(0).astype(int)
        
        return home_goals, away_goals


    def _process_match_outcomes(self) -> pd.DataFrame:
        """
        Рассчитывает исходы каждого матча для обеих команд.
        Превращает "матч между А и Б" в две записи: "команда А сыграла матч" и "команда Б сыграла матч".
        """
        # Извлекаем голы по периодам, овертаймам и буллитам
        # Распаковываем счет матчей по периодам, овертаймам и буллитам
        period1_home,   period1_away    = self._parse_score(self.matches_df[MatchSchema.PERIOD_1])  # Голы хозяев и гостей в 1-м периоде
        period2_home,   period2_away    = self._parse_score(self.matches_df[MatchSchema.PERIOD_2])  # Голы хозяев и гостей во 2-м периоде
        period3_home,   period3_away    = self._parse_score(self.matches_df[MatchSchema.PERIOD_3])  # Голы хозяев и гостей в 3-м периоде
        overtime_home,  overtime_away   = self._parse_score(self.matches_df[MatchSchema.OVERTIME])  # Голы хозяев и гостей в овертайме
        shootouts_home, shootouts_away  = self._parse_score(self.matches_df[MatchSchema.BULLETS])   # Победные буллиты хозяев и гостей

        # Считаем голы в основное время (первые 3 периода)
        reg_home: pd.Series = period1_home + period2_home + period3_home                            # Общие голы хозяев в основное время
        reg_away: pd.Series = period1_away + period2_away + period3_away                            # Общие голы гостей в основное время
        
        # Считаем голы с учетом овертайма
        total_home: pd.Series = reg_home + overtime_home                                            # Голы хозяев за основное время и овертайм
        total_away: pd.Series = reg_away + overtime_away                                            # Голы гостей за основное время и овертайм

        # Определяем логические маски (True/False) для исходов в основное время
        reg_home_win: pd.Series = reg_home.gt(reg_away)                                             # Маска: победа хозяев в основное время
        reg_away_win: pd.Series = reg_home.lt(reg_away)                                             # Маска: победа гостей в основное время
        reg_tie:      pd.Series = reg_home.eq(reg_away)                                             # Маска: ничья в основное время

        # Определяем исходы в овертайме
        overtime_home_win: pd.Series = reg_tie & overtime_home.gt(overtime_away)                    # Маска: победа хозяев в овертайме
        overtime_away_win: pd.Series = reg_tie & overtime_home.lt(overtime_away)                    # Маска: победа гостей в овертайме
        overtime_tie:      pd.Series = reg_tie & overtime_home.eq(overtime_away)                    # Маска: ничья по итогам овертайма

        # Определяем исходы в серии буллитов
        shootouts_home_win: pd.Series = overtime_tie & shootouts_home.gt(shootouts_away)            # Маска: победа хозяев в серии буллитов
        shootouts_away_win: pd.Series = overtime_tie & shootouts_home.lt(shootouts_away)            # Маска: победа гостей в серии буллитов

        # Определяем буквенный код исхода для хозяев поля (по умолчанию "П" - поражение)
        # И последовательно заменяем (маскируем) значение в зависимости от условий
        # Порядок маскирования важен: проверка на победу в овертайме (ВО) должна идти раньше, чем на победу в буллитах (ВБ),
        # так как условие для shootouts_home_win (ПБ) = overtime_tie & shootouts_home.lt(shootouts_away ) проверяет победу в буллитах (соответственно, shootouts_away_win - поражение)
        # то есть сначала проверяем победу в овертайме (ВО), потом в буллитах (ВБ)
        # и если мы проиграли в буллитах (ПБ), то мы уже не можем выиграть в овертайме (ВО), поэтому ПБ идет раньше
        home_code: pd.Series = pd.Series("П", index=self.matches_df.index)
        home_code = home_code.mask(reg_home_win, "В").mask(overtime_home_win, "ВО").mask(shootouts_home_win, "ВБ")
        home_code = home_code.mask(shootouts_away_win, "ПБ").mask(overtime_away_win, "ПО")

        # Аналогично определяем буквенный код исхода для гостей
        away_code: pd.Series = pd.Series("П", index=self.matches_df.index)
        away_code = away_code.mask(reg_away_win, "В").mask(overtime_away_win, "ВО").mask(shootouts_away_win, "ВБ")
        away_code = away_code.mask(shootouts_home_win, "ПБ").mask(overtime_home_win, "ПО")

        # Переводим буквенные коды в очки с помощью словаря POINTS_MAP
        home_pts: pd.Series = home_code.map(POINTS_MAP).astype(int)
        away_pts: pd.Series = away_code.map(POINTS_MAP).astype(int)

        # Полное количество шайб (в КХЛ победный буллит идет в общий зачет как +1 гол)
        home_goals: pd.Series = total_home + shootouts_home_win.astype(int)
        away_goals: pd.Series = total_away + shootouts_away_win.astype(int)

        # Создаем плоские датафреймы для хозяев и для гостей
        home_df: pd.DataFrame = pd.DataFrame({
            "Дата":         self.matches_df[MatchSchema.DATE],
            "Команда":      self.matches_df[MatchSchema.TEAM_1],
            "Забито":       home_goals,
            "Пропущено":    away_goals,
            "Очки_матч":    home_pts,
            "Исход":        home_code
        })
        away_df: pd.DataFrame = pd.DataFrame({
            "Дата":         self.matches_df[MatchSchema.DATE],
            "Команда":      self.matches_df[MatchSchema.TEAM_2],
            "Забито":       away_goals,
            "Пропущено":    home_goals,
            "Очки_матч":    away_pts,
            "Исход":        away_code
        })

        # Объединяем их по вертикали (строка под строкой) в один большой реестр сыгранных матчей
        # Забываем старые индексы и создаем новую непрерывную нумерацию
        return pd.concat([home_df, away_df], ignore_index=True)


    def _build_global_standings(self) -> pd.DataFrame:
        """
        Строит итоговую сводную таблицу чемпионата на основе реестра матчей.
        """
        # С помощью сводной таблицы (pivot_table) подсчитываем количество каждого исхода ("В", "ВО" и т.д.) для команд.
        # index="Команда" группирует по клубам, columns="Исход" создает столбцы для каждого типа исхода.
        outcomes_pivot: pd.DataFrame = self.team_games_df.pivot_table(
            index="Команда",
            columns="Исход",
            values="Очки_матч",
            aggfunc="count",
            fill_value=0
        ).reindex(columns=["В", "ВО", "ВБ", "ПБ", "ПО", "П"], fill_value=0).astype(int)

        # Группируем игры по командам и суммируем забитые/пропущенные шайбы, а также набранные очки
        # используем синтаксис именованной агрегации
        # Имя_Новой_Колонки=("Исходная_Колонка","Функция_Агрегации")
        # иначе бы пришлось сначала аггрегировать по существующим колонкам, 
        # а потом переименовывать их через .rename(columns={"Очки_матч": "О"})
        aggregations: pd.DataFrame = self.team_games_df.groupby("Команда").agg(
            Забито=("Забито", "sum"),
            Пропущено=("Пропущено", "sum"),
            О=("Очки_матч", "sum")
        )

        # Объединяем сводную таблицу исходов и таблицу суммарных показателей по индексу (названию клуба)
        # concat чаще всего используется для склеивания таблиц по вертикали (строка под строкой) или по горизонтали (столбец к столбцу).
        # join используется для слияния (объединения) таблиц по их индексам (или ключевым колонкам), когда нужно сопоставить строки по смыслу.
        standings: pd.DataFrame = outcomes_pivot.join(aggregations)
        
        # Считаем количество проведенных игр ("И") как сумму всех возможных исходов
        standings["И"]          = standings[["В", "ВО", "ВБ", "ПБ", "ПО", "П"]].sum(axis=1)
        # Считаем разницу шайб
        standings["Разница"]    = standings["Забито"] - standings["Пропущено"]
        # Формируем строковое представление забитых и пропущенных шайб (например, "150-120")
        standings["Ш"] = standings["Забито"].astype(str) + "-" + standings["Пропущено"].astype(str)
        
        # Сбрасываем индекс, превращая "Клуб" из индекса в обычную колонку
        standings = standings.rename_axis("Клуб").reset_index()
        # Сортируем таблицу согласно регламенту КХЛ (Очки -> Победы -> Разница -> Забито)
        standings = standings.sort_values(by=SORT_COLUMNS, ascending=SORT_ASCENDING)
        # Проставляем места командам от 1 до N
        standings["Sub_Место"] = np.arange(1, len(standings) + 1) # Временное поле
        standings["Место"] = standings["Sub_Место"]

        # Метод df.drop() в Pandas используется для удаления строк или столбцов из DataFrame.
        standings = standings.drop(columns=["Sub_Место"])
        
        return standings


    def get_champion_table(self) -> StandingsTable:
        """Возвращает общую таблицу регулярного чемпионата."""
        return StandingsTable(self.global_standings_raw)


    def get_conference_tables(self) -> pd.Series:
        """
        Формирует таблицы конференций с учетом лидерства в дивизионах.
        По регламенту КХЛ лидеры дивизионов автоматически занимают первые 2 места в конференции.
        """
        # Получаем структуру конференций и дивизионов для конкретного сезона из config.py
        conf_dict: Dict[str, List[str]] = CONFERENCES.get(self.season_key, {})
        div_dict: Dict[str, List[List[str]]] = DIVISIONS.get(self.season_key, {})

        # Строим соответствие "Клуб -> Конференция" с помощью Pandas
        conf_mapping: pd.Series = pd.DataFrame({
            "Конференция": [*conf_dict.keys()],
            "Клуб": [*conf_dict.values()]
        }).explode("Клуб").set_index("Клуб")["Конференция"]
        
        mapped_standings: pd.DataFrame = self.global_standings_raw.copy()
        # Прикрепляем к каждой команде её конференцию
        mapped_standings["Конференция"] = mapped_standings["Клуб"].map(conf_mapping)

        # То же самое делаем для дивизионов (если они описаны для этого сезона в конфиге)
        div_list_west: List[List[str]] = div_dict.get("Запад", [])
        div_list_east: List[List[str]] = div_dict.get("Восток", [])

        # Разносим клубы по числовым номерам дивизионов (0, 1 для Запада; 2, 3 для Востока)
        # Использование списков идентификаторов [0, 1] для Западной конференции
        # и [2, 3] для Восточной конференции обусловлено необходимостью присвоить
        # каждому из четырех дивизионов уникальный числовой идентификатор в рамках всей лиги.

        # Строим соответствие "Клуб -> Дивизион" чисто средствами Pandas
        # Поворачивает таблицу так, что названия столбцов становятся значениями в одной новой колонке ("Клуб"),
        # а данные внутри столбцов переносятся в другую колонку (value).
        df_melted: pd.DataFrame = pd.DataFrame(div_dict).melt(value_name="Клуб", ignore_index=False)
        
        # Вычисляем ID дивизиона: для Запада это индекс (0 или 1), для Востока — индекс + 2
        df_melted["Дивизион"] = df_melted["variable"].map({"Запад": 0, "Восток": 2}) + df_melted.index
        
        # Разворачиваем списки клубов в отдельные строки и формируем Series-маппинг
        div_mapping: pd.Series = df_melted.explode("Клуб").set_index("Клуб")["Дивизион"]

        # Записываем дивизион в общую таблицу, отсутствующим ставим -1
        mapped_standings["Дивизион"] = mapped_standings["Клуб"].map(div_mapping).fillna(-1)

        # Находим лидеров дивизионов (группируем по дивизиону и берем строку с максимальными очками "О")
        # .indxmax() - ищем индекс первого элемента с максимальным значением
        division_leaders_idx: pd.Series = mapped_standings.groupby("Дивизион")["О"].idxmax()
        # Игнорируем тех, у кого дивизион не определен (-1)
        # через .drop() удаляем все строки с лейюелами равными -1
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
        return pd.Series([*conf_dict.keys()], index=conf_dict.keys()).apply(process_sub_conf)


    # Индивидуальное задание №1
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


    # Индивидуальное задание №2
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


    # Индивидуальное задание №3
    def plot_team_goal_diff(self, team_name: str) -> None:
        """Строит кумулятивный график разницы забитых/пропущенных шайб команды."""
        # Выбираем матчи конкретной команды
        # copy нужен, чтобы избежать ошибки "chained assignment" при добавлении новых столбцов или предупреждения
        # SettingWithCopyWarning: A value is trying to be set on a copy of a slice from a DataFrame.
        # Явный вызов .copy() в самом конце цепочки:
        #   Полностью разрывает связь с исходным DataFrame self.team_games_df.
        #   Гарантирует, что в памяти создан абсолютно независимый объект.
        #   Полностью исключает появление предупреждения SettingWithCopyWarning при последующем добавлении новых колонок.

        # Пользуемся булевой индексацией (Boolean Indexing) или фильтрацией по маске
        # Pandas берет столбец "Команда" и сравнивает ячейку в каждой строке со значением переменной team_name.
        # В результате получается одномерный массив (Series), состоящий исключительно из булевых значений True и False
        team_data: pd.DataFrame = self.team_games_df[self.team_games_df["Команда"] == team_name].sort_values("Дата").copy()
        # Считаем разницу шайб в отдельно взятом матче
        team_data["Разница_матча"] = team_data["Забито"] - team_data["Пропущено"]
        # Считаем разницу нарастающим итогом
        team_data["Разница_кум"] = team_data["Разница_матча"].cumsum()

        # Функция plt.subplots() создает сетку из нескольких графиков внутри одной фигуры.
        # Она возвращает сразу два объекта:
        # саму фигуру (fig) и массив осей (ax или axes),
        # через которые идет управление каждым отдельным графиком.
        fig, ax = plt.subplots(figsize=(10, 5))
        # Строим линию разницы шайб (с квадратными маркерами)
        ax.plot(team_data["Дата"], team_data["Разница_кум"], marker="s", color="crimson", linewidth=2)
        # Команда ax.axhline(0, color="black", linestyle="-.", linewidth=1) рисует постоянную горизонтальную линию через весь график на уровне y = 0.
        # Буквы ax в начале названия означают Axis (ось), а hline — Horizontal Line.
        # Разбор параметров:0 — координата по оси Y, где пройдет линия.color="black" — черный цвет линии (можно сократить до color="k").
        # linestyle="-." — штрих-пунктирный стиль линии.linewidth=1 — толщина линии (можно сократить до lw=1).
        ax.axhline(0, color="black", linestyle="-.", linewidth=1)
        
        ax.set_title(f"Разница забитых и пропущенных шайб команды «{team_name}»", fontsize=12)
        ax.set_xlabel("Дата")
        ax.set_ylabel("Суммарная разница шайб")

        # Строка кода ax.grid(True, linestyle="--", alpha=0.5)
        # включает координатную сетку на графике и делает её визуально аккуратной.
        # True — активирует отображение сетки (можно опустить, если передаются другие параметры: ax.grid(linestyle="--") тоже включит сетку).
        # linestyle="--" — делает линии сетки пунктирными (штриховыми).
        # Также можно использовать ":" (точечная) или "-." (штрих-пунктирная).
        # alpha=0.5 — задает прозрачность линий в диапазоне от 0 (полностью прозрачная) до 1 (полностью непрозрачная).
        # Значение 0.5 делает сетку полупрозрачной, чтобы она не отвлекала внимание от самих данных.
        ax.grid(True, linestyle="--", alpha=0.5)
        # Метод fig.autofmt_xdate() автоматически форматирует и
        # поворачивает даты на оси X, чтобы они не перекрывали друг друга.
        fig.autofmt_xdate()
        # Функция tight_layout регулирует внутренние отступы
        # Это нужно чтобы графики не накладывались друг на друга
        plt.tight_layout()
        # Функция show() отображает график
        plt.show()

    
    # Индивидуальное задание №4
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
