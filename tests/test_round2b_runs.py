"""Round 2b: from the second set of live runs (2026-10-28).

A run cut off by the subscription's session limit stored the error text ("You've hit your session limit...") as its
summary. Failed and superseded runs must not reach the published site, and supplemental findings need a home in the
leadership email as an addendum.
"""
from conftest import EV_STATS, OPENER, POST, Q3_ADL, SUPP, fake_result, make_ctx


def test_error_results_never_become_the_summary(store):
    from storydesk.runner import record_result

    run_id = store.start_run("post_game", OPENER, POST, route="sdk")
    r = fake_result(1.0, 100)
    r.subtype, r.is_error, r.result = "error_during_execution", True, "You've hit your session limit · resets 7:40pm"
    record_result(store, run_id, r, route="sdk", num_agents=5)
    assert not store.get_run(run_id).get("summary")


def _post_run(ns, claim, status_complete=True):
    from storydesk.gates import apply_gates
    from storydesk.runner import record_result
    from storydesk.tools import write_finding

    ctx = make_ctx(ns.stats_db, ns.store, "post_game", POST)
    fid = write_finding(ctx, agent="stats", source_type="stats", kind="checked", number=26, query=Q3_ADL,
                        claim=claim, evidence=[EV_STATS])
    apply_gates(ns.store, ctx.run_id, stats_db=ns.stats_db, as_of=POST)
    r = fake_result(1.0, 100)
    if not status_complete:
        r.subtype, r.is_error = "error_during_execution", True
    record_result(ns.store, ctx.run_id, r, route="sdk", num_agents=5)
    return fid


def test_site_shows_only_the_latest_complete_run_of_each_type(demo_store, tmp_path):
    from storydesk.site import build_site

    failed = _post_run(demo_store, "Failed rerun: Adelaide scored 26 in Q3", status_complete=False)
    out = tmp_path / "site"
    build_site(demo_store.store, demo_store.stats_db, out, game_id=OPENER)
    assert not (out / "findings" / f"{failed}.html").exists()           # failed run stays off
    assert (out / "findings" / f"{demo_store.f_checked}.html").exists()  # earlier complete run still shown

    newer = _post_run(demo_store, "Newer complete run: Adelaide scored 26 in Q3")
    build_site(demo_store.store, demo_store.stats_db, out, game_id=OPENER)
    assert (out / "findings" / f"{newer}.html").exists()
    email = (out / "index.html").read_text(encoding="utf-8")
    assert "Newer complete run" in email
    assert not (out / "findings" / f"{demo_store.f_checked}.html").exists()  # superseded post-game run is off
    assert (out / "findings" / f"{demo_store.pre_finding}.html").exists()    # other run types unaffected


def test_supplemental_findings_appear_as_an_email_addendum(demo_store, tmp_path):
    from storydesk.gates import apply_gates
    from storydesk.runner import record_result
    from storydesk.site import build_site
    from storydesk.tools import write_finding

    ctx = make_ctx(demo_store.stats_db, demo_store.store, "supplemental", SUPP)
    fid = write_finding(ctx, agent="commentary", source_type="press", kind="attributed",
                        claim="Melbourne's coach said the third quarter cost them the game",
                        headline="Coach: the third quarter cost us",
                        evidence=[{"source_type": "press", "url": "https://example.test/presser", "ref": SUPP,
                                   "quote": "We lost the third quarter and that cost us the game."}])
    apply_gates(demo_store.store, ctx.run_id, stats_db=demo_store.stats_db, as_of=SUPP)
    record_result(demo_store.store, ctx.run_id, fake_result(0.5, 60), route="sdk", num_agents=3)
    out = tmp_path / "site"
    build_site(demo_store.store, demo_store.stats_db, out, game_id=OPENER)
    email = (out / "emails" / "supplemental.html").read_text(encoding="utf-8")  # the addendum is its own email page
    assert "Addendum" in email and "Coach: the third quarter cost us" in email
    assert (out / "findings" / f"{fid}.html").exists()
