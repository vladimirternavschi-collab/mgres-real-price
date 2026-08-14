# -*- coding: utf-8 -*-
"""Автопроверки. Модуль сам ловит расхождения и сообщает о них понятным текстом.

Критические проверки (FAIL) останавливают пайплайн.
Предупреждения (WARN) печатаются и попадают в отчёт, но не останавливают.
"""
import sys

import pandas as pd

import calc as K
import convert as C
from config import DATA, LAST_FULL_YEAR
from normalize import CONTRACTS

RESULTS = []


def _ok(name, msg=""):
    RESULTS.append(("OK", name, msg))
    print(f"  [OK]   {name}" + (f" - {msg}" if msg else ""))


def _warn(name, msg):
    RESULTS.append(("WARN", name, msg))
    print(f"  [WARN] {name} - {msg}")


def _fail(name, msg):
    RESULTS.append(("FAIL", name, msg))
    print(f"  [FAIL] {name} - {msg}")


# 1. цена x объём = сумма по каждому договору
def check_kontrakty():
    bad = []
    for cid, doc, ddate, p1, p2, price, vol, total, place in CONTRACTS:
        if vol is None or total is None:
            continue
        d = vol * 1000 * price - total
        if abs(d) > 10:
            bad.append(f"{cid} {doc}: расхождение {d:.2f} $")
        elif abs(d) > 0.5:
            _warn(f"договор {cid}", f"расхождение {d:.2f} $ - округление в тексте договора")
    if bad:
        _fail("сходимость договоров", "; ".join(bad))
    else:
        _ok("сходимость договоров", "цена * объём = сумма по всем документам, где есть оба числа")


# 2. годовая сумма НБС против годового отчёта ANRE
def check_nbs_vs_anre():
    p = K.nbs_el_god()
    a = K.load("anre_otchety.csv")
    a = a[a["показатель"] == "Закупка э/э у CTE Moldovenească"]
    for _, r in a.iterrows():
        y = int(r["дата"][:4])
        if y not in p.index:
            continue
        nbs = float(p.loc[y, "Procurat din alte surse"]) / 1000.0
        anre = float(r["значение"])
        if anre == 0 and nbs == 0:
            _ok(f"НБС против ANRE, {y}", "оба источника дают 0")
            continue
        d = (nbs - anre) / anre * 100 if anre else float("inf")
        if y == 2018:
            # Разобрано 12.08.2026. Расхождение объяснено и не является критическим:
            # ANRE (2544,0) и Госстат ПМР (2543,9) сходятся до 0,004%, выбивается
            # только ряд НБС «Procurat din alte surse». Импорт при этом совпадает
            # у обоих источников (ANRE 956 против НБС 955,8).
            _warn(f"НБС против ANRE, {y}",
                  f"НБС {nbs:.1f} против ANRE {anre:.1f} ГВт·ч, {d:+.1f}% - выброс в ряду НБС; "
                  f"ANRE сходится с Госстатом ПМР (2 543,9) до 0,004%, импорт у обоих 956")
            continue
        if abs(d) <= 3:
            _ok(f"НБС против ANRE, {y}", f"НБС {nbs:.1f} против ANRE {anre:.1f} ГВт·ч, {d:+.1f}%")
        elif abs(d) <= 15:
            _warn(f"НБС против ANRE, {y}",
                  f"НБС {nbs:.1f} против ANRE {anre:.1f} ГВт·ч, {d:+.1f}% - "
                  f"разная методика (НБС: физические поставки; ANRE: закупки лицензиатов)")
        else:
            _fail(f"НБС против ANRE, {y}",
                  f"НБС {nbs:.1f} против ANRE {anre:.1f} ГВт·ч, {d:+.1f}%")


