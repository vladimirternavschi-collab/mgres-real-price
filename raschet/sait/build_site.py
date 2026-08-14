# -*- coding: utf-8 -*-
"""Собирает index.html одним файлом. Запуск: python3 build_site.py"""
import json, re, os
import plots

HERE = "/sessions/dazzling-gallant-davinci/mnt/outputs"
OUT = "/sessions/dazzling-gallant-davinci/mnt/Downloads/Claude files/sait_mgres"
os.makedirs(OUT, exist_ok=True)

D = json.load(open(f"{HERE}/data.json", encoding="utf-8"))
ETALON = open("/sessions/dazzling-gallant-davinci/mnt/uploads/index.html", encoding="utf-8").read()
FONT = re.search(r"base64,([A-Za-z0-9+/=]{200,})", ETALON).group(1)
CSS = re.search(r":root\{.*?\n</style>", ETALON, re.S).group(0)[:-len("\n</style>")]

sc = {r["name"][0]: r for r in D["scenarii"]["rows"]}
ROM = [r for r in D["scenarii"]["rows"] if r["name"].startswith("Румыния")][0]
T = D["tarif"] = D["scenarii"]["tarif"]
dn = D["dolg"]["na_semyu"]

U = "https://vladimirternavschi-collab.github.io/mgres-real-price/"
# Репозиторий: github.com/vladimirternavschi-collab/mgres-real-price
# Собранная страница кладётся сразу в него, чтобы адрес не подставлять руками.
REPO = "/sessions/dazzling-gallant-davinci/mnt/mgres-real-price"

