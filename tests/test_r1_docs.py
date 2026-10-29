"""Docs-only R1 security and rough-edges checks (rows 31, 36 and 62)."""

from __future__ import annotations

import re

from conftest import REPO


def test_r1_row_31_security_note_file_line_references_point_at_named_settings():
    note_path = REPO / "docs" / "before-you-run.md"
    assert note_path.is_file()
    note = note_path.read_text(encoding="utf-8")
    references = [
        (name, int(line))
        for name, line in re.findall(r"(?:src/storydesk/)?(agents|runner)\.py:(\d+)", note)
    ]
    assert references, "use literal agents.py:N / runner.py:N references so a reader can check them"
    resolved: list[tuple[str, int, str]] = []
    for name, line_number in references:
        source = (REPO / "src" / "storydesk" / f"{name}.py").read_text(encoding="utf-8").splitlines()
        assert 1 <= line_number <= len(source), f"{name}.py:{line_number} is outside the file"
        resolved.append((name, line_number, source[line_number - 1]))

    for setting in ("allowed_tools", "disallowed_tools", "dontAsk", "setting_sources=[]", "strict_mcp_config", "max_budget_usd"):
        compact = setting.replace(" ", "")
        assert any(compact in line.replace(" ", "") for _name, _number, line in resolved), setting
    runner_lines = [line for name, _number, line in resolved if name == "runner"]
    assert runner_lines and any("judge" in line.lower() or "ClaudeAgentOptions" in line for line in runner_lines)


def test_r1_row_36_whats_rough_names_the_cole_anthony_problem_and_better_stat():
    path = REPO / "docs" / "whats-rough.md"
    assert path.is_file(), "What's rough must be its own docs page"
    page = path.read_text(encoding="utf-8")
    assert re.search(r"^#.*what.?s rough", page, re.I | re.M)
    for phrase in ("Cole Anthony", "fewest minutes for a 30-point game", "quickest to 30", "play-by-play"):
        assert phrase.lower() in page.lower(), phrase


def test_r1_row_62_security_note_has_self_review_and_safe_run_advice():
    path = REPO / "docs" / "before-you-run.md"
    assert path.is_file()
    note = path.read_text(encoding="utf-8")
    headings = " ".join(re.findall(r"^#{1,6}\s+(.+)$", note, re.M)).lower()
    assert "review" in headings and "run" in headings
    assert re.search(r"review prompt", note, re.I) and re.search(r"claude code", note, re.I)
    assert re.search(r"separate.{0,80}(console|api) key", note, re.I | re.S)
    assert re.search(r"spend limit", note, re.I)
    assert re.search(r"container|fresh VM", note, re.I)
    assert re.search(r"dry[- ]run", note, re.I)
    assert "what I'd ask of any outside code coming into LK systems" in note
