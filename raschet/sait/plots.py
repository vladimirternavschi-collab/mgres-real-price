# -*- coding: utf-8 -*-
"""Статические SVG для <noscript>. Геометрия один в один с JS в index.html."""
import json

C = dict(amber="#c98200", amberLit="#edb04e", teal="#0da18b", violet="#b063d4",
         ink="#edf0f8", ink2="#aaafbe", ink3="#83899b", line="#303544", bg="#111628")


def _open(w, h, label):
    # Только aria-label, без <title>. Браузер рисует по <title> свою жёлтую
    # подсказку поверх нашей, а читалкам достаточно aria-label.
    return f'<svg viewBox="0 0 {w} {h}" role="img" aria-label="{label}">'



def _grid(m, iw, ticks, Y, fmt=str):
    s = '<g class="grid">'
    for t in ticks:
        s += f'<line x1="{m["l"]}" x2="{m["l"]+iw}" y1="{Y(t):.1f}" y2="{Y(t):.1f}"/>'
        s += (f'<text x="{m["l"]-10}" y="{Y(t)+4:.1f}" text-anchor="end" fill="{C["ink3"]}"'
              f' font-size="13">{fmt(t)}</text>')
    return s + "</g>"


def _txt(x, y, t, fill, size=13, weight=500, anchor="start"):
    return (f'<text x="{x:.1f}" y="{y:.1f}" text-anchor="{anchor}" fill="{fill}"'
            f' font-size="{size}" font-weight="{weight}">{t}</text>')


def _path(pts, stroke, width=2.6, dash=None):
    d = " ".join(("M" if i == 0 else "L") + f"{p[0]:.1f} {p[1]:.1f}" for i, p in enumerate(pts))
    da = f' stroke-dasharray="{dash}"' if dash else ""
    return (f'<path d="{d}" fill="none" stroke="{stroke}" stroke-width="{width}"'
            f' stroke-linejoin="round" stroke-linecap="round"{da}/>')