# ================================================================= надстройка стилей
# Всё, что добавлено поверх эталона. Отдельной строкой, не f-string:
# в CSS слишком много фигурных скобок, чтобы их удваивать.
CSS2 = r'''
/* ---------- дополнения токенов ---------- */
:root{
  --line-lit:#3d4459;                 /* видимая линия там, где нужен раздел */
  --amber-dim:rgba(237,176,78,.13);
  --ring:0 0 0 2px var(--bg), 0 0 0 4px var(--amber-lit);
  --z-rail:70;
}

/* ---------- выделение и полосы прокрутки ---------- */
/* В эталоне стоит body{overflow-x:hidden}. Это делает body контейнером прокрутки
   и ломает position:sticky у указателя разделов в Chrome. overflow-x:clip режет
   вылезающее так же, но контейнером прокрутки не становится. Браузеры, которые
   clip не понимают, просто пропустят строку и останутся на hidden. */
body{overflow-x:clip}
::selection{background:rgba(237,176,78,.28);color:#fff}
html{scrollbar-color:var(--line-lit) var(--bg)}

/* ---------- фокус с клавиатуры: был невидим на тёмном фоне ---------- */
a:focus-visible,button:focus-visible,input:focus-visible,
[tabindex]:focus-visible,summary:focus-visible{
  outline:none;box-shadow:var(--ring);border-radius:.35rem}
.rf input:focus-visible{outline:none;box-shadow:var(--ring)}

/* Полосы прочитанного и любых анимаций по прокрутке на странице нет.
   Они цеплялись за тачпад: браузер пересчитывал их на каждом кадре, прокрутка
   подвисала и потом прыгала. Страница листается сверху вниз и всё. */

/* ---------- разделы: два тона вместо одного ---------- */
section{position:relative;border-top:0}
section+section::before{content:"";position:absolute;inset:0 var(--pad) auto;height:1px;
  background:linear-gradient(90deg,transparent,var(--line-lit) 12%,var(--line-lit) 88%,transparent)}
/* Грунт меняется не линией, а растяжкой: сверху 10rem уходим от обычного фона
   к тёмному, снизу 6rem возвращаемся. Стыка не видно. */
section.deep{background:
  linear-gradient(180deg,var(--bg) 0,transparent 10rem),
  linear-gradient(0deg,var(--bg) 0,transparent 6rem),
  var(--bg-deep);
  padding-top:clamp(5.2rem,12vh,9rem);padding-bottom:clamp(4.4rem,10vh,7.6rem)}
section.deep::before{display:none}
/* пятно света начинается ниже стыка, иначе оно само становится границей */
section.deep::after{content:"";position:absolute;inset:0;pointer-events:none;
  background:radial-gradient(52% 58% at 84% 34%,rgba(237,176,78,.115),transparent 72%)}
section.deep>.wrap{position:relative;z-index:1}
section.deep+section::before{display:none}
section.deep h2{max-width:19ch}
/* ---------- заголовок раздела: номер как ориентир, а не украшение ---------- */
.sec-head h2{position:relative}

/* ---------- цифры ---------- */
.claim b,.claim em,.bar-val,.facts-val,.tarif-val{font-variant-numeric:tabular-nums lining-nums;
  letter-spacing:-.015em}
/* Числа в шапке прижимаются вправо, как и подписи под ними. Без этого «0» уезжал
   влево: ширину блока задаёт длинная подпись «не куплено ничего», а само число
   стояло по её левому краю и выпадало из общей вертикали. */
.facts-val{text-align:right}
.claim{line-height:1.52}
/* итоговая строка тарифа: теперь это отдельный ряд, а не .tarif-row */
.tarif-tot{display:flex;align-items:center;gap:.8rem;border-top:1px solid var(--line-lit);
  margin-top:1.05rem;padding-top:.9rem}

/* Длинная подпись в одну узкую колонку вытягивалась на целый экран.
   На широких экранах разбиваем её на две колонки: длина строки остаётся
   читаемой, а высота падает вдвое и пустое место справа исчезает. */
@media (min-width:62rem){
  .cap2{max-width:none;columns:2;column-gap:clamp(2rem,4vw,3.4rem)}
  .cap2>*{break-inside:avoid}
}

/* ---------- таблица реестра ---------- */
.rt th{box-shadow:inset 0 -1px 0 var(--line-lit);z-index:1}
.rt tbody tr:hover td{background:rgba(255,255,255,.032)}
.rhint{font-size:.82rem;color:var(--ink-3);margin-bottom:.6rem;display:none}
@media (max-width:46rem){.rhint{display:block}}

/* ---------- таблица спрятана за кнопкой: она длиннее всей остальной страницы ---------- */
.dt{margin-top:1.6rem;border:1px solid var(--line);border-radius:.7rem;background:var(--surface)}
.dt summary{list-style:none;cursor:pointer;display:flex;align-items:center;gap:.9rem;
  padding:1rem 1.15rem;border-radius:.7rem;
  transition:background .16s var(--ease),border-color .16s var(--ease)}
.dt summary::-webkit-details-marker{display:none}
.dt summary::before{content:"";flex:none;width:.62rem;height:.62rem;margin-left:.1rem;
  border-right:2px solid var(--amber-lit);border-bottom:2px solid var(--amber-lit);
  transform:rotate(-45deg);transition:transform .22s var(--ease)}
.dt[open] summary::before{transform:rotate(45deg)}
.dt summary:hover{background:rgba(255,255,255,.035)}
.dt summary:focus-visible{box-shadow:var(--ring)}
.dt-t{font-weight:700;color:var(--ink)}
.dt-n{font-size:.86rem;color:var(--ink-3);margin-left:auto;text-align:right}
.dt-body{padding:1.2rem 1.15rem;border-top:1px solid var(--line)}
/* самая мелкая статья тарифа - меньше бана; без этого полоска была бы в полпикселя */
.bar-fill{min-width:2px}
/* Единица прямо под числом: человек видит цифру и сразу знает, лей это или доллар.
   Подзаголовок блока про единицу тоже остаётся, но глазу нужна подпись у самого числа. */
.bar-val{min-width:4.8rem;line-height:1.15}
.bar-val s{display:block;text-decoration:none;font-size:.68rem;font-weight:500;
  color:var(--ink-3);text-align:right;margin-top:.12rem;letter-spacing:0}
.dt[open] summary{border-radius:.7rem .7rem 0 0}
@media (max-width:34rem){.dt-n{display:none}}

/* Подсказка на строке с полосой. Строка сама становится целью наведения
   и получает фокус с клавиатуры, поэтому работает и мышью, и пальцем, и табом. */
/* Ссылка на первоисточник в таблице фактов */
.rl{color:var(--amber-lit);text-decoration:none;
  border-bottom:1px solid rgba(237,176,78,.3);transition:border-color .16s var(--ease)}
.rl:hover,.rl:focus-visible{border-bottom-color:var(--amber-lit)}

.tipp{cursor:default;border-radius:.4rem;transition:background .16s var(--ease)}
.tipp:hover,.tipp:focus-visible{background:rgba(255,255,255,.04)}
.cmp-item{position:relative}

/* ---------- кнопки фильтра: попадаемые пальцем и видимые во включённом виде ---------- */
.rb2{min-height:2.1rem;padding:.42rem .8rem;transition:border-color .16s var(--ease),
  color .16s var(--ease),background .16s var(--ease)}
.rb2:hover{border-color:var(--line-lit);color:var(--ink-2)}
.rb2.on{border-color:var(--amber-lit);background:var(--amber-dim);color:var(--ink)}
@media (pointer:coarse){.rb2{min-height:2.75rem;padding:.6rem 1rem;font-size:.86rem}}

/* Заголовок шапки - это вопрос из комментариев, ради которого страница и сделана.
   Мелкая строка над ним нужна, чтобы читатель не принял вопрос за позицию автора,
   а первая фраза лида сразу отвечает. */
.hero-kick{font-size:.88rem;color:var(--ink-3);margin-bottom:.95rem;line-height:1.4}
.hero h1.hero-q{max-width:min(20ch,100%);font-weight:800;
  font-size:clamp(2.05rem,1.1rem + 4.3vw,4.2rem);letter-spacing:-.035em}

/* Рисунок в шапке живёт в тех же колонках, что и блок с ценами над ним:
   та же пропорция 1.35fr / 1fr и тот же отступ, что у .hero-grid. Поэтому его
   левый и правый края встают ровно под краями блока с ценами, а низ - на одной
   линии с абзацем про единицы. Отдельная сетка со своими пропорциями давала
   рисунок, висящий сам по себе. */
.hero-foot{margin-top:1.5rem}
.hero-foot .units{margin-top:0}
/* Скрытие идёт ДО медиазапроса. Наоборот нельзя: специфичность у обоих правил
   одинаковая, и более позднее display:none перебило бы display:block внутри
   @media, то есть рисунок не показался бы ни на одном экране. */
.hmark{display:none}
@media (min-width:74rem){
  .hero-foot{display:grid;grid-template-columns:1.35fr 1fr;
    gap:clamp(2rem,4vw,3.5rem);align-items:end}
  .hero-foot .units{max-width:none}
  .hmark{display:block;width:100%;height:auto;
    color:var(--ink);opacity:.075;margin-bottom:-.3rem}
}

/* Контурный рисунок фоном раздела. Живёт в правом нижнем углу, где иначе
   остаётся голый фон. Прозрачность подобрана так, чтобы он читался краем глаза
   и не спорил с текстом. */
.smark{position:absolute;right:0;bottom:0;width:min(24rem,26vw);
  color:var(--ink);opacity:.045;pointer-events:none;display:none;z-index:0}
@media (min-width:78rem){.smark{display:block}}
section>.wrap{position:relative;z-index:1}
/* overflow:hidden здесь НЕ ставим: он обрезал бы подсказки на графиках.
   Рисунок прижат к правому нижнему углу и за пределы раздела не выходит. */

/* ---------- подвал ---------- */
footer{position:relative;overflow:hidden}
/* Опора ЛЭП в пустой правой трети подвала. Чистое оформление: aria-hidden,
   на узких экранах не показывается, на печати убирается. */
.mark{position:absolute;right:-2.5rem;bottom:-3rem;width:min(30rem,34vw);
  color:var(--ink);opacity:.05;pointer-events:none;display:none}
@media (min-width:74rem){.mark{display:block}}
footer>.wrap{position:relative;z-index:1}
footer::before{content:"";position:absolute;inset:0 0 auto;height:1px;
  background:linear-gradient(90deg,transparent,var(--line-lit) 20%,var(--line-lit) 80%,transparent)}
.limits li::marker{color:var(--amber)}
.srcs a{transition:border-color .16s var(--ease),color .16s var(--ease)}
.sign{padding-top:1.4rem;border-top:1px solid var(--line);max-width:52rem}
/* Подпись автора - ссылка на страницу в Facebook. Оформлена как ссылки
   в списке источников, чтобы не выглядеть чужеродно. */
.me{color:var(--amber-lit);text-decoration:none;font-weight:700;
  border-bottom:1px solid rgba(237,176,78,.35);
  transition:border-color .16s var(--ease)}
.me:hover,.me:focus-visible{border-bottom-color:var(--amber-lit)}
@media print{.me::after{content:" (facebook.com/vivlont)";font-size:8pt;color:#555;font-weight:400}}

/* ---------- печать ---------- */
@media print{
  .mark,.smark,.hmark{display:none}
  body{background:#fff;color:#111;font-size:10.5pt;line-height:1.45}
  section,footer,section.deep{background:#fff;border-top:1px solid #bbb;padding:1.2rem 0}
  section.deep::after,section::before,footer::before,.hero::before{display:none}
  h1{font-size:24pt}h2{font-size:15pt}
  .lead,.dim,.cap,.sec-head p,.rt td{color:#333}
  .facts-val,.claim em,.bar-val{color:#8a5a00}
  .srcs a{color:#111;text-decoration:underline}
  .srcs a::after{content:" (" attr(href) ")";font-size:8pt;color:#555;word-break:break-all}
  figure,.cmp-item,section{break-inside:avoid}
  .rtw{max-height:none;overflow:visible}
}
'''

def mark(name, cls="smark"):
    """Контурный рисунок фоном. Только оформление: aria-hidden, не мешает тексту,
    не показывается на узких экранах и на печати."""
    t = open(f"{HERE}/risunki/{name}.svg", encoding="utf-8").read()
    for junk in (' width="480" height="480"', ' width="480" height="380"',
                 ' width="480" height="300"', ' color="#edf0f8"', ' role="img"'):
        t = t.replace(junk, "")
    t = re.sub(r' aria-label="[^"]*"', "", t)
    return t.replace('<svg ', f'<svg class="{cls}" aria-hidden="true" focusable="false" ', 1)


