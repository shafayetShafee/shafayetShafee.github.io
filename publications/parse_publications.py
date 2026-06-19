"""
Parse publications from a BibTeX file into a "pub-year / pub-grid / pub-entry"
HTML layout (article cards with badge, authors, title, venue, and action chips
including a copy-to-clipboard BibTeX button).

Instructions:
=============
1. Keep your publications in a single .bib file (hand-written or exported).
2. Set `bib_path` to your .bib file path.
3. Add additional links (PDF, datasets, code, etc.) in `pubs_additional_links.yml`.
   Keys in the YAML must match the BibTeX entry key exactly
   (e.g. `shafee2025investigating`).
4. Use a python code block in your index.qmd to render the HTML, calling
   `render_year_section(year)` for each year in `KEYS_BY_YEAR`, sorted descending.

Dependencies:
    pip install bibtexparser<2 dominate pyyaml
"""

from collections import defaultdict
from typing import cast
import base64
import re
import dominate.tags as tags
import yaml
from pathlib import Path
from dominate.util import text as dom_text
import bibtexparser
from bibtexparser.bparser import BibTexParser
from bibtexparser.customization import convert_to_unicode

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

# How your name appears — used to bold your name in author lists
MY_NAME_FAMILY = "Shafee"
MY_NAME_GIVEN  = "Shafayet Khan"

bib_path        = "publications.bib"
yaml_links_path = "pubs_additional_links.yml"

# Maps BibTeX entry types to a display badge label + CSS modifier
BIB_TYPE_MAP = {
    "article":        ("Article",  "article"),
    "inproceedings":  ("Conference", "conf"),
    "conference":     ("Conference", "conf"),
    "proceedings":    ("Conference", "conf"),
    "incollection":   ("Chapter",  "chapter"),
    "inbook":         ("Chapter",  "chapter"),
    "book":           ("Chapter",  "chapter"),
    "misc":           ("Preprint", "preprint"),
    "unpublished":    ("Preprint", "preprint"),
    "techreport":     ("Preprint", "preprint"),
    "phdthesis":      ("Chapter",  "chapter"),
    "mastersthesis":  ("Chapter",  "chapter"),
}

MONTH_NAMES = [
    "", "January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December",
]

# ---------------------------------------------------------------------------
# Load data
# ---------------------------------------------------------------------------

def _load_bib(path: str) -> dict[str, dict]:
    parser = BibTexParser(common_strings=True)
    parser.customization = convert_to_unicode
    with open(path, encoding="utf-8") as f:
        db = bibtexparser.load(f, parser=parser)
    return {entry["ID"]: entry for entry in db.entries}


def _load_yaml(path: str) -> dict:
    p = Path(path)
    if not p.exists():
        return {}
    return yaml.safe_load(p.read_text()) or {}


def _load_raw_bib_text(path: str) -> dict[str, str]:
    """
    Split the raw .bib file text into per-entry raw strings, keyed by entry ID,
    for use in the BibTeX copy-to-clipboard button. Strips any 'annote' field.
    """
    raw = Path(path).read_text(encoding="utf-8")
    parts = re.split(r"\n(?=@)", raw.strip())
    out = {}
    for part in parts:
        part = part.strip()
        if not part.startswith("@"):
            continue
        m = re.match(r"^@(\w+)\s*\{\s*([^,]+),", part)
        if not m:
            continue
        key = m.group(2).strip()
        cleaned = re.sub(r"^\s*annote\s*=\s*\{[\s\S]*?\}\s*,?\s*\n", "", part, flags=re.IGNORECASE | re.MULTILINE)
        out[key] = cleaned
    return out


PUB_DATA  = _load_bib(bib_path)
LINK_DATA = _load_yaml(yaml_links_path)
RAW_BIB   = _load_raw_bib_text(bib_path)

KEYS_BY_YEAR: dict[str, list[str]] = defaultdict(list)
for _key, _entry in PUB_DATA.items():
    _year = _entry.get("year", "n.d.")
    KEYS_BY_YEAR[_year].append(_key)

# ---------------------------------------------------------------------------
# Name helpers
# ---------------------------------------------------------------------------