# ------------------------------------------------------------------ 1. три линии
def real_plot(D):
    """Шкала обрезана на 16 центах: 2022 год выносится за верх с явной подписью.
    Иначе пик расплющивает 2015-2021, а главное в графике именно спокойные годы."""
    T = D["tri_linii"]
    w, h, m = 880, 440, dict(t=44, r=168, b=52, l=56)
    iw, ih = w - m["l"] - m["r"], h - m["t"] - m["b"]
    y0, y1, HI = 2015, 2022, 16.0
    X = lambda y: m["l"] + (y - y0) / (y1 - y0) * iw
    Y = lambda v: m["t"] + (1 - min(v, HI) / HI) * ih
    s = _open(w, h, "График: цена киловатт-часа от Молдавской ГРЭС. Нижняя линия - что платили "
                    "деньгами, верхняя - сколько стоило вместе с газом, записанным в долг. "
                    "Шкала обрезана, значение 2022 года вынесено подписью")
    s += _grid(m, iw, [0, 5, 10, 15], Y)
    s += _txt(m["l"], m["t"] - 18, "центов за киловатт-час", C["ink3"], 12.5, 500)
    segs, cur = [], []
    for i, y in enumerate(T["years"]):
        if cur and y - T["years"][i - 1] > 1:
            segs.append(cur); cur = []
        cur.append(i)
    segs.append(cur)
    for seg in segs:
        if len(seg) < 2:
            continue
        ar = [(X(T["years"][i]), Y(T["real"][i])) for i in seg]
        ca = [(X(T["years"][i]), Y(T["cash"][i])) for i in seg]
        poly = " ".join(f"{p[0]:.1f},{p[1]:.1f}" for p in ar + ca[::-1])
        s += f'<polygon points="{poly}" fill="{C["amber"]}" opacity=".17"/>'
    for seg in segs:
        if len(seg) > 1:
            s += _path([(X(T["years"][i]), Y(T["rom"][i])) for i in seg], C["violet"], 1.6, "5 5")
    for seg in segs:
        if len(seg) > 1:
            s += _path([(X(T["years"][i]), Y(T["cash"][i])) for i in seg], C["teal"], 3.0)
            s += _path([(X(T["years"][i]), Y(T["real"][i])) for i in seg], C["amber"], 3.4)
    for i, y in enumerate(T["years"]):
        rv, cv = T["real"][i], T["cash"][i]
        ax, an = (X(y) + 9, "start") if i == 0 else (X(y), "middle")
        if rv <= HI:
            s += (f'<circle cx="{X(y):.1f}" cy="{Y(rv):.1f}" r="4.6" fill="{C["amber"]}"'
                  f' stroke="{C["bg"]}" stroke-width="1.8"/>')
            s += _txt(ax, Y(rv) - 11, str(rv).replace(".", ","), C["amberLit"], 13, 800, an)
        s += (f'<circle cx="{X(y):.1f}" cy="{Y(cv):.1f}" r="4.2" fill="{C["teal"]}"'
              f' stroke="{C["bg"]}" stroke-width="1.8"/>')
        s += _txt(ax, Y(cv) + 20, str(cv).replace(".", ","), C["teal"], 12.5, 700, an)
        s += _txt(X(y), h - 22, str(y), C["ink3"], 13, 500, "middle")
    gx = X(2018)
    s += (f'<line x1="{gx:.1f}" x2="{gx:.1f}" y1="{m["t"]}" y2="{m["t"]+ih}"'
          f' stroke="{C["line"]}" stroke-width="1" stroke-dasharray="3 5"/>')
    s += _txt(gx, h - 38, "нет данных", C["ink3"], 11, 600, "middle")
    i16 = T["years"].index(2016)
    s += _txt(X(2016.4), Y((T["real"][i16] + T["cash"][i16]) / 2) + 4,
              "это уходило в долг", C["amberLit"], 13.5, 800, "middle")
    over = [i for i, v in enumerate(T["real"]) if v > HI]
    for i in over:
        y = T["years"][i]
        s += (f'<line x1="{X(y):.1f}" x2="{X(y):.1f}" y1="{m["t"]+4}" y2="{m["t"]-4}"'
              f' stroke="{C["amber"]}" stroke-width="3"/>')
        s += _txt(X(y), m["t"] - 12, str(T["real"][i]).replace(".", ","), C["amberLit"], 15, 800, "middle")
        s += _txt(X(y), m["t"] - 28, "за пределами шкалы", C["ink3"], 11, 600, "middle")
    xr = m["l"] + iw + 16
    s += _txt(xr, Y(14.2), "реальная цена", C["amberLit"], 14, 800)
    s += _txt(xr, Y(14.2) + 17, "вместе с газом в долг", C["ink2"], 12.5, 500)
    s += _txt(xr, Y(11.4), "Румыния, биржа", C["violet"], 12.5, 700)
    s += _txt(xr, Y(T["cash"][-1]) + 5, "платили деньгами", C["teal"], 14, 800)
    return s + "</svg>"


# ------------------------------------------------------------------ 2. тендер
def tender_plot(D):
    S = D["tender2017"]["steps"]
    w, h, m = 880, 300, dict(t=26, r=150, b=34, l=54)
    iw, ih = w - m["l"] - m["r"], h - m["t"] - m["b"]
    hi = 62.0
    X = lambda v: m["l"] + v / hi * iw
    bh, gap = 34, 22
    s = _open(w, h, "График: конкурс 2017 года. Станция просила 58,5 доллара, "
                    "проиграла украинской компании с 50,2 и вернулась с ценой 45,0")
    for i, st in enumerate(S):
        y = m["t"] + i * (bh + gap)
        col = C["amber"] if st["kind"] == "mgres" else (C["violet"] if st["kind"] == "win" else C["teal"])
        s += (f'<rect x="{m["l"]}" y="{y}" width="{X(st["v"])-m["l"]:.1f}" height="{bh}"'
              f' rx="4" fill="{col}" opacity="{.55 if st["kind"]=="mgres" else 1}"/>')
        s += _txt(X(st["v"]) + 10, y + bh / 2 + 5,
                  f'{str(st["v"]).replace(".", ",")} $', C["ink"], 15, 800)
        tcol = C["ink"] if st["kind"] == "mgres" else "#0b0f1c"
        s += _txt(m["l"] + 12, y + bh / 2 + 5, st["lab"], tcol, 13.5, 700)
    s += _txt(m["l"], h - 10, "долларов за мегаватт-час", C["ink3"], 12.5, 500)
    return s + "</svg>"


