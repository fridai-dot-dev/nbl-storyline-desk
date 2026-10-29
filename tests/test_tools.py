"""Agent tools: read-only SQL, as_of cutoffs on every source, handle stripping, finding validation (D6)."""
import sqlite3

import pytest

from conftest import CORPUS, EV_COMMENTARY, EV_STATS, OPENER, POST, Q3_ADL, SUPP, make_ctx


# ---------- stats_sql is read-only and bounded ----------

@pytest.mark.parametrize("sql", [
    "DELETE FROM results",
    "DROP TABLE results",
    "INSERT INTO results SELECT * FROM results",
    "CREATE TABLE x AS SELECT 1",
    "ATTACH 'other.db' AS other",
    "COPY results TO 'out.csv'",
    "SELECT 1; DROP TABLE results",
    "SELECT * FROM read_csv('/etc/passwd')",
    "SELECT * FROM read_text('/etc/hostname')",
])
def test_stats_sql_rejects_writes_and_file_access(post_ctx, sql):
    from storydesk.tools import ToolError, stats_sql

    with pytest.raises(ToolError):
        stats_sql(post_ctx, sql)


def test_stats_sql_truncates_to_limit(post_ctx):
    from storydesk.tools import stats_sql

    out = stats_sql(post_ctx, "SELECT match_id FROM results", limit=5)
    assert len(out["rows"]) == 5
    assert out["truncated"] is True
    assert out["columns"] == ["match_id"]


# ---------- corpus search respects as_of ----------

def test_transcripts_cut_off_at_as_of(stats_db, store):
    from storydesk.tools import search_transcripts

    post = make_ctx(stats_db, store, "post_game", POST)
    hits = search_transcripts(post, "third quarter")
    quotes = " ".join(h["quote"] for h in hits)
    assert "Adelaide have won the third quarter" in quotes
    assert "cost us the game" not in quotes  # presser at 11:55Z is after the post-game cutoff
    for h in hits:
        assert {"quote", "timestamp", "source_url"} <= set(h)

    supp = make_ctx(stats_db, store, "supplemental", SUPP)
    assert any("cost us the game" in h["quote"] for h in search_transcripts(supp, "third quarter"))


def test_fans_cut_off_and_handles_stripped(post_ctx):
    from storydesk.tools import search_fans

    hits = search_fans(post_ctx, "third quarter bench")
    texts = [h["text"] for h in hits]
    assert "Third quarter defence was rough tonight" in texts
    assert not any("cost them" in t for t in texts)  # 12:10Z comment is after the cutoff
    for h in hits:
        assert "author" not in h and "username" not in h
        assert "test_handle" not in repr(h)
        assert {"text", "score", "timestamp", "source_url"} <= set(h)


def test_media_uses_day_level_cutoff(post_ctx, pre_ctx):
    from storydesk.tools import search_media

    titles = [h["title"] for h in search_media(post_ctx, "Melbourne Adelaide")]
    assert any("preview" in t.lower() for t in titles)      # 2026-09-18
    assert not any("game-day" in t.lower() for t in titles)  # same day counts as after
    assert not any("recap" in t.lower() for t in titles)     # 2026-09-20
    pre_titles = [h["title"] for h in search_media(pre_ctx, "Melbourne Adelaide")]
    assert any("preview" in t.lower() for t in pre_titles)


# ---------- D6: findings must carry evidence and valid lineage ----------

def _ok(**over):
    base = dict(agent="stats", source_type="stats", kind="checked",
                claim="Adelaide scored 26 points in the third quarter",
                number=26, query=Q3_ADL, evidence=[EV_STATS])
    base.update(over)
    return base


@pytest.mark.parametrize("over", [
    {"evidence": []},
    {"evidence": [{"source_type": "stats", "ref": "box_team"}]},                 # no url
    {"evidence": [{"source_type": "stats", "url": "https://www.nbl.com.au"}]},  # no ref
    {"query": None},                                                             # checked needs a query
    {"number": None},                                                            # checked needs a number
    {"kind": "attributed", "evidence": [EV_STATS]},                              # attributed needs a quote
    {"parent_id": 999_999},                                                      # parent must exist
    {"sensitivity": "gossip"},                                                   # unknown category
    {"kind": "speculation"},                                                     # unknown kind
])
def test_write_finding_rejects_invalid(post_ctx, over):
    from storydesk.tools import ToolError, write_finding

    with pytest.raises(ToolError):
        write_finding(post_ctx, **_ok(**over))


def test_write_finding_accepts_valid_and_links_parent(post_ctx, store):
    from storydesk.tools import read_findings, write_finding

    root = write_finding(post_ctx, **_ok())
    child = write_finding(post_ctx, agent="commentary", source_type="commentary", kind="attributed",
                          claim="Commentators credited Adelaide's bench", evidence=[EV_COMMENTARY],
                          parent_id=root)
    nothing = write_finding(post_ctx, agent="media", source_type="media", kind="nothing_found",
                            claim="No media coverage before the cutoff mentioned the bench", evidence=[])
    assert all(isinstance(i, int) for i in (root, child, nothing))
    assert store.get_finding(child)["parent_id"] == root
    assert store.get_finding(root)["status"] == "pending"
    ev = store.evidence(child)
    assert ev[0]["quote"].startswith("Adelaide have won")
    assert {f["id"] for f in read_findings(post_ctx)} >= {root, child, nothing}


# ---------- tracking tables ----------

def test_tracking_tables_are_namespaced_and_validated(post_ctx, store):
    from storydesk.tools import ToolError, create_tracking_table, update_tracking_table

    assert create_tracking_table(post_ctx, "streaks", {"team": "TEXT", "n": "INTEGER"}) == "track_streaks"
    assert update_tracking_table(post_ctx, "streaks", [{"team": "ADL", "n": 4}]) == 1
    with pytest.raises(ToolError):
        create_tracking_table(post_ctx, "x; drop table findings", {"a": "TEXT"})
    with pytest.raises(ToolError):
        create_tracking_table(post_ctx, "blobs", {"a": "BLOB"})
    con = sqlite3.connect(store.path)
    assert con.execute("SELECT n FROM track_streaks").fetchone()[0] == 4


def test_store_schema(store):
    con = sqlite3.connect(store.path)
    names = {r[0] for r in con.execute("SELECT name FROM sqlite_master WHERE type = 'table'")}
    assert {"runs", "findings", "evidence", "requests", "directives", "feedback", "signoffs", "tool_calls"} <= names


def test_corpus_fixture_is_present():
    assert (CORPUS / "transcripts.jsonl").exists() and OPENER
