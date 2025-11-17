"""
Copied from: https://github.com/Jhsmit/website_quarto/blob/master/publications/parse_publications.py

Instructions:
=============
Parse publications to HTML

How to use:
1. Export your publications from zotero as JSON CSL file
2. Adapt `NAME` and json path to your needs
3. If you want to add additional links (PDF, datasets, code, etc), add them in a yaml file (adjust `yaml_links_path`).
   The keys in the yaml file should match `citekey(entry)` of the publication.
4. Use a python code block on your index.qmd file to add the resulting HTML to your web page.
"""

# %%
from collections import defaultdict
from typing import cast
import dominate.tags as tags
import json
import yaml
from pathlib import Path
from dominate.util import text as dom_text

# %%
NAME = "S.K. Shafee"

almost_name = {"family": "Shafee", "given": "Shafayet Khan"}
correct_name = {"family": "Shafee", "given": "Shafayet Khan"}

json_path = "Exported Items.json"
yaml_links_path = "pubs_additional_links.yml"
json_loaded = json.loads(Path(json_path).read_bytes())


# %%


def regen_yaml() -> None:
    """Regenerate the YAML file with the publication keys."""
    raise NotImplementedError("file already exists")
    lines = [p + ": {}" for p in PUB_DATA.keys()]
    s = "\n".join(lines)
    Path("pubs_additional_links.yaml").write_text(s)


def format_name(name_dict: dict) -> str:
    initials = "".join([part[0].upper() + "." for part in name_dict["given"].split()])
    family_name = name_dict["family"]
    name = initials
    if particle := name_dict.get("non-dropping-particle"):
        name += f" {particle}"
    name += f" {family_name}"
    return name


def make_button(text: str, link: str, icon="ai ai-doi") -> tags.dom_tag:
    btn = cast(tags.dom_tag, tags.a(href=link, _class="pub-button", target="_blank"))
    with btn:
        tags.i(_class=icon)
        dom_text(text)
    return btn


def citekey(entry: dict) -> str:
    """Create a citation key from the entry.

    with better bibtex not stricly necesary, could also use field "id".
    """
    title = (
        "_".join(entry["title"].split()[:3])
        .replace("-", "_")
        .translate({ord(c): None for c in "!@#$;:,"})
        .lower()
    )

    parts = [
        entry["author"][0]["family"].lower(),
        title,
        get_year(entry),
    ]
    return "_".join(parts)


def get_year(entry: dict) -> str:
    return entry["issued"]["date-parts"][0][0]


def get_title(entry: dict) -> str:
    """Get the journal title from possible keys in the entry.

    Return empty string if not found.
    """
    keys = ["container-title", "JournalAbbreviation"]
    for key in keys:
        if key in entry:
            return entry[key]
    return ""


def make_pub(key: str) -> tags.dom_tag:
    json_entry = PUB_DATA[key]

    # fix incorrect author name
    authors = [
        a if json.dumps(a) != json.dumps(almost_name) else correct_name
        for a in json_entry["author"]
    ]
    authors_fmt = [format_name(author) for author in authors]
    assert NAME in authors_fmt, "Author not found in the list of authors: " + str(key)
    author_tags = [dom_text(a) if a != NAME else tags.strong(a) for a in authors_fmt]

    pub = cast(tags.dom_tag, tags.p())

    for i, t in enumerate(author_tags):
        pub.add(t)
        if i == len(author_tags) - 1:
            pub.add("; ")
        else:
            pub.add(", ")

    pub.add(
        tags.span(
            json_entry["title"],
            style="color: var(--bs-primary); font-weight: bold;"
        )
    )
    pub.add("; ")

    journal = get_title(json_entry)
    pub.add(tags.i(journal))

    volume = json_entry.get("volume")
    issue = json_entry.get("issue")
    pages = json_entry.get("page") or json_entry.get("pages")

    parts = []

    if volume:
        if issue:
            parts.append(f"{volume}({issue})")
        else:
            parts.append(f"{volume}")

    if pages:
        parts.append(f": {pages}")

    if parts:
        pub.add(" ")
        pub.add(" ".join(parts))

    pub.add(tags.br())

    doi = json_entry.get("DOI")
    if doi:
        doi_link = f"https://doi.org/{doi}"
        btn = make_button("DOI", doi_link)
        pub.add(btn)

    links = LINK_DATA.get(key, [])
    for link in links:
        btn = make_button(**link)
        pub.add(btn)

    return pub



# %%

PUB_DATA = {citekey(entry): entry for entry in json_loaded}
LINK_DATA = yaml.safe_load(Path(yaml_links_path).read_text())


KEYS_BY_YEAR = defaultdict(list)
for key, entry in PUB_DATA.items():
    year = get_year(entry)
    KEYS_BY_YEAR[year].append(key)