# ------------------------------------------------------------------ 3. газ ПМР
def gaz_plot(D):
    R = D["gaz_levogo"]["rows"]
    w, h, m = 880, 400, dict(t=30, r=24, b=46, l=56)
    iw, ih = w - m["l"] - m["r"], h - m["t"] - m["b"]
    hi = 2400
    n = len(R)
    bw = iw / n * .62
    X = lambda i: m["l"] + (i + .5) / n * iw
    Y = lambda v: m["t"] + (1 - v / hi) * ih
    s = _open(w, h, "График: на что уходил газ левого берега с 2010 по 2020 год. "
                    "Около сорока трёх процентов сжигалось ради электричества для правого берега")
    s += _grid(m, iw, [0, 500, 1000, 1500, 2000], Y, lambda t: f"{t:,}".replace(",", " "))
    s += _txt(m["l"], m["t"] - 14, "млн куб. м", C["ink3"], 12, 500, "start")
    for i, r in enumerate(R):
        x = X(i) - bw / 2
        acc = 0
        for key, col in (("right", C["amber"]), ("left", C["violet"]), ("kommun", C["teal"])):
            v = r[key]
            s += (f'<rect x="{x:.1f}" y="{Y(acc+v):.1f}" width="{bw:.1f}"'
                  f' height="{(Y(acc)-Y(acc+v)):.1f}" fill="{col}" opacity=".92"/>')
            acc += v
        s += _txt(X(i), h - 12, str(r["y"]), C["ink3"], 12.5, 500, "middle")
        s += _txt(X(i), Y(r["right"]) + 18, f'{r["right"]/r["total"]*100:.0f}%',
                  "#0b0f1c", 12.5, 800, "middle")
    return s + "</svg>"


# ------------------------------------------------------------------ 4. сверка
def sverka_plot(D):
    S = D["sverka"]
    w, h, m = 880, 380, dict(t=32, r=26, b=46, l=62)
    iw, ih = w - m["l"] - m["r"], h - m["t"] - m["b"]
    lo, hi = 2000, 3600
    n = len(S["years"])
    X = lambda i: m["l"] + i / (n - 1) * iw
    Y = lambda v: m["t"] + (1 - (v - lo) / (hi - lo)) * ih
    s = _open(w, h, "График: сколько электроэнергии Приднестровье отпустило за пределы "
                    "республики и сколько Молдова записала как закупку. В 2018 году ряды разошлись")
    s += _grid(m, iw, [2000, 2400, 2800, 3200, 3600], Y,
               lambda t: f"{t:,}".replace(",", " "))
    s += _txt(m["l"], m["t"] - 14, "млн кВт·ч", C["ink3"], 12, 500, "start")
    s += _path([(X(i), Y(v)) for i, v in enumerate(S["pmr"])], C["amber"], 2.8)
    s += _path([(X(i), Y(v)) for i, v in enumerate(S["nbs"])], C["teal"], 2.8)
    for i, y in enumerate(S["years"]):
        s += (f'<circle cx="{X(i):.1f}" cy="{Y(S["pmr"][i]):.1f}" r="4.3" fill="{C["amber"]}"'
              f' stroke="{C["bg"]}" stroke-width="1.6"/>')
        s += (f'<circle cx="{X(i):.1f}" cy="{Y(S["nbs"][i]):.1f}" r="4.3" fill="{C["teal"]}"'
              f' stroke="{C["bg"]}" stroke-width="1.6"/>')
        s += _txt(X(i), h - 12, str(y), C["ink3"], 13, 500, "middle")
    i18 = S["years"].index(2018)
    s += (f'<circle cx="{X(i18):.1f}" cy="{Y(S["anre2018"]):.1f}" r="6.5" fill="none"'
          f' stroke="{C["violet"]}" stroke-width="2.6"/>')
    s += _txt(X(i18) + 12, Y(S["anre2018"]) + 26, "отчёт ANRE: 2 544", C["violet"], 13, 700)
    s += _txt(X(i18) + 12, Y(S["nbs"][i18]) - 10, "НБС Молдовы: 2 964", C["teal"], 13, 700)
    s += _txt(X(0) + 8, Y(S["pmr"][0]) - 14, "Госстат Приднестровья", C["amberLit"], 13.5, 700)
    s += _txt(X(0) + 8, Y(S["nbs"][0]) + 22, "НБС Молдовы", C["teal"], 13.5, 700)
    i20 = S["years"].index(2020)
    s += _txt(X(i20), Y(3251) - 18, "сошлись до 0,01%", C["ink"], 13, 700, "end")
    return s + "</svg>"