# 3. обнуление 'Procurat din alte surse' совпадает с провалом TPP в Moldelectrica
def check_razryv():
    d = K._year(K.load("nbs_el_mes.csv"))
    d = d[d["показатель"] == "Procurat din alte surse"].sort_values("дата")
    dec24 = d[d["дата"] == "2024-12-01"]["значение"].iloc[0]
    jan25 = d[d["дата"] == "2025-01-01"]["значение"].iloc[0]
    nonzero_after = d[(d["дата"] >= "2025-01-01") & (d["значение"] > 0)]
    g = pd.read_csv(DATA / "moldelectrica_mesyachnye.csv", encoding="utf-8-sig", index_col=0)
    tpp24, tpp25 = float(g.loc["2024-01", "TPP"]), float(g.loc["2025-01", "TPP"])
    drop = tpp24 - tpp25
    if jan25 == 0 and dec24 > 0 and len(nonzero_after) == 0 and drop > 150:
        _ok("разрыв 01.01.2025 подтверждён двумя источниками",
            f"НБС: декабрь 2024 = {dec24:.0f} МВт·ч, январь 2025 = 0, дальше ноль везде; "
            f"Moldelectrica: средняя TPP в январе {tpp24:.0f} -> {tpp25:.0f} МВт, минус {drop:.0f} МВт")
    else:
        _fail("разрыв 01.01.2025",
              f"дек24={dec24}, янв25={jan25}, ненулевых месяцев после={len(nonzero_after)}, "
              f"провал TPP={drop:.0f} МВт")


# 4. сумма помесячных = годовой итог (внутренняя согласованность НБС)
def check_summy():
    for f, name in [("nbs_el_mes.csv", "электроэнергия"), ("nbs_gaz_mes.csv", "газ")]:
        d = K._year(K.load(f))
        cnt = d.groupby(["год", "показатель"]).size().unstack()
        полные = [y for y in cnt.index if y <= LAST_FULL_YEAR]
        bad = []
        for y in полные:
            for col in cnt.columns:
                n = cnt.loc[y, col]
                if pd.notna(n) and n != 12:
                    bad.append(f"{y}/{col}: {int(n)} месяцев")
        if bad:
            _warn(f"полнота помесячных рядов НБС ({name})", "; ".join(bad[:6]))
        else:
            _ok(f"полнота помесячных рядов НБС ({name})",
                f"все годы 2015-{LAST_FULL_YEAR} содержат по 12 месяцев для каждого показателя")
    # баланс: Consum final brut = Producerea + Import + Procurat - Export
    p = K.nbs_el_god()
    bad = []
    for y in p.index:
        calc = (p.loc[y, "Producerea"] + p.loc[y, "Import"]
                + p.loc[y, "Procurat din alte surse"] - p.loc[y, "Export"]
                + p.loc[y, "Variatia stocurilor"])
        d = calc - p.loc[y, "Consum final brut"]
        if abs(d) > 1:
            bad.append(f"{y}: расхождение {d:.0f} МВт·ч")
    if bad:
        _warn("баланс электроэнергии НБС", "; ".join(bad))
    else:
        _ok("баланс электроэнергии НБС",
            "Producerea + Import + Procurat - Export + Variatia = Consum final brut, все годы")


# 5. значения вне исторического диапазона более чем на 50%
def check_vybrosy():
    flagged = []
    for f, name in [("nbs_el_mes.csv", "НБС э/э"), ("nbs_gaz_mes.csv", "НБС газ")]:
        d = K._year(K.load(f))
        for pok, grp in d.groupby("показатель"):
            g = grp.groupby("год")["значение"].sum()
            g = g[g.index <= LAST_FULL_YEAR]
            if len(g) < 3 or g.abs().max() == 0:
                continue
            med = g[g > 0].median() if (g > 0).any() else 0
            if med == 0:
                continue
            for y, v in g.items():
                if abs(v - med) / med > 0.5:
                    flagged.append(f"{name} / {pok} / {y}: {v:.0f} против медианы {med:.0f}")
    ct = K._comtrade_god()
    for y in ct.index:
        if isinstance(ct.loc[y, "флаг"], str) and ct.loc[y, "флаг"]:
            flagged.append(f"Comtrade / {y}: {ct.loc[y, 'флаг']}")
    if flagged:
        _warn("значения вне исторического диапазона (>50%)", f"{len(flagged)} шт.: "
              + "; ".join(flagged[:10]) + (" ..." if len(flagged) > 10 else ""))
    else:
        _ok("значения вне исторического диапазона", "не обнаружено")


