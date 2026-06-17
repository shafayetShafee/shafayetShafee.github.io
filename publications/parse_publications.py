"""
Parse publications from a BibTeX file to APA-style HTML.

Instructions:
=============
1. Export your publications as a .bib file (from Zotero, Mendeley, or hand-written).
2. Set `bib_path` to your .bib file path.
3. Add additional links (PDF, datasets, code, etc.) in `pubs_additional_links.yml`.
   Keys in the YAML must match the BibTeX entry key exactly
   (e.g. `shafee2025investigating`, `shafee2026estimationmedianoddsratio`).
4. Use a python code block in your index.qmd to render the HTML.

Dependencies:
    pip install bibtexparser dominate pyyaml
"""

from collections import defaultdict
from typing import cast
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
MY_NAME_GIVEN = "Shafayet Khan"

bib_path = "publications.bib"
yaml_links_path = "pubs_additional_links.yml"

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


PUB_DATA = _load_bib(bib_path)
LINK_DATA = _load_yaml(yaml_links_path)

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
    import re

    # Normalise all variants of ' AND ' (case-insensitive) to ' and '
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
# Button helper
# ---------------------------------------------------------------------------


def _make_button(text: str, link: str, icon: str = "ai ai-doi") -> tags.dom_tag:
    btn = cast(tags.dom_tag, tags.a(href=link, _class="pub-button", target="_blank"))
    with btn:
        tags.i(_class=icon)
        dom_text(" " + text)
    return btn


# ---------------------------------------------------------------------------
# APA field extractors
# ---------------------------------------------------------------------------


def _get_year(entry: dict) -> str:
    return entry.get("year", "n.d.")


def _get_journal(entry: dict) -> str:
    return (
        entry.get("journal") or entry.get("booktitle") or entry.get("publisher") or ""
    )


def _get_volume_issue_pages(entry: dict) -> str:
    volume = entry.get("volume", "")
    number = entry.get("number", "")
    pages = entry.get("pages", "").replace("--", "–")

    parts = []
    if volume:
        vi = f"{volume}({number})" if number else volume
        parts.append(vi)
    if pages:
        parts.append(f", {pages}")

    return "".join(parts)


def _get_arxiv_id(entry: dict) -> str | None:
    """Return the arXiv eprint identifier if present."""
    return entry.get("eprint") or None


def _get_arxiv_primary_class(entry: dict) -> str | None:
    return entry.get("primaryclass") or entry.get("primaryClass") or None


def _get_doi(entry: dict) -> str | None:
    return entry.get("doi") or entry.get("DOI") or None


def _get_url(entry: dict) -> str | None:
    return entry.get("url") or entry.get("URL") or None


# ---------------------------------------------------------------------------
# Core pub renderer
# ---------------------------------------------------------------------------


def make_pub(key: str) -> tags.dom_tag:
    """
    Render one publication as an APA-style HTML <p> block.

    APA template used:
        Authors (Year). Title. Journal, volume(issue), pages. DOI/arXiv link.
    """
    entry = PUB_DATA[key]
    entrytype = entry.get("ENTRYTYPE", "article").lower()

    raw_authors = entry.get("author", "")
    authors = _parse_author_field(raw_authors)

    # ---- Author string ------------------------------------------------
    author_nodes = []
    for i, a in enumerate(authors):
        fmt = _format_name_apa(a)
        node = tags.strong(fmt) if _is_me(a) else dom_text(fmt)
        author_nodes.append(node)

    pub = cast(tags.dom_tag, tags.p(_class="pub-entry"))

    # Authors
    for i, node in enumerate(author_nodes):
        pub.add(node)
        if i < len(author_nodes) - 2:
            pub.add(dom_text(", "))
        elif i == len(author_nodes) - 2:
            # pub.add(dom_text(", & "))
            pub.add(dom_text(", "))

    year = _get_year(entry)
    pub.add(dom_text(f" ({year}). "))

    # Title
    title = entry.get("title", "").strip("{}")
    pub.add(tags.span(title + ". ", style="color: var(--bs-primary);"))
    #  font-weight: bold;

    arxiv_id = _get_arxiv_id(entry)
    arxiv_class = _get_arxiv_primary_class(entry)
    doi = _get_doi(entry)
    url = _get_url(entry)

    # ---- Source / journal block --------------------------------------
    if entrytype in ("article", "incollection", "inproceedings"):
        journal = _get_journal(entry)
        if journal:
            pub.add(tags.i(journal))

        vip = _get_volume_issue_pages(entry)
        if vip:
            pub.add(dom_text(f", {vip}"))

        pub.add(dom_text("."))

    elif entrytype == "misc" and arxiv_id:
        # arXiv preprint — APA 7 style
        class_str = f" [{arxiv_class.upper()}]" if arxiv_class else ""
        pub.add(dom_text(f"arXiv:{arxiv_id}{class_str}."))

    # ---- Buttons (DOI / PDF / Data / Code etc.) ----------------------
    pub.add(tags.br())

    if doi:
        pub.add(_make_button("DOI", f"https://doi.org/{doi}", icon="ai ai-doi"))
    elif arxiv_id:
        pub.add(
            _make_button(
                "arXiv", f"https://arxiv.org/abs/{arxiv_id}", icon="ai ai-arxiv"
            )
        )

    for link_item in LINK_DATA.get(key, []):
        pub.add(_make_button(**link_item))

    return pub