# ------------------------------------------------------------------ 5. калибровка
def kalib_plot(D):
    """Парные точки по годам: цена из договора против того, что дал окольный счёт.
    Точечная диаграмма по диагонали читалась плохо: годы стояли вразнобой,
    и было неясно, что с чем сравнивается."""
    K = sorted(D["kalibrovka"], key=lambda p: p["y"])
    w, m = 880, dict(t=52, r=150, b=44, l=62)
    rowh = 27
    h = m["t"] + rowh * len(K) + m["b"]
    iw = w - m["l"] - m["r"]
    lo, hi = 4.0, 7.6
    X = lambda v: m["l"] + (v - lo) / (hi - lo) * iw
    s = _open(w, h, "Для каждого года две точки: цена из договора и цена, "
                    "полученная окольным счётом. Чем короче отрезок между ними, "
                    "тем точнее окольный счёт")
    for t in (4, 5, 6, 7):
        s += (f'<line x1="{X(t):.1f}" x2="{X(t):.1f}" y1="{m["t"]-18}" y2="{m["t"]+rowh*len(K)}"'
              f' stroke="{C["line"]}" stroke-width="1"/>')
        s += _txt(X(t), m["t"] - 26, f"{t} цента" if t < 5 else f"{t} центов",
                  C["ink3"], 12.5, 500, "middle")
    for i, p in enumerate(K):
        y = m["t"] + i * rowh + rowh / 2
        x1, x2 = X(p["direct"]), X(p["est"])
        col = C["teal"] if abs(p["dev"]) <= 5 else C["amber"]
        s += _txt(m["l"] - 14, y + 4, str(p["y"]), C["ink2"], 13, 700, "end")
        s += (f'<line x1="{x1:.1f}" x2="{x2:.1f}" y1="{y:.1f}" y2="{y:.1f}"'
              f' stroke="{col}" stroke-width="3" stroke-linecap="round" opacity=".55"/>')
        s += (f'<circle cx="{x1:.1f}" cy="{y:.1f}" r="5.4" fill="{C["ink"]}"'
              f' stroke="{C["bg"]}" stroke-width="1.6"/>')
        s += (f'<circle cx="{x2:.1f}" cy="{y:.1f}" r="5.4" fill="{C["bg"]}"'
              f' stroke="{col}" stroke-width="2.2"/>')
        s += _txt(m["l"] + iw + 16, y + 4,
                  ("совпало" if abs(p["dev"]) < 0.5 else
                   f'{abs(p["dev"]):.1f}'.replace(".", ",") + "% " +
                   ("выше" if p["dev"] > 0 else "ниже")),
                  col if abs(p["dev"]) > 5 else C["ink3"], 12.5, 600)
    s += _txt(m["l"] + iw + 16, m["t"] - 26, "разошлось на", C["ink3"], 12, 500)
    s += _txt(m["l"], h - 10, "закрашенная точка - цена из договора, "
                              "полая - что дал окольный счёт", C["ink3"], 12.5, 500)
    return s + "</svg>"


ALL = dict(real=real_plot, tender=tender_plot, gaz=gaz_plot,
           sverka=sverka_plot, kalib=kalib_plot)


