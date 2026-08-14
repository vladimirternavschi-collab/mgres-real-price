# -*- coding: utf-8 -*-
"""Расчётные функции.

Каждая функция возвращает список записей для реестра фактов:
    dict(показатель, значение, единица, период, источник_файл, точное_место,
         формула, статус)

Статусы: из_источника | вычислено | допущение | требует_проверки
"""
import csv
import math
from collections import defaultdict
from datetime import datetime

import pandas as pd

import convert as C
from config import DATA, LAST_FULL_YEAR, TODAY

# ------------------------------------------------------------------ загрузка
_cache = {}


def load(name):
    if name not in _cache:
        _cache[name] = pd.read_csv(DATA / name, encoding="utf-8-sig")
    return _cache[name].copy()


def _year(df):
    df = df.copy()
    df["год"] = df["дата"].str[:4].astype(int)
    return df


def fact(pok, val, unit, period, src, place, formula="", status="вычислено"):
    return dict(показатель=pok, значение=val, единица=unit, период=period,
                источник_файл=src, точное_место=place, формула=formula,
                статус=status, дата_расчёта=TODAY)


# =============================================================== НБС агрегаты
def nbs_el_god():
    d = _year(load("nbs_el_mes.csv"))
    return d.pivot_table(index="год", columns="показатель", values="значение", aggfunc="sum")


def nbs_gaz_god():
    d = _year(load("nbs_gaz_mes.csv"))
    return d.pivot_table(index="год", columns="показатель", values="значение", aggfunc="sum")


# =============================================================== 1. доля МГРЭС
def dolya_mgres(god=None):
    """Доля МГРЭС в потреблении Молдовы (правый берег), 2015-2026."""
    p = nbs_el_god()
    out = []
    years = [god] if god else list(p.index)
    for y in years:
        mg = p.loc[y, "Procurat din alte surse"]
        cons = p.loc[y, "Consum final brut"]
        note = "" if y <= LAST_FULL_YEAR else " (неполный год)"
        out.append(fact(
            f"Доля МГРЭС в валовом конечном потреблении э/э, {y}",
            round(mg / cons * 100, 1), "%", str(y),
            "ENE010100_20260809-013935 (2).xlsx",
            "лист ENE010100, строки 'Procurat din alte surse' и 'Consum final brut'",
            f"{mg:.0f} / {cons:.0f} * 100{note}"))
        out.append(fact(
            f"Поставки МГРЭС (Procurat din alte surse), {y}",
            round(mg / 1000, 1), "ГВт·ч", str(y),
            "ENE010100_20260809-013935 (2).xlsx",
            "лист ENE010100, строка 'Procurat din alte surse', сумма 12 месяцев",
            "сумма помесячных значений", "из_источника"))
        out.append(fact(
            f"Валовое конечное потребление э/э, {y}",
            round(cons / 1000, 1), "ГВт·ч", str(y),
            "ENE010100_20260809-013935 (2).xlsx",
            "лист ENE010100, строка 'Consum final brut', сумма 12 месяцев",
            "сумма помесячных значений", "из_источника"))
    return out


# ====================================================== 2. цена газа: сравнение
def _comtrade_god():
    d = _year(load("comtrade_gaz.csv"))
    d = d[d["ряд"].str.contains("годовой") & d["показатель"].str.startswith("World")]
    p = d.pivot_table(index="год", columns="показатель", values="значение", aggfunc="first")
    flags = d.groupby("год")["флаг"].apply(lambda s: "; ".join(sorted({x for x in s.dropna() if x})))
    res = pd.DataFrame(index=p.index)
    res["стоимость_USD"] = p.get("World | стоимость CIF")
    res["количество_кг"] = p.get("World | количество")
    res["объём_тыс_м3"] = res["количество_кг"] / C.k("плотность_газа_кг_м3") / 1000.0
    res["цена_USD_1000м3"] = res["стоимость_USD"] / res["объём_тыс_м3"] * 1000.0 / 1000.0
    res["цена_USD_1000м3"] = res["стоимость_USD"] / (res["объём_тыс_м3"] / 1000.0) / 1000.0
    # проще и без путаницы: $/1000 м³ = стоимость / (объём м³) * 1000
    obem_m3 = res["количество_кг"] / C.k("плотность_газа_кг_м3")
    res["цена_USD_1000м3"] = res["стоимость_USD"] / obem_m3 * 1000.0
    res["объём_млн_м3"] = obem_m3 / 1e6
    res["флаг"] = flags
    return res


def _pink_gaz_god():
    d = _year(load("worldbank_pink.csv"))
    d = d[d["показатель"] == "Natural gas, Europe"]
    s = d.groupby("год")["значение"].mean()
    return s.apply(C.usd_per_mmbtu_to_usd_per_1000m3)


def cena_gaza_sravnenie():
    ct = _comtrade_god()
    pk = _pink_gaz_god()
    out, kum = [], 0.0
    rows = []
    for y in sorted(ct.index):
        if pd.isna(ct.loc[y, "цена_USD_1000м3"]) or y not in pk.index:
            continue
        mine = ct.loc[y, "цена_USD_1000м3"]
        euro = pk.loc[y]
        vol = ct.loc[y, "объём_млн_м3"]
        diff_unit = euro - mine
        diff_total = diff_unit * vol * 1000.0 / 1e6   # млн $  (vol млн м³ -> тыс. м³)
        flg = ct.loc[y, "флаг"] if isinstance(ct.loc[y, "флаг"], str) else ""
        status = "требует_проверки" if flg else "вычислено"
        rows.append((y, mine, euro, diff_unit, vol, diff_total, flg))
        if not flg:
            kum += diff_total
        out.append(fact(
            f"Цена импорта газа Молдовой (Comtrade), {y}", round(mine, 1),
            "USD/1000 м³", str(y), "TradeData_*.csv",
            "код 271121, репортёр Молдова, партнёр World, годовые строки",
            "стоимость CIF / (количество кг / 0,717) * 1000", status))
        out.append(fact(
            f"Европейский индекс цены газа (World Bank), {y}", round(euro, 1),
            "USD/1000 м³", str(y), "CMO-Historical-Data-Monthly.xlsx",
            "лист 'Monthly Prices', ряд 'Natural gas, Europe', среднее по 12 месяцам",
            "среднегодовое $/mmbtu * 38,5*1000 / 1055,056"))
        out.append(fact(
            f"Разница цены газа для Молдовы против европейского индекса, {y}",
            round(diff_unit / euro * 100, 1), "%", str(y),
            "TradeData_*.csv + CMO-Historical-Data-Monthly.xlsx", "-",
            f"({euro:.1f} - {mine:.1f}) / {euro:.1f} * 100", status))
        out.append(fact(
            f"Экономия/переплата Молдовы на цене газа, {y}", round(diff_total, 1),
            "млн USD", str(y), "TradeData_*.csv + CMO-Historical-Data-Monthly.xlsx", "-",
            f"({euro:.1f} - {mine:.1f}) $/1000 м³ * {vol:.1f} млн м³", status))
    # экономия только за годы, когда цена была НИЖЕ индекса (по 2022 включительно)
    kum_skidka = sum(r[5] for r in rows if not r[6] and r[5] > 0)
    kum_pereplata = sum(r[5] for r in rows if not r[6] and r[5] < 0)
    gody_skidki = [r[0] for r in rows if not r[6] and r[5] > 0]
    gody_pereplaty = [r[0] for r in rows if not r[6] and r[5] < 0]
    out.append(fact(
        "Экономия Молдовы на цене газа за годы скидки (нетто-положительные годы)",
        round(kum_skidka, 1), "млн USD",
        f"{min(gody_skidki)}-{max(gody_skidki)}, {len(gody_skidki)} лет с данными",
        "TradeData_*.csv + CMO-Historical-Data-Monthly.xlsx", "-",
        "сумма годовых разниц только за годы, где цена для Молдовы ниже индекса; "
        "2016 исключён (битые количества в Comtrade)"))
    out.append(fact(
        "Переплата Молдовы против европейского индекса после разрыва",
        round(kum_pereplata, 1), "млн USD",
        f"{min(gody_pereplaty)}-{max(gody_pereplaty)}",
        "TradeData_*.csv + CMO-Historical-Data-Monthly.xlsx", "-",
        "сумма годовых разниц за годы, где цена для Молдовы выше индекса"))
    out.append(fact(
        "Кумулятивная экономия Молдовы на цене газа, НЕТТО по всем годам с данными",
        round(kum, 1), "млн USD", "годы с данными Comtrade",
        "TradeData_*.csv + CMO-Historical-Data-Monthly.xlsx", "-",
        "сумма годовых разниц; 2016 исключён (битые количества в Comtrade)"))
    return out, rows, kum, kum_skidka, kum_pereplata