HEAD = f'''<!doctype html>
<html lang="ru"><head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="color-scheme" content="dark">

<!-- ============================================================
     Страница собирается скриптом build_site.py, руками её не правят.
     Адрес публикации задан в скрипте переменной U и подставлен ниже
     в canonical, og:url, og:image, og:image:secure_url и twitter:image.
     Исходники и расчётный модуль: см. README в рабочей папке проекта.
     ============================================================ -->

<title>Сколько на самом деле стоило электричество с Молдавской ГРЭС</title>
<meta name="description" content="Расчёт по открытым документам: цена закупки у МГРЭС за 2010-2024 годы, газовый долг левого берега и стоимость киловатт-часа в четырёх сценариях.">
<meta name="author" content="Владимир Тернавский">
<link rel="canonical" href="{U}">

<meta property="og:type" content="website">
<meta property="og:url" content="{U}">
<meta property="og:site_name" content="Реальная цена электричества с Молдавской ГРЭС">
<meta property="og:locale" content="ru_RU">
<meta property="og:title" content="Платили 5 центов, а стоило 12: газовый долг в цене киловатт-часа">
<meta property="og:description" content="{D["meta"]["reestr_zapisey"]} фактов из отчётов ANRE, статежегодников Приднестровья, договоров и тендерных протоколов. Каждое число со ссылкой на страницу источника.">
<meta property="og:image" content="{U}og-image.png">
<meta property="og:image:secure_url" content="{U}og-image.png">
<meta property="og:image:width" content="1200">
<meta property="og:image:height" content="630">
<meta property="og:image:type" content="image/png">
<meta property="og:image:alt" content="Две линии: деньгами платили около пяти центов за киловатт-час, а с учётом газа в долг выходило от девяти до тридцати двух.">

<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="Платили 5 центов, а стоило 12: газовый долг в цене киловатт-часа">
<meta name="twitter:description" content="Расчёт по открытым документам за 2010-2024 годы. Все цифры проверяемы.">
<meta name="twitter:image" content="{U}og-image.png">
<meta name="twitter:image:alt" content="Реальная цена киловатт-часа с Молдавской ГРЭС в сравнении с тем, что платили деньгами.">

<link rel="icon" href="favicon.svg" type="image/svg+xml">
<link rel="alternate icon" href="data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 32 32'%3E%3Crect width='32' height='32' rx='7' fill='%23111628'/%3E%3Cpath d='M18 4 L9 18 h6 l-2 10 9-14 h-6 z' fill='%23edb04e'/%3E%3C/svg%3E">
<style>
@font-face{{font-family:"GolosSub";src:url(data:font/woff2;base64,{FONT}) format("woff2-variations");
  font-weight:400 900;font-style:normal;font-display:swap}}
{CSS}
.stack-leg{{display:flex;flex-wrap:wrap;gap:.5rem 1.5rem;margin-top:1rem;font-size:.88rem;color:var(--ink-2)}}
.stack-leg i{{display:inline-block;width:.9rem;height:.9rem;border-radius:3px;margin-right:.5rem;vertical-align:-1px}}
.tarif{{margin-top:2.2rem;padding-top:1.2rem;border-top:1px solid var(--line);max-width:44rem}}
.tarif-row{{display:flex;align-items:center;gap:.8rem;margin:.5rem 0}}
.tarif-lab{{flex:1;font-size:.92rem;color:var(--ink-2)}}
.tarif-bar{{height:.5rem;border-radius:.25rem;background:var(--amber);min-width:2px;flex:none;max-width:34%}}
.tarif-val{{min-width:4.2rem;text-align:right;font-weight:700;font-size:.95rem}}
.tarif-tot{{border-top:1px solid var(--line);margin-top:.7rem;padding-top:.7rem}}
.tarif-tot .tarif-lab,.tarif-tot .tarif-val{{color:var(--ink);font-weight:800}}
.rf{{display:flex;flex-wrap:wrap;gap:.8rem;align-items:center;margin-bottom:1rem}}
.rf input{{flex:1;min-width:min(100%,16rem);background:var(--surface);border:1px solid var(--line);
  border-radius:.5rem;padding:.6rem .8rem;color:var(--ink);font:inherit;font-size:.95rem}}
.rf input:focus{{outline:2px solid var(--amber);outline-offset:1px}}
.rf span{{font-size:.86rem;color:var(--ink-3);white-space:nowrap}}
.rst{{display:flex;flex-wrap:wrap;gap:.45rem;margin-bottom:1rem}}
.rb2{{background:transparent;border:1px solid var(--line);border-radius:999px;
  padding:.3rem .75rem;color:var(--ink-3);font:inherit;font-size:.82rem;cursor:pointer}}
.rb2 b{{color:var(--ink-2);font-weight:700}}
.rb2.on{{border-color:var(--amber);color:var(--ink)}}
.rb2.on b{{color:var(--amber-lit)}}
.rtw{{overflow-x:auto;border:1px solid var(--line);border-radius:.6rem}}
.rt{{width:100%;border-collapse:collapse;font-size:.84rem;min-width:44rem}}
.rt th{{text-align:left;padding:.6rem .7rem;color:var(--ink-3);font-weight:600;
  border-bottom:1px solid var(--line);background:var(--surface);position:sticky;top:0}}
.rt td{{padding:.55rem .7rem;border-bottom:1px solid var(--line);vertical-align:top;color:var(--ink-2)}}
.rt tr:last-child td{{border-bottom:0}}
.rt .rv{{color:var(--ink);font-weight:700;white-space:nowrap}}
.rt .rv s,.rt .rs s{{display:block;text-decoration:none;color:var(--ink-3);font-weight:400;font-size:.78rem}}
.rt .rs{{max-width:22rem}}
.st{{font-style:normal;font-size:.76rem;padding:.16rem .5rem;border-radius:999px;white-space:nowrap;
  border:1px solid var(--line);color:var(--ink-3)}}
.st-1{{border-color:rgba(13,161,139,.5);color:var(--teal)}}
.st-4,.st-2{{border-color:rgba(201,130,0,.55);color:var(--amber-lit)}}
{CSS2}
</style></head>
<body>
'''

FACTS_HTML = "".join(
    '<div class="facts-row"><span class="facts-when">{}<s>{}</s></span>'
    '<span class="facts-val"{}>{}<s>{}</s></span></div>'.format(
        f["when"], f["sub"] + (" · " + f["lei"] if f["lei"] else ""),
        ' style="color:var(--teal)"' if f["v"] == "0" else "",
        f["v"], f["u"]) for f in D["facts"])

