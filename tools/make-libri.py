#!/usr/bin/env python3
"""Genera le pagine dei libri dell'Officina della Narrazione.

Fonti:
  tools/libri-amazon.json  dati verificati su amazon.it (ASIN, ISBN, pagine, date, recensioni)
  tools/libri-testi.json   testi della pagina, indice, estratto, copertina sorgente

Produce:
  libri/<slug>.html                 una pagina per libro
  libri/copertine/<slug>-{320,640}.webp
  libri/og/<slug>.jpg               card Open Graph 1200x630
  index.html                        catalogo e JSON-LD fra i marcatori GENERATO
  llms.txt                          elenco dei libri fra i marcatori GENERATO
  sitemap.xml

Rigenerare con:  python tools/make-libri.py
Le pagine generate non vanno ritoccate a mano: si cambiano i due JSON e si rilancia.
"""

import json
import os
import re
from datetime import date
from html import escape

from PIL import Image, ImageDraw, ImageFont

RADICE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SITO = "https://officina.rosariodileva.com"
AUTORE = "https://rosariodileva.com/autore#author"
COLLANA = SITO + "/#collana"
AMAZON = "https://www.amazon.it/dp/"

MESI = ["gennaio", "febbraio", "marzo", "aprile", "maggio", "giugno", "luglio",
        "agosto", "settembre", "ottobre", "novembre", "dicembre"]


def leggi(nome):
    with open(os.path.join(RADICE, "tools", nome), encoding="utf-8") as f:
        return json.load(f)


def scrivi(percorso, testo):
    percorso = os.path.join(RADICE, percorso)
    os.makedirs(os.path.dirname(percorso), exist_ok=True)
    with open(percorso, "w", encoding="utf-8", newline="\n") as f:
        f.write(testo)


def data_it(iso, giorno=True):
    a, m, g = (int(x) for x in iso.split("-"))
    return ("%d %s %d" % (g, MESI[m - 1], a)) if giorno else ("%s %d" % (MESI[m - 1], a))


def e(testo):
    return escape(testo, quote=True)


def url_libro(l):
    return "%s/libri/%s" % (SITO, l["slug"])


def id_libro(l):
    return url_libro(l) + "#book"


def etichetta(l):
    if l["key"] == "wb":
        return "volume %02d · quaderno di esercizi" % l["vol"]
    if l["key"] == "agg":
        return "aggiornamento 2026 · %s" % l["fase"]
    if l["vol"]:
        return "volume %02d · %s" % (l["vol"], l["fase"])
    return "officina della narrazione · %s" % l["fase"]


def numerati(libri):
    return sorted((l for l in libri if l["vol"]), key=lambda l: l["vol"])


def fuori_numero(libri):
    return [l for l in libri if not l["vol"]]


# ── Copertine ────────────────────────────────────────────────

def copertine(l, t):
    """Due larghezze in webp: 320 per lo schermo normale, 640 per il retina."""
    src = Image.open(t["copertina"]).convert("RGB")
    misure = {}
    for w in (320, 640, 144):
        h = round(src.height * w / src.width)
        img = src.resize((w, h), Image.LANCZOS)
        rel = "libri/copertine/%s-%d.webp" % (l["slug"], w)
        os.makedirs(os.path.join(RADICE, "libri", "copertine"), exist_ok=True)
        img.save(os.path.join(RADICE, rel), "WEBP", quality=82, method=6)
        misure[w] = (w, h)
    return src, misure


# ── Card Open Graph ──────────────────────────────────────────

CARTA = (236, 231, 223)
INCHIOSTRO = (38, 33, 30)
MATTONE = (128, 36, 32)
GRIGIO = (122, 112, 104)
FONTS = r"C:\Windows\Fonts"


def font(nome, size):
    return ImageFont.truetype(os.path.join(FONTS, nome), size)


def a_capo(d, testo, f, larghezza):
    righe, riga = [], ""
    for parola in testo.split():
        prova = (riga + " " + parola).strip()
        if d.textbbox((0, 0), prova, font=f)[2] <= larghezza:
            riga = prova
        else:
            righe.append(riga)
            riga = parola
    righe.append(riga)
    return righe


