"""Shared validation for SQL that may inspect the cutoff-safe statistics views."""

from __future__ import annotations

import re


SAFE_RELATIONS = frozenset({"results", "box_team", "box_player", "pbp"})
_READ_START = re.compile(r"^(?:select|with)\b", re.IGNORECASE)
_MUTATING = re.compile(
    r"\b(?:insert|update|delete|merge|create|drop|alter|attach|detach|copy|pragma|install|load|"
    r"export|import|call|vacuum)\b",
    re.IGNORECASE,
)
_FORBIDDEN_OBJECT = re.compile(
    r"\b(?:raw_[a-z0-9_]*|match_ends|information_schema|pg_catalog|sqlite_[a-z0-9_]*|"
    r"duckdb_[a-z0-9_]*|read_[a-z0-9_]*|parquet_scan|csv_scan|glob|httpfs)\b",
    re.IGNORECASE,
)
_RELATION = re.compile(r"\b(?:from|join)\s+([a-z_][a-z0-9_$]*(?:\s*\.\s*[a-z_][a-z0-9_$]*)?)", re.IGNORECASE)
_TABLE_FUNCTION = re.compile(r"\b(?:from|join)\s+[a-z_][a-z0-9_$]*\s*\(", re.IGNORECASE)
_CTE = re.compile(r"\b([a-z_][a-z0-9_$]*)\s+as\s*\(", re.IGNORECASE)


def _without_literals_and_comments(sql: str) -> str:
    """Blank strings/comments so object names inside prose cannot affect checks."""
    output: list[str] = []
    index = 0
    while index < len(sql):
        if sql.startswith("--", index):
            end = sql.find("\n", index)
            if end < 0:
                output.extend(" " * (len(sql) - index))
                break
            output.extend(" " * (end - index))
            index = end
            continue
        if sql.startswith("/*", index):
            end = sql.find("*/", index + 2)
            if end < 0:
                raise ValueError("unterminated SQL comment")
            output.extend(" " * (end + 2 - index))
            index = end + 2
            continue
        if sql[index] == "'":
            output.append(" ")
            index += 1
            while index < len(sql):
                output.append(" ")
                if sql[index] == "'":
                    if index + 1 < len(sql) and sql[index + 1] == "'":
                        output.append(" ")
                        index += 2
                        continue
                    index += 1
                    break
                index += 1
            else:
                raise ValueError("unterminated SQL string")
            continue
        output.append(sql[index])
        index += 1
    return "".join(output)


def validate_safe_sql(sql: str) -> str:
    """Accept one read-only statement whose relations are all cutoff-safe views."""
    statement = sql.strip()
    if not statement or ";" in statement or not _READ_START.match(statement):
        raise ValueError("one SELECT or WITH statement is required")
    if '"' in statement or "`" in statement:
        raise ValueError("quoted identifiers are not permitted")
    visible = _without_literals_and_comments(statement)
    if _MUTATING.search(visible):
        raise ValueError("only read-only SQL is permitted")
    if _FORBIDDEN_OBJECT.search(visible):
        raise ValueError("the query references a relation outside the cutoff-safe catalog")
    if _TABLE_FUNCTION.search(visible):
        raise ValueError("table functions are not permitted")

    ctes = {match.group(1).lower() for match in _CTE.finditer(visible)}
    for match in _RELATION.finditer(visible):
        relation = re.sub(r"\s+", "", match.group(1)).lower()
        if "." in relation or relation not in SAFE_RELATIONS | ctes:
            raise ValueError(f"relation {relation!r} is not available")
    return statement