HERO = f'''
<header class="hero"><div class="wrap"><div class="hero-grid">
  <div>
    <p class="hero-kick">Так спрашивают в комментариях под моим постом</p>
    <h1 class="hero-q">«У нас же есть Молдавская ГРЭС. Почему не 2 лея, как раньше?»</h1>
    <p class="lead">Вопрос справедливый. Здесь то, что не поместилось в пост: графики, из которых видно, откуда взялась каждая цифра, и таблица со всеми {D["meta"]["reestr_zapisey"]} фактами. У каждого числа указан документ, страница и способ расчёта. Смотрите, спорьте, проверяйте.</p>
  </div>
  <div class="facts">
    <p class="facts-h">Что Кишинёв платил за 100 киловатт-часов электричества с МГРЭС</p>
    {FACTS_HTML}
    <p class="facts-note">Договоры с МГРЭС были в долларах, поэтому цена показана в долларах, а рядом - в леях по курсу того года. За пятнадцать лет она не выросла, а упала на треть: в ней не было главного - стоимости топлива.</p>
  </div>
</div>
  <div class="hero-foot">
  <p class="units"><b>Цент за киловатт-час</b> - цена на границе: столько получал продавец, без доставки по проводам. <b>Лей за 100 киловатт-часов</b> - то, что видно в квитанции: сюда входит и сама энергия, и доставка по сетям. НДС на электричество для домов сейчас нулевой.</p>
  {mark("4-grafik", "hmark")}
  </div>
</div></header>
'''


def sec(h2, p, body, cls="", sid="", nav="", pic=""):
    """sid - якорь для указателя разделов, nav - короткая подпись в указателе,
    cls='deep' - раздел на тёмном грунте (используется для двух смысловых пиков)."""
    if sid and nav:
        NAVLIST.append((sid, nav))
    a = f' id="{sid}"' if sid else ""
    c = f' class="{cls}"' if cls else ""
    pm = mark(pic) if pic else ""
    return f'''<section{a}{c}>{pm}<div class="wrap">
  <div class="sec-head">
    <h2>{h2}</h2>
    {p}
  </div>
  {body}
</div></section>
'''


NAVLIST = []


def fig(pid, static, legend, cap):
    # подписи длиннее 420 знаков верстаются в две колонки, иначе тянутся на экран
    cls = "cap cap2" if len(cap) > 420 else "cap"
    return f'''<figure><div class="plot" id="{pid}"><noscript>{static}</noscript></div>
    {legend}
    <figcaption class="{cls}">{cap}</figcaption>
  </figure>'''


# ---------------------------------------------------------------- секция 1
bars = []
order = [("A", "МГРЭС, а газ ей достаётся бесплатно", "var(--ink-3)"),
         ("Р", "Купить готовое в Румынии, по нынешним ценам", "var(--violet)"),
         ("B", "МГРЭС, газ по цене Газпрома 2021 года", "var(--amber)"),
         ("D", "МГРЭС, газ по европейской бирже", "var(--amber)"),
         ("E", "МГРЭС, газ с премией за малый объём", "var(--amber)")]
MAXB = 700
for key, lab, col in order:
    r = ROM if key == "Р" else sc[key]
    v = r["full"]
    bars.append(f'''<div class="bar-lab">{lab}</div>
     <div class="bar-row"><div class="bar-track"><div class="bar-fill nojs" style="width:{v/MAXB*100:.1f}%;background:{col}"></div></div><span class="bar-val" style="color:{col if col!='var(--ink-3)' else 'var(--ink-2)'}">{v:.0f}<s>лей</s></span></div>''')

tar_rows = [("Сама энергия, закупка Энергокомом", T["energiya"]),
            ("Передача по магистральным сетям", T["peredacha"]),
            ("Распределение до вашего счётчика", T["raspredelenie"]),
            ("Работа биржи", T["rynok"]),
            ("Работа поставщика и перерасчёты прошлых лет", T["sbyt"])]
# Те же полосы, что и в левом столбце: длина = доля этой статьи в 356 леях.
tar_html = "".join(
    f'''<div class="bar-lab">{n}</div>
     <div class="bar-row"><div class="bar-track"><div class="bar-fill nojs" style="width:{v/T["itogo"]*100:.1f}%;background:{"var(--amber)" if v > 1 else "var(--ink-3)"}"></div></div>'''
    f'<span class="bar-val" style="color:{"var(--amber-lit)" if v > 1 else "var(--ink-2)"}">'
    # биржа стоит меньше бана, на двух знаках после запятой это был бы ноль
    + (f'{v/100:.3f}' if v < 1 else f'{v/100:.2f}').replace(".", ",")
    + '<s>лея за кВт·ч</s></span></div>'
    for n, v in tar_rows)
tar_html += ('<div class="tarif-tot"><span class="tarif-lab">Итого в квитанции, лея за киловатт-час</span>'
             '<span class="tarif-val">3,56</span></div>')

SEC1 = sec(
    "Пока газ бесплатный, схема выигрывает. Как только за него платят - проигрывает",
    "<p>Полная сумма в квитанции за 100 киловатт-часов в месяц: и сама энергия, и доставка по сетям. "
    "НДС для домов сейчас нулевой, так что это итог. Сегодня в квитанции стоит 356 лей.</p>",
    f'''<div class="cmp" id="cmp"><div class="cmp-item"><h3>Ваш счёт за 100 кВт·ч в пяти сценариях</h3>
    <p class="cmp-when">четыре сценария - электричество производит МГРЭС, и меняется только то, почём ей достаётся газ. Пятый - купить готовое в Румынии. Лей в месяц, всё включено</p>{"".join(bars)}
    <p class="verdict">Первый сценарий невозможен, он здесь для отсчёта: столько выходило, когда за газ никто не платил. Ни один сценарий с платным газом не обходит Румынию. Даже самый мягкий, по старой цене Газпрома, дороже на 15 процентов.</p></div>
    <div class="cmp-item"><h3>Из чего складываются 356 лей, которые вы платите сейчас</h3>
    <p class="cmp-when">это не сценарий, а факт: действующие тарифы на апрель 2026 года. Длина полосы - доля статьи в счёте</p>{tar_html}
    <p class="verdict">На севере, у FEE Nord, тот же счёт стоит 395 лей: там дороже распределение.</p></div></div>''',
    sid="scen", nav="Счёт за 100 кВт·ч")

# ---------------------------------------------------------------- секция 2
TL = D["tri_linii"]
SEC2 = sec(
    "Платили 5 центов. А стоило от 9 до 32",
    "<p>Нижняя линия - деньги, которые Кишинёв переводил в Тирасполь. Верхняя - те же деньги плюс газ, "
    "сожжённый ради этих киловатт-часов, по цене, по которой он записывался в долг. Между ними и есть долг.</p>",
    fig("p-real", plots.real_plot(D),
        '<div class="legend"><span><i style="background:var(--amber)"></i>сколько стоило на самом деле</span>'
        '<span><i style="background:var(--teal)"></i>сколько платили деньгами</span>'
        '<span><i style="background:var(--violet);height:2px"></i>оптовая цена на бирже Румынии</span></div>',
        "Шкала обрезана на шестнадцати центах: в 2022 году реальная цена подскочила до 31,59, и в полном масштабе "
        "все спокойные годы сплющились бы в нижнюю треть. Значение вынесено подписью над графиком. "
        "Как считается реальная цена: контрактная цена плюс норматив 0,3047 кубометра газа, умноженный на цену "
        "закупки газа из годовых отчётов ANRE - по ней долг и начислялся. Румынская линия здесь мера стоимости, "
        "а не упущенная возможность: до постройки линии Вулкэнешты-Кишинёв столько импортировать было физически нельзя. "
        "За 2018 год цену именно МГРЭС не публиковали, отсюда разрыв. За 2010 год реальная цена выходила 13,45 при 5,83 "
        "деньгами, но биржевых цен Румынии до 2015 года нет, и в общий ряд этот год не встроить."),
    cls="deep", sid="real", nav="5 центов против 32")