def card_og(l, cover):
    W, H = 1200, 630
    img = Image.new("RGB", (W, H), CARTA)
    d = ImageDraw.Draw(img)
    d.rectangle([28, 28, W - 29, H - 29], outline=MATTONE, width=2)
    d.rectangle([36, 36, W - 37, H - 37], outline=(214, 206, 196), width=1)

    # copertina a destra, con un'ombra appena accennata
    ch = 470
    cw = round(cover.width * ch / cover.height)
    c = cover.resize((cw, ch), Image.LANCZOS)
    cx, cy = W - 90 - cw, (H - ch) // 2
    d.rectangle([cx + 8, cy + 10, cx + cw + 8, cy + ch + 10], fill=(214, 206, 196))
    img.paste(c, (cx, cy))
    d.rectangle([cx, cy, cx + cw - 1, cy + ch - 1], outline=(199, 193, 184), width=1)

    x, testo_w = 90, cx - 90 - 60
    kicker = "OFFICINA DELLA NARRAZIONE" + (" · VOL. %d" % l["vol"] if l["vol"] else "")
    fx = x
    fk = font("cambria.ttc", 22)
    for ch_ in kicker:
        d.text((fx, 96), ch_, font=fk, fill=MATTONE)
        fx += d.textbbox((0, 0), ch_, font=fk)[2] + 4

    size = 64
    while True:
        ft = font("cambriab.ttf", size)
        righe = a_capo(d, l["titolo"], ft, testo_w)
        if len(righe) <= 3 or size <= 44:
            break
        size -= 4
    y = 150
    for r in righe:
        d.text((x, y), r, font=ft, fill=INCHIOSTRO)
        y += int(size * 1.18)
    d.line([(x, y + 22), (x + 110, y + 22)], fill=MATTONE, width=2)

    fs = font("cambriai.ttf", 28)
    y += 48
    for r in a_capo(d, l["sottotitolo"], fs, testo_w)[:4]:
        d.text((x, y), r, font=fs, fill=GRIGIO)
        y += 38

    fp = font("cambria.ttc", 22)
    d.text((x, H - 92), "Rosario Di Leva · officina.rosariodileva.com", font=fp, fill=GRIGIO)

    rel = "libri/og/%s.jpg" % l["slug"]
    os.makedirs(os.path.join(RADICE, "libri", "og"), exist_ok=True)
    img.save(os.path.join(RADICE, rel), "JPEG", quality=86, optimize=True, progressive=True)


# ── JSON-LD ──────────────────────────────────────────────────

def nodo_libro(l, t, completo=True):
    n = {
        "@type": "Book",
        "@id": id_libro(l),
        "name": l["titolo"],
        "alternateName": "%s. %s" % (l["titolo"], l["sottotitolo"]),
        "url": url_libro(l),
        "inLanguage": "it",
        "author": {"@id": AUTORE},
        "isPartOf": {"@id": COLLANA},
    }
    if l["vol"]:
        n["position"] = l["vol"]
    if not completo:
        n["description"] = t["riga"]
        return n
    n["description"] = t["meta_description"]
    n["image"] = "%s/libri/copertine/%s-640.webp" % (SITO, l["slug"])
    n["genre"] = "Manuale di scrittura"
    edizioni = []
    if l.get("kindle"):
        k = l["kindle"]
        ed = {"@type": "Book", "bookFormat": "https://schema.org/EBook",
              "url": AMAZON + k["asin"], "datePublished": k["data"],
              "identifier": {"@type": "PropertyValue", "propertyID": "ASIN", "value": k["asin"]}}
        if k.get("pagine"):
            ed["numberOfPages"] = k["pagine"]
        edizioni.append(ed)
    c = l["cartaceo"]
    edizioni.append({"@type": "Book", "bookFormat": "https://schema.org/Paperback",
                     "url": AMAZON + c["asin"], "isbn": c["isbn"].replace("-", ""),
                     "numberOfPages": c["pagine"], "datePublished": c["data"]})
    n["workExample"] = edizioni
    n["datePublished"] = min(x["datePublished"] for x in edizioni)
    base = l.get("compagno_di") or l.get("aggiorna")
    if base:
        n["isBasedOn"] = {"@id": "%s/libri/%s#book" % (SITO, t["_slug_di"][base])}
    return n


