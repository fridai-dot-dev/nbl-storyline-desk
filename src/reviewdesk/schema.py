"""JSON schemas for the Review Desk: the weekly findings file and the theme-coding result.

The theme-coding schemas are sent to the model as structured output, so they use only the
JSON Schema keywords structured outputs support (no numeric or string-length constraints,
``additionalProperties: false`` on every object). The weekly schema is checked in tests only.
"""

from __future__ import annotations

from typing import Any

REGIONS = ("south-east Melbourne", "western Melbourne", "Geelong region", "regional Victoria and the border")
STORE_FORMATS = ("standalone", "food court", "petrol-station kiosk")
CAUSAL_LABELS = ("coincides with", "consistent with", "tested")
THREADS = ("network", "spike", "praise", "promo_side_effect", "data_first", "food_safety", "quiet_stores")
SENSITIVITIES = ("food safety", "named staff")
CHARTS = ("theme_mix", "rating_trend", "store_scatter")
THEMES = (
    "freshness", "service", "wait_time", "product_range", "price_value",
    "cleanliness", "delivery", "stock_availability", "food_safety",
)
SOURCES = (
    "Google reviews", "delivery-platform ratings", "complaints inbox", "POS by hour",
    "rosters and manager changes", "stock-outs and waste", "promotions calendar",
    "membership deals", "weather", "local events",
)

REVIEW_CODING_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "required": ["review_id", "sentiment", "themes", "mentions_staff", "food_safety"],
    "properties": {
        "review_id": {"type": "string"},
        "sentiment": {"type": "string", "enum": ["positive", "mixed", "negative"]},
        "themes": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": ["theme", "quote"],
                "properties": {
                    "theme": {"type": "string", "enum": list(THEMES)},
                    "quote": {"type": "string"},
                },
            },
        },
        "mentions_staff": {"type": "boolean"},
        "food_safety": {"type": "boolean"},
    },
}

THEME_CODING_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "required": ["reviews"],
    "properties": {"reviews": {"type": "array", "items": REVIEW_CODING_SCHEMA}},
}

_STORE_ID = {"type": "integer", "minimum": 1}
_FINDING_ID = {"type": "string", "pattern": "^dd-[0-9]{2}$"}
_TEXT = {"type": "string", "minLength": 1}

FINDING_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "required": [
        "id", "thread", "headline", "premise", "number", "status", "causal",
        "scope", "sensitivity", "chart", "suggestion", "evidence",
    ],
    "properties": {
        "id": _FINDING_ID,
        "thread": {"enum": list(THREADS)},
        "headline": {"type": "string", "pattern": r"\?$"},
        "premise": _TEXT,
        "number": {
            "type": "object",
            "additionalProperties": False,
            "required": ["value", "label"],
            "properties": {"value": {"type": "string", "pattern": "^[0-9]"}, "label": _TEXT},
        },
        "status": _TEXT,
        "causal": {"enum": [*CAUSAL_LABELS, None]},
        "scope": {
            "type": "object",
            "additionalProperties": False,
            "required": ["level", "stores", "region"],
            "properties": {
                "level": {"enum": ["store", "region", "network"]},
                "stores": {"type": "array", "items": _STORE_ID},
                "region": {"enum": [*REGIONS, None]},
            },
        },
        "sensitivity": {"enum": [*SENSITIVITIES, None]},
        "chart": {"enum": [*CHARTS, None]},
        "suggestion": {"anyOf": [{"type": "string", "pattern": "^Suggestion: "}, {"type": "null"}]},
        "escalated": _TEXT,
        "evidence": {
            "type": "array",
            "minItems": 1,
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": ["source", "detail"],
                "properties": {"source": {"enum": list(SOURCES)}, "detail": _TEXT},
            },
        },
    },
    "allOf": [
        # Food-safety mentions are escalated on the day, and always sensitive.
        {"if": {"properties": {"thread": {"const": "food_safety"}}},
         "then": {"required": ["escalated"], "properties": {"sensitivity": {"const": "food safety"}}}},
        # Named staff are sensitive and never feed performance management automatically.
        {"if": {"properties": {"thread": {"const": "praise"}}},
         "then": {"properties": {"sensitivity": {"const": "named staff"}}}},
        # Explanations carry the judge's causal label; descriptive stories may not.
        {"if": {"properties": {"thread": {"enum": ["spike", "praise", "promo_side_effect", "data_first"]}}},
         "then": {"properties": {"causal": {"enum": list(CAUSAL_LABELS)}}}},
    ],
}

