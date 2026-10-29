"""Bulk theme coding as a Message Batches job: builds the request list only, never sends it."""

from __future__ import annotations

import json
import re
from collections.abc import Iterable, Mapping
from typing import Any

from .agents import AGENT_DIR
from .schema import REVIEW_CODING_SCHEMA

BATCH_MODEL = "claude-haiku-5-5"
THEME_CODING_SKILL = AGENT_DIR / ".claude" / "skills" / "theme-coding" / "SKILL.md"
REVIEW_FIELDS = ("review_id", "store", "source", "posted", "rating", "text")  # never the author


def _skill_body() -> str:
    text = THEME_CODING_SKILL.read_text(encoding="utf-8")
    return re.sub(r"\A---\n.*?\n---\n", "", text, count=1, flags=re.S).strip()


def build_theme_coding_batch(reviews: Iterable[Mapping[str, Any]], *, model: str = BATCH_MODEL, max_tokens: int = 1024) -> list[dict[str, Any]]:
    system = _skill_body()
    requests: list[dict[str, Any]] = []
    seen: set[str] = set()
    for review in reviews:
        custom_id = re.sub(r"[^A-Za-z0-9_-]", "-", str(review["review_id"]))[:64]
        if not custom_id or custom_id in seen:
            raise ValueError(f"Review id {review['review_id']!r} gives an empty or duplicate batch custom_id")
        seen.add(custom_id)
        requests.append({
            "custom_id": custom_id,
            "params": {
                "model": model,
                "max_tokens": max_tokens,
                "system": system,
                "messages": [{"role": "user", "content": json.dumps({name: review[name] for name in REVIEW_FIELDS}, ensure_ascii=False)}],
                "output_config": {"format": {"type": "json_schema", "schema": REVIEW_CODING_SCHEMA}},
            },
        })
    return requests