# ---------------------------------------------------------------- секция 3
TN = D["tender2017"]
SEC3 = sec(
    "Один раз провели конкурс. Цена упала на 17%",
    "<p>Март 2017 года. МГРЭС запросила 58,5 доллара за мегаватт-час, потом сбросила до 54,4. "
    "Украинская DTEK предложила 50,2 и выиграла. Через два месяца МГРЭС вернулась с ценой 45,0.</p>",
    fig("p-tender", plots.tender_plot(D),
        '<div class="legend"><span><i style="background:var(--amber)"></i>предложения МГРЭС, отклонены</span>'
        '<span><i style="background:var(--violet)"></i>победитель конкурса</span>'
        '<span><i style="background:var(--teal)"></i>чем всё кончилось</span></div>',
        f"Министерство экономики оценило выигрыш бюджета в {TN['ekonomiya_mln_lei']} миллионов лей. "
        f"Доля МГРЭС в потреблении правого берега в тот год упала с {str(TN['dolya']['2016']).replace('.', ',')}% "
        f"до {str(TN['dolya']['2017']).replace('.', ',')}%, а в следующем вернулась к "
        f"{str(TN['dolya']['2018']).replace('.', ',')}%. Станция потеряла треть выработки не потому, "
        f"что не могла производить, а потому что проиграла по цене. За год до этого сработало так же: "
        f"в апреле 2016-го цена упала с 67,95 до 48,995 доллара, минус 28%, тоже после появления украинских "
        f"предложений. Два раза за двадцать лет - и оба раза мгновенно."),
    sid="tender", nav="Конкурс 2017")

# ---------------------------------------------------------------- секция 4
GZ = D["gaz_levogo"]
SEC4 = sec(
    "43% газа левого берега горело ради электричества для правого берега",
    "<p>Долг за газ - это за весь газ левого берега: и отопление Тирасполя, и завод в Рыбнице, и электричество. "
    "Нас касается только та часть, которая превращалась в киловатт-часы для правого берега.</p>",
    fig("p-gaz", plots.gaz_plot(D),
        '<div class="stack-leg"><span><i style="background:var(--amber)"></i>электричество, ушедшее на правый берег</span>'
        '<span><i style="background:var(--violet)"></i>электричество для самого Приднестровья</span>'
        '<span><i style="background:var(--teal)"></i>дома, котельные и заводы левого берега</span></div>',
        f"Миллионы кубометров. Газ на электричество считается по норме правительства Приднестровья: "
        f"около 30 кубометров на 100 киловатт-часов. Число на нижнем куске столбца - какая доля всего газа "
        f"ушла на электричество для правого берега в этот год. По всем одиннадцати годам вместе выходит "
        f"{str(GZ['share_right_avg']).replace('.', ',')}%. В 2013 году МГРЭС резко просела, и доля упала до 35%; "
        f"причину мы не установили."),
    sid="gaz", nav="43% газа", pic="2-stanciya")

# ---------------------------------------------------------------- секция 5
DG = D["dolg"]
oc_bars = "".join(
    f'''<div class="bar-lab">{o["lab"]}</div>
     <div class="bar-row"><div class="bar-track"><div class="bar-fill nojs" style="width:{o["v"]/10000*100:.0f}%;background:var(--amber)"></div></div><span class="bar-val" style="color:var(--amber-lit)">{o["v"]/1000:.1f}<s>млрд $</s></span></div>'''
    for o in DG["ocenki_levogo"])
SEC5 = sec(
    "1 772 $ выгоды на каждую семью, 3 281 $ долга",
    f'<p class="claim">Скидка на газ дала правому берегу <b>2,27 миллиарда долларов</b> за тринадцать лет, по которым есть данные. '
    f'Переплата 2023-2025 годов забрала 491 миллион. Осталось <b>1,78 миллиарда</b>. '
    f'А долг за газ, сожжённый ради нашего электричества, - <em>3,3 миллиарда</em>.</p>',
    f'''<div class="cmp"><div class="cmp-item"><h3>На одну семью</h3>
    <p class="cmp-when">долларов на каждую семью, всего 1 006 800 семей по переписи 2024 года</p>
    <div class="bar-lab" style="color:var(--teal)">Выгода от дешёвого газа за 25 лет</div>
    <div class="bar-row"><div class="bar-track"><div class="bar-fill nojs" style="width:{dn["skidka"]/7558*100:.0f}%;background:var(--teal)"></div></div><span class="bar-val" style="color:var(--teal)">{dn["skidka"]}<s>$</s></span></div>
    <div class="bar-lab" style="color:var(--amber-lit)">Долг за электричество, которое купили</div>
    <div class="bar-row"><div class="bar-track"><div class="bar-fill nojs" style="width:{dn["dolg_elektro"]/7558*100:.0f}%;background:var(--amber)"></div></div><span class="bar-val" style="color:var(--amber-lit)">{dn["dolg_elektro"]}<s>$</s></span></div>
    <div class="bar-lab" style="color:var(--ink-3)">Долг за весь остальной газ левого берега</div>
    <div class="bar-row"><div class="bar-track"><div class="bar-fill nojs" style="width:{dn["ostalnoy"]/7558*100:.0f}%;background:var(--ink-3)"></div></div><span class="bar-val" style="color:var(--ink-2)">{dn["ostalnoy"]}<s>$</s></span></div>
    <p class="verdict">Если считать только электрическую часть, каждая семья в минусе на {dn["minus"]} долларов. Это не то, что нужно заплатить завтра, - это то, что записано в долг и когда-то придётся закрывать.</p></div>
    <div class="cmp-item"><h3>Сколько должен левый берег: от 6 до 10 миллиардов долларов</h3>
    <p class="cmp-when">миллиарды долларов, четыре разные оценки одного долга</p>{oc_bars}
    <p class="verdict">Для сравнения, весь долг правого берега, вокруг которого шли переговоры, - 0,76 миллиарда. Его проверяли независимые аудиторы. Левобережный долг не проверял никто.</p></div></div>''',
    cls="deep", sid="dolg", nav="Долг на семью")

# ---------------------------------------------------------------- секция 6
SEC6 = sec(
    "Две статслужбы по разные стороны Днестра считают один поток",
    "<p>Госстат Приднестровья публикует, сколько отпущено за пределы республики. Национальное бюро статистики "
    "Молдовы - сколько закуплено из других источников. Они не признают друг друга и считают независимо.</p>",
    fig("p-sverka", plots.sverka_plot(D),
        '<div class="legend"><span><i style="background:var(--amber)"></i>Госстат Приднестровья отпустил</span>'
        '<span><i style="background:var(--teal)"></i>НБС Молдовы закупила</span>'
        '<span><i style="background:var(--violet);height:.85rem;width:.85rem;border-radius:50%"></i>отчёт ANRE за 2018 год</span></div>',
        "Миллионы киловатт-часов. В 2020 году службы разошлись на четыре десятых миллиона при объёме в три с "
        "четвертью миллиарда - одна сотая процента. Из шести лет выбивается один: в 2018 молдавская цифра выше на 16,5 процента. "
        "Причину нашёл третий источник, не связанный ни с одной из служб: годовой отчёт ANRE даёт 2 544 миллиона, "
        "что совпадает с приднестровской цифрой до четырёх тысячных процента. Значит, ошибается ряд НБС."))

