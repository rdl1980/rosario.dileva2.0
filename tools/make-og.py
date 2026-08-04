#!/usr/bin/env python3
"""Genera le card Open Graph 1200x630 dell'Officina della Narrazione.

Niente foto: l'identita' della collana e' tipografica (carta crema, inchiostro,
rosso mattone, rombo separatore), e la card la ripete cosi' com'e'. Rigenerare
con:  python tools/make-og.py
"""

import os
from PIL import Image, ImageDraw, ImageFont

W, H = 1200, 630
CARTA = (236, 231, 223)
INCHIOSTRO = (38, 33, 30)
MATTONE = (128, 36, 32)
GRIGIO = (122, 112, 104)

FONTS = r"C:\Windows\Fonts"
SERIF_B = os.path.join(FONTS, "cambriab.ttf")   # titoli
SERIF_I = os.path.join(FONTS, "cambriai.ttf")   # sottotitoli
SERIF_R = os.path.join(FONTS, "cambria.ttc")    # testo


def font(path, size):
    return ImageFont.truetype(path, size)


def larghezza(d, testo, f, tracking=0):
    if not tracking:
        return d.textbbox((0, 0), testo, font=f)[2]
    return sum(d.textbbox((0, 0), c, font=f)[2] + tracking for c in testo) - tracking


def scrivi_tracked(d, xy, testo, f, colore, tracking):
    """PIL non ha la spaziatura tra lettere: la si compone a mano."""
    x, y = xy
    for c in testo:
        d.text((x, y), c, font=f, fill=colore)
        x += d.textbbox((0, 0), c, font=f)[2] + tracking


def rombo(d, cx, cy, r, colore):
    d.polygon([(cx, cy - r), (cx + r, cy), (cx, cy + r), (cx - r, cy)], fill=colore)


def card(nome, kicker, righe, sottotitolo, piede):
    img = Image.new("RGB", (W, H), CARTA)
    d = ImageDraw.Draw(img)

    # cornice sottile, come il filetto di una copertina
    d.rectangle([28, 28, W - 29, H - 29], outline=MATTONE, width=2)
    d.rectangle([36, 36, W - 37, H - 37], outline=(214, 206, 196), width=1)

    f_kick = font(SERIF_R, 24)
    f_tit = font(SERIF_B, 78)
    f_sub = font(SERIF_I, 34)
    f_pie = font(SERIF_R, 26)

    # kicker centrato, maiuscoletto spaziato
    tr = 6
    kw = larghezza(d, kicker, f_kick, tr)
    scrivi_tracked(d, ((W - kw) / 2, 96), kicker, f_kick, MATTONE, tr)

    # rombo separatore
    rombo(d, W / 2, 156, 7, MATTONE)

    # titolo su piu' righe, centrato
    y = 200
    for riga in righe:
        rw = larghezza(d, riga, f_tit)
        d.text(((W - rw) / 2, y), riga, font=f_tit, fill=INCHIOSTRO)
        y += 92

    # filetto corto
    d.line([(W / 2 - 60, y + 26), (W / 2 + 60, y + 26)], fill=MATTONE, width=2)

    sw = larghezza(d, sottotitolo, f_sub)
    d.text(((W - sw) / 2, y + 54), sottotitolo, font=f_sub, fill=GRIGIO)

    tr2 = 4
    pw = larghezza(d, piede, f_pie, tr2)
    scrivi_tracked(d, ((W - pw) / 2, H - 96), piede, f_pie, GRIGIO, tr2)

    out = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), nome)
    img.save(out, "PNG", optimize=True)
    print("%s  %d KB" % (nome, os.path.getsize(out) // 1024))


card(
    "og-officina.png",
    "OFFICINA DELLA NARRAZIONE",
    ["Strumenti, metodo e strategia", "per scrittori contemporanei"],
    "I manuali di scrittura di Rosario Di Leva",
    "OFFICINA.ROSARIODILEVA.COM",
)

card(
    "og-kit.png",
    "OFFICINA DELLA NARRAZIONE",
    ["Le 17 schede per", "revisionare il tuo romanzo"],
    "Kit gratuito in PDF compilabile e stampabile",
    "OFFICINA.ROSARIODILEVA.COM/KIT",
)
