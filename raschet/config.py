# -*- coding: utf-8 -*-
"""Пути и общие настройки расчётного модуля МГРЭС.

Каталог исходников задаётся переменной окружения MGRES_SRC.
По умолчанию - папка «Загрузки» пользователя EcoVisio.
"""
import os
from pathlib import Path

# Папка с первичными документами. Нужна, только если вы хотите пересобрать
# таблицы в data/ с нуля. Для обычного прогона расчёта она не требуется.
SRC = Path(os.environ.get("MGRES_SRC", Path(__file__).resolve().parent / "istochniki"))
HERE = Path(__file__).resolve().parent
DATA = HERE / "data"
OUT = HERE
DATA.mkdir(exist_ok=True)

# ---- имена исходных файлов (ровно как на диске) ----
F = {
    "nbs_gaz":        SRC / "gas-data" / "ENE010400_20260809-013825.xlsx",
    "nbs_el":         SRC / "ENE010100_20260809-013935 (2).xlsx",
    "nbs_balans":     SRC / "ENE020300_20260809-014024.xlsx",
    "pink":           SRC / "CMO-Historical-Data-Monthly.xlsx",
    "bafa":           SRC / "egas_aufkommen_export_1999.xlsx",
    "fred_gas":       SRC / "PNGASEUUSDM.csv",
    "fred_brent":     SRC / "MCOILBRENTEU.csv",
    "fred_hoil":      SRC / "MHOILNYH.csv",
    "fred_dfuel":     SRC / "MDFUELNYH.csv",
    "ember":          SRC / "european_wholesale_electricity_price_data_monthly.csv",
    "ecb":            SRC / "data.csv",
    "bnm_usd":        SRC / "Evolution.csv",
    "bnm_eur":        SRC / "Evolution (1).csv",
    "cbpmr":          SRC / "cbpmr.csv",
    "pmr_dohody":     SRC / "Приложения к Закону" / "Приложения к Закону" / "Приложение № 1 (доходы РБ) (тек. ред. на 28.05.26г.).xlsx",
    "pmr_rashody":    SRC / "Приложения к Закону" / "Приложения к Закону" / "Приложение № 2 (расходы РБ) (тек. ред. на 06.06.26г.).xlsx",
}
COMTRADE_GLOB = "TradeData_*.csv"
MOLDELECTRICA_GLOB = "Archive_data_for_period_*.zip"

# Год, до которого ряды считаются полными (2026 - неполный)
LAST_FULL_YEAR = 2025
TODAY = "2026-08-11"