# ------------------------------------------------------------------ 6. скидка на газ
def skidka_plot(D):
    S = D["skidka"]
    w, h, m = 880, 400, dict(t=32, r=26, b=46, l=58)
    iw, ih = w - m["l"] - m["r"], h - m["t"] - m["b"]
    y0, y1 = S["years"][0], S["years"][-1]
    lo, hi = -70, 70
    X = lambda y: m["l"] + (y - y0) / (y1 - y0) * iw
    Y = lambda v: m["t"] + (1 - (v - lo) / (hi - lo)) * ih
    s = _open(w, h, "График: на сколько процентов Молдова платила за газ дешевле или дороже "
                    "европейского индекса. Двадцать лет ниже нуля, с 2023 года выше")
    s += _grid(m, iw, [-60, -40, -20, 0, 20, 40, 60], Y, lambda t: f"{t:+d}%" if t else "0")
    s += _txt(m["l"], m["t"] - 14, "дешевле или дороже Европы", C["ink3"], 12, 500, "start")
    z = Y(0)
    s += (f'<defs><clipPath id="clUp"><rect x="{m["l"]}" y="{m["t"]}" width="{iw}"'
          f' height="{z-m["t"]:.1f}"/></clipPath><clipPath id="clDn"><rect x="{m["l"]}"'
          f' y="{z:.1f}" width="{iw}" height="{m["t"]+ih-z:.1f}"/></clipPath></defs>')
    segs, cur = [], []
    for i, y in enumerate(S["years"]):
        if cur and y - S["years"][i - 1] > 1:
            segs.append(cur); cur = []
        cur.append(i)
    segs.append(cur)
    for seg in segs:
        if len(seg) < 2:
            continue
        pts = [(X(S["years"][i]), Y(S["pct"][i])) for i in seg]
        poly = " ".join(f"{p[0]:.1f},{p[1]:.1f}" for p in pts)
        area = f'{poly} {pts[-1][0]:.1f},{z:.1f} {pts[0][0]:.1f},{z:.1f}'
        for clip, col in (("clDn", C["teal"]), ("clUp", C["amber"])):
            s += f'<polygon points="{area}" fill="{col}" opacity=".16" clip-path="url(#{clip})"/>'
        for clip, col in (("clDn", C["teal"]), ("clUp", C["amber"])):
            s += _path(pts, col, 3.0).replace("<path ", f'<path clip-path="url(#{clip})" ')
    s += (f'<line x1="{m["l"]}" x2="{m["l"]+iw}" y1="{Y(0):.1f}" y2="{Y(0):.1f}"'
          f' stroke="{C["ink2"]}" stroke-width="1.8"/>')
    s += _txt(m["l"] + 8, Y(0) - 9, "столько же, сколько в Европе", C["ink2"], 12.5, 600)
    for i, y in enumerate(S["years"]):
        col = C["amber"] if S["pct"][i] > 0 else C["teal"]
        s += (f'<circle cx="{X(y):.1f}" cy="{Y(S["pct"][i]):.1f}" r="4.2" fill="{col}"'
              f' stroke="{C["bg"]}" stroke-width="1.6"/>')
    for y in S["years"]:
        if y % 5 == 0 or y in (2021, 2023, 2025):
            s += _txt(X(y), h - 12, str(y), C["ink3"], 12.5, 500, "middle")
    g0, g1 = X(2011), X(2020)
    s += f'<rect x="{g0:.1f}" y="{m["t"]}" width="{g1-g0:.1f}" height="{ih}" fill="{C["ink"]}" opacity=".05"/>'
    s += _txt((g0 + g1) / 2, m["t"] + 20, "в эти годы Молдова", C["ink3"], 12, 600, "middle")
    s += _txt((g0 + g1) / 2, m["t"] + 36, "не отчитывалась в таможенную базу", C["ink3"], 12, 600, "middle")
    i05 = S["years"].index(2005)
    s += _txt(X(2006), Y(-62), "2005: дешевле на 65%", C["teal"], 13, 700, "start")
    i23 = S["years"].index(2023)
    s += _txt(X(2023), Y(S["pct"][i23]) - 14, "2023: дороже на 53%", C["amberLit"], 13, 700, "middle")
    return s + "</svg>"