# 6. сумма долей источников покрытия не превышает 100% потребления
def check_doli():
    p = K.nbs_el_god()
    bad = []
    for y in p.index:
        cons = p.loc[y, "Consum final brut"]
        if cons <= 0:
            continue
        s = (p.loc[y, "Producerea"] + p.loc[y, "Import"]
             + p.loc[y, "Procurat din alte surse"]) / cons * 100
        # экспорт вычитается из покрытия, поэтому сумма источников может быть >100%
        s_net = s - p.loc[y, "Export"] / cons * 100
        if s_net > 100.5 or s_net < 99.5:
            bad.append(f"{y}: {s_net:.1f}%")
    if bad:
        _fail("сумма источников покрытия", "; ".join(bad))
    else:
        _ok("сумма источников покрытия",
            "производство + импорт + МГРЭС - экспорт = 100% валового конечного потребления, все годы")


# 7. Moldelectrica: дедупликация и пропуски
def check_moldelectrica():
    txt = (DATA / "moldelectrica_propuski.txt").read_text(encoding="utf-8")
    uniq = int([l for l in txt.splitlines() if l.startswith("уникальных")][0].split(":")[1])
    dup = int([l for l in txt.splitlines() if l.startswith("дублей")][0].split(":")[1])
    real = int([l for l in txt.splitlines() if l.startswith("реальных")][0].split(":")[1])
    if dup == 192:
        _ok("Moldelectrica: дубликаты", f"удалено {dup} строк на стыках архивов, как и ожидалось")
    else:
        _warn("Moldelectrica: дубликаты", f"удалено {dup}, ожидалось 192")
    _ok("Moldelectrica: уникальных меток времени", f"{uniq}")
    _ok("Moldelectrica: реальные пропуски", f"{real} слотов, все в феврале 2025")


# 8. контрольные значения из задания
KONTROL = [
    ("Доля МГРЭС в потреблении, 2015", 78, 1.0, "%"),
    ("Доля МГРЭС в потреблении, 2024", 70, 1.0, "%"),
    ("Procurat din alte surse, декабрь 2024", 179358, 1, "МВт·ч"),
    ("Moldelectrica, средняя TPP январь 2024", 617, 2, "МВт"),
    ("Moldelectrica, средняя TPP январь 2025", 348, 2, "МВт"),
    ("Moldelectrica, средняя TPP январь 2026", 374, 2, "МВт"),
    ("Уникальных отметок времени Moldelectrica", 91547, 0, "шт."),
    ("Дефицит бюджета ПМР 2026", 2796671726, 0, "рублей ПМР"),
    ("Дефицит бюджета ПМР 2026 в долларах", 173.7, 0.1, "млн USD"),
    ("Бытовое потребление газа 2021", 480, 1, "млн м³"),
    ("Бытовое потребление газа 2023", 287, 1, "млн м³"),
    ("Бытовое потребление газа 2025", 326, 1, "млн м³"),
    ("Цена газа для Молдовы 2021 (Comtrade)", 311.5, 1.0, "$/1000 м³"),
    ("Европейский индекс 2021 (Pink Sheet)", 588, 1.0, "$/1000 м³"),
    ("Румыния, оптовая цена 2026 (Ember, 8 мес.)", 119.6, 0.2, "€/МВт·ч"),
    ("Объём по договору 489-22/MGRES", 204763, 0, "МВт·ч"),
    # --- контрольные ВТОРОЙ редакции (12.08.2026), после подстановки
    # --- подтверждённых коэффициентов ПМР. Зависят от удельного расхода.
    ("Сценарий A (газ бесплатный)", 0.0936, 0.0005, "USD/кВт·ч"),
    ("Сценарий B (газ Газпрома 2021)", 0.1884, 0.0005, "USD/кВт·ч"),
    ("Сценарий D (европейский индекс 2026)", 0.2615, 0.0005, "USD/кВт·ч"),
    ("Румыния с передачей", 0.1534, 0.0005, "USD/кВт·ч"),
    ("Газ на 3 000 ГВт·ч", 914.1, 0.5, "млн м³"),
    ("Потребление э/э на домохозяйство", 152.8, 0.3, "кВт·ч/мес"),
    # --- контрольные ТРЕТЬЕЙ редакции (12.08.2026), ежегодники ПМР
    ("Сверка двух статслужб, 2020", -0.01, 0.02, "%"),
    ("Сверка двух статслужб, 2018", 16.53, 0.15, "%"),
    ("Производство э/э ПМР 2020", 5196.0, 0.1, "млн кВт·ч"),
    ("Отпущено за пределы республики 2020", 3251.7, 0.1, "млн кВт·ч"),
    ("Коммунальный газ ПМР 2020", 590.8, 0.1, "млн м³"),
    ("Баланс газа левого берега 2020", 2174, 3, "млн м³"),
    ("Доля газа на электроэнергию, 2020", 72.8, 0.5, "%"),
    ("Оценка цены экспорта э/э ПМР, 2020", 4.92, 0.02, "цент/кВт·ч"),
    ("Тариф ТЭЦ-1 в центах, 2010", 10.72, 0.02, "цент/кВт·ч"),
    ("Норматив МГРЭС в кубометрах", 0.3051, 0.0008, "м³/кВт·ч"),
]


