#!/usr/bin/env python3
"""Venezuela: laws listed by the Asamblea Nacional (https://www.asambleanacional.gob.ve,
"Leyes > Vigentes" and "Leyes > Sancionadas"); each law page links the official text (PDF of
the law as sanctioned / published in Gaceta Oficial). Plus the Constitution (CRBV 1999 with
Enmienda N° 1 of 2009) PDF published by the Asamblea.

Usage: ve_fetch.py [list|download|convert|all]
"""
import json
import os
import re
import sys
import time
import unicodedata
from datetime import date

import requests
from bs4 import BeautifulSoup

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ve_pdfmd as P  # noqa: E402

RAW = os.environ.get("RAW", "/Users/magicaltux/projects/lawcodex/_raw/ve")
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
UA = "LawCodex/1.0 (+https://github.com/LawCodex)"
SITE = "https://www.asambleanacional.gob.ve"
CONST = SITE + "/storage/documentos/botones/constitucion-nacional-20191205135853.PDF"
CONST_TS = os.environ.get("VE_CONST_TS", "20260921112152")
TODAY = date.today().isoformat()
s = requests.Session()
s.headers["User-Agent"] = UA
_last = [0.0]
DELAY = 5.0  # the site answers 403 to faster clients; stay slow


def get(url, binary=False):
    for k in range(5):
        w = DELAY - (time.time() - _last[0])
        if w > 0:
            time.sleep(w)
        _last[0] = time.time()
        try:
            r = s.get(url, timeout=(30, 600))
            if r.status_code == 200:
                return r.content if binary else r.content.decode("utf-8", "replace")
            if r.status_code == 404:
                return None
            print("HTTP", r.status_code, url, file=sys.stderr, flush=True)
            if r.status_code == 403:
                time.sleep(300 * (k + 1))  # temporary block: back off for minutes
                continue
        except requests.RequestException as e:
            print("ERR", url, e, file=sys.stderr, flush=True)
        time.sleep(10 * (k + 1))
    return None


def slug(t, n=90):
    t = unicodedata.normalize("NFKD", t).encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9]+", "-", t).strip("-")[:n].rstrip("-")


def build_list():
    laws = {}
    for cat in ("vigentes", "sancionadas"):
        page = 1
        while True:
            html = get(f"{SITE}/leyes/{cat}?page={page}")
            if not html:
                break
            links = sorted(set(re.findall(re.escape(SITE) + r"/leyes/sancionadas/[a-z0-9-]+", html)))
            new = [u for u in links if u not in laws]
            for u in links:
                laws.setdefault(u, {"url": u, "lists": []})
                if cat not in laws[u]["lists"]:
                    laws[u]["lists"].append(cat)
            if not links:
                break
            page += 1
        print(cat, "pages", page - 1, "laws", len(laws), flush=True)
    # law pages: metadata + PDF link
    for u, d in laws.items():
        cache = os.path.join(RAW, "pages", u.rsplit("/", 1)[-1][:150] + ".html")
        os.makedirs(os.path.dirname(cache), exist_ok=True)
        if os.path.exists(cache):
            html = open(cache, encoding="utf-8").read()
        else:
            html = get(u) or ""
            open(cache, "w", encoding="utf-8").write(html)
        soup = BeautifulSoup(html, "lxml")
        pdfs = re.findall(r'href="(' + re.escape(SITE) + r'/storage/documentos/leyes/[^"]+\.(?:pdf|PDF))"', html)
        d["pdf"] = pdfs[0] if pdfs else None
        txt = re.sub(r"[ \t\r]+", " ", soup.get_text("\n"))
        txt = re.sub(r"\n\s*\n+", "\n", txt)
        h = soup.find(["h1", "h2", "h3"], string=re.compile(r"\w"))
        m = re.search(r"\nContáctanos\n(.+?)\n", txt)
        d["title"] = (m.group(1).strip() if m else (h.get_text(strip=True) if h else u.rsplit("/", 1)[-1]))
        for k, lab in (("tipo", "Tipo"), ("condicion", "Condición"), ("sancion", "Sancion"), ("gaceta", "Nº Gaceta"),
                       ("fecha_gaceta", "Fecha"), ("vigencia", "Vigencia")):
            m = re.search(r"\n" + re.escape(lab) + r"\n\s*([^\n]+)", txt)
            d[k] = m.group(1).strip() if m else None
    json.dump(list(laws.values()), open(os.path.join(RAW, "list.json"), "w"), ensure_ascii=False, indent=1)
    print("laws", len(laws), "with pdf", sum(1 for d in laws.values() if d["pdf"]))


IA = "https://web.archive.org/web/{ts}id_/{url}"
CDX = "https://web.archive.org/cdx/search/cdx?url={prefix}&matchType=prefix&filter=statuscode:200&collapse=urlkey&fl=original,timestamp"