# ------------------------------------------------------------------ 7. наценка
def nacenka_plot(D):
    N = D["nacenka"]
    w, h, m = 880, 400, dict(t=32, r=58, b=46, l=58)
    iw, ih = w - m["l"] - m["r"], h - m["t"] - m["b"]
    y0, y1 = N["years"][0], N["years"][-1]
    lo, hi = 0, 4.0
    X = lambda y: m["l"] + (y - y0) / (y1 - y0) * iw
    Y = lambda v: m["t"] + (1 - (v / 100 - lo) / (hi - lo)) * ih
    s = _open(w, h, "График: по какой цене электричество покупали компании-поставщики "
                    "и по какой продавали всем потребителям в среднем")
    s += '<g class="grid">'
    for t in (0, 1, 2, 3, 4):
        s += f'<line x1="{m["l"]}" x2="{m["l"]+iw}" y1="{Y(t*100):.1f}" y2="{Y(t*100):.1f}"/>'
        s += _txt(m["l"] - 10, Y(t * 100) + 4, f"{t},00".replace(",00", ",00"), C["ink3"], 13, 500, "end")
    s += "</g>"
    s += _txt(m["l"], m["t"] - 14, "лея за киловатт-час", C["ink3"], 12, 500, "start")
    rp = [(X(y), Y(N["roz"][i])) for i, y in enumerate(N["roz_years"])]
    zp2 = [(X(y), Y(N["zak"][N["years"].index(y)])) for y in N["roz_years"]]
    poly = " ".join(f"{p[0]:.1f},{p[1]:.1f}" for p in rp + zp2[::-1])
    s += f'<polygon points="{poly}" fill="{C["amber"]}" opacity=".16"/>'
    s += _path([(X(y), Y(N["zak"][i])) for i, y in enumerate(N["years"])], C["teal"], 2.8)
    s += _path(rp, C["amber"], 3.0)
    for i, y in enumerate(N["years"]):
        s += (f'<circle cx="{X(y):.1f}" cy="{Y(N["zak"][i]):.1f}" r="3.6" fill="{C["teal"]}"'
              f' stroke="{C["bg"]}" stroke-width="1.4"/>')
    for i, y in enumerate(N["roz_years"]):
        s += (f'<circle cx="{X(y):.1f}" cy="{Y(N["roz"][i]):.1f}" r="4.2" fill="{C["amber"]}"'
              f' stroke="{C["bg"]}" stroke-width="1.6"/>')
        s += _txt(X(y), Y(N["roz"][i]) - 13, f'{N["roz"][i]/100:.2f}'.replace(".", ","),
                  C["amberLit"], 12.5, 700, "middle")
    # Тарифные решения до 2020 года. Отдельный ряд: это утверждённый тариф
    # конкретной компании с конкретной даты, а не средняя за год. Полыми ромбами
    # и пунктиром - чтобы читатель ни на секунду не спутал их со сплошной линией.
    TD = D.get("tarify_do2020", [])
    if TD:
        tp = [(X(t["y"]), Y(t["v"])) for t in TD if y0 <= t["y"] <= y1]
        # соединяем только соседние годы: тянуть пунктир через 2013-2016,
        # где данных нет, значит рисовать тренд, которого мы не знаем
        for i in range(len(TD) - 1):
            if TD[i + 1]["y"] - TD[i]["y"] == 1:
                (x1, yy1), (x2, yy2) = tp[i], tp[i + 1]
                s += (f'<path d="M{x1:.1f} {yy1:.1f} L{x2:.1f} {yy2:.1f}" fill="none"'
                      f' stroke="{C["amber"]}" stroke-width="1.6" stroke-dasharray="5 5"'
                      f' opacity=".8"/>')
        for (px, py), t in zip(tp, TD):
            s += (f'<path d="M{px:.1f} {py-5.2:.1f} L{px+5.2:.1f} {py:.1f} '
                  f'L{px:.1f} {py+5.2:.1f} L{px-5.2:.1f} {py:.1f} Z" fill="{C["bg"]}"'
                  f' stroke="{C["amberLit"]}" stroke-width="1.8"/>')
            s += _txt(px, py - 13, f'{t["v"]/100:.2f}'.replace(".", ","),
                      C["amberLit"], 12, 600, "middle")
    for y in N["years"]:
        if y % 2 == 0 or y == y1:
            s += _txt(X(y), h - 12, str(y), C["ink3"], 12.5, 500, "middle")
    s += _txt(X(2013), Y(N["zak"][N["years"].index(2013)]) + 26,
              "по этой цене покупали компании", C["teal"], 13.5, 700, "middle")
    s += _txt(X(2021), Y(372), "а по этой продавали потребителям", C["amberLit"], 13.5, 700, "middle")
    return s + "</svg>"


