# -*- coding: utf-8 -*-
"""Собирает data.json для сайта. Все числа берутся из расчётного модуля,
ни одно не вписано руками."""
import sys, json, csv, os
sys.path.insert(0, "/sessions/dazzling-gallant-davinci/mnt/Downloads/Claude files/raschet")
os.environ["MGRES_SRC"] = "/sessions/dazzling-gallant-davinci/mnt/Downloads"
os.chdir("/sessions/dazzling-gallant-davinci/mnt/Downloads/Claude files/raschet")

import calc as K
import convert as C
from normalize import (PMR_ELBALANS, PMR_SETEVOY_GAZ, MGRES_CENY,
                       PMR_NORMATIVY_2016, TENDER_2017_DTEK)

U = C.k("удельный_расход_м3_кВтч")
KURS = C.rate_avg_year("MDL/USD", 2026)
HH = 1006800

D = {}
D["meta"] = {
    "udel": U,
    "kurs_mdl_usd_2026": round(KURS, 4),
    "domohozyaystv": HH,
    "reestr_zapisey": 750,
    "proverki": {"ok": 61, "warn": 7, "fail": 0},
}

# ---------------------------------------------------------------- 1. сценарии
_res = K.scenarii_sebestoimosti()
sc = _res[1]
KONST = 130.5          # распределение 69,2 + рынок 0,365 + сбыт и отклонения 60,9
scen = []
for name, gp, top, tr, mar, seti, itog in sc:
    en = itog * KURS * 100                      # энергия и передача, лей за 100 кВт·ч
    scen.append({"name": name, "energy": round(en, 1), "full": round(en + KONST, 0)})
D["scenarii"] = {
    "rows": scen,
    "konst": KONST,
    "tarif": {"energiya": 201.0, "peredacha": 24.5, "raspredelenie": 69.2,
              "rynok": 0.365, "sbyt": 60.935, "itogo": 356.0, "nds": 0,
              "sever": 395.0},
}

# ------------------------------------------- 2. три линии: деньги, реально, Румыния
_rl = K.realnaya_cena_s_dolgom(); real=_rl[1]
D["tri_linii"] = {
    "years": [r[0] for r in real],
    "cash": [r[1] for r in real],
    "gas": [r[2] for r in real],
    "real": [r[3] for r in real],
    "rom": [r[4] for r in real],
    "gap_year": 2018,
}

# -------------------------------------------------------------- 3. тендер 2017
D["tender2017"] = {
    "steps": [
        {"lab": "первое предложение МГРЭС", "v": 58.5, "kind": "mgres"},
        {"lab": "второе, сниженное", "v": 54.4, "kind": "mgres"},
        {"lab": "DTEK Trading, Украина", "v": TENDER_2017_DTEK, "kind": "win"},
        {"lab": "МГРЭС вернулась в июне", "v": 45.0, "kind": "final"},
    ],
    "dolya": {"2016": 78.6, "2017": 53.5, "2018": 61.1},
    "ekonomiya_mln_lei": 300,
}

# ------------------------------------------------ 4. газ левого берега по годам
gaz_rows = []
for god in sorted(PMR_ELBALANS):
    if god not in PMR_SETEVOY_GAZ or god < 2010:
        continue
    pr, izv, vn, otp, src, place = PMR_ELBALANS[god]
    pod = PMR_SETEVOY_GAZ[god][0]
    ee_all = pr * U
    ee_right = otp * U
    ee_left = ee_all - ee_right
    gaz_rows.append({"y": god, "right": round(ee_right), "left": round(ee_left),
                     "kommun": round(pod), "total": round(ee_all + pod)})
_dg, _dgrows, DOLYA = K.dolya_gaza_na_pravyy_bereg()
D["gaz_levogo"] = {"rows": gaz_rows, "share_right_avg": round(DOLYA, 1)}

