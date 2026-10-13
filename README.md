# LawCodex — Venezuela (ve)

Venezuelan legislation as Markdown: the **Constitución de la República Bolivariana de
Venezuela (1999, with Enmienda N° 1 of 2009)** and the **laws listed by the Asamblea Nacional**
("Leyes > Sancionadas / Vigentes", https://www.asambleanacional.gob.ve) whose official PDF has a
text layer — taken from **Internet Archive captures** of the Asamblea's pages and PDFs.

Part of [LawCodex](https://github.com/LawCodex): one public repository per jurisdiction.

Retrieved: **2026-10-13**. Language: Spanish (`es`).

Status: **minimal** — see "What is NOT covered".

## What is covered

| Category | Directory | Files |
|---|---|---|
| Constitución de la República Bolivariana de Venezuela | `constitucion/` | 1 |
| Laws (leyes, decree-laws, approval laws, reforms), by year of the Gaceta Oficial | `leyes/<year>/` | 60 |

The Internet Archive holds 293 law records / PDFs of the Asamblea's site; 60 PDFs have a text
layer and were converted, 189 are scanned images (no OCR applied) and 44 records had no archived
PDF. Texts are as published by the Asamblea (as sanctioned / as in the Gaceta Oficial), not
consolidated. Front matter gives the Gaceta Oficial number and date when the Asamblea's record
has them (`identifier`), the official URL (`source`, `source_pdf`) and the archived copy used
(`archived_source`).

## What is NOT covered

- **Live access to www.asambleanacional.gob.ve**: after a handful of requests the site answers
  HTTP 403 to our client (also when slowed to one request per 5 seconds); we did not try to
  work around the block. The Tribunal Supremo de Justicia (TSJ) and Gaceta Oficial sites were
  unreachable (timeouts) from our network.
- Codes (Código Civil, Código Penal, COPP, Código de Comercio, …) and the bulk of the
  legislation: no official consolidated or complete source was reachable.
- Scanned PDFs (no OCR) and laws never captured by the Internet Archive.

## Source

Asamblea Nacional de la República Bolivariana de Venezuela — law pages
`/leyes/sancionadas/<slug>` and PDFs `/storage/documentos/leyes/…`, via the Internet Archive
Wayback Machine (CDX API; latest successful capture; raw `id_` download). Constitution:
`/storage/documentos/botones/constitucion-nacional-20191205135853.PDF`.

## Copyright

Venezuela's Ley sobre el Derecho de Autor excludes official texts (laws, decrees, judicial
decisions) from copyright protection.

## Regenerate

```
python3 -m venv .venv && .venv/bin/pip install -r scripts/requirements.txt
RAW=/path/to/scratch .venv/bin/python scripts/ve_fetch.py all          # via the Internet Archive
RAW=/path/to/scratch .venv/bin/python scripts/ve_fetch.py list-live    # (live site, if reachable)
```
