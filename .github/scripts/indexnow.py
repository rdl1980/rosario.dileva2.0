#!/usr/bin/env python3
"""Avvisa i motori che supportano IndexNow (Bing, Yandex, Seznam, Naver...)
delle pagine cambiate.

Uso:
    python .github/scripts/indexnow.py                # tutte le URL della sitemap
    python .github/scripts/indexnow.py a.html b.html  # solo le pagine indicate

La chiave e' pubblica per definizione: sta nel file <chiave>.txt alla radice
del sito, ed e' cosi' che il motore verifica che la richiesta arriva da chi
controlla il dominio. Lo script la trova da solo.
"""

import glob
import json
import os
import re
import sys
import urllib.request

ENDPOINT = "https://api.indexnow.org/indexnow"


def chiave():
    for f in glob.glob("*.txt"):
        nome = os.path.basename(f)[:-4]
        if re.fullmatch(r"[0-9a-f]{32}", nome):
            with open(f, encoding="utf-8") as h:
                if h.read().strip() == nome:
                    return nome
    sys.exit("Nessun file chiave IndexNow (<32 cifre esadecimali>.txt) alla radice.")


def url_sitemap():
    with open("sitemap.xml", encoding="utf-8") as h:
        return re.findall(r"<loc>\s*([^<\s]+)\s*</loc>", h.read())


def url_di(file_html, tutte):
    """index.html -> /, kit.html -> /kit, libri/x.html -> /libri/x"""
    percorso = file_html[:-5] if file_html.endswith(".html") else file_html
    percorso = "" if percorso == "index" else percorso
    for u in tutte:
        if re.sub(r"^https?://[^/]+/", "", u).rstrip("/") == percorso:
            return u
    return None


def main(argv):
    tutte = url_sitemap()
    if not tutte:
        sys.exit("Sitemap vuota.")
    if argv:
        urls = sorted({u for u in (url_di(f, tutte) for f in argv) if u})
        if not urls:
            print("Nessuna pagina della sitemap tra i file cambiati: niente da inviare.")
            return 0
    else:
        urls = tutte

    host = re.match(r"https?://([^/]+)/", tutte[0]).group(1)
    k = chiave()
    corpo = {
        "host": host,
        "key": k,
        "keyLocation": "https://%s/%s.txt" % (host, k),
        "urlList": urls,
    }
    req = urllib.request.Request(
        ENDPOINT,
        data=json.dumps(corpo).encode("utf-8"),
        headers={"Content-Type": "application/json; charset=utf-8"},
        method="POST",
    )
    print("Invio %d URL di %s a IndexNow:" % (len(urls), host))
    for u in urls:
        print("  " + u)
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            print("Risposta: HTTP %d" % r.status)
    except urllib.error.HTTPError as e:
        # 422: URL non del dominio o chiave non valida; 403: chiave non trovata
        # all'indirizzo dichiarato (succede se il deploy non e' ancora online).
        print("::warning::IndexNow ha risposto HTTP %d: %s" % (e.code, e.read()[:300]))
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
