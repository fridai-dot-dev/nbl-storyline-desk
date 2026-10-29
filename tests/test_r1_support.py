"""Small fixture/HTML helpers shared only by the R1 checks."""

from __future__ import annotations

import json
from html.parser import HTMLParser
from pathlib import Path
from types import SimpleNamespace

from conftest import FIX


R1_FIXTURE = FIX / "r1" / "site-store.json"
VOID = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "param", "source", "track", "wbr"}


class Node:
    def __init__(self, tag: str, attrs=(), parent: "Node | None" = None):
        self.tag = tag
        self.attrs = dict(attrs)
        self.parent = parent
        self.children: list[Node | str] = []

    @property
    def classes(self) -> set[str]:
        return set(self.attrs.get("class", "").split())

    def text(self) -> str:
        return " ".join(" ".join(child.split()) if isinstance(child, str) else child.text() for child in self.children).strip()

    def descendants(self, tag: str | None = None, cls: str | None = None) -> list["Node"]:
        found: list[Node] = []
        for child in self.children:
            if isinstance(child, str):
                continue
            if (tag is None or child.tag == tag) and (cls is None or cls in child.classes):
                found.append(child)
            found.extend(child.descendants(tag, cls))
        return found


class TreeParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.root = Node("document")
        self.stack = [self.root]

    def handle_starttag(self, tag, attrs):
        node = Node(tag, attrs, self.stack[-1])
        self.stack[-1].children.append(node)
        if tag not in VOID:
            self.stack.append(node)

    def handle_startendtag(self, tag, attrs):
        self.stack[-1].children.append(Node(tag, attrs, self.stack[-1]))

    def handle_endtag(self, tag):
        for index in range(len(self.stack) - 1, 0, -1):
            if self.stack[index].tag == tag:
                del self.stack[index:]
                return

    def handle_data(self, data):
        self.stack[-1].children.append(data)


def parse_html(text: str) -> Node:
    parser = TreeParser()
    parser.feed(text)
    return parser.root


def one(root: Node, *, tag: str | None = None, cls: str | None = None, **attrs: str) -> Node:
    matches = [
        node for node in root.descendants(tag, cls)
        if all(node.attrs.get(name.replace("_", "-")) == value for name, value in attrs.items())
    ]
    assert len(matches) == 1, f"expected one {tag or '*'} {cls or ''} {attrs}, found {len(matches)}"
    return matches[0]


def load_r1_payload() -> dict:
    return json.loads(R1_FIXTURE.read_text(encoding="utf-8"))


def seed_r1_store(tmp_path: Path, stats_db, *, with_fans: bool = True):
    """Seed through Store's public API so the builder sees the same record shape as a real run."""
    from storydesk.store import Store

    payload = load_r1_payload()
    store = Store(tmp_path / ("r1-with-fans.db" if with_fans else "r1-no-fans.db"))
    store.init()
    run_ids: dict[str, int] = {}
    for item in payload["runs"]:
        run_id = store.start_run(item["run_type"], payload["game_id"], item["as_of"], route="fixture")
        store.set_run_summary(run_id, item["summary"])
        store.set_exec_summary(run_id, item["summary"])
        store.finish_run(
            run_id, status="complete", cost_usd=item["cost_usd"], duration_s=item["duration_s"],
            model_usage={}, num_agents=5, route="fixture",
        )
        run_ids[item["key"]] = run_id

    finding_ids: dict[str, int] = {}
    pending_stances: list[tuple[int, dict]] = []
    for item in payload["findings"]:
        fields = dict(item)
        key = fields.pop("key")
        fields["run_id"] = run_ids[fields.pop("run")]
        parent = fields.pop("parent", None)
        fields["parent_id"] = finding_ids[parent] if parent else None
        evidence = fields.pop("evidence", [])
        if not with_fans:
            evidence = [row for row in evidence if row.get("source_type") != "fans"]
        stances = fields.pop("stances", [])
        status = fields.pop("status")
        followups = fields.pop("followups", [])
        scores = {
            "novelty": fields.pop("novelty", None),
            "audience_fit": fields.pop("audience_fit", None),
            "direction": fields.pop("judge_direction", None),
        }
        finding_id = store.add_finding(**fields)
        store.update_finding(finding_id, status=status, **{key: value for key, value in scores.items() if value is not None})
        if followups:
            store.set_followups(finding_id, followups)
        if evidence:
            store.add_evidence(finding_id, evidence)
        finding_ids[key] = finding_id
        pending_stances.extend((finding_id, stance) for stance in stances)

    # Assumed public stance signature:
    # Store.set_stance(finding_id, role, stance, comment=None, *, at=None, simulated=False).
    set_stance = getattr(store, "set_stance", None)
    if callable(set_stance):
        for finding_id, stance in pending_stances:
            set_stance(
                finding_id, stance["role"], stance["stance"], stance.get("comment"),
                at=stance["time"], simulated=stance.get("simulated", False),
            )

    request = store.add_request(
        finding_ids["top_pick"], "Producer, Adelaide broadcast",
        "How often had Adelaide overcome a 30-point bench deficit?",
    )
    store.answer_request(request, run_ids["follow_up"])
    return SimpleNamespace(
        store=store, stats_db=stats_db, game_id=payload["game_id"], run_ids=run_ids,
        finding_ids=finding_ids, payload=payload, stance_count=len(pending_stances),
    )


def build_r1_site(tmp_path: Path, stats_db, *, with_fans: bool = True):
    from storydesk.site import build_site

    ns = seed_r1_store(tmp_path, stats_db, with_fans=with_fans)
    out = tmp_path / ("site-with-fans" if with_fans else "site-no-fans")
    build_site(ns.store, ns.stats_db, out, game_id=ns.game_id)
    return ns, out