def ia_get(url, ts, binary=False):
    """Fetch an Internet Archive capture (raw bytes, id_ mode), politely."""
    global DELAY
    old, DELAY = DELAY, 1.5
    try:
        return get(IA.format(ts=ts, url=url), binary)
    finally:
        DELAY = old


def build_list_ia():
    """www.asambleanacional.gob.ve answers HTTP 403 to our client after a few requests (also
    at one request per 5 s), so law pages and PDFs are taken from Internet Archive captures."""
    pages = [l.split() for l in (get(CDX.format(prefix="asambleanacional.gob.ve/leyes/sancionadas/")) or "").splitlines() if l.strip()]
    pdfs = [l.split() for l in (get(CDX.format(prefix="asambleanacional.gob.ve/storage/documentos/leyes/")) or "").splitlines() if l.strip()]
    pdf_ts = {}
    for u, ts in pdfs:
        k = u.split("://", 1)[-1].replace("www.", "")
        if k not in pdf_ts or ts > pdf_ts[k][1]:
            pdf_ts[k] = (u, ts)
    laws = {}
    for u, ts in pages:
        slugp = u.rstrip("/").rsplit("/", 1)[-1].split("?")[0]
        if not re.fullmatch(r"[a-z0-9-]+", slugp) or slugp in laws:
            continue
        cache = os.path.join(RAW, "pages", slugp[:150] + ".html")
        os.makedirs(os.path.dirname(cache), exist_ok=True)
        if os.path.exists(cache):
            html = open(cache, encoding="utf-8").read()
        else:
            html = ia_get(u, ts) or ""
            open(cache, "w", encoding="utf-8").write(html)
        d = parse_law_page(html, SITE + "/leyes/sancionadas/" + slugp)
        d["archived_page"] = f"https://web.archive.org/web/{ts}/{u}"
        laws[slugp] = d
    used_pdf = set()
    for d in laws.values():
        if d.get("pdf"):
            k = d["pdf"].split("://", 1)[-1].replace("www.", "")
            if k in pdf_ts:
                d["pdf_capture"] = pdf_ts[k]
                used_pdf.add(k)
            else:
                d["pdf_capture"] = None
    for k, (u, ts) in pdf_ts.items():
        if k in used_pdf or not u.lower().endswith(".pdf"):
            continue
        name = re.sub(r"-\d{14}\.pdf$", "", u.rsplit("/", 1)[-1], flags=re.I).replace("-", " ")
        laws["pdf:" + k] = {"url": None, "lists": [], "pdf": u, "pdf_capture": (u, ts),
                            "title": name[:1].upper() + name[1:], "tipo": None, "condicion": None, "sancion": None,
                            "gaceta": None, "fecha_gaceta": None, "vigencia": None}
    json.dump(list(laws.values()), open(os.path.join(RAW, "list.json"), "w"), ensure_ascii=False, indent=1)
    print("laws", len(laws), "with archived pdf", sum(1 for d in laws.values() if d.get("pdf_capture")))


def parse_law_page(html, url):
    soup = BeautifulSoup(html, "lxml")
    d = {"url": url, "lists": []}
    pdfs = re.findall(r'href="(https?://(?:www\.)?asambleanacional\.gob\.ve/storage/documentos/leyes/[^"]+\.(?:pdf|PDF))"', html)
    pdfs = [re.sub(r"^https?://web\.archive\.org/web/\d+(?:id_)?/", "", p) for p in pdfs]
    d["pdf"] = pdfs[0] if pdfs else None
    txt = re.sub(r"[ \t\r]+", " ", soup.get_text("\n"))
    txt = re.sub(r"\n\s*\n+", "\n", txt)
    h = soup.select_one("h3.uk-margin-medium-bottom")
    m = re.search(r"\nContáctanos\n(.+?)\n", txt)
    d["title"] = (h.get_text(" ", strip=True) if h else (m.group(1).strip() if m else url.rsplit("/", 1)[-1]))
    for k, lab in (("tipo", "Tipo"), ("condicion", "Condición"), ("sancion", "Sancion"), ("gaceta", "Nº Gaceta"),
                   ("fecha_gaceta", "Fecha"), ("vigencia", "Vigencia")):
        m = re.search(r"\n" + re.escape(lab) + r"\n\s*([^\n]+)", txt)
        d[k] = m.group(1).strip() if m else None
    return d


def download_ia():
    os.makedirs(os.path.join(RAW, "pdf"), exist_ok=True)
    rows = json.load(open(os.path.join(RAW, "list.json")))
    caps = [(CONST, CONST_TS)] + [tuple(r["pdf_capture"]) for r in rows if r.get("pdf_capture")]
    for u, ts in caps:
        p = pdf_path(u)
        for k in range(3):
            if os.path.exists(p) and P.pdf_ok(p):
                break
            c = ia_get(u, ts, binary=True)
            if c:
                open(p, "wb").write(c)
        print("ok" if P.pdf_ok(p) else "BAD", u, flush=True)