# ============================================ 3. газ, ушедший в электроэнергию
def gaz_na_elektro(god=None, udel=None):
    u = udel if udel is not None else C.k("удельный_расход_м3_кВтч")
    p = nbs_el_god()
    out = []
    years = [god] if god else [y for y in p.index if y <= LAST_FULL_YEAR]
    for y in years:
        mwh = p.loc[y, "Procurat din alte surse"]
        m3 = mwh * 1000.0 * u          # МВт·ч -> кВт·ч -> м³
        out.append(fact(
            f"Газ, сожжённый для электроэнергии правому берегу, {y}",
            round(m3 / 1e6, 1), "млн м³", str(y),
            "ENE010100 + допущение удельного расхода",
            "лист ENE010100, 'Procurat din alte surse'",
            f"{mwh:.0f} МВт·ч * 1000 * {u} м³/кВт·ч", "допущение"))
    return out


# ================================================= 4. цена э/э от МГРЭС по годам
def _cena_mgres_god():
    """Цена, по которой Молдова платила за электроэнергию МГРЭС, $/кВт·ч.

    2022 - средневзвешенная по договорам (документ).
    Прочие годы - средняя цена закупки э/э лицензиатами по ANRE, переведённая
    в доллары по среднегодовому курсу НБМ. Это ПРОКСИ: в среднюю входят импорт
    и местная генерация. МГРЭС в 2020-2024 - 55-75% закупок, поэтому средняя
    близка к контрактной, но не равна ей.
    """
    res = {}
    # 2022 - по договорам
    k = load("kontrakty_mgres.csv")
    k = k[k["ряд"] == "Контракты Energocom-МГРЭС 2022"]
    sums, vols = 0.0, 0.0
    for cid in ["D1", "D2b", "D4b", "D5a", "D6a", "D6b", "D7"]:
        pr = k[k["показатель"].str.startswith(cid + " ") & k["показатель"].str.endswith("цена")]
        vo = k[k["показатель"].str.startswith(cid + " ") & k["показатель"].str.endswith("объём")]
        su = k[k["показатель"].str.startswith(cid + " ") & k["показатель"].str.endswith("сумма")]
        if len(pr) and len(vo):
            sums += float(vo["значение"].iloc[0]) * 1000 * float(pr["значение"].iloc[0])
            vols += float(vo["значение"].iloc[0]) * 1000
        elif len(pr) and len(su):
            sums += float(su["значение"].iloc[0])
            vols += float(su["значение"].iloc[0]) / float(pr["значение"].iloc[0])
    res[2022] = (sums / vols, "договоры Energocom-МГРЭС 2022, средневзвешенная",
                 "из_источника")
    # прочие годы - прокси ANRE
    a = load("anre_otchety.csv")
    a = a[a["показатель"] == "Средняя цена закупки э/э лицензиатами"]
    for _, r in a.iterrows():
        y = int(r["дата"][:4])
        if y in res:
            continue
        bani = float(r["значение"])
        res[y] = (bani / 100.0 / C.rate_avg_year("MDL/USD", y),
                  "ANRE, средняя цена закупки э/э лицензиатами (прокси)",
                  "требует_проверки")
    # 2010 - контрактная цена CERS Moldovenească из отчёта ANRE 2010
    res[2010] = (0.0583, "отчёт ANRE 2010, контрактная цена CERS Moldovenească", "из_источника")
    return res


# ===================================================== 5. реальная цена кВт·ч
GAZ_LEVYY_BEREG_DOPUSHCHENIE = 2000.0   # млн м³ в год до 2025


def realnaya_cena(god, rezhim="узкий", udel=None, cena_ee=None):
    """Реальная стоимость кВт·ч электроэнергии МГРЭС для Молдовы.

    узкий:  (деньги за э/э + долг за газ, ушедший НА ЭТУ электроэнергию) / объём
    полный: (деньги за э/э + долг за ВЕСЬ газ левого берега) / объём

    Долг начисляется по контрактной цене Газпрома для Молдовы того же года
    (Comtrade: стоимость / количество).
    """
    u = udel if udel is not None else C.k("удельный_расход_м3_кВтч")
    p = nbs_el_god()
    if god not in p.index:
        return None
    mwh = float(p.loc[god, "Procurat din alte surse"])
    if mwh <= 0:
        return None
    kwh = mwh * 1000.0
    if cena_ee is not None:
        price_el, price_src, price_status = (
            cena_ee, "задана вручную (сценарий)", "допущение")
    else:
        ceny = _cena_mgres_god()
        if god not in ceny:
            return None
        price_el, price_src, price_status = ceny[god]
    dengi = kwh * price_el

    ct = _comtrade_god()
    if god not in ct.index or pd.isna(ct.loc[god, "цена_USD_1000м3"]):
        return None
    fl = ct.loc[god, "флаг"]
    if isinstance(fl, str) and fl:
        return None   # год с битыми количествами в Comtrade - цена газа недостоверна
    gas_price = float(ct.loc[god, "цена_USD_1000м3"])

    if rezhim == "узкий":
        gas_m3 = kwh * u
        gas_src = f"{mwh:.0f} МВт·ч * 1000 * {u} м³/кВт·ч"
        gas_status = "допущение"
    else:
        gas_m3 = (GAZ_LEVYY_BEREG_DOPUSHCHENIE if god < 2025 else 689.2) * 1e6
        gas_src = ("допущение 2 000 млн м³/год" if god < 2025
                   else "ANRE 2025: 689,2 млн м³ (февраль-декабрь)")
        gas_status = "допущение" if god < 2025 else "из_источника"
    dolg = gas_m3 / 1000.0 * gas_price
    itog = (dengi + dolg) / kwh
    return dict(год=god, режим=rezhim, объём_ГВтч=mwh / 1000.0,
                цена_ээ=price_el, цена_ээ_источник=price_src,
                цена_ээ_статус=price_status,
                деньги_млн=dengi / 1e6, газ_млн_м3=gas_m3 / 1e6,
                цена_газа=gas_price, долг_млн=dolg / 1e6,
                итог_USD_кВтч=itog, газ_формула=gas_src, газ_статус=gas_status)


def realnaya_cena_tablica(udel=None, cena_ee=None):
    out, rows = [], []
    p = nbs_el_god()
    for y in sorted(p.index):
        if y > LAST_FULL_YEAR:
            continue
        for rez in ("узкий", "полный"):
            r = realnaya_cena(y, rez, udel, cena_ee)
            if not r:
                continue
            rows.append(r)
            out.append(fact(
                f"Реальная цена кВт·ч от МГРЭС, {rez} счёт, {y}",
                round(r["итог_USD_кВтч"], 4), "USD/кВт·ч", str(y),
                "ENE010100 + TradeData_*.csv + договоры/ANRE", "-",
                f"({r['деньги_млн']:.1f} млн $ деньгами + {r['долг_млн']:.1f} млн $ долгом) "
                f"/ {r['объём_ГВтч']*1e6:.0f} кВт·ч; газ {r['газ_млн_м3']:.0f} млн м³ "
                f"по {r['цена_газа']:.1f} $/1000 м³",
                "допущение"))
    return out, rows


