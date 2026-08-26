"""
Runtime leakage/consistency guards for the explainability pipeline —
defense in depth alongside the dedicated tests in tests/test_explainability.py.

Forbidden inputs (per PROJECT_CONTEXT.md and the task brief): labels,
events/scenario metadata, future observations, merchant identifiers as
predictive features. This module asserts the feature matrix handed to SHAP
never contains any of these, and that it matches the artifact's own
recorded column order exactly — the artifact is the source of truth for
"what this model was trained on," not the current feature manifest (which
could in principle drift from what a specific saved artifact used).
"""

from __future__ import annotations

FORBIDDEN_SUBSTRINGS = [
    "baseline_",
    "event_type",
    "event_id",
    "severity_score",
    "hard_negative",
    "elevation_ratio",
    "future_chargeback",
    "future_transaction",
    "label_elevated",
    "archetype",
]
FORBIDDEN_EXACT_NAMES = {"merchant_id", "day_index", "date", "as_of_date", "business_tier"}


def assert_no_forbidden_columns(feature_columns: list[str]) -> None:
    for col in feature_columns:
        if col in FORBIDDEN_EXACT_NAMES:
            raise ValueError(f"Forbidden identifier/label column found in feature set: {col!r}")
        for bad in FORBIDDEN_SUBSTRINGS:
            if bad in col:
                raise ValueError(f"Forbidden column pattern {bad!r} found in feature name: {col!r}")


def assert_columns_match_artifact(actual_columns: list[str], artifact_columns: list[str]) -> None:
    if actual_columns != artifact_columns:
        raise ValueError(
            "Feature matrix columns do not match the artifact's recorded feature_columns_in_order exactly "
            "(order and/or membership differ). Refusing to compute SHAP against a mismatched feature set.\n"
            f"actual:   {actual_columns}\n"
            f"artifact: {artifact_columns}"
        )