def pdf_path(u):
    return os.path.join(RAW, "pdf", re.sub(r"[^\w.-]", "_", u.rsplit("/", 1)[-1]))


def download():
    os.makedirs(os.path.join(RAW, "pdf"), exist_ok=True)
    rows = json.load(open(os.path.join(RAW, "list.json")))
    for u in [CONST] + [r["pdf"] for r in rows if r.get("pdf")]:
        p = pdf_path(u)
        for k in range(3):
            if os.path.exists(p) and P.pdf_ok(p):
                break
            c = get(u, binary=True)
            if c:
                open(p, "wb").write(c)
        print("ok" if P.pdf_ok(p) else "BAD", u, flush=True)


def dmy(x):
    m = re.search(r"(\d{2})/(\d{2})/(\d{4})", x or "")
    return f"{m.group(3)}-{m.group(2)}-{m.group(1)}" if m else None


def write(out, front, title, md, pre):
    path = os.path.join(REPO, out)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    open(path, "w", encoding="utf-8").write(P.render(front, title, md, None, pre))


def convert():
    st = {"ok": 0, "scanned": 0, "nopdf": 0}
    pages = P.extract_pages(pdf_path(CONST))
    md = P.lines_to_md(P.clean_pages(pages))
    write("constitucion/constitucion-de-la-republica-bolivariana-de-venezuela.md",
          {"title": "Constitución de la República Bolivariana de Venezuela", "identifier": "Gaceta Oficial N° 5.908 Extraordinario (19-02-2009)",
           "type": "constitution", "jurisdiction": "ve", "language": "es", "date": "1999-12-20",
           "last_amended": "2009-02-15", "status": "in_force", "source": CONST,
           "archived_source": f"https://web.archive.org/web/{CONST_TS}/{CONST}", "retrieved": TODAY},
          "Constitución de la República Bolivariana de Venezuela", md,
          "> Texto publicado por la Asamblea Nacional (CRBV de 1999 con la Enmienda N° 1 de 2009).")
    rows = json.load(open(os.path.join(RAW, "list.json")))
    used = set()
    skipped = []
    for r in rows:
        cap = r.get("pdf_capture")
        if not cap or not P.pdf_ok(pdf_path(cap[0])):
            st["nopdf"] += 1
            skipped.append((r, "sin PDF"))
            continue
        pages = P.extract_pages(pdf_path(cap[0]))
        empty = sum(1 for t in pages if len(t.strip()) < 200)
        if empty > 0.5 * len(pages):
            st["scanned"] += 1
            skipped.append((r, "PDF escaneado (sin capa de texto)"))
            continue
        d = dmy(r.get("fecha_gaceta")) or dmy(r.get("sancion"))
        year = d[:4] if d else "sin-fecha"
        fn = f"leyes/{year}/{slug(r['title'])}.md" if d else f"leyes/sin-fecha/{slug(r['title'])}.md"
        while fn in used:
            fn = fn[:-3] + "-2.md"
        used.add(fn)
        md = P.lines_to_md(P.clean_pages(pages))
        title = r["title"].rstrip(".")
        cond = (r.get("condicion") or "").lower()
        status = "in_force" if "vigencia" in cond or "vigentes" in r["lists"] else "unknown"
        ident = f"Gaceta Oficial N° {r['gaceta']} ({r.get('fecha_gaceta')})" if r.get("gaceta") else None
        typ = "code" if title.lower().startswith("código") else "act"
        write(fn, {"title": title, "identifier": ident, "type": typ, "jurisdiction": "ve", "language": "es",
                   "date": d, "status": status, "source": r["url"] or cap[0], "source_pdf": cap[0],
                   "archived_source": f"https://web.archive.org/web/{cap[1]}/{cap[0]}", "retrieved": TODAY},
              title, md, "> Texto del documento PDF publicado por la Asamblea Nacional para esta ley (copia archivada por el Internet Archive)"
              + (f" (Gaceta Oficial N° {r['gaceta']}, {r.get('fecha_gaceta')})." if r.get("gaceta") else "."))
        st["ok"] += 1
    json.dump(skipped, open(os.path.join(RAW, "skipped.json"), "w"), ensure_ascii=False, indent=1)
    print(st)


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "all"
    if cmd == "list-live":
        build_list()
    if cmd == "download-live":
        download()
    if cmd in ("list", "all"):
        build_list_ia()
    if cmd in ("download", "all"):
        download_ia()
    if cmd in ("convert", "all"):
        convert()