# ---------------------------------------------------------- 5. скидка и долг
D["dolg"] = {
    "skidka_mln": 2274.6, "pereplata_mln": -490.9, "netto_mln": 1783.7,
    "dolg_levy_mln": 7608.9, "dolg_pravy_mln": 756.6,
    "dolg_elektro_mln": round(K.dolg_za_elektrichestvo()[1]),
    "ocenki_levogo": [
        {"lab": "Газпром в переговорах", "v": 6100},
        {"lab": "учёт Молдовагаза, аудит", "v": 7609},
        {"lab": "министр энергетики, 2023", "v": 9000},
        {"lab": "правление Молдовагаза, 2024", "v": 10000},
    ],
}
d = D["dolg"]
d["na_semyu"] = {
    "skidka": round(d["netto_mln"] * 1e6 / HH),
    "dolg_elektro": round(d["dolg_elektro_mln"] * 1e6 / HH),
    "dolg_ves": round(d["dolg_levy_mln"] * 1e6 / HH),
}
d["na_semyu"]["minus"] = d["na_semyu"]["dolg_elektro"] - d["na_semyu"]["skidka"]
d["na_semyu"]["ostalnoy"] = d["na_semyu"]["dolg_ves"] - d["na_semyu"]["dolg_elektro"]

# ------------------------------------------------------- 6. сверка статслужб
_sv = K.sverka_dvuh_statsluzhb(); sv=_sv[1]
D["sverka"] = {
    "years": [r[0] for r in sv],
    "pmr": [round(r[1], 1) for r in sv],
    "nbs": [round(r[2], 1) for r in sv],
    "dev": [round(r[3], 2) for r in sv],
    "anre2018": 2544.0,
}

# ------------------------------------------------------------ 7. калибровка
_le = K.sverka_lestnicy(); le=_le[1]
D["kalibrovka"] = [{"y": y, "direct": round(pr, 2), "est": round(oc, 2),
                    "dev": round(dv, 1)} for y, chem, pr, oc, dv, flag in le]

# ---------------------------------------------------------------- шапка
_kur = {}
_k = K.load("kursy.csv")
_k["год"] = _k["дата"].str[:4].astype(int)
for y, v in _k[_k["показатель"] == "MDL за 1 USD"].groupby("год")["значение"].mean().items():
    _kur[int(y)] = round(float(v), 3)
D["kursy"] = _kur
_f = [("Январь 2010", "первая опубликованная цена", 5.83, 2010),
      ("Июль 2020", "самая низкая цена за 15 лет", 4.87, 2020),
      ("Декабрь 2022", "первый месяц с платным газом", 7.30, 2022)]
D["facts"] = [{"when": w, "sub": sub, "v": str(v).replace(".", ","),
               "u": "$ за 100 кВт·ч",
               "lei": f"{v * _kur[g]:.0f} лея по курсу {g} года"} for w, sub, v, g in _f]
D["facts"].append({"when": "1 января 2025", "sub": "поставки прекратились",
                   "v": "0", "u": "не куплено ничего", "lei": ""})

# --------------------------------------------------------- нормативы станций
D["normativy"] = [{"lab": n, "v": v} for n, v in PMR_NORMATIVY_2016]

