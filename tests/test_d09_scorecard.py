"""D9: the scorecard command prints every field. Plus the judge's deterministic novelty signal."""
import json

from conftest import run_py

FIELDS = {"recheck_pass_rate", "coverage", "novelty", "audience_fit", "direction", "held", "duration_s", "cost_usd"}


def test_scorecard_prints_every_field(demo_store):
    out = run_py("-m", "storydesk", "scorecard", "--store", str(demo_store.store.path),
                 "--stats-db", str(demo_store.stats_db), "--run-id", str(demo_store.post_run), "--json")
    assert out.returncode == 0, out.stderr
    card = json.loads(out.stdout)
    assert FIELDS <= set(card)
    assert card["recheck_pass_rate"] == 1.0
    assert card["held"] >= 1
    assert card["duration_s"] == 1180
    assert card["cost_usd"] == 2.10


def test_novelty_similarity_signal():
    from storydesk.judge import novelty_similarity

    coverage = ["Adelaide won the third quarter 26-22 and held on in Melbourne."]
    assert novelty_similarity("Adelaide won the third quarter 26-22 and held on", coverage) > 0.6
    assert novelty_similarity("United's bench minutes fell for a third straight season", coverage) < 0.3