# ---------------------------------------------------------------- секция 7
SEC7 = sec(
    "Как я проверял оценку там, где нет договоров",
    "<p>За годы без опубликованных контрактов цена оценивалась косвенно: экспорт топливно-энергетических товаров "
    "Приднестровья, делённый на отпуск электроэнергии. Метод проверен на одиннадцати годах, где известно и то и другое.</p>",
    fig("p-kalib", plots.kalib_plot(D),
        '<div class="legend"><span><i style="background:var(--teal);height:.85rem;width:.85rem;border-radius:50%"></i>расхождение до 5%</span>'
        '<span><i style="background:var(--amber);height:.85rem;width:.85rem;border-radius:50%"></i>расхождение от 5 до 9%</span></div>',
        "Чем короче отрезок между точками, тем точнее оценка. Максимальное расхождение за одиннадцать лет - девять процентов, "
        "в 2018 году. Оценка остаётся оценкой: топливно-энергетические товары это таможенная категория, "
        "и в неё может входить не только электроэнергия. Но разброс известен, и это лучше, чем догадка."))

MARK = mark("1-opora-lep", "mark")

FOOT = f'''
<footer>{MARK}<div class="wrap">
  <h3>Откуда цифры</h3>
  <p style="max-width:46rem;margin-bottom:1.1rem;color:var(--ink-2);font-size:.92rem">Сами документы
  выложены целиком: <a href="{D["drive_root"]}">папка с первоисточниками</a>, 58 файлов.
  В таблице фактов имя источника в каждой строке - это ссылка прямо на нужный документ.</p>
  <div class="srcs">
    <div><a href="https://anre.md/raport-de-activitate-3-10">Годовые отчёты ANRE</a> - регулятор энергетики Молдовы. Семнадцать отчётов с 2009 по 2025 год: объёмы закупки у станции, средние цены закупки газа и электроэнергии, тарифы. Отчёт за 2013 год пришлось распознавать: 44 страницы из 66 вставлены картинками</div>
    <div><a href="https://anre.md/energie-electrica-3-290">Действующие тарифы ANRE</a> - постановления 214, 215, 221 и 222 от марта 2026 года: передача 24,5 баня, распределение 69,2, энергия 201, итог для населения 356 баней за киловатт-час</div>
    <div><a href="https://rdp.moldelectrica.md/ro/finances/electricity_procurement">Тендеры Молдэлектрики</a> - протоколы определения победителя за 2017-2021 годы. Отсюда прямые цены за 2019 и 2020 годы с прямым указанием источника энергии</div>
    <div><a href="https://premierenergy.md/cunoaste-ne/achizitii-pe/achizitii-anuale-de-energie/">Закупки Premier Energy</a> - помесячные сообщения компании и таблица цен со столбцом «источник», где источником прямо названа Молдавская ГРЭС</div>
    <div><a href="https://istmat.org/node/67664">Статистические ежегодники Приднестровья</a> - выпуски 2016, 2017, 2019, 2020 и 2021 годов. Электробаланс, использование сетевого газа, товарная структура внешней торговли. Издания перекрываются по годам, все пересечения сверены, расхождений не найдено</div>
    <div><a href="https://www.energie.gov.md/sites/default/files/20230602_final_report_wr_fra_rev117725439.1.pdf">Аудит долга Молдовагаза</a> - Wikborg Rein и Forensic Risk Alliance, 2 июня 2023 года, 79 страниц. Отсюда суммы долга по обоим берегам и структура правобережной задолженности</div>
    <div><a href="https://www.zdg.md/">Договоры Энергокома с МГРЭС</a> - девять документов, опубликованных изданием Ziarul de Garda 24 января 2023 года. Цены, объёмы, условия оплаты за 2022 год</div>
    <div><a href="https://ember-energy.org/data/european-wholesale-electricity-price-data/">Ember</a> - оптовые биржевые цены на электроэнергию в Европе, помесячно с 2015 года. Использована Румыния</div>
  </div>
  <div class="limits">
    <h3 style="margin-bottom:.8rem">Чего эти данные не доказывают</h3>
    <ul>
      <li>Расход газа на киловатт-час - это <b>норма</b>, утверждённая правительством Приднестровья, а не замер. По определению самой инструкции это верхняя допустимая граница, а не факт.</li>
      <li>Норма утверждена на 2016 год. Более поздние приказы существуют, но их текстов у нас нет.</li>
      <li>Доля 43,4% посчитана по объёмам газа за 2010-2020 годы и перенесена на весь долг. Это оценка, а не строка из документа.</li>
      <li>Румынская биржевая цена на графике - мера стоимости, а не упущенная выгода. До постройки линии Вулкэнешты-Кишинёв столько импортировать было физически нельзя.</li>
      <li>Накопленная скидка сложена за тринадцать лет, а не за весь период: с 2011 по 2020 год Молдова не подавала данные в таможенную базу ООН, и цены импорта газа за эти годы нет ни у кого.</li>
      <li>Выгода и долг посчитаны по разным основаниям. Выгода - по всему газу, который покупал правый берег. Долг - по газу левого берега, сожжённому на электричество. Это сопоставление итогов одних и тех же отношений с одним поставщиком, а не вычитание внутри одного счёта.</li>
      <li>Первый сценарий, где газ достаётся бесплатно, опирается на цену из договора 489-22 за декабрь 2022 года (73 доллара за мегаватт-час) и добавляет транспорт газа. Если взять последний контракт 2024 года (66 долларов) и транспорт не считать, выходит 269 лей вместо 292. На выводы это не влияет: обе цифры далеко ниже любого сценария с платным газом.</li>
      <li>Цены 2019, 2020, 2023 и 2024 годов включают наценку посредника - Энергокома. Цены 2011-2013, 2016, 2017 и 2021 годов - прямые договоры с МГРЭС. Это два разных ряда.</li>
    </ul>
  </div>
  <p class="dimmer" style="margin-top:2rem;max-width:46rem">Ссылки на документы ведут на Google Диск.
  Если какая-то из них перестанет открываться, напишите - выложу заново.</p>
  <p class="sign"><a class="me" href="https://www.facebook.com/vivlont" target="_blank" rel="noopener">Владимир Тернавский</a>. Расчёты, исходные файлы и таблицу со всеми фактами отдам любому, кто попросит - напишите.</p>
</div></footer>
'''