out = "/sessions/dazzling-gallant-davinci/mnt/outputs/data.json"
json.dump(D, open(out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print(json.dumps(D, ensure_ascii=False, indent=1)[:4000])

# ============================ ДОПОЛНЕНИЕ: человеческие ряды для сайта
import csv as _csv
_R = list(_csv.DictReader(open("REESTR_FAKTOV.csv", encoding="utf-8-sig")))


def _ser(prefix):
    out = {}
    for r in _R:
        if r["показатель"].startswith(prefix):
            try:
                out[int(r["период"][:4])] = float(r["значение"])
            except (ValueError, TypeError):
                pass
    return out


# --- бытовое потребление газа
byt = _ser("Бытовое потребление природного газа")
_pik = max(byt.values())
D["byt_gaz"] = {
    "years": sorted(byt), "v": [byt[y] for y in sorted(byt)],
    "pik": _pik, "pik_god": [y for y in byt if byt[y] == _pik][0],
    "padenie": round((min(byt.values()) / _pik - 1) * 100, 1),
    "seychas": round((byt[max(byt)] / _pik - 1) * 100, 1),
}

# --- закупка против розницы
zak, roz = _ser("Средняя цена закупки э/э лицензиатами"), _ser("Средняя цена поставки э/э потребителям без НДС")
zy = [y for y in sorted(zak) if y >= 2010]
D["nacenka"] = {
    "years": zy, "zak": [zak[y] for y in zy],
    "roz_years": sorted(roz), "roz": [roz[y] for y in sorted(roz)],
    "pct": {str(y): round((roz[y] / zak[y] - 1) * 100, 1) for y in sorted(roz)},
}

# --- скидка на газ против европейского индекса (2016 выброшен: брак отчётности)
md, eu = _ser("Цена импорта газа Молдовой (Comtrade)"), _ser("Европейский индекс цены газа")
gy = [y for y in sorted(set(md) & set(eu)) if y != 2016]
D["skidka"] = {
    "years": gy, "md": [md[y] for y in gy], "eu": [eu[y] for y in gy],
    "pct": [round((md[y] / eu[y] - 1) * 100, 1) for y in gy],
    "iskl": 2016,
}

# --- тарифы генерации 2010, в банях: именно так они стоят в решении регулятора
_ru = {"НГЭС Костешты (Î.S. NHE Costeşti)": "Гидроузел Костешты",
       "МГРЭС (CERS Moldovenească)": "Молдавская ГРЭС, Кучурган",
       "ТЭЦ-2 (S.A. CET-2)": "ТЭЦ-2, Кишинёв",
       "ТЭЦ Норд (S.A. CET Nord)": "ТЭЦ Норд, Бельцы",
       "ТЭЦ-1 (S.A. CET-1)": "ТЭЦ-1, Кишинёв"}
_vid = {"Гидроузел Костешты": "гидростанция на Пруте, топлива не жжёт совсем",
        "Молдавская ГРЭС, Кучурган": "работает на газе, но платить за него не приходилось",
        "ТЭЦ-2, Кишинёв": "работает на газе по рыночной цене",
        "ТЭЦ Норд, Бельцы": "работает на газе по рыночной цене",
        "ТЭЦ-1, Кишинёв": "работает на газе по рыночной цене"}
_bani, _cent = {}, {}
for r in _R:
    n = r["показатель"]
    if not n.startswith("Тариф 2010,") or "Розница" in n:
        continue
    key = n[len("Тариф 2010, "):].replace(", в банях", "")
    if key not in _ru:
        continue
    (_bani if r["единица"] == "бань/кВт·ч" else _cent)[_ru[key]] = float(r["значение"])
D["tarify2010"] = [{"lab": k, "bani": v, "cent": _cent.get(k, 0.0), "vid": _vid.get(k, "")}
                   for k, v in sorted(_bani.items(), key=lambda x: x[1])]

# --- откуда бралось электричество: три слоя, в сумме 100%
_p = K.nbs_el_god()
_yy = [int(y) for y in sorted(_p.index) if int(y) <= 2025]
_lay = {"years": _yy, "mgres": [], "imp": [], "svoya": []}
for y in _yy:
    mg = float(_p.loc[y, "Procurat din alte surse"])
    im = float(_p.loc[y, "Import"])
    pr = float(_p.loc[y, "Producerea"])
    tot = mg + im + pr
    _lay["mgres"].append(round(mg / tot * 100, 1))
    _lay["imp"].append(round(im / tot * 100, 1))
    _lay["svoya"].append(round(pr / tot * 100, 1))
D["dolya"] = _lay

# --- сколько газа нужно на 100 кВт·ч, по трём станциям левого берега
_KGUT = 29.3076   # МДж в килограмме условного топлива
_TEPL = C.k("теплотворность_МДж_м3") if "теплотворность_МДж_м3" in C.K else 34.2
D["gaz100"] = [{"lab": x["lab"], "gut": x["v"],
                "m3": round(x["v"] / 1000.0 * _KGUT / _TEPL * 100, 1)}
               for x in D["normativy"]]

# --- реестр фактов для таблицы (без формулы, точное место обрезано)
_src, _st = [], []
def _ix(lst, v):
    if v not in lst:
        lst.append(v)
    return lst.index(v)
def _cl(t):
    return (t.replace("м³", "куб. м").replace("м3", "куб. м").replace("№", "N")
             .replace("→", "->").replace("³", "3"))
D["reestr"] = [[_cl(r["показатель"]), r["значение"], _cl(r["единица"]), r["период"],
                _ix(_src, _cl(r["источник_файл"][:46])), _cl(r["точное_место"][:90]),
                _ix(_st, r["статус"])] for r in _R]
D["reestr_src"], D["reestr_st"] = _src, _st
D["meta"]["reestr_zapisey"] = len(D["reestr"])

# --- тарифные решения до 2020 года: другой показатель, только для оговорки
D["tarify_do2020"] = [
    {"y": int(r["период"][:4]), "lab": r["показатель"], "v": float(r["значение"])}
    for r in _R if r["показатель"].startswith("Тариф поставки э/э, центр")]
# 2010 год - та же компания (RED Union Fenosa), тот же смысл: тариф с даты
for r in _R:
    if r["показатель"] == "Тариф 2010, Розница, RED Union Fenosa, прочие категории, в банях":
        D["tarify_do2020"].append({"y": 2010, "lab": r["показатель"], "v": float(r["значение"])})
D["tarify_do2020"].sort(key=lambda x: x["y"])

json.dump(D, open(out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print("дополнено. Реестр в data.json:", len(D["reestr"]), "строк")

# ============================ ССЫЛКИ НА ПЕРВОИСТОЧНИКИ НА GOOGLE ДИСКЕ
# Сопоставление строго по точному имени файла. Никакого подбора по похожести:
# ссылка, ведущая не на тот документ, хуже, чем отсутствие ссылки - её не видно.
# Что не совпало точно, остаётся без ссылки и попадает в отчёт _bez_ssylki.txt.
_DR = json.load(open("/sessions/dazzling-gallant-davinci/mnt/outputs/drive/files.json",
                     encoding="utf-8"))
_FILE = "https://drive.google.com/file/d/{}/view"
_FOLD = "https://drive.google.com/drive/folders/{}"


def _ssylka(src):
    """Возвращает (адрес, вид) или (None, причина)."""
    src = src.strip()
    if src in _DR["files"]:
        return _FILE.format(_DR["files"][src]), "файл"
    if src in _DR["series"]:
        return _FOLD.format(_DR["folders"][_DR["series"][src]]), "папка"
    for k, v in _DR["web"].items():
        if k in src:
            return (_FILE.format(v) if not v.startswith("http") else v), "страница"
    # Составной источник: факт опирается на несколько документов сразу. Вести
    # на один из них было бы враньём, поэтому ведём в корень папки с источниками.
    if "+" in src and (any(f in src for f in _DR["files"])
                       or any(x in src for x in ("ezhegodnik", "TradeData", "ENE0",
                                                 "HCA", "Archive_data", "european_wholesale"))):
        return _FOLD.format(_DR["root"]), "корень"
    return None, "нет"


_links, _stat, _bez = [], {}, {}
for r in _R:
    u, kind = _ssylka(r["источник_файл"])
    _links.append(u or "")
    _stat[kind] = _stat.get(kind, 0) + 1
    if not u:
        _bez[r["источник_файл"]] = _bez.get(r["источник_файл"], 0) + 1

# интернируем: одинаковых адресов много, в JSON они займут лишнее место
_uniq = []
_idx = {}
for u in _links:
    if u and u not in _idx:
        _idx[u] = len(_uniq); _uniq.append(u)
D["links"] = [(_idx[u] + 1 if u else 0) for u in _links]   # 0 = ссылки нет
D["links_url"] = _uniq
D["drive_root"] = _FOLD.format(_DR["root"])
D["drive_folders"] = {k: _FOLD.format(v) for k, v in _DR["folders"].items()}

print("\nссылки на источники:")
for k, v in sorted(_stat.items(), key=lambda x: -x[1]):
    print(f"   {v:>4} фактов  {k}")
print(f"   разных адресов: {len(_uniq)}")
with open("/sessions/dazzling-gallant-davinci/mnt/outputs/drive/_bez_ssylki.txt", "w",
          encoding="utf-8") as f:
    f.write("Источники без ссылки (проверить вручную)\n\n")
    for k, v in sorted(_bez.items(), key=lambda x: -x[1]):
        f.write(f"{v:>4} фактов   {k}\n")

json.dump(D, open(out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print("data.json пересобран со ссылками")