def _parse_author_field(raw: str) -> list[dict]:
    """
    Split a BibTeX author field into a list of {'family': ..., 'given': ...}.
    Handles both "Family, Given" and "Given Family" forms, and 'and'-separated lists.
    Normalises AND / And / and before splitting.
    """
    normalised = re.sub(r"\s+[Aa][Nn][Dd]\s+", " and ", raw)

    authors = []
    for part in normalised.split(" and "):
        part = part.strip()
        if not part:
            continue
        if "," in part:
            family, given = part.split(",", 1)
            authors.append({"family": family.strip(), "given": given.strip()})
        else:
            tokens = part.split()
            if len(tokens) == 1:
                authors.append({"family": tokens[0], "given": ""})
            else:
                authors.append({"family": tokens[-1], "given": " ".join(tokens[:-1])})
    return authors


def _format_name_apa(name: dict) -> str:
    """Format a name dict as 'Family, I.' (APA style)."""
    given = name.get("given", "")
    family = name.get("family", "")
    if not given:
        return family
    initials = " ".join(p[0].upper() + "." for p in given.split() if p)
    return f"{family}, {initials}"


def _is_me(name: dict) -> bool:
    return (
        name.get("family", "").lower() == MY_NAME_FAMILY.lower()
        and MY_NAME_GIVEN.split()[0].lower() in name.get("given", "").lower()
    )

# ---------------------------------------------------------------------------
# Field extractors
# ---------------------------------------------------------------------------

def _get_year(entry: dict) -> str:
    return entry.get("year", "n.d.")


def _get_date_label(entry: dict) -> str:
    """Return 'November 2025' style label if month is available, else just the year."""
    year = _get_year(entry)
    month_raw = entry.get("month", "")
    try:
        month_idx = int(month_raw)
        if 1 <= month_idx <= 12:
            return f"{MONTH_NAMES[month_idx]} {year}"
    except (ValueError, TypeError):
        pass
    return year


def _get_journal(entry: dict) -> str:
    return entry.get("journal") or entry.get("booktitle") or entry.get("publisher") or ""


def _get_venue_meta(entry: dict) -> str:
    """Return 'vol. X, no. Y, pp. Z' style string."""
    volume = entry.get("volume", "")
    number = entry.get("number", "")
    pages  = entry.get("pages", "").replace("--", "–")

    parts = []
    if volume:
        parts.append(f"vol. {volume}")
    if number:
        parts.append(f"no. {number}")
    if pages:
        parts.append(f"pp. {pages}")
    return ", ".join(parts)


def _get_arxiv_id(entry: dict) -> str | None:
    return entry.get("eprint") or None

  
def _get_arxiv_primary_class(entry: dict) -> str | None:
    return entry.get("primaryclass") or entry.get("primaryClass") or None


def _get_doi(entry: dict) -> str | None:
    return entry.get("doi") or entry.get("DOI") or None


def _get_url(entry: dict) -> str | None:
    return entry.get("url") or entry.get("URL") or None
  

def _get_badge(entrytype: str) -> tuple[str, str]:
    return BIB_TYPE_MAP.get(entrytype, ("Article", "article"))


def _utf8_base64(s: str) -> str:
    return base64.b64encode(s.encode("utf-8")).decode("ascii")

# ---------------------------------------------------------------------------
# Chip / button helper
# ---------------------------------------------------------------------------

def _make_chip(text: str, link: str) -> tags.dom_tag:
    return tags.a(
        text,
        _class="pub-chip",
        href=link,
        target="_blank",
        rel="noopener noreferrer",
    )


def _make_bibtex_chip(key: str) -> tags.dom_tag:
    raw = RAW_BIB.get(key, "")
    encoded = _utf8_base64(raw)
    btn = cast(tags.dom_tag, tags.button(
        "BibTeX",
        type="button",
        _class="pub-chip pub-chip--bibtex",
    ))
    btn["data-bibtex"] = encoded
    btn["aria-label"] = "Copy BibTeX entry"
    btn["aria-live"] = "polite"
    return btn

# ---------------------------------------------------------------------------
# Core entry renderer
# ---------------------------------------------------------------------------