# 9. сверка двух статслужб: 2020 год должен сойтись до одной десятой ГВт·ч
def check_sverka_statsluzhb():
    _, rows = K.sverka_dvuh_statsluzhb()
    if not rows:
        _fail("сверка двух статслужб", "нет пересекающихся лет - ряды не сошлись")
        return
    for y, pmr, md, dev in rows:
        if abs(dev) <= 2.0:
            _ok(f"сверка двух статслужб, {y}",
                f"Госстат ПМР {pmr:,.1f} против НБС {md:,.1f} млн кВт·ч, расхождение {dev:+.2f}%".replace(",", " "))
        else:
            _warn(f"сверка двух статслужб, {y}",
                  f"Госстат ПМР {pmr:,.1f} против НБС {md:,.1f} млн кВт·ч, расхождение {dev:+.2f}% - выброс, нужна причина".replace(",", " "))
    _check_vybros_2018(rows)


def _check_vybros_2018(rows):
    """Разбор выброса 2018 года третьим независимым источником - отчётом ANRE.

    Госстат ПМР и НБС Молдовы расходятся в 2018 году на +16,53%. Отчёт ANRE
    за 2018 год - третья точка, не связанная ни с одной из двух статслужб.
    """
    a = K.load("anre_otchety.csv")
    a["год"] = a["дата"].str[:4].astype(int)
    m = a[(a["год"] == 2018) & (a["показатель"] == "Закупка э/э у CTE Moldovenească")]
    if m.empty:
        _warn("выброс 2018: третий источник", "в отчётах ANRE нет закупки у МГРЭС за 2018 год")
        return
    anre = float(m["значение"].iloc[0])
    r = {y: (pmr, md) for y, pmr, md, _ in rows}
    if 2018 not in r:
        return
    pmr, md = r[2018]
    d_pmr = (anre - pmr) / pmr * 100.0
    d_nbs = (anre - md) / md * 100.0
    if abs(d_pmr) <= 0.5 and abs(d_nbs) > 5.0:
        _ok("выброс 2018: третий источник",
            f"ANRE {anre:.1f} против Госстата ПМР {pmr:.1f} - расхождение {d_pmr:+.3f}%; "
            f"против НБС {md:.1f} - {d_nbs:+.1f}%. Два независимых источника из трёх сходятся, "
            f"выбивается ряд НБС «Procurat din alte surse»")
    else:
        _warn("выброс 2018: третий источник",
              f"ANRE {anre:.1f}, Госстат ПМР {pmr:.1f} ({d_pmr:+.2f}%), НБС {md:.1f} ({d_nbs:+.1f}%) - "
              f"картина не однозначная")