def schema_pagina(l, t):
    grafo = [
        {"@type": "WebPage", "@id": url_libro(l) + "#page", "url": url_libro(l),
         "name": titolo_pagina(l), "inLanguage": "it-IT",
         "isPartOf": {"@id": SITO + "/#website"}, "about": {"@id": id_libro(l)},
         "primaryImageOfPage": "%s/libri/copertine/%s-640.webp" % (SITO, l["slug"])},
        nodo_libro(l, t),
        {"@type": "BreadcrumbList", "itemListElement": [
            {"@type": "ListItem", "position": 1, "name": "Officina della Narrazione", "item": SITO + "/"},
            {"@type": "ListItem", "position": 2, "name": "La collana", "item": SITO + "/#collana"},
            {"@type": "ListItem", "position": 3, "name": l["titolo"], "item": url_libro(l)}]},
    ]
    return json.dumps({"@context": "https://schema.org", "@graph": grafo}, ensure_ascii=False, indent=2)


# ── Pagina del libro ─────────────────────────────────────────

def titolo_pagina(l):
    return "%s — Rosario Di Leva" % l["titolo"]


TESTA = """<!doctype html>
<html lang="it">
<head>
<meta charset="utf-8" />
<meta name="viewport" content="width=device-width, initial-scale=1" />
<meta name="theme-color" content="#ECE7DF" />
<link rel="icon" href="/favicon.svg" type="image/svg+xml" />
<link rel="icon" href="/favicon-32.png" sizes="32x32" type="image/png" />
<link rel="apple-touch-icon" href="/apple-touch-icon.png" />
<title>{title}</title>
<meta name="description" content="{desc}" />
<link rel="canonical" href="{url}" />

<meta property="og:type" content="book" />
<meta property="og:url" content="{url}" />
<meta property="og:title" content="{og_title}" />
<meta property="og:description" content="{desc}" />
<meta property="og:locale" content="it_IT" />
<meta property="og:image" content="{og_img}" />
<meta property="og:image:width" content="1200" />
<meta property="og:image:height" content="630" />
<meta property="og:image:alt" content="Copertina di {og_title}" />
<meta property="book:author" content="https://rosariodileva.com/autore" />
<meta property="book:isbn" content="{isbn}" />
<meta property="book:release_date" content="{data}" />
<meta name="twitter:card" content="summary_large_image" />
<meta name="twitter:image" content="{og_img}" />

<link rel="preload" as="image" href="/libri/copertine/{slug}-320.webp" imagesrcset="/libri/copertine/{slug}-320.webp 320w, /libri/copertine/{slug}-640.webp 640w" imagesizes="(max-width: 760px) 230px, 300px" />
<link rel="stylesheet" href="/styles.css" />

<script type="application/ld+json">
{schema}
</script>
</head>
<body>

<header class="site-head">
  <div class="wrap">
    <a class="brand" href="/">
      Officina della Narrazione
      <em>manuali di scrittura</em>
    </a>
    <nav class="site-nav" aria-label="Navigazione principale">
      <a href="/#collana">La collana</a>
      <a href="/kit">Le 17 schede</a>
      <a href="https://www.amazon.it/dp/B0GPM7S8NZ" target="_blank" rel="noopener">Su Amazon</a>
    </nav>
  </div>
</header>

<main>
"""

PIEDE = """
</main>

<footer class="site-foot">
  <div class="wrap">
    <span>© 2026 Rosario Di Leva · Officina della Narrazione</span>
    <span><a href="/privacy">Privacy</a> · <a href="https://rosariodileva.com" target="_blank" rel="noopener">rosariodileva.com</a></span>
  </div>
</footer>

</body>
</html>
"""

ROMBO = '\n  <div class="rhombus" aria-hidden="true"><span></span><span></span><span></span></div>\n'


def lista(voci):
    return "\n".join("            <li>%s</li>" % e(v) for v in voci)