WEEK_SCHEMA: dict[str, Any] = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "type": "object",
    "additionalProperties": False,
    "required": [
        "illustrative", "desk", "subject", "week", "sent", "recipients", "lead", "stores",
        "charts", "findings", "store_sections", "meeting", "footer",
    ],
    "properties": {
        "illustrative": {"const": True},
        "desk": {"const": "Review Desk"},
        "subject": _TEXT,
        "week": {
            "type": "object",
            "additionalProperties": False,
            "required": ["label", "start", "end"],
            "properties": {"label": _TEXT, "start": {"type": "string", "format": "date"},
                           "end": {"type": "string", "format": "date"}},
        },
        "sent": _TEXT,
        "recipients": {"type": "string", "pattern": "internal only$"},
        "lead": _TEXT,
        "stores": {
            "type": "array",
            "minItems": 1,
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": ["store", "region", "format"],
                "properties": {"store": _STORE_ID, "region": {"enum": list(REGIONS)},
                               "format": {"enum": list(STORE_FORMATS)}},
            },
        },
        "charts": {
            "type": "object",
            "additionalProperties": False,
            "required": list(CHARTS),
            "properties": {
                "theme_mix": {
                    "type": "object",
                    "additionalProperties": False,
                    "required": ["title", "centre_label", "unit", "slices"],
                    "properties": {
                        "title": _TEXT, "centre_label": _TEXT, "unit": {"type": "string"},
                        "slices": {"type": "array", "minItems": 2, "items": {
                            "type": "object", "additionalProperties": False, "required": ["label", "value"],
                            "properties": {"label": _TEXT, "value": {"type": "number", "exclusiveMinimum": 0}}}},
                    },
                },
                "rating_trend": {
                    "type": "object",
                    "additionalProperties": False,
                    "required": ["title", "store", "baseline", "baseline_label", "points"],
                    "properties": {
                        "title": _TEXT, "store": _STORE_ID, "baseline": {"type": "number"}, "baseline_label": _TEXT,
                        "points": {"type": "array", "minItems": 3, "items": {
                            "type": "object", "additionalProperties": False, "required": ["label", "rating"],
                            "properties": {"label": _TEXT, "rating": {"type": "number"}}}},
                    },
                },
                "store_scatter": {
                    "type": "object",
                    "additionalProperties": False,
                    "required": ["title", "x_label", "y_label", "points"],
                    "properties": {
                        "title": _TEXT, "x_label": _TEXT, "y_label": _TEXT,
                        "points": {"type": "array", "minItems": 3, "items": {
                            "type": "object", "additionalProperties": False, "required": ["store", "x", "y"],
                            "properties": {"store": _STORE_ID, "x": {"type": "number"}, "y": {"type": "number"}}}},
                    },
                },
            },
        },
        "findings": {"type": "array", "minItems": 7, "items": FINDING_SCHEMA},
        "store_sections": {
            "type": "array",
            "minItems": 1,
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": ["store", "note", "finding_ids"],
                "properties": {"store": _STORE_ID, "note": _TEXT,
                               "finding_ids": {"type": "array", "items": _FINDING_ID}},
            },
        },
        "meeting": {
            "type": "object",
            "additionalProperties": False,
            "required": ["day", "note", "questions"],
            "properties": {"day": _TEXT, "note": _TEXT,
                           "questions": {"type": "array", "minItems": 1, "items": {"type": "string", "pattern": r"\?$"}}},
        },
        "footer": {
            "type": "object",
            "additionalProperties": False,
            "required": ["run", "data_to", "cost"],
            "properties": {"run": _TEXT, "data_to": _TEXT, "cost": _TEXT},
        },
    },
}
