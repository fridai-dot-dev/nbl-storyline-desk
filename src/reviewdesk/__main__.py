"""``python -m reviewdesk render --data <week.json> --out <weekly.html>``."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="reviewdesk", description="Review Desk tools.")
    commands = parser.add_subparsers(dest="command", required=True)
    render = commands.add_parser("render", help="render the weekly email page and its charts from a findings file")
    render.add_argument("--data", required=True, type=Path, help="the week's findings JSON")
    render.add_argument("--out", required=True, type=Path, help="where to write weekly.html; charts go beside it in charts/")
    args = parser.parse_args(argv)

    from .render import render_week

    data = json.loads(args.data.read_text(encoding="utf-8"))
    for path in render_week(data, args.out):
        print(path)
    return 0


if __name__ == "__main__":
    sys.exit(main())