# ============================================== 6. сценарии себестоимости кВт·ч
def _tarify_usd(god_kursa=2026):
    hca = load("anre_hca.csv")
    tr_gaz_lei = (float(hca[hca["показатель"].str.contains("выход из сетей транспортировки")]["значение"].iloc[0])
                  - float(hca[hca["показатель"].str.contains("вход в сети транспортировки")]["значение"].iloc[0]))
    seti_lei_mwh = float(hca[hca["показатель"].str.contains("передачу")]["значение"].iloc[0])
    kurs = C.rate_avg_year("MDL/USD", god_kursa)
    return tr_gaz_lei, tr_gaz_lei / kurs, seti_lei_mwh, seti_lei_mwh / kurs / 1000.0, kurs


def scenarii_sebestoimosti(udel=None, cena_stancii=0.073):
    """Сколько стоил бы киловатт-час, произведённый на МГРЭС, при разной цене газа.

    cena_stancii - НЕ маржа и не себестоимость станции. Это цена, по которой
    станция фактически продавала электроэнергию по договору 489-22 (декабрь
    2022 года), когда газ доставался ей бесплатно. Мы принимаем её за
    нетопливную часть цены и в сценариях с платным газом добавляем топливо
    сверху. Это допущение, и оно завышает стоимость МГРЭС: реальная станция
    могла бы продавать и дешевле. Так помечено и в реестре фактов.
    """
    u = udel if udel is not None else C.k("удельный_расход_м3_кВтч")
    tr_lei, tr_usd_1000m3, seti_lei, seti_usd_kwh, kurs = _tarify_usd()
    ct = _comtrade_god()
    pk = _pink_gaz_god()

    gaz_2021 = float(ct.loc[2021, "цена_USD_1000м3"])
    gaz_2022 = float(ct.loc[2022, "цена_USD_1000м3"])
    gaz_2026_spot = float(pk.loc[2026])
    scen = [
        ("A. Газ бесплатный, как было до 2025", 0.0),
        (f"B. Газ по цене Газпрома 2021 ({gaz_2021:.0f} $)", gaz_2021),
        (f"C. Газ по цене Газпрома 2022 ({gaz_2022:.0f} $)", gaz_2022),
        (f"D. Газ по европейскому индексу 2026 ({gaz_2026_spot:.0f} $)", gaz_2026_spot),
        ("E. Газ с премией за малый объём (700 $)", 700.0),
    ]
    rows, out = [], []
    for name, gp in scen:
        toplivo = gp / 1000.0 * u
        transport = tr_usd_1000m3 / 1000.0 * u
        itog = toplivo + transport + cena_stancii + seti_usd_kwh
        rows.append((name, gp, toplivo, transport, cena_stancii, seti_usd_kwh, itog))
        out.append(fact(
            f"Сценарий себестоимости кВт·ч МГРЭС: {name}", round(itog, 4),
            "USD/кВт·ч", "2026",
            "HCA 44 + HCA 214 + TradeData/Pink Sheet + договор 489-22/MGRES", "-",
            f"топливо {gp:.0f}/1000*{u} = {toplivo:.4f}; транспорт газа "
            f"{tr_lei:.0f} лей/1000 м³ = {transport:.4f}; цена станции по договору 489-22 {cena_stancii}; "
            f"сети {seti_lei:.0f} лей/МВт·ч = {seti_usd_kwh:.4f}", "допущение"))
    # Румыния
    em = _year(load("ember.csv"))
    ro = em[(em["показатель"] == "Romania") & (em["год"] == 2026)]
    ro_eur = ro["значение"].mean()
    eurusd = _year(load("kursy.csv"))
    eurusd = eurusd[(eurusd["показатель"] == "USD за 1 EUR") & (eurusd["год"] == 2026)]["значение"].mean()
    ro_usd_kwh = ro_eur * eurusd / 1000.0
    ro_itog = ro_usd_kwh + seti_usd_kwh
    rows.append((f"Румыния, оптовая 2026 ({ro_eur:.1f} €/МВт·ч), с передачей",
                 None, None, None, None, seti_usd_kwh, ro_itog))
    out.append(fact(
        "Румыния: оптовая цена э/э 2026 плюс передача", round(ro_itog, 4),
        "USD/кВт·ч", "2026 (8 месяцев)",
        "european_wholesale_electricity_price_data_monthly.csv + data.csv + HCA 214", "-",
        f"{ro_eur:.2f} €/МВт·ч * {eurusd:.4f} USD/EUR / 1000 + {seti_usd_kwh:.4f}"))
    out.append(fact("Оптовая цена э/э Румынии, среднее за 8 месяцев 2026",
                    round(ro_eur, 2), "EUR/МВт·ч", "2026 (январь-август)",
                    "european_wholesale_electricity_price_data_monthly.csv",
                    "строки Country=Romania", "среднее по 8 месяцам", "из_источника"))
    return out, rows, ro_itog


def godovoy_schet(rows, ro_itog, obem_gvtch=3000.0):
    out = []
    kwh = obem_gvtch * 1e6
    for r in rows:
        name, itog = r[0], r[6]
        out.append(fact(
            f"Годовой счёт за {obem_gvtch:.0f} ГВт·ч, сценарий {name.split('.')[0]}",
            round(itog * kwh / 1e6, 0), "млн USD", "2026",
            "расчёт", "-", f"{itog:.4f} $/кВт·ч * {kwh:.0f} кВт·ч"))
    return out


# ============================================== 7. дефицит ПМР и маржа из него
def deficit_pmr():
    b = load("pmr_budjet.csv")
    dohody = float(b[b["показатель"].str.startswith("Доходы")]["значение"].iloc[0])
    rashody = float(b[b["показатель"].str.startswith("Расходы")]["значение"].iloc[0])
    place_d = b[b["показатель"].str.startswith("Доходы")]["флаг"].iloc[0]
    place_r = b[b["показатель"].str.startswith("Расходы")]["флаг"].iloc[0]
    deficit = rashody - dohody
    kurs = C.k("курс_рубля_ПМР")
    out = [
        fact("Доходы республиканского бюджета ПМР на 2026 год", dohody, "рублей ПМР",
             "2026", "Приложение № 1 (доходы РБ) (тек. ред. на 28.05.26г.).xlsx",
             place_d, "", "из_источника"),
        fact("Расходы республиканского бюджета ПМР на 2026 год", rashody, "рублей ПМР",
             "2026", "Приложение № 2 (расходы РБ) (тек. ред. на 06.06.26г.).xlsx",
             place_r, "", "из_источника"),
        fact("Дефицит республиканского бюджета ПМР на 2026 год", deficit, "рублей ПМР",
             "2026", "Приложения № 1 и № 2 к закону о бюджете ПМР", "-",
             f"{rashody:.0f} - {dohody:.0f}"),
        fact("Дефицит республиканского бюджета ПМР на 2026 год в долларах",
             round(deficit / kurs / 1e6, 1), "млн USD", "2026",
             "Приложения № 1 и № 2 + cbpmr.csv", "курс ЦБ ПМР 16,1000 на 01.08.2026",
             f"{deficit:.0f} / {kurs}"),
    ]
    return out, dohody, rashody, deficit