def make_pub(key: str) -> tags.dom_tag:
    """Render one publication as a <article class="pub-entry"> card."""
    entry = PUB_DATA[key]
    entrytype = entry.get("ENTRYTYPE", "article").lower()
    badge_label, badge_mod = _get_badge(entrytype)

    raw_authors = entry.get("author", "")
    authors = _parse_author_field(raw_authors)

    arxiv_id = _get_arxiv_id(entry)
    arxiv_class = _get_arxiv_primary_class(entry)
    doi = _get_doi(entry)
    url = _get_url(entry)

    article = cast(tags.dom_tag, tags.article(_class="pub-entry"))
    article["data-bibtype"] = badge_mod

    # ---- Head row: badge + date -----------------------------------
    head = cast(tags.dom_tag, tags.div(_class="pub-entry-head"))
    head.add(tags.span(badge_label, _class=f"pub-badge pub-badge--{badge_mod}"))
    date_tag = cast(tags.dom_tag, tags._time(_get_date_label(entry), _class="pub-date"))
    date_tag["data-ordinal-dates"] = "wrapped"
    head.add(date_tag)
    article.add(head)

    # ---- Authors -----------------------------------------------------
    authors_p = cast(tags.dom_tag, tags.p(_class="pub-authors"))
    for i, a in enumerate(authors):
        fmt = _format_name_apa(a)
        node = tags.span(fmt, _class="pub-author--self") if _is_me(a) else dom_text(fmt)
        authors_p.add(node)
        if i < len(authors) - 1:
            authors_p.add(dom_text(", "))
    article.add(authors_p)

    # ---- Title (linked) ----------------------------------------------
    title = entry.get("title", "").strip("{}")
    title_link = (
        doi and f"https://doi.org/{doi}"
        or url
        or (arxiv_id and f"https://arxiv.org/abs/{arxiv_id}")
        or "#"
    )
    h3 = cast(tags.dom_tag, tags.h3(_class="pub-title no-anchor"))
    h3.add(tags.a(title, href=title_link, target="_blank", rel="noopener noreferrer"))
    article.add(h3)

    # ---- Venue ---------------------------------------------------------
    venue_p = cast(tags.dom_tag, tags.p(_class="pub-venue"))
    if entrytype in ("article", "incollection", "inproceedings"):
        journal = _get_journal(entry)
        if journal:
            venue_p.add(tags.em(journal))
        meta = _get_venue_meta(entry)
        if meta:
            venue_p.add(dom_text(", "))
            venue_p.add(tags.span(meta, _class="pub-venue-meta"))
    elif entrytype == "misc" and arxiv_id:
        venue_p.add(tags.em("arXiv preprint"))
        venue_p.add(dom_text(", "))
        venue_p.add(
          tags.span(f"arXiv:{arxiv_id} [{arxiv_class}]", _class="pub-venue-meta")
        )
    article.add(venue_p)

    # ---- Actions (DOI / arXiv / extra links / BibTeX) -----------------
    actions = cast(tags.dom_tag, tags.div(_class="pub-actions"))

    if doi:
        actions.add(_make_chip("DOI", f"https://doi.org/{doi}"))
    elif arxiv_id:
        actions.add(_make_chip("arXiv", f"https://arxiv.org/abs/{arxiv_id}"))

    for link_item in LINK_DATA.get(key, []):
        actions.add(_make_chip(link_item["text"], link_item["link"]))

    actions.add(_make_bibtex_chip(key))
    article.add(actions)

    return article

# ---------------------------------------------------------------------------
# Year section renderer
# ---------------------------------------------------------------------------

def render_year_section(year: str) -> tags.dom_tag:
    """
    Render a full year block: <h2 class="pub-year"> (year number only,
    no count/types spans) followed by a <div class="pub-grid"> of entries.
    """
    section = cast(tags.dom_tag, tags.div())

    h2 = cast(tags.dom_tag, tags.h2(_class="pub-year no-anchor", id=f"pub-year-{year}"))
    h2.add(tags.span(year, _class="pub-year-num"))
    section.add(h2)

    grid = cast(tags.dom_tag, tags.div(_class="pub-grid"))
    for key in KEYS_BY_YEAR[year]:
        grid.add(make_pub(key))
    section.add(grid)

    return section