# ------------------------------------------------------------------ 8. бытовой газ
def byt_plot(D):
    B = D["byt_gaz"]
    w, h, m = 880, 380, dict(t=32, r=26, b=46, l=58)
    iw, ih = w - m["l"] - m["r"], h - m["t"] - m["b"]
    n = len(B["years"])
    hi = 520
    bw = iw / n * .58
    X = lambda i: m["l"] + (i + .5) / n * iw
    Y = lambda v: m["t"] + (1 - v / hi) * ih
    s = _open(w, h, "График: сколько газа потребляли молдавские домохозяйства. "
                    "Пик в 2021 году, потом падение на сорок процентов")
    s += _grid(m, iw, [0, 100, 200, 300, 400, 500], Y)
    s += _txt(m["l"], m["t"] - 14, "млн куб. м в год", C["ink3"], 12, 500, "start")
    ip = B["years"].index(B["pik_god"])
    for i, y in enumerate(B["years"]):
        v = B["v"][i]
        col = C["amber"] if i == ip else (C["teal"] if i > ip else C["ink3"])
        s += (f'<rect x="{X(i)-bw/2:.1f}" y="{Y(v):.1f}" width="{bw:.1f}"'
              f' height="{(Y(0)-Y(v)):.1f}" rx="3" fill="{col}" opacity="{1 if i==ip else .82}"/>')
        s += _txt(X(i), h - 12, str(y), C["ink3"], 12, 500, "middle")
    s += _txt(X(ip), Y(B["pik"]) - 24, f'{str(B["pik"]).replace(".", ",")}', C["amberLit"], 15, 800, "middle")
    s += _txt(X(ip), Y(B["pik"]) - 9, "пик", C["amberLit"], 12, 600, "middle")
    ilo = B["v"].index(min(B["v"][ip:]))
    s += _txt(X(ilo), Y(B["v"][ilo]) - 12, f'{str(B["padenie"]).replace(".", ",")}%',
              C["teal"], 14, 800, "middle")
    s += (f'<line x1="{m["l"]}" x2="{m["l"]+iw}" y1="{Y(B["pik"]):.1f}" y2="{Y(B["pik"]):.1f}"'
          f' stroke="{C["amberLit"]}" stroke-width="1.4" stroke-dasharray="6 5" opacity=".6"/>')
    return s + "</svg>"