def blocco_dati(l):
    righe = []
    c, k = l["cartaceo"], l.get("kindle")
    formati = "Kindle e copertina flessibile" if k else "Solo copertina flessibile"
    righe.append(("Formati", formati))
    pag = "%d nel cartaceo" % c["pagine"]
    righe.append(("Pagine", pag))
    righe.append(("Formato", c["formato"]))
    righe.append(("Uscita", data_it(min(c["data"], k["data"]) if k else c["data"])))
    righe.append(("ISBN", c["isbn"]))
    return "\n".join("          <dt>%s</dt><dd>%s</dd>" % (a, e(b)) for a, b in righe)


def blocco_cta(l):
    c, k = l["cartaceo"], l.get("kindle")
    btn = []
    if k:
        btn.append('<a class="btn btn-primary" href="%s%s" target="_blank" rel="noopener">Kindle su Amazon</a>' % (AMAZON, k["asin"]))
        btn.append('<a class="btn btn-ghost" href="%s%s" target="_blank" rel="noopener">Copertina flessibile</a>' % (AMAZON, c["asin"]))
    else:
        btn.append('<a class="btn btn-primary" href="%s%s" target="_blank" rel="noopener">Copertina flessibile su Amazon</a>' % (AMAZON, c["asin"]))
    return "\n          ".join(btn)


def blocco_indice(t):
    parti = t["indice"]
    con_parti = any(p.get("parte") for p in parti)
    if not con_parti:
        voci = [c for p in parti for c in p["capitoli"]]
        return ('      <div class="indice indice-unica">\n        <ol>\n%s\n        </ol>\n      </div>'
                % "\n".join("          <li>%s</li>" % e(v) for v in voci))
    out = ['      <div class="indice">']
    for p in parti:
        out.append('        <div class="indice-parte">')
        if p.get("parte"):
            out.append("          <h3>%s</h3>" % e(p["parte"]))
        out.append("          <ol>")
        out.extend("            <li>%s</li>" % e(c) for c in p["capitoli"])
        out.append("          </ol>")
        out.append("        </div>")
    out.append("      </div>")
    return "\n".join(out)


def blocco_recensioni(l):
    rec = l.get("recensioni") or []
    if not rec:
        return ""
    fig = []
    for r in rec:
        fig.append("""        <figure class="recensione">
          <blockquote><p>%s</p></blockquote>
          <figcaption>%s, %d stelle su 5 · %s · <a href="%s%s" target="_blank" rel="noopener">su Amazon</a></figcaption>
        </figure>""" % (e(r["testo"]), e(r["autore"]), r["stelle"], data_it(r["data"], giorno=False),
                        AMAZON, (l.get("kindle") or l["cartaceo"])["asin"]))
    return """
  <section>
    <div class="wrap measure">
      <span class="label">dicono del libro</span>
      <h2>Dalle recensioni dei lettori.</h2>
      <div class="recensioni">
%s
      </div>
    </div>
  </section>
""" % "\n".join(fig)


def blocco_schede(t):
    if not t.get("schede"):
        return ""
    voci = "\n".join('            <li>%s <span class="muted">· %s</span></li>' % (e(s["scheda"]), e(s["titolo_capitolo"]))
                     for s in t["schede"])
    return """
  <section class="alt">
    <div class="wrap">
      <span class="label">le schede del libro</span>
      <h2>Diciassette schede, in ordine di lavoro.</h2>
      <p class="measure muted">Nel libro sono in appendice, da fotocopiare. Qui le trovi in PDF
      compilabile e stampabile, gratis.</p>
      <ul class="schede">
%s
      </ul>
      <p style="margin-top:2rem"><a class="btn btn-primary" href="/kit?da=%s">Scarica le 17 schede</a></p>
    </div>
  </section>
""" % (voci, "revisione")


