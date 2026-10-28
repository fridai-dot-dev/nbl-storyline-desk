"""The starting set is prepared once by code, and never leaks anything past the run's cutoff."""
import re

from conftest import CORPUS, OPENER, POST, PRE


def _digest(run_type, as_of, stats_db, store, tmp_path):
    from storydesk.prepare import prepare_run

    out = prepare_run(run_type, game_id=OPENER, as_of=as_of, stats_db=stats_db, store=store,
                      corpus_dir=CORPUS, out_dir=tmp_path / run_type)
    files = sorted(out.glob("*.md"))
    assert files, "digest produced no markdown files"
    return "\n".join(f.read_text(encoding="utf-8") for f in files)


FINAL_SCORE = re.compile(r"95\s*[-–]\s*97|97\s*[-–]\s*95")


def test_pre_game_digest_has_no_result(stats_db, store, tmp_path):
    text = _digest("pre_game", PRE, stats_db, store, tmp_path)
    assert "Melbourne United" in text and "Adelaide 36ers" in text
    assert not FINAL_SCORE.search(text)
    assert "Four threes in a row" not in text      # in-game commentary
    assert "Test preview" in text                  # media dated the day before


def test_post_game_digest_has_the_game_but_nothing_later(stats_db, store, tmp_path):
    text = _digest("post_game", POST, stats_db, store, tmp_path)
    assert FINAL_SCORE.search(text)
    assert "Adelaide have won the third quarter" in text
    assert "cost us the game" not in text          # presser after the cutoff
    assert "cost them" not in text                 # fan comment after the cutoff
    assert "test_handle" not in text