def marzha_iz_deficita(deficit_usd, obemy=(3000.0, 2500.0, 2000.0)):
    out, rows = [], []
    for g in obemy:
        m = deficit_usd / (g * 1e6)
        rows.append((g, m))
        out.append(fact(
            f"Маржа Тирасполя, покрывающая дефицит бюджета, при объёме {g:.0f} ГВт·ч",
            round(m, 4), "USD/кВт·ч", "2026", "расчёт", "-",
            f"{deficit_usd:.0f} $ / ({g:.0f} ГВт·ч * 1e6 кВт·ч)"))
    return out, rows


def vyruchka_mgres(god=2024, mesyacev=10):
    """Стоимость э/э, поставленной МГРЭС правому берегу, за первые N месяцев года."""
    d = _year(load("nbs_el_mes.csv"))
    d = d[(d["показатель"] == "Procurat din alte surse") & (d["год"] == god)]
    d = d.sort_values("дата").head(mesyacev)
    mwh = d["значение"].sum()
    ceny = _cena_mgres_god()
    if god not in ceny:
        return [], None
    price, psrc, pstatus = ceny[god]
    v = mwh * 1000.0 * price
    return [fact(
        f"Стоимость э/э МГРЭС правому берегу за первые {mesyacev} месяцев {god}",
        round(v / 1e6, 1), "млн USD", f"{god}, январь-{mesyacev:02d}",
        "ENE010100 + " + psrc, "-",
        f"{mwh:.0f} МВт·ч * 1000 * {price:.5f} $/кВт·ч", "требует_проверки")], v


# ================================================================ 8. платёжка
def platyozhka(scenarii, domohozyaystv=None, god=2025):
    dh = domohozyaystv or C.k("домохозяйств_правый_берег")
    p = nbs_el_god()
    byt = float(p.loc[god, "din care: consumat în sectorul rezidential"])   # МВт·ч
    kwh_mes = byt * 1000.0 / dh / 12.0
    kurs = C.rate_avg_year("MDL/USD", 2026)
    out = [fact(
        f"Бытовое потребление э/э на домохозяйство, {god}", round(kwh_mes, 1),
        "кВт·ч в месяц", str(god), "ENE010100 + допущение о числе домохозяйств",
        "строка 'din care: consumat în sectorul rezidential'",
        f"{byt:.0f} МВт·ч * 1000 / {dh:.0f} / 12", "допущение")]
    rows = []
    for name, usd_kwh in scenarii:
        lei = kwh_mes * usd_kwh * kurs
        rows.append((name, usd_kwh, lei))
        out.append(fact(
            f"Платёжка домохозяйства, сценарий: {name}", round(lei, 0),
            "лей в месяц", "2026", "расчёт", "-",
            f"{kwh_mes:.1f} кВт·ч * {usd_kwh:.4f} $/кВт·ч * {kurs:.4f} лей/$ "
            f"(энергия и передача, без распределения, сбыта и НДС)", "допущение"))
    return out, rows, kwh_mes


# ==================================================== 9. агрегаты Moldelectrica
def moldelectrica_agregaty():
    d = pd.read_csv(DATA / "moldelectrica_15min.csv", encoding="utf-8-sig")
    d["ts"] = pd.to_datetime(d["ts"])
    d["месяц"] = d["ts"].dt.strftime("%Y-%m")
    cols = ["Load", "TPP", "HPP", "RES", "MD-UA", "MD-RO"]
    for c in cols:
        d[c] = pd.to_numeric(d[c], errors="coerce")
    g = d.groupby("месяц")[cols].mean().round(1)
    g["слотов"] = d.groupby("месяц").size()
    g.to_csv(DATA / "moldelectrica_mesyachnye.csv", encoding="utf-8-sig")
    out = []
    for m in ["2024-01", "2025-01", "2026-01"]:
        if m in g.index:
            out.append(fact(
                f"Moldelectrica: средняя мощность ТЭС (TPP), {m}",
                float(g.loc[m, "TPP"]), "МВт", m,
                "Archive_data_for_period_*.zip", "колонка TPP, 15-минутный ряд",
                f"среднее по {int(g.loc[m,'слотов'])} слотам, после дедупликации",
                "из_источника"))
    return out, g


def tranzitnyy_profil():
    g = pd.read_csv(DATA / "moldelectrica_mesyachnye.csv", encoding="utf-8-sig", index_col=0)
    out = []
    for m in g.index:
        if not str(m).startswith(("2024", "2025", "2026")):
            continue
        out.append(fact(
            f"Moldelectrica: средний переток MD-RO, {m}", float(g.loc[m, "MD-RO"]),
            "МВт", str(m), "Archive_data_for_period_*.zip",
            "колонка MD-RO (плюс = импорт из Румынии в Молдову)", "среднее по месяцу", "из_источника"))
        out.append(fact(
            f"Moldelectrica: средний переток MD-UA, {m}", float(g.loc[m, "MD-UA"]),
            "МВт", str(m), "Archive_data_for_period_*.zip",
            "колонка MD-UA (минус = экспорт из Молдовы в Украину)", "среднее по месяцу", "из_источника"))
    return out, g[["MD-RO", "MD-UA", "Load", "TPP"]]


# =========================================== 10. бытовое потребление газа
def gaz_naseleniyu():
    p = nbs_gaz_god()
    s = p["din care: consumat în sectorul rezidential"] / 1000.0   # млн м³
    pik = s[s.index <= LAST_FULL_YEAR].max()
    pik_god = int(s[s.index <= LAST_FULL_YEAR].idxmax())
    dno = s[(s.index >= 2022) & (s.index <= LAST_FULL_YEAR)].min()
    dno_god = int(s[(s.index >= 2022) & (s.index <= LAST_FULL_YEAR)].idxmin())
    out = []
    for y in s.index:
        if y > LAST_FULL_YEAR:
            continue
        out.append(fact(
            f"Бытовое потребление природного газа, {y}", round(float(s.loc[y]), 1),
            "млн м³ при 20 °C", str(y), "ENE010400_20260809-013825.xlsx",
            "строка 'din care: consumat în sectorul rezidential', сумма 12 месяцев",
            "сумма помесячных значений", "из_источника"))
    out.append(fact("Глубина падения бытового потребления газа от пика",
                    round((dno / pik - 1) * 100, 1), "%", f"{pik_god} -> {dno_god}",
                    "ENE010400_20260809-013825.xlsx", "-",
                    f"({dno:.1f} / {pik:.1f} - 1) * 100"))
    last = float(s.loc[LAST_FULL_YEAR])
    out.append(fact("Уровень невозврата бытового потребления газа к пику",
                    round((last / pik - 1) * 100, 1), "%",
                    f"{pik_god} -> {LAST_FULL_YEAR}",
                    "ENE010400_20260809-013825.xlsx", "-",
                    f"({last:.1f} / {pik:.1f} - 1) * 100"))
    return out, s