# ---------------------------------------------------------------- новые секции
SK = D["skidka"]
SEC_SKIDKA = sec(
    "20 лет дешевле Европы. Потом линия перешла ноль",
    "<p>Сколько Молдова платила за газ по сравнению с европейским индексом. Ниже нуля - платили меньше "
    "европейцев, выше - больше. Скидка была настоящей и большой. И она закончилась.</p>",
    fig("p-skidka", plots.skidka_plot(D),
        '<div class="legend"><span><i style="background:var(--teal)"></i>дешевле Европы</span>'
        '<span><i style="background:var(--amber)"></i>дороже Европы</span></div>',
        "В 2005 году Молдова платила за тысячу кубометров 80 долларов при европейских 231. В 2021-м - 311 при 588. "
        "А в 2023-м уже 731 при европейских 478. Причина переворота простая: газ теперь покупается малыми объёмами "
        "и через несколько границ, и это дороже биржи. Серым закрыты 2011-2020 годы: Молдова в этот период "
        "не подавала данные в таможенную базу ООН. Год 2016 выброшен отдельно: там количество занижено примерно "
        "в семь раз, и в подсчёты этот год не входит."),
    sid="skidka", nav="Скидка на газ")

NA = D["nacenka"]
TD = sorted(D["tarify_do2020"], key=lambda t: t["y"])   # тарифные решения по центру страны
# Месяц берём из цитаты в реестре, привязка идёт по году, а не по порядку в списке.
# Раньше здесь был отдельный список дат, и после добавления 2010 года весь ряд
# съехал на одну позицию: цифры встали не к своим датам.
TD_KOGDA = {2012: "с мая 2012-го", 2017: "с марта 2017-го",
            2018: "с июля 2018-го", 2019: "с августа 2019-го"}


def _tarif_stroka(t):
    kogda = TD_KOGDA.get(t["y"], f"в {t['y']} году")
    return f"{t['v']/100:.2f} лея {kogda}".replace(".", ",")

SEC_NACENKA = sec(
    "Между закупкой и вашей розеткой цена растёт на 30% и больше",
    "<p>Зелёная линия - по какой цене электричество покупали компании-поставщики. Оранжевая - по какой "
    "продали конечным потребителям. Разница между ними это доставка по проводам, работа поставщика и налоги.</p>",
    fig("p-nacenka", plots.nacenka_plot(D),
        '<div class="legend"><span><i style="background:var(--teal)"></i>по этой цене покупали компании</span>'
        '<span><i style="background:var(--amber)"></i>по этой продавали потребителям</span>'
        '<span><i style="background:transparent;border:2px solid var(--amber-lit);height:.8rem;'
        'width:.8rem;transform:rotate(45deg);border-radius:2px"></i>тариф с конкретной даты, '
        'другой показатель</span></div>',
        "Леи за киловатт-час, из годовых отчётов регулятора. Важно: оранжевая линия - это средняя цена по всем "
        "потребителям сразу, вместе с заводами, которые платят заметно меньше. Дома платят больше средней: "
        "в 2020 году средняя была 1,76 лея, а в квитанции у людей стояло около 1,9. "
        "Смотрите не на сам разрыв, а на то, как он скачет: 81% в 2020 году, 36% в 2024-м, 54% в 2025-м. "
        "Это не плавный рост расходов, а разные тарифные решения в разные годы. "
        "Ромбы слева - это тоже цена для потребителей, но другая по смыслу, поэтому они "
        "не соединены со сплошной линией. Средневзвешенную за год регулятор начал публиковать "
        "только с 2020 года. До этого он публиковал утверждённый тариф конкретной компании "
        "с конкретной даты: для центра страны " +
        ", ".join(_tarif_stroka(t) for t in TD) +
        ". Годы 2011 и 2013-2016 остаются пустыми: за них в отчётах есть только "
        "картинка графика без таблицы, снять числа не с чего."),
    sid="nacenka", nav="Закупка и розница")

BG = D["byt_gaz"]
SEC_BYT = sec(
    "Страна перестала топить",
    f'<p class="claim">В 2021 году молдавские дома сожгли <b>480,5 миллиона кубометров</b> газа. '
    f'В 2023-м - <b>286,9</b>. Падение на <em>40 процентов</em>. Четыре года спустя потребление '
    f'всё ещё на треть ниже пика.</p>',
    fig("p-byt", plots.byt_plot(D),
        '<div class="legend"><span><i style="background:var(--ink-3)"></i>до пика</span>'
        '<span><i style="background:var(--amber)"></i>пик 2021 года</span>'
        '<span><i style="background:var(--teal)"></i>после подорожания</span></div>',
        "Миллионы кубометров в год, данные Национального бюро статистики, приведены к 20 градусам Цельсия. "
        "Честная оговорка: рост до 2021 года частично объясняется газификацией новых домов, а падение после - "
        "не только ценой, но и тёплыми зимами. Но масштаб такой, что одной погодой его не закрыть. Это самая "
        "человеческая цифра во всём материале: за ней закрытые комнаты и котлы, которые включают пореже."))

SEC_DOLYA = sec(
    "Три четверти всего электричества на правом берегу шло от одного поставщика",
    "<p>Откуда бралось электричество, которым пользовался правый берег. Три источника, в сумме сто процентов. "
    "Провал 2017 года - тот самый конкурс. Ноль в 2025-м - утро 1 января.</p>",
    fig("p-dolya", plots.dolya_plot(D),
        '<div class="stack-leg"><span><i style="background:var(--amber)"></i>Молдавская ГРЭС</span>'
        '<span><i style="background:var(--violet)"></i>импорт из Румынии и Украины</span>'
        '<span><i style="background:var(--teal)"></i>станции на правом берегу</span></div>',
        "Проценты от всего, что правый берег получил за год, по данным Национального бюро статистики. "
        "Максимум у МГРЭС - 78,6% в 2016 году. Единственный серьёзный провал до 2025-го - 53,5% в 2017-м, "
        "когда конкурс выиграла украинская компания, и её долю видно фиолетовым. Свои станции на правом берегу "
        "все эти годы давали примерно пятую часть и ни разу не поднимались выше 26%. "
        "В декабре 2024 года Кишинёв купил у МГРЭС 179 358 мегаватт-часов, в январе 2025-го - ноль."),
    sid="dolya", nav="Откуда электричество")

def bani_slovo(v):
    """Согласование числа со словом «бан». Дробные - родительный падеж
    единственного числа: 71,71 бана. Целые - по последним цифрам."""
    if abs(v - round(v)) > 1e-9:
        return "бана"
    n = int(round(v))
    if 11 <= n % 100 <= 14:
        return "бань"
    return {1: "бан", 2: "бана", 3: "бана", 4: "бана"}.get(n % 10, "бань")