def blocco_compagni(l, libri, testi, misure):
    legati = []
    for k in testi[l["key"]].get("legati", []):
        x = next(y for y in libri if y["key"] == k)
        legati.append(x)
    if not legati:
        return ""
    card = []
    for x in legati:
        w, h = misure[x["slug"]][144]
        card.append("""        <a class="compagno" href="/libri/%s">
          <img src="/libri/copertine/%s-144.webp" width="72" height="%d" alt="" loading="lazy" />
          <div><strong>%s</strong><span>%s</span></div>
        </a>""" % (x["slug"], x["slug"], round(h / 2), e(x["titolo"]), e(testi[x["key"]]["riga"])))
    return """
  <section>
    <div class="wrap">
      <span class="label">da leggere insieme</span>
      <div class="compagni">
%s
      </div>
    </div>
  </section>
""" % "\n".join(card)


def blocco_nav(l, libri):
    serie = numerati(libri)
    if not l["vol"]:
        return """
  <section>
    <div class="wrap">
      <nav class="libro-nav" aria-label="La collana">
        <a href="/#collana"><small>torna a</small>Tutti i libri della collana</a>
      </nav>
    </div>
  </section>
"""
    i = serie.index(l)
    parti = []
    if i > 0:
        p = serie[i - 1]
        parti.append('<a class="prec" href="/libri/%s"><small>← volume %02d</small>%s</a>' % (p["slug"], p["vol"], e(p["titolo"])))
    if i < len(serie) - 1:
        s = serie[i + 1]
        parti.append('<a class="succ" href="/libri/%s"><small>volume %02d →</small>%s</a>' % (s["slug"], s["vol"], e(s["titolo"])))
    return """
  <section>
    <div class="wrap">
      <nav class="libro-nav" aria-label="Volumi vicini nella collana">
        %s
      </nav>
    </div>
  </section>
""" % "\n        ".join(parti)


# Titoletti interni agli estratti: nel libro sono intestazioni, sulla pagina diventano etichette
ETICHETTE = {"prima", "dopo", "situazione iniziale", "lettura narratologica", "errore tipico", "chiusura"}


def con_corsivi(testo):
    """Il testo arriva con <em> dai manoscritti: si fa l'escape di tutto e si ripristina solo quello."""
    return e(testo).replace("&lt;em&gt;", "<em>").replace("&lt;/em&gt;", "</em>")


def paragrafo_estratto(p):
    nudo = re.sub(r"</?em>", "", p).strip()
    if nudo.lower() in ETICHETTE:
        return '            <p class="estratto-etichetta">%s</p>' % e(nudo.lower())
    return "            <p>%s</p>" % con_corsivi(p)