# ====================================== 11. прочие показатели из НБС
def prochee():
    pe = nbs_el_god()
    pg = nbs_gaz_god()
    out = []
    for y in sorted(pe.index):
        if y > LAST_FULL_YEAR:
            continue
        out.append(fact(f"Собственная генерация э/э Молдовы, {y}",
                        round(float(pe.loc[y, "Producerea"]) / 1000, 1), "ГВт·ч", str(y),
                        "ENE010100_20260809-013935 (2).xlsx", "строка 'Producerea'",
                        "сумма 12 месяцев", "из_источника"))
        out.append(fact(f"Импорт э/э, {y}",
                        round(float(pe.loc[y, "Import"]) / 1000, 1), "ГВт·ч", str(y),
                        "ENE010100_20260809-013935 (2).xlsx", "строка 'Import'",
                        "сумма 12 месяцев", "из_источника"))
        out.append(fact(f"Экспорт э/э, {y}",
                        round(float(pe.loc[y, "Export"]) / 1000, 1), "ГВт·ч", str(y),
                        "ENE010100_20260809-013935 (2).xlsx", "строка 'Export'",
                        "сумма 12 месяцев", "из_источника"))
        out.append(fact(f"Бытовое потребление э/э, {y}",
                        round(float(pe.loc[y, "din care: consumat în sectorul rezidential"]) / 1000, 1),
                        "ГВт·ч", str(y), "ENE010100_20260809-013935 (2).xlsx",
                        "строка 'din care: consumat în sectorul rezidential'",
                        "сумма 12 месяцев", "из_источника"))
        out.append(fact(f"Импорт природного газа (правый берег), {y}",
                        round(float(pg.loc[y, "Import"]) / 1000, 1), "млн м³ при 20 °C",
                        str(y), "ENE010400_20260809-013825.xlsx", "строка 'Import'",
                        "сумма 12 месяцев", "из_источника"))
        out.append(fact(f"Валовое внутреннее потребление газа (правый берег), {y}",
                        round(float(pg.loc[y, "Consumul intern brut"]) / 1000, 1),
                        "млн м³ при 20 °C", str(y), "ENE010400_20260809-013825.xlsx",
                        "строка 'Consumul intern brut'", "сумма 12 месяцев", "из_источника"))
    return out


# ============================================ 13. ежегодники ПМР: базовые ряды
def _pmr():
    """Ряды из статежегодников ПМР, сводная таблица год x показатель."""
    d = load("pmr_ezhegodnik.csv")
    d["год"] = d["дата"].str[:4].astype(int)
    return d.pivot_table(index="год", columns="показатель", values="значение", aggfunc="first")


_PMR_EL = "Произведено электроэнергии (ПМР)"
_PMR_OTP = "Отпущено электроэнергии за пределы республики (ПМР)"
_PMR_VN = "Потреблено электроэнергии внутри республики (ПМР)"
_PMR_GAZ = "Подано сетевого газа в сеть (ПМР, коммунальная сеть)"
_PMR_GAZ_NAS = "Отпущено сетевого газа населению (ПМР)"
_PMR_EX = "Экспорт топливно-энергетических товаров (ПМР)"
_PMR_IM = "Импорт топливно-энергетических товаров (ПМР)"


def pmr_ryady():
    """Ежегодники ПМР как есть - в реестр фактов, со статусом из_источника."""
    from normalize import PMR_ELBALANS, PMR_SETEVOY_GAZ, PMR_TEK_TORGOVLYA
    d = load("pmr_ezhegodnik.csv")
    out = []
    for _, r in d.iterrows():
        y = r["дата"][:4]
        out.append(fact(f"{r['показатель']}, {y}", r["значение"], r["единица"], y,
                        r["источник_файл"], r["флаг"], "", "из_источника"))
    return out


# ============================== 14. сверка двух статистических служб
def sverka_dvuh_statsluzhb():
    """«Отпущено за пределы республики» (Госстат ПМР) против «Procurat din alte
    surse» (НБС Молдовы). Две службы по разные стороны Днестра, не признающие
    друг друга, считают один и тот же поток независимо."""
    p = _pmr()
    nbs = nbs_el_god()
    rows, out = [], []
    for y in sorted(p.index):
        if _PMR_OTP not in p.columns or pd.isna(p.loc[y, _PMR_OTP]):
            continue
        if y not in nbs.index:
            continue
        pmr = float(p.loc[y, _PMR_OTP])
        md = float(nbs.loc[y, "Procurat din alte surse"]) / 1000.0   # МВт·ч -> млн кВт·ч
        if md <= 0:
            continue
        dev = (md - pmr) / pmr * 100.0
        rows.append((y, pmr, md, dev))
        out.append(fact(f"Сверка двух статслужб: расхождение НБС против Госстата ПМР, {y}",
                        round(dev, 2), "%", str(y),
                        "pmr_ezhegodnik.csv + ENE010100_20260809-013935 (2).xlsx",
                        "«Отпущено за пределы республики» против «Procurat din alte surse»",
                        f"({md:.1f} - {pmr:.1f}) / {pmr:.1f} * 100"))
    return out, rows


# ================== 15. оценка цены экспорта э/э ПМР по таможенной категории
def ocenka_ceny_eksporta_pmr():
    """Экспорт топливно-энергетических товаров делить на отпуск электроэнергии
    за пределы республики.

    ЭТО ОЦЕНКА, А НЕ КОНТРАКТНАЯ ЦЕНА. Категория «топливно-энергетические
    товары» - таможенная; в неё может входить не только электроэнергия.
    Статус во всех записях - `оценка`."""
    p = _pmr()
    rows, out = [], []
    for y in sorted(p.index):
        if pd.isna(p.loc[y, _PMR_EX]) or pd.isna(p.loc[y, _PMR_OTP]):
            continue
        ex, otp = float(p.loc[y, _PMR_EX]), float(p.loc[y, _PMR_OTP])
        cent = ex * 1e6 / (otp * 1e6) * 100.0     # млн $ / млн кВт·ч -> цент/кВт·ч
        rows.append((y, ex, otp, cent))
        out.append(fact(f"Оценка цены экспорта э/э ПМР по таможенной категории, {y}",
                        round(cent, 2), "цент/кВт·ч", str(y),
                        "statisticheskiy_ezhegodnik_pmr_*.pdf",
                        "табл. 15.2 строка «топливно-энергетические товары» / табл. 8.13 "
                        "строка «Отпущено за пределы республики»",
                        f"{ex} млн $ / {otp} млн кВт·ч * 100", "оценка"))
    return out, rows


# ====================== 16. баланс газа левого берега (электроэнергия + быт)
def balans_gaza_levogo_berega(god=None, udel=None):
    """Производство э/э x удельный расход + коммунальная сеть = итого по левому берегу.

    Удельный расход - НОРМАТИВ 2016 года (0,3047 м³/кВт·ч), не измеренная величина.
    Фактический расход из ежегодника не выводится: таблицы расхода топлива
    электростанциями в нём нет (проверены все 191 страница выпуска 2021)."""
    u = udel if udel is not None else C.k("удельный_расход_м3_кВтч")
    p = _pmr()
    years = [god] if god else sorted(p.index)
    rows, out = [], []
    for y in years:
        if y not in p.index or pd.isna(p.loc[y, _PMR_EL]) or pd.isna(p.loc[y, _PMR_GAZ]):
            continue
        el = float(p.loc[y, _PMR_EL])
        gaz_komm = float(p.loc[y, _PMR_GAZ])
        gaz_el = el * u                      # млн кВт·ч * м³/кВт·ч = млн м³
        itog = gaz_el + gaz_komm
        dolya = gaz_el / itog * 100.0
        rows.append((y, el, gaz_el, gaz_komm, itog, dolya))
        out.append(fact(f"Газ левого берега на электроэнергию, {y}", round(gaz_el), "млн м³",
                        str(y), "statisticheskiy_ezhegodnik_pmr_*.pdf + приказ ПМР 2015",
                        "табл. 8.13 «Произведено электроэнергии» x норматив 356,1 г у.т./кВт·ч",
                        f"{el} млн кВт·ч * {u} м³/кВт·ч", "вычислено"))
        out.append(fact(f"Газ левого берега всего, {y}", round(itog), "млн м³", str(y),
                        "statisticheskiy_ezhegodnik_pmr_*.pdf",
                        "электроэнергия по нормативу + табл. 4.4.7 «Подано в сеть»",
                        f"{gaz_el:.0f} + {gaz_komm} ", "вычислено"))
        out.append(fact(f"Доля газа левого берега, идущая на электроэнергию, {y}",
                        round(dolya, 1), "%", str(y),
                        "statisticheskiy_ezhegodnik_pmr_*.pdf", "-",
                        f"{gaz_el:.0f} / {itog:.0f} * 100", "вычислено"))
    return out, rows


