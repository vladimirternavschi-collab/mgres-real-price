# -*- coding: utf-8 -*-
"""og-image.png 1200x630 в палитре сайта, тем же шрифтом."""
import json
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager

OUT = "/sessions/dazzling-gallant-davinci/mnt/Downloads/Claude files/sait_mgres"
D = json.load(open("/sessions/dazzling-gallant-davinci/mnt/outputs/data.json", encoding="utf-8"))

for p in ("/tmp/golos800.ttf", "/tmp/golos500.ttf"):
    font_manager.fontManager.addfont(p)
F8 = font_manager.FontProperties(fname="/tmp/golos800.ttf")
F5 = font_manager.FontProperties(fname="/tmp/golos500.ttf")

BG, SURF, INK, INK2, INK3 = "#111628", "#1d2234", "#edf0f8", "#aaafbe", "#83899b"
AMBER, AMBER_L, TEAL, VIOLET, LINE = "#c98200", "#edb04e", "#0da18b", "#b063d4", "#303544"

fig = plt.figure(figsize=(12, 6.3), dpi=100, facecolor=BG)
T = D["tri_linii"]

# ------------------------------------------------------------------ текст
fig.text(.055, .875, "Платили 5 центов за киловатт-час.", fontproperties=F8,
         fontsize=40, color=INK)
fig.text(.055, .782, "А стоило от 9 до 32.", fontproperties=F8, fontsize=40, color=AMBER_L)
fig.text(.055, .705, "Цена электричества с Молдавской ГРЭС: деньгами и вместе с газом,\n"
                     "который записывался в долг перед Газпромом",
         fontproperties=F5, fontsize=17, color=INK2, linespacing=1.5, va="top")

# ------------------------------------------------------------------ график
ax = fig.add_axes([.055, .13, .60, .40])
ax.set_facecolor(BG)
segs, cur = [], []
for i, y in enumerate(T["years"]):
    if cur and y - T["years"][i - 1] > 1:
        segs.append(cur); cur = []
    cur.append(i)
segs.append(cur)
for sg in segs:
    if len(sg) < 2:
        continue
    xs = [T["years"][i] for i in sg]
    ax.fill_between(xs, [T["cash"][i] for i in sg], [T["real"][i] for i in sg],
                    color=AMBER, alpha=.15, lw=0)
    ax.plot(xs, [T["real"][i] for i in sg], color=AMBER, lw=3.4, solid_capstyle="round")
    ax.plot(xs, [T["cash"][i] for i in sg], color=TEAL, lw=2.8, solid_capstyle="round")
for i, y in enumerate(T["years"]):
    ax.plot([y], [T["real"][i]], "o", color=AMBER, ms=7, mec=BG, mew=1.6)
    ax.plot([y], [T["cash"][i]], "o", color=TEAL, ms=6, mec=BG, mew=1.6)
for s in ax.spines.values():
    s.set_visible(False)
ax.tick_params(colors=INK3, length=0, labelsize=13)
for lab in ax.get_xticklabels() + ax.get_yticklabels():
    lab.set_fontproperties(F5)
ax.set_xticks(range(2015, 2023))
ax.set_yticks([0, 10, 20, 30])
ax.grid(axis="y", color=LINE, lw=1)
ax.set_axisbelow(True)
ax.set_ylim(0, 34)
ax.set_xlim(2014.7, 2022.3)

fig.text(.055, .555, "цент за киловатт-час", fontproperties=F5, fontsize=12.5, color=INK3)

# ------------------------------------------------------------------ правая колонка
x0 = .705
fig.text(x0, .505, "РЕАЛЬНАЯ ЦЕНА, 2015", fontproperties=F5, fontsize=12.5, color=INK3)
fig.text(x0, .395, "14,6", fontproperties=F8, fontsize=54, color=AMBER_L)
fig.text(x0, .335, "цента за киловатт-час,", fontproperties=F5, fontsize=13.5, color=INK2)
fig.text(x0, .292, "вместе с газом в долг", fontproperties=F5, fontsize=13.5, color=INK2)

fig.text(x0, .215, "ДЕНЬГАМИ ЗАПЛАТИЛИ", fontproperties=F5, fontsize=12.5, color=INK3)
fig.text(x0, .105, "6,8", fontproperties=F8, fontsize=54, color=TEAL)
fig.text(x0, .045, "остальное ушло в долг", fontproperties=F5, fontsize=13.5, color=INK2)

fig.text(.055, .045, "Владимир Тернавский, EcoVisio  ·  753 факта из открытых документов",
         fontproperties=F5, fontsize=13, color=INK3)

fig.savefig(f"{OUT}/og-image.png", facecolor=BG)
print("og-image.png готов")