def pagina(l, t, libri, testi, misure):
    c = l["cartaceo"]
    w, h = misure[l["slug"]][320]
    corpo = TESTA.format(
        title=e(titolo_pagina(l)), desc=e(t["meta_description"]), url=url_libro(l),
        og_title=e(l["titolo"]), og_img="%s/libri/og/%s.jpg" % (SITO, l["slug"]),
        isbn=c["isbn"].replace("-", ""), data=c["data"], slug=l["slug"],
        schema=schema_pagina(l, t))

    corpo += """
  <div class="wrap">
    <nav class="briciole" aria-label="Percorso">
      <a href="/">Officina</a> › <a href="/#collana">La collana</a> › <span aria-current="page">%s</span>
    </nav>
  </div>

  <section class="hero libro-hero">
    <div class="wrap libro-testa">
      <figure class="libro-cover">
        <img src="/libri/copertine/%s-320.webp"
             srcset="/libri/copertine/%s-320.webp 320w, /libri/copertine/%s-640.webp 640w"
             sizes="(max-width: 760px) 230px, 300px"
             width="%d" height="%d" fetchpriority="high"
             alt="Copertina di %s" />
      </figure>
      <div class="libro-info">
        <span class="label">%s</span>
        <h1>%s</h1>
        <p class="libro-sotto">%s</p>
        <dl class="libro-dati">
%s
        </dl>
        <p class="libro-cta">
          %s
        </p>
      </div>
    </div>
  </section>
""" % (e(l["titolo"]), l["slug"], l["slug"], l["slug"], w, h, e(l["titolo"]), e(etichetta(l)),
       e(l["titolo"]), e(l["sottotitolo"]), blocco_dati(l), blocco_cta(l))

    corpo += ROMBO
    corpo += """
  <section>
    <div class="wrap">
      <div class="libro-intro measure">
%s
      </div>
      <div class="due-colonne">
        <div>
          <span class="label">cosa trovi nel libro</span>
          <ul class="schede una-col">
%s
          </ul>
        </div>
        <div>
          <span class="label">a chi serve</span>
          <ul class="schede una-col">
%s
          </ul>
        </div>
      </div>
    </div>
  </section>
""" % ("\n".join("        <p>%s</p>" % e(p) for p in t["intro"]), lista(t["impari"]), lista(t["per_chi"]))

    corpo += """
  <section class="alt">
    <div class="wrap">
      <span class="label">indice</span>
      <h2>Cosa c'è dentro.</h2>
%s
    </div>
  </section>
""" % blocco_indice(t)

    es = t["estratto"]
    corpo += """
  <section>
    <div class="wrap">
      <div class="frame">
        <div>
          <span class="label">un estratto · dal capitolo «%s»</span>
%s          <blockquote class="estratto measure">
%s
          </blockquote>
        </div>
      </div>
    </div>
  </section>
""" % (e(es["capitolo"]),
       ('          <p class="estratto-nota measure">%s</p>\n' % e(es["didascalia"])) if es.get("didascalia") else "",
       "\n".join(paragrafo_estratto(p) for p in es["paragrafi"]))

    corpo += blocco_recensioni(l)
    corpo += blocco_schede(t)
    corpo += blocco_compagni(l, libri, testi, misure)

    if not t.get("schede"):
        corpo += """
  <section class="alt">
    <div class="wrap">
      <div class="frame">
        <div>
          <span class="label">in regalo</span>
          <h2>Le diciassette schede<br>con cui revisionare il tuo romanzo.</h2>
          <p class="measure">Le schede operative del metodo di revisione, in PDF compilabile a
          schermo e stampabile in A4. Te le mando per email, gratis.</p>
          <p><a class="btn btn-primary" href="/kit?da=%s">Ricevi le 17 schede</a></p>
        </div>
      </div>
    </div>
  </section>
""" % l["slug"]

    corpo += blocco_nav(l, libri)
    corpo += PIEDE
    scrivi("libri/%s.html" % l["slug"], corpo)


# ── Home, llms.txt e sitemap ─────────────────────────────────

def sostituisci(percorso, nome, nuovo):
    p = os.path.join(RADICE, percorso)
    testo = open(p, encoding="utf-8").read()
    rx = re.compile(r"(<!-- GENERATO:%s -->\n).*?(\n[ \t]*<!-- /GENERATO:%s -->)" % (nome, nome), re.S)
    if not rx.search(testo):
        raise SystemExit("marcatore GENERATO:%s mancante in %s" % (nome, percorso))
    testo = rx.sub(lambda m: m.group(1) + nuovo + m.group(2), testo)
    with open(p, "w", encoding="utf-8", newline="\n") as f:
        f.write(testo)


NUMERI = ["zero", "uno", "due", "tre", "quattro", "cinque", "sei", "sette", "otto", "nove", "dieci",
          "undici", "dodici", "tredici", "quattordici", "quindici"]