T10 = D["tarify2010"]
_mx = max(t["bani"] for t in T10)
t10_bars = "".join(
    '<div class="bar-lab">{lab}</div>\n'
    '     <div class="bar-row tipp" tabindex="0" data-tip="{tip}">'
    '<div class="bar-track"><div class="bar-fill nojs" style="width:{w:.0f}%;background:{col}"></div></div>'
    '<span class="bar-val" style="color:{txt}">{v}<s>лея</s></span></div>'.format(
        lab=t["lab"], w=t["bani"] / _mx * 100,
        col=("var(--teal)" if t["bani"] < 50 else
             ("var(--amber)" if "Молдавская" in t["lab"] else "var(--ink-3)")),
        txt=("var(--teal)" if t["bani"] < 50 else
             ("var(--amber-lit)" if "Молдавская" in t["lab"] else "var(--ink-2)")),
        v=f'{t["bani"]/100:.2f}'.replace(".", ","),
        tip="{}|{} лея за киловатт-час, это {} {}. В долларах того года - {} цента|{}".format(
            t["lab"], f'{t["bani"]/100:.2f}'.replace(".", ","),
            f'{t["bani"]:.2f}'.rstrip("0").rstrip(".").replace(".", ","),
            bani_slovo(t["bani"]),
            f'{t["cent"]:.2f}'.replace(".", ","), t["vid"]))
    for t in T10)
NR = D["normativy"]
_mn = max(x["v"] for x in NR)
nr_bars = "".join(
    f'''<div class="bar-lab">{x["lab"]}</div>
     <div class="bar-row"><div class="bar-track"><div class="bar-fill nojs" style="width:{x["v"]/_mn*100:.0f}%;background:{"var(--amber)" if "Молдавская" in x["lab"] else "var(--teal)"}"></div></div><span class="bar-val" style="color:{"var(--amber-lit)" if "Молдавская" in x["lab"] else "var(--teal)"}">{str(x["v"]).replace(".", ",")}<s>г у.т.</s></span></div>'''
    for x in NR)

G100 = D["gaz100"]
SEC_TOPLIVO = sec(
    "Гидростанция дешевле в 4 раза. Вот сколько в цене занимает топливо",
    "<p>Два документа, которые объясняют всё остальное. Сначала - сколько стоил киловатт-час у разных станций "
    "в январе 2010 года. Потом - сколько газа нужно сжечь, чтобы получить 100 киловатт-часов.</p>",
    f'''<div class="cmp" style="grid-template-columns:1fr"><div class="cmp-item"><h3>Цена киловатт-часа в январе 2010</h3>
    <p class="cmp-when">лея за киловатт-час, из решения регулятора о тарифах. Наведите на строку, чтобы увидеть ту же цену в банях и в центах</p>{t10_bars}
    <p class="verdict">Гидроузел Костешты на Пруте - единственный в списке, кто не жжёт топливо вообще. Он в четыре раза дешевле МГРЭС и почти в восемь раз дешевле ТЭЦ-1 в Кишинёве. Вся разница между ними - это стоимость сожжённого газа.</p></div></div>
    <figure style="margin-top:2.4rem"><div class="plot" id="p-gaz100"><noscript>{plots.gaz100_plot(D)}</noscript></div>
    <figcaption class="cap">Сколько кубометров газа нужно сжечь на 100 киловатт-часов. Это не измеренный расход, а норма, которую утвердило само правительство Приднестровья приказом на 2016 год - для всех трёх станций левого берега сразу. Молдавская ГРЭС тратит больше всех: 30,5 кубометра там, где соседям хватает 25-26. То есть она худшая из трёх в собственном регионе, по документу того правительства, которое её защищает.</figcaption></figure>''',
    sid="toplivo", nav="Топливо в цене")

SEC_REESTR = sec(
    "Откуда взялись эти цифры",
    "<p>Каждое число на этой странице либо взято из документа напрямую, либо посчитано "
    "по документам. Оставался вопрос, насколько велика может быть погрешность в тех, "
    "что посчитаны. Чтобы это выяснить, я поставил опыт на тех годах, где цена и так "
    "известна из договора. Результат ниже.</p>",
    f'''<figure><div class="plot" id="p-kalib"><noscript>{plots.kalib_plot(D)}</noscript></div>
    <div class="legend"><span><i style="background:var(--teal);height:.85rem;width:.85rem;border-radius:50%"></i>расхождение до 5%</span><span><i style="background:var(--amber);height:.85rem;width:.85rem;border-radius:50%"></i>от 5 до 9%</span></div>
    <figcaption class="cap cap2">За часть лет договоров нет вообще - их не публиковали. Для этих лет цену пришлось считать окольным путём: сколько денег Приднестровье выручило за энергетический экспорт, делённое на то, сколько электричества оно вывезло. Вопрос был в том, можно ли такому счёту верить. Проверка простая: взять одиннадцать лет, где известна и настоящая цена из договора, и результат окольного счёта, и посмотреть, насколько они расходятся. Каждая строка - один такой год. Закрашенная точка это цена из договора, полая - то, что дал окольный счёт. Чем короче отрезок между ними, тем точнее совпало; справа расхождение подписано в процентах. Самое большое за одиннадцать лет - девять процентов, в 2018 году. Значит, окольному счёту верить можно, и погрешность известна.</figcaption>
    </figure>
    <details class="dt">
      <summary><span class="dt-t">Открыть таблицу фактов</span><span class="dt-n">{D["meta"]["reestr_zapisey"]} записей с поиском</span></summary>
      <div class="dt-body">
        <p class="cap" style="max-width:64ch;margin-bottom:.8rem">Вся база: {D["meta"]["reestr_zapisey"]} записей, у каждой
        указан файл-источник, точное место в нём и способ расчёта. Наберите слово или год,
        чтобы найти нужное.</p>
        <p class="cap" style="max-width:64ch;margin-bottom:1.1rem">В таблице встречаются служебные
        слова из первичных документов. <b>Лицензиат</b> - компания, у которой есть лицензия на продажу
        электричества или газа. <b>Бань</b> - сотая часть лея. <b>кВт·ч</b> - киловатт-час, столько
        тратит стоваттная лампочка за десять часов.</p>
        <p class="rhint">Таблица широкая: на телефоне её нужно листать вбок.</p>
        <div id="reestr"><noscript><p class="cap">Для таблицы нужен JavaScript. Полный файл со всеми фактами лежит рядом в репозитории: data.json</p></noscript></div>
      </div>
    </details>''',
    sid="reestr-sec", nav="База фактов")

# SEC6, SEC7 и SEC_BYT собраны, но в страницу не включены: убраны по правкам автора.
# Оставлены в коде, чтобы вернуть одним словом.

# Липкого указателя разделов на странице нет: он дёргал прокрутку. Якоря id
# у секций оставлены - на них можно давать прямые ссылки из поста и комментариев.

JS = open(f"{HERE}/site.js", encoding="utf-8").read()
html = (HEAD + HERO + SEC1 + SEC2 + SEC_SKIDKA + SEC_NACENKA + SEC3 +
        SEC_DOLYA + SEC_TOPLIVO + SEC4 + SEC5 + SEC_REESTR + FOOT +
        "\n<script>\nconst D = " + json.dumps(D, ensure_ascii=False) + ";\n" + JS + "\n</script>\n</body></html>\n")

html = html.replace("—", "-")
open(f"{OUT}/index.html", "w", encoding="utf-8").write(html)
json.dump(D, open(f"{OUT}/data.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
if os.path.isdir(REPO):                       # сразу в репозиторий GitHub Pages
    open(f"{REPO}/index.html", "w", encoding="utf-8").write(html)
    json.dump(D, open(f"{REPO}/data.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("записано и в репозиторий:", REPO)
print("index.html:", len(html), "байт")
print("длинных тире:", html.count("—"))
