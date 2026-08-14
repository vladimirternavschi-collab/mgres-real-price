# -*- coding: utf-8 -*-
"""Весь пайплайн одной командой.

    python run_all.py

1. normalize.py - раскладывает исходники в data/*.csv
2. calc.py      - считает все показатели
3. checks.py    - автопроверки
4. пишет REESTR_FAKTOV.csv и RESULTS.md
"""
import csv
import sys
from pathlib import Path

import pandas as pd

import normalize
import convert as C
import calc as K
import checks
from config import DATA, OUT, TODAY, LAST_FULL_YEAR

def nf(x, d=0):
    """Число с пробелом как разделителем тысяч."""
    return f"{x:,.{d}f}".replace(",", "\u00a0")


REESTR_COLS = ["id", "показатель", "значение", "единица", "период", "источник_файл",
               "точное_место", "формула", "статус", "дата_расчёта"]


def main():
    print("=" * 78)
    print("РАСЧЁТНЫЙ МОДУЛЬ: МГРЭС, ГАЗ, РЕАЛЬНАЯ ЦЕНА КИЛОВАТТ-ЧАСА")
    print("=" * 78)

    # ---------------------------------------------------------------- ЭТАП 1
    # Раскладка исходников нужна только тому, у кого есть первичные файлы:
    # годовые отчёты, ежегодники, выгрузки. Они весят больше сотни мегабайт и
    # в репозиторий не кладутся, зато результат их разбора лежит в data/*.csv.
    # Если исходников рядом нет, этап пропускается и расчёт идёт по готовым
    # таблицам. Числа при этом получаются те же самые, до последнего знака.
    from config import F
    if F["nbs_el"].exists():
        normalize.main()
    else:
        print("\nЭТАП 1. Первичные файлы не найдены, раскладка пропущена.")
        print("        Считаю по готовым таблицам из data/ (%d шт)."
              % len(list(DATA.glob("*.csv"))))
        print("        Чтобы пересобрать их с нуля, скачайте исходники")
        print("        и укажите путь: MGRES_SRC=/путь/к/папке")

    # ---------------------------------------------------------------- ЭТАП 2
    print("\nРАСЧЁТЫ")
    facts = []
    facts += K.dolya_mgres()
    gaz_out, gaz_rows, kum, kum_skidka, kum_pereplata = K.cena_gaza_sravnenie()
    facts += gaz_out
    facts += K.gaz_na_elektro()
    # вилка удельного расхода
    for u in C.K["удельный_расход_вилка"]["v"]:
        for f in K.gaz_na_elektro(2024, udel=u):
            f["показатель"] += f" [удельный расход {u}]"
            facts.append(f)
    real_out, real_rows = K.realnaya_cena_tablica()
    facts += real_out
    # чувствительность: реальная цена по последней документально зафиксированной
    # контрактной цене электроэнергии (0,073 $/кВт·ч, декабрь 2022)
    real_out073, real_rows073 = K.realnaya_cena_tablica(cena_ee=0.073)
    for f in real_out073:
        f["показатель"] += " [цена э/э по договору 489-22: 0,073]"
        facts.append(f)

    scen_out, scen_rows, ro_itog = K.scenarii_sebestoimosti()
    facts += scen_out
    facts += K.godovoy_schet(scen_rows, ro_itog, 3000.0)
    # вилка удельного расхода в сценариях
    scen_lo = K.scenarii_sebestoimosti(udel=0.27)[1]
    scen_hi = K.scenarii_sebestoimosti(udel=0.36)[1]
    for i, (lo, hi) in enumerate(zip(scen_lo, scen_hi)):
        if lo[1] is None:
            continue
        facts.append(K.fact(
            f"Сценарий себестоимости, вилка удельного расхода: {lo[0]}",
            f"{lo[6]:.4f}..{hi[6]:.4f}", "USD/кВт·ч", "2026",
            "расчёт", "-", "удельный расход 0,27 и 0,36 м³/кВт·ч", "допущение"))
    # модернизация до ПГУ
    scen_pgu = K.scenarii_sebestoimosti(udel=C.k("удельный_расход_ПГУ"))[1]
    for r in scen_pgu:
        if r[1] is None:
            continue
        facts.append(K.fact(
            f"Сценарий с модернизацией до ПГУ (0,17 м³/кВт·ч): {r[0]}",
            round(r[6], 4), "USD/кВт·ч", "2026", "расчёт", "-",
            f"топливо {r[2]:.4f} + транспорт {r[3]:.4f} + маржа {r[4]} + сети {r[5]:.4f}",
            "допущение"))

    def_out, dohody, rashody, deficit = K.deficit_pmr()
    facts += def_out
    marzha_out, marzha_rows = K.marzha_iz_deficita(deficit / C.k("курс_рубля_ПМР"))
    facts += marzha_out
    vyr_out, vyr = K.vyruchka_mgres(2024, 10)
    facts += vyr_out

    plat_scen = [("Как было при бесплатном газе", scen_rows[0][6]),
                 ("Румыния, как сегодня", ro_itog),
                 ("МГРЭС при европейском газе 2026", scen_rows[3][6]),
                 ("МГРЭС при цене с премией 700 $", scen_rows[4][6])]
    plat_out, plat_rows, kwh_mes = K.platyozhka(plat_scen)
    facts += plat_out

    ml_out, ml_g = K.moldelectrica_agregaty()
    facts += ml_out
    tr_out, tr_g = K.tranzitnyy_profil()
    facts += tr_out
    gaz_nas_out, gaz_nas = K.gaz_naseleniyu()
    facts += gaz_nas_out
    facts += K.prochee()
    facts += K.kontrakty()

    # ------------------------------------------------- третья редакция: ПМР
    facts += K.pmr_ryady()
    sv_out, sv_rows = K.sverka_dvuh_statsluzhb()
    facts += sv_out
    oc_out, oc_rows = K.ocenka_ceny_eksporta_pmr()
    facts += oc_out
    bal_out, bal_rows = K.balans_gaza_levogo_berega()
    facts += bal_out
    tar_out, tar_rows = K.tarify_moldavskoy_generacii_2010()
    facts += tar_out
    facts += K.normativy_treh_stanciy()
    lest_out, lest_rows = K.cenovaya_lestnica()
    facts += lest_out
    sl_out, sl_rows = K.sverka_lestnicy()
    facts += sl_out
    facts += K.vyruchka_mgres_2024()
    dg_out, dg_rows, _dolya = K.dolya_gaza_na_pravyy_bereg()
    facts += dg_out
    de_out, _chast, _d2 = K.dolg_za_elektrichestvo()
    facts += de_out
    sr_out, sr_rows = K.srednegodovaya_cena_mgres()
    facts += sr_out
    rl_out, rl_rows = K.realnaya_cena_s_dolgom()
    facts += rl_out

    # коэффициенты конвертации - тоже в реестр
    for name, v, unit, status, src in C.spisok_koefficientov():
        facts.append(K.fact(f"Коэффициент: {name}", v, unit, "-", "convert.py",
                            "модуль конвертаций", src, status))
    # данные ANRE и HCA - в реестр как есть
    for f in [K.load("anre_otchety.csv"), K.load("anre_hca.csv")]:
        for _, r in f.iterrows():
            facts.append(K.fact(f"{r['показатель']} ({r['дата'][:4]})", r["значение"],
                                r["единица"], r["дата"][:4], r["источник_файл"],
                                r["флаг"] if isinstance(r["флаг"], str) else "-",
                                "", "из_источника"))

    # ---------------------------------------------------------------- ЭТАП 3
    print()
    checks.run_all()

    # ---------------------------------------------------------------- РЕЕСТР
    p = OUT / "REESTR_FAKTOV.csv"
    with open(p, "w", newline="", encoding="utf-8-sig") as fh:
        w = csv.DictWriter(fh, fieldnames=REESTR_COLS, extrasaction="ignore")
        w.writeheader()
        for i, f in enumerate(facts, 1):
            f["id"] = f"F{i:04d}"
            w.writerow(f)
    print(f"\nРеестр фактов: {p} - {len(facts)} записей")

    # ---------------------------------------------------------------- RESULTS
    with open(OUT / "RESULTS.md", "w", encoding="utf-8") as fh:
        wr = fh.write
        wr(f"# Результаты расчётного модуля\n\nДата расчёта: {TODAY}\n\n")

        wr("## Доля МГРЭС в потреблении Молдовы\n\n")
        wr("| Год | МГРЭС, ГВт·ч | Потребление, ГВт·ч | Доля |\n|---|---|---|---|\n")
        pe = K.nbs_el_god()
        for y in sorted(pe.index):
            mg, cs = pe.loc[y, "Procurat din alte surse"], pe.loc[y, "Consum final brut"]
            note = " *" if y > LAST_FULL_YEAR else ""
            wr(f"| {y}{note} | {nf(mg/1000)} | {nf(cs/1000)} | {mg/cs*100:.1f}% |\n")
        wr("\n\\* 2026 - неполный год.\n\n")

        wr("## Цена газа для Молдовы против европейского индекса\n\n")
        wr("| Год | Молдова (Comtrade), $/1000 м³ | Европа (World Bank), $/1000 м³ | Разница | Объём, млн м³ | Экономия/переплата, млн $ | Флаг |\n")
        wr("|---|---|---|---|---|---|---|\n")
        for y, mine, euro, du, vol, dt, fl in gaz_rows:
            wr(f"| {y} | {nf(mine,1)} | {nf(euro,1)} | {du/euro*100:+.1f}% | {nf(vol)} | {nf(dt,1)} | {fl} |\n")
        wr(f"\n- Экономия за годы скидки: **{nf(kum_skidka)} млн $**\n")
        wr(f"- Переплата после разрыва: **{nf(kum_pereplata)} млн $**\n")
        wr(f"- Нетто по всем годам с данными: **{nf(kum)} млн $**\n\n")

        wr("## Реальная цена кВт·ч от МГРЭС\n\n")
        wr("| Год | Режим | Объём, ГВт·ч | Цена э/э, $/кВт·ч | Деньгами, млн $ | Газ, млн м³ | Цена газа, $/1000 м³ | Долгом, млн $ | Итог, $/кВт·ч |\n")
        wr("|---|---|---|---|---|---|---|---|---|\n")
        for r in real_rows:
            wr(f"| {r['год']} | {r['режим']} | {nf(r['объём_ГВтч'])} | {r['цена_ээ']:.4f} | "
               f"{nf(r['деньги_млн'])} | {nf(r['газ_млн_м3'])} | {nf(r['цена_газа'])} | "
               f"{nf(r['долг_млн'])} | **{r['итог_USD_кВтч']:.4f}** |\n")
        wr("\n")

        wr("## Сценарии себестоимости кВт·ч\n\n")
        wr("| Сценарий | Топливо | Транспорт газа | Станция и маржа | Сети | Итого, $/кВт·ч | Годовой счёт за 3 000 ГВт·ч, млн $ |\n")
        wr("|---|---|---|---|---|---|---|\n")
        for r in scen_rows:
            if r[1] is None:
                wr(f"| **{r[0]}** | | | | {r[5]:.4f} | **{r[6]:.4f}** | {nf(r[6]*3e9/1e6)} |\n")
            else:
                wr(f"| {r[0]} | {r[2]:.4f} | {r[3]:.4f} | {r[4]:.3f} | {r[5]:.4f} | **{r[6]:.4f}** | {nf(r[6]*3e9/1e6)} |\n")
        wr("\n")

        wr("## Дефицит ПМР и маржа\n\n")
        wr(f"- Доходы 2026: {nf(dohody)} рублей ПМР\n")
        wr(f"- Расходы 2026: {nf(rashody)} рублей ПМР\n")
        wr(f"- Дефицит: **{nf(deficit)} рублей ПМР** = **{deficit/16.10/1e6:.1f} млн $** по курсу 16,10\n\n")
        wr("| Объём поставки, ГВт·ч | Маржа, $/кВт·ч |\n|---|---|\n")
        for g, m in marzha_rows:
            wr(f"| {nf(g)} | {m:.4f} |\n")
        if vyr:
            wr(f"\nСтоимость э/э МГРЭС за январь-октябрь 2024: **{vyr/1e6:.1f} млн $** "
               f"(при цене-прокси ANRE; см. оговорку в FAKTURA)\n\n")

        wr("## Платёжка домохозяйства\n\n")
        wr(f"Бытовое потребление э/э {LAST_FULL_YEAR}: {kwh_mes:.0f} кВт·ч в месяц на домохозяйство "
           f"(при 1,1 млн домохозяйств).\n\n")
        wr("| Сценарий | $/кВт·ч | Лей в месяц |\n|---|---|---|\n")
        for n, u, l in plat_rows:
            wr(f"| {n} | {u:.4f} | **{l:.0f}** |\n")
        wr("\nЭнергия и передача, без распределения, сбыта и НДС.\n\n")

        wr("## Бытовое потребление газа\n\n| Год | млн м³ |\n|---|---|\n")
        for y, v in gaz_nas.items():
            if y <= LAST_FULL_YEAR:
                wr(f"| {y} | {nf(v)} |\n")
        wr("\n")

        wr("## Moldelectrica: месячные средние, МВт\n\n")
        wr(ml_g.to_markdown())
        wr("\n\nЗнак: MD-RO плюс = импорт из Румынии в Молдову; MD-UA минус = экспорт из Молдовы в Украину.\n\n")

        wr("## Сверка двух статистических служб\n\n")
        wr("Строка «Отпущено электроэнергии за пределы республики» из статежегодника ПМР "
           "против строки `Procurat din alte surse` из НБС Молдовы.\n\n")
        wr("| Год | Госстат ПМР отпустил, млн кВт·ч | НБС Молдовы закупила, млн кВт·ч | Расхождение |\n")
        wr("|---|---|---|---|\n")
        for y, pmr_v, md_v, dev in sv_rows:
            wr(f"| {y} | {nf(pmr_v,1)} | {nf(md_v,1)} | {dev:+.2f}% |\n")
        wr("\n")

        wr("## Ценовая лестница МГРЭС\n\n")
        wr("Три разных типа значений. **Смешивать нельзя:** `контракт` - прямая цена из договора "
           "или решения регулятора; `оценка` - производная от таможенной категории ПМР, не цена "
           "контракта; `blended` - средняя цена закупки или импорта по Молдове, где МГРЭС лишь доля.\n\n")
        wr("| Год | Тип | Цента/кВт·ч | Источник |\n|---|---|---|---|\n")
        for god, tip, cent, ist in lest_rows:
            wr(f"| {god} | {tip} | **{cent:.2f}** | {ist} |\n")
        wr("\n### Сверка оценки с прямой ценой\n\n")
        wr("| Год | Против чего | Прямая цена | Оценка по ежегоднику | Расхождение | Флаг |\n")
        wr("|---|---|---|---|---|---|\n")
        for y, чем, pr, oc_v, dev, flag in sl_rows:
            wr(f"| {y} | {чем} | {pr:.2f} | {oc_v:.2f} | {dev:+.1f}% | {flag or 'в пределах 15%'} |\n")
        wr("\n")

        wr("## Баланс газа левого берега\n\n")
        wr("Удельный расход - **норматив** 356,1 г у.т./кВт·ч (0,3047 м³/кВт·ч), а не измеренная "
           "величина. Таблицы фактического расхода топлива электростанциями в ежегоднике нет.\n\n")
        wr("| Год | Производство э/э, млн кВт·ч | Газ на э/э, млн м³ | Коммунальная сеть, млн м³ | Итого, млн м³ | Доля на э/э |\n")
        wr("|---|---|---|---|---|---|\n")
        for y, el, ge, gk, it, dl in bal_rows:
            wr(f"| {y} | {nf(el,1)} | {nf(ge)} | {nf(gk,1)} | **{nf(it)}** | {dl:.1f}% |\n")
        wr("\n")

        wr("## Тарифы молдавской генерации, январь 2010\n\n")
        wr(f"Курс, применённый самим регулятором в решении: **12,3 лея за доллар** "
           f"(в предыдущем тарифе - 10,7).\n\n")
        wr("| Источник | Бань/кВт·ч | Цента/кВт·ч |\n|---|---|---|\n")
        for name, bani, cent, kind in tar_rows:
            mark = "**" if "МГРЭС" in name else ""
            wr(f"| {mark}{name}{mark} | {bani:.2f} | {mark}{cent:.2f}{mark} |\n")
        wr("\n")

        wr("## Экспорт и импорт топливно-энергетических товаров ПМР\n\n")
        wr("| Год | Экспорт ТЭ, млн $ | Отпуск э/э, млн кВт·ч | Оценка цены, цента/кВт·ч |\n")
        wr("|---|---|---|---|\n")
        for y, ex, otp, cent in oc_rows:
            wr(f"| {y} | {nf(ex,1)} | {nf(otp,1)} | {cent:.2f} |\n")
        wr("\n**Статус: оценка, не контрактная цена.**\n\n")

        wr("## Автопроверки\n\n| Статус | Проверка | Комментарий |\n|---|---|---|\n")
        for s, n, m in checks.RESULTS:
            wr(f"| {s} | {n} | {m} |\n")
    print(f"Сводка результатов: {OUT / 'RESULTS.md'}")


if __name__ == "__main__":
    main()