# ================ 17. тарифы молдавской генерации, январь 2010 (бань -> центы)
def tarify_moldavskoy_generacii_2010():
    """Пересчёт бань в центы по курсу, который сам регулятор применил в решении:
    12,3 лея за доллар. Не по среднегодовому курсу БНМ - именно по тарифному."""
    from normalize import MD_TARIFY_2010, KURS_ANRE_2010
    rows, out = [], []
    for name, bani, kind, cite in MD_TARIFY_2010:
        cent = bani / KURS_ANRE_2010
        rows.append((name, bani, cent, kind))
        out.append(fact(f"Тариф 2010, {name}", round(cent, 2), "цент/кВт·ч", "2010",
                        "Raport final 2010_31.03.11.doc", cite,
                        f"{bani} бань / {KURS_ANRE_2010} лей/$", "вычислено"))
        # В решении регулятора эти тарифы стоят именно в банях. Центы - производные.
        # Для сайта нужны исходные бани: читателю в Молдове понятнее лей, чем цент.
        out.append(fact(f"Тариф 2010, {name}, в банях", bani, "бань/кВт·ч", "2010",
                        "Raport final 2010_31.03.11.doc", cite, "-", "из_источника"))
    # МГРЭС - прямо в центах, пересчёт не нужен
    mg = 5.83
    rows.append(("МГРЭС (CERS Moldovenească)", mg * KURS_ANRE_2010, mg, "закупка"))
    out.append(fact("Тариф 2010, МГРЭС (CERS Moldovenească)", mg, "цент/кВт·ч", "2010",
                    "Raport final 2010_31.03.11.doc",
                    "цена закупки у станции приведена в отчёте напрямую в центах",
                    "-", "из_источника"))
    out.append(fact("Тариф 2010, МГРЭС (CERS Moldovenească), в банях",
                    round(mg * KURS_ANRE_2010, 2), "бань/кВт·ч", "2010",
                    "Raport final 2010_31.03.11.doc",
                    "цена 5,83 ¢/kWh приведена в отчёте напрямую; в бани пересчитана здесь",
                    f"{mg} цента * {KURS_ANRE_2010} лей/$", "вычислено"))
    # насколько МГРЭС была дешевле каждой молдавской ТЭЦ
    for name, bani, cent, kind in rows:
        if kind != "генерация":
            continue
        d = (cent - mg) / cent * 100.0
        out.append(fact(f"Насколько МГРЭС дешевле: {name}, 2010", round(d, 1), "%", "2010",
                        "Raport final 2010_31.03.11.doc", "сравнение тарифов января 2010",
                        f"({cent:.2f} - {mg}) / {cent:.2f} * 100", "вычислено"))
    return out, rows


# ============================ 18. нормативы трёх станций ПМР: МГРЭС худшая
def normativy_treh_stanciy():
    from normalize import PMR_NORMATIVY_2016, PMR_NORMATIV_ISTOCHNIK
    out = []
    baza = dict(PMR_NORMATIVY_2016)["ЗАО «Молдавская ГРЭС»"]
    for name, g in PMR_NORMATIVY_2016:
        out.append(fact(f"Норматив удельного расхода топлива на 2016 год: {name}", g,
                        "г у.т./кВт·ч", "2016", "приказ Минрегионразвития ПМР 15.05.2015",
                        PMR_NORMATIV_ISTOCHNIK, "", "из_источника"))
        out.append(fact(f"Норматив в кубометрах газа: {name}",
                        round(C.g_ut_to_m3(g), 4), "м³/кВт·ч", "2016",
                        "приказ Минрегионразвития ПМР 15.05.2015 + convert.py",
                        "пересчёт по низшей теплоте сгорания 34,2 МДж/м³",
                        f"{g} / 1000 * 29,3076 / 34,2", "вычислено"))
        if name != "ЗАО «Молдавская ГРЭС»":
            d = (baza - g) / baza * 100.0
            out.append(fact(f"Насколько экономичнее МГРЭС: {name}", round(d, 1), "%", "2016",
                            "приказ Минрегионразвития ПМР 15.05.2015",
                            "сравнение п. 1 приказа",
                            f"({baza} - {g}) / {baza} * 100", "вычислено"))
    return out


# ================================= 19. ценовая лестница МГРЭС по годам
def cenovaya_lestnica():
    """Сводит в один ряд всё, что известно о цене киловатт-часа от МГРЭС.

    Три разных типа значений, смешивать нельзя:
      контракт  - прямая цена из договора или из решения регулятора
      оценка    - производная от таможенной категории ПМР
      blended   - средняя цена закупки/импорта по Молдове, где МГРЭС лишь доля
    """
    a = load("anre_otchety.csv")
    a["год"] = a["дата"].str[:4].astype(int)
    ap = a.pivot_table(index="год", columns="показатель", values="значение", aggfunc="first")
    kurs = load("kursy.csv")
    kurs["год"] = kurs["дата"].str[:4].astype(int)

    _, oc_rows = ocenka_ceny_eksporta_pmr()
    ocenka = {y: c for y, _, _, c in oc_rows}

    rows, out = [], []

    def add(god, tip, cent, ist, place):
        rows.append((god, tip, cent, ist))
        out.append(fact(f"Ценовая лестница МГРЭС, {god} ({tip})", round(cent, 2),
                        "цент/кВт·ч", str(god), ist, place, "",
                        {"контракт": "из_источника", "оценка": "оценка",
                         "blended": "из_источника"}[tip]))

    add(2010, "контракт", 4.69, "Raport final 2010_31.03.11.doc",
        "цена, включённая в предыдущий тариф; действовала до января 2010")
    add(2010, "контракт", 5.83, "Raport final 2010_31.03.11.doc",
        "цена по договору с CERS Moldovenească, установлена в январе 2010, рост 24,0%")
    # прямые цены из тендеров, коммюнике и сообщений Минэкономики
    from normalize import MGRES_CENY
    for d1, d2, v, tip, src, place in MGRES_CENY:
        if tip.startswith("оферта"):
            continue
        add(int(d1[:4]), "контракт", v / 10.0, src, f"период {d1}..{d2}; {place}")
    for y in sorted(ocenka):
        add(y, "оценка", ocenka[y], "statisticheskiy_ezhegodnik_pmr_*.pdf",
            "экспорт ТЭ товаров / отпуск э/э за пределы республики")
    for y, col in ((2018, "Средняя цена импорта э/э (blended, вкл. МГРЭС)"),
                   (2019, "Средняя цена импорта э/э (blended, вкл. МГРЭС)")):
        if col in ap.columns and not pd.isna(ap.loc[y, col]):
            add(y, "blended", float(ap.loc[y, col]),
                "RAPORT DE ACTIVITATE 2019 FINAL 30.11.2020.docx.pdf",
                "средняя цена импорта э/э: МГРЭС плюс Украина, доля МГРЭС не выделена")
    # контрактные цены 2022-2023 из договоров Energocom
    from normalize import CONTRACTS
    seen = set()
    for cid, doc, ddate, p1, p2, price, vol, total, place in CONTRACTS:
        key = (p1[:4], round(price * 100, 2))
        if key in seen:
            continue
        seen.add(key)
        add(int(p1[:4]), "контракт", price * 100, "OCR_Contracts_MGRES_FULL.txt",
            f"{doc}, период с {p1}, {place}")
    if 2022 in ap.index and "Цена закупки э/э у CTE Moldovenească, декабрь" in ap.columns:
        v = ap.loc[2022, "Цена закупки э/э у CTE Moldovenească, декабрь"]
        if not pd.isna(v):
            add(2022, "контракт", float(v) / 10.0,
                "Raport privind Activitatea ANRE in anul 2022.pdf",
                "73,5 USD/МВт·ч в декабре 2022 - независимое подтверждение договорной цены 7,30")
    rows.sort(key=lambda r: (r[0], r[1]))
    return out, rows