def home(libri, testi, meta):
    serie = numerati(libri)
    extra = fuori_numero(libri)

    voci = []
    for l in serie:
        t = testi[l["key"]]
        voci.append("""        <li class="volume">
          <span class="vol-n">%02d</span>
          <div class="vol-testo">
            <h3><a href="/libri/%s">%s</a></h3>
            <p>%s</p>
          </div>
          <span class="vol-fase">%s</span>
        </li>""" % (l["vol"], l["slug"], e(l["titolo"]), e(t["riga"]), l["fase"]))
    altri = "\n".join("""          <li>
            <a href="/libri/%s">%s</a>.
            %s
          </li>""" % (l["slug"], e(l["titolo"]), e(testi[l["key"]]["riga"])) for l in extra)

    catalogo = """      <h2>%s volumi.</h2>
      <p class="measure muted">Nell'ordine in cui sono usciti. Ognuno si regge da solo: si può
      partire dal problema che si ha adesso, non dal primo numero.</p>

      <ol class="volumi">
%s
      </ol>

      <div class="vol-extra">
        <span class="label">anche nella collana</span>
        <ul class="vol-extra-lista">
%s
        </ul>
      </div>""" % (NUMERI[len(serie)].capitalize(), "\n".join(voci), altri)
    sostituisci("index.html", "catalogo", catalogo)

    lista_items = []
    for l in serie:
        lista_items.append({"@type": "ListItem", "position": l["vol"], "url": url_libro(l),
                            "item": nodo_libro(l, testi[l["key"]], completo=False)})
    grafo = [
        {"@type": "WebSite", "@id": SITO + "/#website", "name": "Officina della Narrazione",
         "url": SITO + "/", "inLanguage": "it-IT", "publisher": {"@id": AUTORE}},
        meta["persona"],
        {"@type": "BookSeries", "@id": COLLANA, "name": "Officina della Narrazione",
         "alternateName": "Officina della Narrazione. Strumenti, Metodo e Strategia per Scrittori Contemporanei",
         "url": SITO + "/#collana", "sameAs": AMAZON + "B0GPM7S8NZ",
         "inLanguage": "it", "author": {"@id": AUTORE},
         "description": "Collana di manuali operativi di scrittura e narratologia: progettazione, stesura, revisione e pubblicazione di un romanzo.",
         "hasPart": [{"@id": id_libro(l)} for l in serie + extra]},
        {"@type": "ItemList", "name": "I volumi dell'Officina della Narrazione",
         "itemListOrder": "https://schema.org/ItemListOrderAscending",
         "numberOfItems": len(serie), "itemListElement": lista_items},
    ]
    for l in extra:
        grafo.append(nodo_libro(l, testi[l["key"]], completo=False))
    schema = json.dumps({"@context": "https://schema.org", "@graph": grafo}, ensure_ascii=False, indent=2)
    sostituisci("index.html", "schema", '<script type="application/ld+json">\n%s\n</script>' % schema)


def llms(libri, testi):
    serie = numerati(libri)
    extra = fuori_numero(libri)
    righe = ["## I volumi della collana", "",
             "%s titoli numerati, nell'ordine di uscita. Disponibili in ebook Kindle e in copertina flessibile, "
             "salvo il quaderno di esercizi (solo cartaceo). Ogni libro ha una pagina sul sito." % NUMERI[len(serie)].capitalize(), ""]
    for l in serie:
        righe.append("%d. **%s** - %s %s" % (l["vol"], l["titolo"], testi[l["key"]]["riga"], url_libro(l)))
    righe += ["", "## Anche nella collana", "", "Fuori dalla numerazione:", ""]
    for l in extra:
        righe.append("- **%s** - %s %s" % (l["titolo"], testi[l["key"]]["riga"], url_libro(l)))
    sostituisci("llms.txt", "libri", "\n".join(righe))


def sitemap(libri):
    oggi = date.today().isoformat()
    voci = [(SITO + "/", "1.0"), (SITO + "/kit", "0.9")] + [(url_libro(l), "0.8") for l in libri]
    corpo = "\n".join("""  <url>
    <loc>%s</loc>
    <lastmod>%s</lastmod>
    <priority>%s</priority>
  </url>""" % (u, oggi, p) for u, p in voci)
    scrivi("sitemap.xml", '<?xml version="1.0" encoding="UTF-8"?>\n'
           '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n%s\n</urlset>\n' % corpo)


def main():
    dati = leggi("libri-amazon.json")
    testi = leggi("libri-testi.json")
    libri = dati["libri"]
    slug_di = {l["key"]: l["slug"] for l in libri}
    for t in testi.values():
        if isinstance(t, dict):
            t["_slug_di"] = slug_di

    misure, sorgenti = {}, {}
    for l in libri:
        src, m = copertine(l, testi[l["key"]])
        misure[l["slug"]], sorgenti[l["slug"]] = m, src
        card_og(l, src)
    for l in libri:
        pagina(l, testi[l["key"]], libri, testi, misure)
        print("libri/%s.html" % l["slug"])
    home(libri, testi, testi["_home"])
    llms(libri, testi)
    sitemap(libri)
    print("home, llms.txt e sitemap aggiornati")


if __name__ == "__main__":
    main()