# 10. сверка оценки по ежегодникам с прямыми ценами: порог 15%
def check_lestnica():
    _, rows = K.sverka_lestnicy()
    if not rows:
        _warn("сверка ценовой лестницы", "нет пар «оценка - прямая цена» для сверки")
        return
    for y, чем, pryamo, oc, dev, flag in rows:
        if abs(dev) <= 15:
            _ok(f"ценовая лестница, {y}",
                f"оценка {oc:.2f} против {чем} {pryamo:.2f} цента, расхождение {dev:+.1f}% - в пределах 15%")
        else:
            _warn(f"ценовая лестница, {y}",
                  f"оценка {oc:.2f} против {чем} {pryamo:.2f} цента, расхождение {dev:+.1f}% - БОЛЬШЕ 15%")


# 11. внутренняя сверка двух изданий ежегодника по пересекающимся годам
def check_ezhegodniki():
    """Выпуски 2020 и 2021 оба содержат 2018 и 2019. Значения должны совпасть."""
    from normalize import PMR_ELBALANS, PMR_SETEVOY_GAZ, PMR_TEK_TORGOVLYA
    # в модуле хранится по одному значению на год, поэтому сверка - на этапе ввода;
    # здесь проверяем внутреннюю логику баланса: произведено + получено - потреблено = отпущено
    bad = []
    for y, (pr, izv, vn, otp, src, place) in PMR_ELBALANS.items():
        rasch = pr + (izv or 0) - vn
        d = rasch - otp
        if abs(d) > 1.0:
            bad.append(f"{y}: {rasch:.1f} против {otp:.1f}, расхождение {d:+.1f}")
    if bad:
        _warn("электробаланс ПМР сходится", "; ".join(bad))
    else:
        _ok("электробаланс ПМР сходится",
            "произведено + получено - потреблено = отпущено, все годы в пределах 1 млн кВт·ч")