def dolya_gaza_na_pravyy_bereg():
    """Какая доля газа левого берега сжигалась ради электричества правому берегу.

    Считается по объёмам, взвешенно: сумма газа на экспортное электричество за все
    годы с данными, делённая на сумму всего газа левого берега за те же годы.
    Взвешенный способ вернее среднего из годовых долей: годы с разным объёмом
    получают разный вес.

    ВНИМАНИЕ. Доля посчитана по 2010-2020 годам - это единственный период, где
    есть и электробаланс, и коммунальная сеть. Долг накапливался дольше и по
    разным ценам, поэтому перенос этой доли на всю сумму долга - оценка,
    а не строка из документа.
    """
    from normalize import PMR_ELBALANS, PMR_SETEVOY_GAZ
    u = C.k("удельный_расход_м3_кВтч")
    rows, s_right, s_total = [], 0.0, 0.0
    for god in sorted(PMR_ELBALANS):
        if god not in PMR_SETEVOY_GAZ or god < 2010:
            continue
        pr, izv, vn, otp, src, place = PMR_ELBALANS[god]
        pod = PMR_SETEVOY_GAZ[god][0]
        right, ee_all = otp * u, pr * u
        total = ee_all + pod
        s_right += right
        s_total += total
        rows.append((god, round(right), round(ee_all - right), round(pod), round(total)))
    dolya = s_right / s_total * 100.0
    out = [fact("Доля газа левого берега, сожжённого ради электричества правому берегу",
                round(dolya, 1), "%", f"{rows[0][0]}-{rows[-1][0]}",
                "статежегодники ПМР + норматив ПМР",
                f"взвешенно по объёмам за {len(rows)} лет",
                f"{s_right:.0f} / {s_total:.0f} * 100", "оценка")]
    return out, rows, dolya


def dolg_za_elektrichestvo(dolg_levy_mln=7608.876836, domohozyaystv=None):
    """Часть левобережного долга, приходящаяся на электричество для правого берега."""
    _, _, dolya = dolya_gaza_na_pravyy_bereg()
    hh = domohozyaystv or C.k("домохозяйств_правого_берега") if False else 1006800
    chast = dolg_levy_mln * dolya / 100.0
    out = [
        fact("Долг левого берега, приходящийся на электричество правому берегу",
             round(chast, 1), "млн USD", "31.10.2021",
             "аудит Wikborg Rein/FRA + расчёт доли по объёмам газа",
             f"{dolg_levy_mln:.1f} млн * {dolya:.1f}%", "", "оценка"),
        fact("То же на одно домохозяйство правого берега",
             round(chast * 1e6 / hh), "USD", "31.10.2021",
             "аудит + перепись 2024", f"{chast:.1f} млн / {hh}", "", "оценка"),
    ]
    return out, chast, dolya


def srednegodovaya_cena_mgres():
    """Средневзвешенная по месяцам цена закупки у МГРЭС за календарный год.

    Добавлено 12.08.2026 для трёхлинейного графика на сайте. Метод: для каждого
    месяца берётся действовавшая в нём контрактная цена из MGRES_CENY (оферты,
    которые были отклонены, не учитываются), дальше среднее по покрытым месяцам.
    Отдельно возвращается покрытие - сколько месяцев года закрыто договорами.
    Год с покрытием меньше 6 месяцев в графики не идёт.
    """
    from normalize import MGRES_CENY, CONTRACTS
    per = [(d1, d2, v) for d1, d2, v, tip, _, _ in MGRES_CENY if "оферта" not in tip]
    # договоры 2022 года лежат отдельной структурой - подмешиваем их сюда,
    # иначе 2022 год закрыт только тремя месяцами прошлогоднего контракта
    for cid, doc, ddate, p1, p2, price, vol, total, place in CONTRACTS:
        per.append((p1, p2, round(price * 1000, 2)))
    out, rows = [], []
    for god in range(2010, 2025):
        mes = []
        for m in range(1, 13):
            day = f"{god}-{m:02d}-15"
            hit = [v for d1, d2, v in per if d1 <= day <= d2]
            if hit:
                mes.append(hit[0])
        if not mes:
            continue
        sred = sum(mes) / len(mes)
        rows.append((god, round(sred, 2), len(mes)))
        out.append(fact(f"Средневзвешенная цена закупки у МГРЭС, {god}", round(sred, 2),
                        "USD/МВт·ч", str(god), "normalize.MGRES_CENY",
                        f"покрыто договорами {len(mes)} месяцев из 12",
                        "среднее по месяцам, в которых действовал известный договор",
                        "вычислено" if len(mes) == 12 else "оценка"))
    return out, rows


def realnaya_cena_s_dolgom():
    """Реальная цена кВт·ч: деньгами плюс газ, записанный в долг.

    К контрактной цене прибавляется стоимость газа, сожжённого на этот киловатт-час:
    норматив 0,3047 м³/кВт·ч, умноженный на цену закупки газа правым берегом
    из годовых отчётов ANRE - именно по ней долг и начислялся.
    Третья линия - оптовая биржевая цена Румынии (Ember), для сопоставления.
    Окно 2015-2023: раньше нет биржевых цен, позже нет цены газа в отчётах ANRE.
    """
    _, ceny = srednegodovaya_cena_mgres()
    cash = {g: v for g, v, cov in ceny if cov >= 6}
    a = load("anre_otchety.csv")
    a["год"] = a["дата"].str[:4].astype(int)
    gz = a[a["показатель"] == "Средняя цена закупки газа (правый берег)"]
    gaz = {int(r["год"]): float(r["значение"]) for _, r in gz.iterrows()}
    em = _year(load("ember.csv"))
    ro = em[em["показатель"] == "Romania"].groupby("год")["значение"].mean()
    ku = _year(load("kursy.csv"))
    eur = ku[ku["показатель"] == "USD за 1 EUR"].groupby("год")["значение"].mean()
    u = C.k("удельный_расход_м3_кВтч")
    out, rows = [], []
    for god in range(2015, 2024):
        if god not in cash or god not in gaz or god not in ro.index:
            continue
        gaz_v_cene = u * gaz[god] / 10.0          # цент/кВт·ч
        dengami = cash[god] / 10.0                 # USD/МВт·ч -> цент/кВт·ч
        realno = dengami + gaz_v_cene
        rom = float(ro.loc[god]) * float(eur.loc[god]) / 10.0
        rows.append((god, round(dengami, 2), round(gaz_v_cene, 2),
                     round(realno, 2), round(rom, 2)))
        out.append(fact(f"Реальная цена кВт·ч от МГРЭС с учётом газа в долг, {god}",
                        round(realno, 2), "цент/кВт·ч", str(god),
                        "normalize.MGRES_CENY + отчёты ANRE + Ember",
                        f"деньгами {dengami:.2f} + газ {gaz_v_cene:.2f}",
                        f"{dengami:.2f} + {u} * {gaz[god]} / 10", "вычислено"))
        out.append(fact(f"Оптовая цена э/э Румынии в центах, {god}", round(rom, 2),
                        "цент/кВт·ч", str(god), "european_wholesale_...csv + data.csv",
                        "средняя за год по бирже OPCOM",
                        f"{float(ro.loc[god]):.2f} EUR/МВт·ч * {float(eur.loc[god]):.4f} / 10",
                        "вычислено"))
    return out, rows