# ------------------------------------------------------------------ 9. откуда электричество
def dolya_plot(D):
    A = D["dolya"]
    w, h, m = 880, 380, dict(t=30, r=196, b=44, l=54)
    iw, ih = w - m["l"] - m["r"], h - m["t"] - m["b"]
    n = len(A["years"])
    X = lambda i: m["l"] + i / (n - 1) * iw
    Y = lambda v: m["t"] + (1 - v / 100) * ih
    s = _open(w, h, "График: откуда правый берег брал электричество с 2015 по 2025 год. "
                    "Молдавская ГРЭС, импорт и собственные станции, в сумме сто процентов")
    s += _grid(m, iw, [0, 25, 50, 75, 100], Y, lambda t: f"{t}%")
    # вертикальные направляющие по годам, под заливками
    for i in range(n):
        s += (f'<line x1="{X(i):.1f}" x2="{X(i):.1f}" y1="{m["t"]}" y2="{m["t"]+ih}"'
              f' stroke="{C["line"]}" stroke-width="1" opacity=".5"/>')
    acc = [0.0] * n
    layers = (("mgres", C["amber"]), ("imp", C["violet"]), ("svoya", C["teal"]))
    for key, col in layers:
        top = [acc[i] + A[key][i] for i in range(n)]
        pts = [(X(i), Y(top[i])) for i in range(n)]
        bot = [(X(i), Y(acc[i])) for i in range(n)]
        poly = " ".join(f"{p[0]:.1f},{p[1]:.1f}" for p in pts + bot[::-1])
        s += f'<polygon points="{poly}" fill="{col}" opacity=".48"/>'
        acc = top
    # контуры поверх заливок: тёмная подложка плюс яркая линия
    acc = [0.0] * n
    for k, (key, col) in enumerate(layers):
        top = [acc[i] + A[key][i] for i in range(n)]
        if k < len(layers) - 1:          # верхняя граница всегда 100%, её не рисуем
            pts = [(X(i), Y(top[i])) for i in range(n)]
            s += _path(pts, C["bg"], 4.6)
            s += _path(pts, col, 2.6)
            for i in range(n):
                s += (f'<circle cx="{pts[i][0]:.1f}" cy="{pts[i][1]:.1f}" r="3.4" fill="{col}"'
                      f' stroke="{C["bg"]}" stroke-width="1.6"/>')
        acc = top
    for i, y in enumerate(A["years"]):
        if i % 2 == 0 or i == n - 1:
            s += _txt(X(i), h - 12, str(y), C["ink3"], 12.5, 500, "middle")
    xr = m["l"] + iw + 14
    s += _txt(xr, Y(88), "свои станции", C["teal"], 13.5, 800)
    s += _txt(xr, Y(88) + 16, "на правом берегу", C["ink3"], 11.5, 500)
    s += _txt(xr, Y(64), "импорт", C["violet"], 13.5, 800)
    s += _txt(xr, Y(30), "Молдавская ГРЭС", C["amberLit"], 13.5, 800)
    i17 = A["years"].index(2017)
    s += _txt(X(i17), Y(A["mgres"][i17]) - 12, "конкурс 2017", C["ink"], 12.5, 700, "middle")
    i25 = A["years"].index(2025)
    s += _txt(X(i25) - 10, Y(40), "с 2025 года", C["ink"], 12.5, 800, "end")
    s += _txt(X(i25) - 10, Y(34), "ничего", C["ink"], 12.5, 800, "end")
    return s + "</svg>"


def gaz100_plot(D):
    G = D["gaz100"]
    w, h, m = 880, 260, dict(t=30, r=210, b=40, l=54)
    iw = w - m["l"] - m["r"]
    hi = 34.0
    X = lambda v: m["l"] + v / hi * iw
    bh, gap = 40, 26
    s = _open(w, h, "График: сколько кубометров газа нужно трём станциям левого берега, "
                    "чтобы произвести сто киловатт-часов. Молдавская ГРЭС тратит больше всех")
    for i, g in enumerate(G):
        y = m["t"] + i * (bh + gap)
        first = "Молдавская" in g["lab"]
        col = C["amber"] if first else C["teal"]
        s += (f'<rect x="{m["l"]}" y="{y}" width="{X(g["m3"])-m["l"]:.1f}" height="{bh}"'
              f' rx="4" fill="{col}" opacity="{1 if first else .8}"/>')
        # значение стоит в неподвижном правом столбце, а не у конца полосы:
        # иначе числа скачут по горизонтали и колонка выглядит рваной
        s += _txt(w - 22, y + bh / 2 + 2, f'{g["m3"]}'.replace(".", ","),
                  C["ink"], 17, 800, "end")
        s += _txt(w - 22, y + bh / 2 + 17, "куб. м", C["ink3"], 11.5, 500, "end")
        nm = g["lab"].replace("ЗАО ", "").replace("ООО ", "").replace("«", "").replace("»", "")
        nm = nm.split(",")[0]
        s += _txt(m["l"] + 14, y + bh / 2 + 6, nm, "#0b0f1c", 14, 800)
    s += _txt(m["l"], h - 12, "кубометров газа на 100 киловатт-часов", C["ink3"], 12.5, 500)
    return s + "</svg>"


ALL.update(dict(skidka=skidka_plot, nacenka=nacenka_plot, byt=byt_plot,
                dolya=dolya_plot, gaz100=gaz100_plot))