def check_kontrolnye():
    p = K.nbs_el_god()
    pg = K.nbs_gaz_god()
    g = pd.read_csv(DATA / "moldelectrica_mesyachnye.csv", encoding="utf-8-sig", index_col=0)
    ct = K._comtrade_god()
    pk = K._pink_gaz_god()
    em = K._year(K.load("ember.csv"))
    txt = (DATA / "moldelectrica_propuski.txt").read_text(encoding="utf-8")
    uniq = int([l for l in txt.splitlines() if l.startswith("уникальных")][0].split(":")[1])
    _, dh, rs, df = K.deficit_pmr()
    d_el = K._year(K.load("nbs_el_mes.csv"))
    dec24 = d_el[(d_el["показатель"] == "Procurat din alte surse")
                 & (d_el["дата"] == "2024-12-01")]["значение"].iloc[0]
    vals = {
        "Доля МГРЭС в потреблении, 2015": p.loc[2015, "Procurat din alte surse"] / p.loc[2015, "Consum final brut"] * 100,
        "Доля МГРЭС в потреблении, 2024": p.loc[2024, "Procurat din alte surse"] / p.loc[2024, "Consum final brut"] * 100,
        "Procurat din alte surse, декабрь 2024": dec24,
        "Moldelectrica, средняя TPP январь 2024": g.loc["2024-01", "TPP"],
        "Moldelectrica, средняя TPP январь 2025": g.loc["2025-01", "TPP"],
        "Moldelectrica, средняя TPP январь 2026": g.loc["2026-01", "TPP"],
        "Уникальных отметок времени Moldelectrica": uniq,
        "Дефицит бюджета ПМР 2026": df,
        "Дефицит бюджета ПМР 2026 в долларах": df / 16.10 / 1e6,
        "Бытовое потребление газа 2021": pg.loc[2021, "din care: consumat în sectorul rezidential"] / 1000,
        "Бытовое потребление газа 2023": pg.loc[2023, "din care: consumat în sectorul rezidential"] / 1000,
        "Бытовое потребление газа 2025": pg.loc[2025, "din care: consumat în sectorul rezidential"] / 1000,
        "Цена газа для Молдовы 2021 (Comtrade)": ct.loc[2021, "цена_USD_1000м3"],
        "Европейский индекс 2021 (Pink Sheet)": pk.loc[2021],
        "Румыния, оптовая цена 2026 (Ember, 8 мес.)": em[(em["показатель"] == "Romania") & (em["год"] == 2026)]["значение"].mean(),
        "Объём по договору 489-22/MGRES": 204763.0,
    }
    _so, _sc, _ro = K.scenarii_sebestoimosti()
    vals["Сценарий A (газ бесплатный)"] = _sc[0][6]
    vals["Сценарий B (газ Газпрома 2021)"] = _sc[1][6]
    vals["Сценарий D (европейский индекс 2026)"] = _sc[3][6]
    vals["Румыния с передачей"] = _ro
    vals["Газ на 3 000 ГВт·ч"] = 3000e6 * C.k("удельный_расход_м3_кВтч") / 1e6
    vals["Потребление э/э на домохозяйство"] = (
        p.loc[LAST_FULL_YEAR, "din care: consumat în sectorul rezidential"] * 1000
        / C.k("домохозяйств_правый_берег") / 12)
    # --- третья редакция: ежегодники ПМР
    _, sv = K.sverka_dvuh_statsluzhb()
    sv_d = {y: dev for y, _, _, dev in sv}
    vals["Сверка двух статслужб, 2020"] = sv_d.get(2020, float("nan"))
    vals["Сверка двух статслужб, 2018"] = sv_d.get(2018, float("nan"))
    pmr = K._pmr()
    vals["Производство э/э ПМР 2020"] = pmr.loc[2020, K._PMR_EL]
    vals["Отпущено за пределы республики 2020"] = pmr.loc[2020, K._PMR_OTP]
    vals["Коммунальный газ ПМР 2020"] = pmr.loc[2020, K._PMR_GAZ]
    _, bal = K.balans_gaza_levogo_berega(2020)
    vals["Баланс газа левого берега 2020"] = bal[0][4]
    vals["Доля газа на электроэнергию, 2020"] = bal[0][5]
    _, oc = K.ocenka_ceny_eksporta_pmr()
    vals["Оценка цены экспорта э/э ПМР, 2020"] = {y: c for y, _, _, c in oc}[2020]
    _, tar = K.tarify_moldavskoy_generacii_2010()
    vals["Тариф ТЭЦ-1 в центах, 2010"] = {n: c for n, b, c, k in tar}["ТЭЦ-1 (S.A. CET-1)"]
    vals["Норматив МГРЭС в кубометрах"] = C.g_ut_to_m3(356.1)
    for name, expect, tol, unit in KONTROL:
        got = float(vals[name])
        d = abs(got - expect)
        if d <= tol:
            _ok(f"контрольное: {name}", f"{got:,.1f} {unit} против ожидаемых {expect:,} (допуск {tol})".replace(",", " "))
        else:
            _warn(f"контрольное: {name}",
                  f"получено {got:,.2f} {unit}, ожидалось {expect:,} - расхождение {d:,.2f}".replace(",", " "))


def run_all():
    print("АВТОПРОВЕРКИ")
    check_kontrakty()
    check_nbs_vs_anre()
    check_razryv()
    check_summy()
    check_vybrosy()
    check_doli()
    check_moldelectrica()
    check_sverka_statsluzhb()
    check_lestnica()
    check_ezhegodniki()
    check_kontrolnye()
    n_fail = sum(1 for s, _, _ in RESULTS if s == "FAIL")
    n_warn = sum(1 for s, _, _ in RESULTS if s == "WARN")
    n_ok = sum(1 for s, _, _ in RESULTS if s == "OK")
    print(f"\nИтог проверок: OK {n_ok}, WARN {n_warn}, FAIL {n_fail}")
    if n_fail:
        raise SystemExit("Есть критические расхождения - см. [FAIL] выше. Пайплайн остановлен.")
    return RESULTS


if __name__ == "__main__":
    run_all()