def vyruchka_mgres_2024():
    """Средняя цена по коммюнике Premier Energy за 2024 год и выручка станции.

    Обе величины стояли в плане статьи, но в реестре их не было. Внесены 12.08.2026.
    Оговорка сохраняется: цены коммюнике включают маржу Energocom, значит 205 млн -
    верхняя граница выручки станции, а не сумма, дошедшая до неё.
    """
    from normalize import MGRES_CENY
    ceny = [v for d1, _, v, tip, _, _ in MGRES_CENY
            if d1.startswith("2024") and "Energocom" in tip]
    if not ceny:
        return []
    sred = sum(ceny) / len(ceny)
    a = load("anre_otchety.csv")
    m = a[(a["показатель"] == "Закупка э/э у CTE Moldovenească") & (a["дата"].str[:4] == "2024")]
    if m.empty:
        return []
    obyom_gwh = float(m["значение"].iloc[0])
    vyruchka = sred * obyom_gwh * 1000.0 / 1e6
    return [
        fact("Средняя цена закупки у МГРЭС по коммюнике Premier Energy, 2024",
             round(sred, 2), "USD/МВт·ч", "2024", "premierenergy.md, помесячные коммюнике",
             f"среднее по {len(ceny)} опубликованным месяцам",
             " + ".join(f"{c}" for c in ceny) + f" делить на {len(ceny)}", "вычислено"),
        fact("Выручка МГРЭС от поставок в Молдову, 2024 (верхняя граница)",
             round(vyruchka, 1), "млн USD", "2024",
             "premierenergy.md + годовой отчёт ANRE за 2024",
             "цена включает маржу Energocom, поэтому это верхняя граница",
             f"{sred:.4f} USD/МВт·ч * {obyom_gwh} млн кВт·ч * 1000 / 1e6", "вычислено"),
    ]


def sverka_lestnicy():
    """Сверяет оценку по ежегодникам с прямыми ценами там, где есть обе.
    Расхождение больше 15% - отдельный флаг."""
    _, oc = ocenka_ceny_eksporta_pmr()
    ocenka = {y: c for y, _, _, c in oc}
    a = load("anre_otchety.csv")
    a["год"] = a["дата"].str[:4].astype(int)
    ap = a.pivot_table(index="год", columns="показатель", values="значение", aggfunc="first")
    pary = []
    if 2010 in ocenka:
        pary.append((2010, "контракт ANRE (январь 2010)", 5.83, ocenka[2010]))
    # 2011-2014: контракты распределительной компании со станцией.
    # Там, где внутри календарного года действовали два контракта, цена взвешена по месяцам.
    if 2011 in ocenka:
        pary.append((2011, "контракт с 01.04.2011 (61,0 USD/МВт·ч); январь-март не установлен",
                     6.10, ocenka[2011]))
    if 2012 in ocenka:
        pary.append((2012, "контракты 2012, взвешенные по месяцам (3 мес. 6,10 + 9 мес. 6,90)",
                     (3 * 6.10 + 9 * 6.90) / 12, ocenka[2012]))
    if 2013 in ocenka:
        pary.append((2013, "контракт 6,90 весь год", 6.90, ocenka[2013]))
    if 2014 in ocenka:
        pary.append((2014, "контракты 2014, взвешенные по месяцам (3 мес. 6,90 + 9 мес. 6,80)",
                     (3 * 6.90 + 9 * 6.80) / 12, ocenka[2014]))
    if 2015 in ocenka:
        pary.append((2015, "контракт 67,95 USD/МВт·ч (действовал до 01.03.2016)",
                     6.795, ocenka[2015]))
    # 2016: два контракта внутри года, взвешиваем по месяцам (3 месяца по 6,795 + 9 по 4,8995)
    if 2016 in ocenka:
        w2016 = (3 * 6.795 + 9 * 4.8995) / 12
        pary.append((2016, "контракты 2016, взвешенные по месяцам (3 мес. 6,795 + 9 мес. 4,8995)",
                     w2016, ocenka[2016]))
    # 2017: контракт МГРЭС с 07.06.2017 - 4,50 цента
    if 2017 in ocenka:
        pary.append((2017, "контракт МГРЭС с 07.06.2017 (45,0 USD/МВт·ч)", 4.50, ocenka[2017]))
    col = "Средняя цена импорта э/э (blended, вкл. МГРЭС)"
    for y in (2018,):
        if y in ocenka and col in ap.columns and not pd.isna(ap.loc[y, col]):
            pary.append((y, "средняя цена импорта ANRE (blended)", float(ap.loc[y, col]), ocenka[y]))
    # 2019-2020: с 12.08.2026 вместо средней цены импорта ANRE (blended) используется
    # цена именно МГРЭС из тендерных документов - она точнее и относится к самой станции.
    if 2019 in ocenka:
        pary.append((2019, "цена МГРЭС по контракту 01.04.2019-31.03.2020 (52,4 USD/МВт·ч, "
                           "9 месяцев из 12)", 5.24, ocenka[2019]))
    if 2020 in ocenka:
        pary.append((2020, "контракты 2020, взвешенные по месяцам "
                           "(3 мес. 5,24 + 3 мес. 4,99 + 6 мес. 4,865)",
                     (3 * 5.24 + 3 * 4.99 + 6 * 4.865) / 12, ocenka[2020]))
    out, rows = [], []
    for y, чем, pryamo, oc in pary:
        dev = (oc - pryamo) / pryamo * 100.0
        flag = "расхождение больше 15%" if abs(dev) > 15 else ""
        rows.append((y, чем, pryamo, oc, dev, flag))
        out.append(fact(f"Сверка оценки по ежегоднику с прямой ценой, {y}", round(dev, 1), "%",
                        str(y), "statisticheskiy_ezhegodnik_pmr_*.pdf + отчёт ANRE",
                        f"оценка {oc:.2f} против «{чем}» {pryamo:.2f}",
                        f"({oc:.2f} - {pryamo:.2f}) / {pryamo:.2f} * 100", "вычислено"))
    return out, rows


# ====================================== 12. контракты 2022: сходимость и цены
def kontrakty():
    from normalize import CONTRACTS
    out = []
    for cid, doc, ddate, p1, p2, price, vol, total, place in CONTRACTS:
        out.append(fact(f"{doc} ({cid}): цена э/э, период {p1}..{p2}", price,
                        "USD/кВт·ч", f"{p1}..{p2}", "OCR_Contracts_MGRES_FULL.txt",
                        place, "", "из_источника"))
        if vol is not None:
            out.append(fact(f"{doc} ({cid}): объём, период {p1}..{p2}", vol, "МВт·ч",
                            f"{p1}..{p2}", "OCR_Contracts_MGRES_FULL.txt", place, "",
                            "из_источника"))
        if total is not None:
            out.append(fact(f"{doc} ({cid}): сумма договора, период {p1}..{p2}", total,
                            "USD", f"{p1}..{p2}", "OCR_Contracts_MGRES_FULL.txt", place,
                            "", "из_источника"))
        if vol is not None and total is not None:
            calc_total = vol * 1000 * price
            out.append(fact(f"{doc} ({cid}): расхождение цена*объём против суммы",
                            round(calc_total - total, 2), "USD", f"{p1}..{p2}",
                            "OCR_Contracts_MGRES_FULL.txt", place,
                            f"{vol} * 1000 * {price} - {total}"))
        if vol is None and total is not None:
            out.append(fact(f"{doc} ({cid}): объём, восстановленный из суммы и цены",
                            round(total / price / 1000, 3), "МВт·ч", f"{p1}..{p2}",
                            "OCR_Contracts_MGRES_FULL.txt", place,
                            f"{total} / {price} / 1000", "вычислено"))
    return out
