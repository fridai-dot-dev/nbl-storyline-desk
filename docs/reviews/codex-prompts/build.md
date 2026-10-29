You had no open questions, so the brief stands as written. Build it per the brief (`docs/handoffs/2026-10-28-round-1-core.md`) and the design it links.

Done when `.venv/bin/python -m pytest -q` exits 0. Never edit anything under `tests/`. Don't add dependencies. Never parse `pbp.rds` or load large files wholesale into Python objects, because this machine has about 7.7 GB of memory.

End with the report the brief asks for.
