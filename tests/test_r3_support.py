"""Shared helpers for the R3 (Daniel's Donuts) checks. Holds no tests itself."""

from __future__ import annotations

import json
import re
from html.parser import HTMLParser
from pathlib import Path
from typing import Any

from conftest import REPO

DD_DOCS = REPO / "docs" / "daniels-donuts"
PRD = DD_DOCS / "prd.md"
SAMPLE_WEEK = DD_DOCS / "sample-week.json"
DD_SITE = REPO / "site" / "daniels-donuts"
WEEKLY = DD_SITE / "weekly.html"
R3_FIX = Path(__file__).parent / "fixtures" / "r3"
REVIEWDESK = REPO / "src" / "reviewdesk"

REGIONS = ("south-east Melbourne", "western Melbourne", "Geelong region", "regional Victoria and the border")
DD_DESCRIPTION = (
    "The Review Desk reads every customer review each week and links it to the sales, staffing, stock and "
    "promotion data, a link that usually takes several teams in a room. It tells store, region and network "
    "leaders what's changing and why it might be, early, with the evidence attached, and gives them one place "
    "to discuss it."
)
OFFER = "I'm happy to use this to walk you through how I build, in an interview or a working session."
NUMBER = re.compile(r"\d+(?:\.\d+)?")
_VOID = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "source", "track", "wbr"}


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def fixture(name: str) -> Any:
    return load_json(R3_FIX / name)


def json_numbers(value: Any) -> set[str]:
    """Every numeric token in any key or leaf of a JSON value, as the renderer may print it."""
    tokens: set[str] = set()
    if isinstance(value, dict):
        for key, item in value.items():
            tokens |= set(NUMBER.findall(str(key))) | json_numbers(item)
    elif isinstance(value, list):
        for item in value:
            tokens |= json_numbers(item)
    elif isinstance(value, bool) or value is None:
        pass
    else:
        tokens |= set(NUMBER.findall(str(value)))
    return tokens


class Node:
    def __init__(self, tag: str, attrs: dict[str, str], parent: "Node | None" = None):
        self.tag, self.attrs, self.parent = tag, attrs, parent
        self.children: list[Node | str] = []

    @property
    def classes(self) -> list[str]:
        return self.attrs.get("class", "").split()

    def text(self) -> str:
        return "".join(child if isinstance(child, str) else child.text() for child in self.children)

    def descendants(self, tag: str | None = None, cls: str | None = None, **attrs: str) -> list["Node"]:
        found = []
        for child in self.children:
            if isinstance(child, str):
                continue
            wanted = {key.replace("_", "-"): value for key, value in attrs.items()}
            if ((tag is None or child.tag == tag) and (cls is None or cls in child.classes)
                    and all(child.attrs.get(key) == value for key, value in wanted.items())):
                found.append(child)
            found.extend(child.descendants(tag, cls, **attrs))
        return found

    def elements(self) -> list["Node"]:
        return [child for child in self.children if isinstance(child, Node)]


class _TreeBuilder(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.root = Node("#root", {})
        self.current = self.root

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        node = Node(tag, {key: value or "" for key, value in attrs}, self.current)
        self.current.children.append(node)
        if tag not in _VOID:
            self.current = node

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self.current.children.append(Node(tag, {key: value or "" for key, value in attrs}, self.current))

    def handle_endtag(self, tag: str) -> None:
        node = self.current
        while node is not self.root and node.tag != tag:
            node = node.parent
        if node is not self.root:
            self.current = node.parent

    def handle_data(self, data: str) -> None:
        self.current.children.append(data)


def parse_html(text: str) -> Node:
    builder = _TreeBuilder()
    builder.feed(text)
    return builder.root


def one(root: Node, tag: str | None = None, cls: str | None = None, **attrs: str) -> Node:
    found = root.descendants(tag, cls, **attrs)
    assert len(found) == 1, f"expected one {tag or ''}.{cls or ''} {attrs}, found {len(found)}"
    return found[0]


def unnumbered_store_mentions(text: str, registry: dict[int, str]) -> list[str]:
    """Singular 'Store N' mentions that don't carry ' · <its region>' straight after."""
    bad = []
    for match in re.finditer(r"\bStore (\d+)\b", text):
        store = int(match.group(1))
        expected = f" · {registry.get(store, '<not in registry>')}"
        if not text[match.end():].startswith(expected):
            bad.append(text[match.start():match.end() + 40])
    return bad
