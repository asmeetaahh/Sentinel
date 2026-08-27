"""
Confidence / Data Quality V1 — a deterministic transparency layer over the
existing risk assessment, NOT a second model and NOT a statistical
confidence interval. See docs/architecture/confidence_data_quality.md for
the full policy rationale.

This module computes nothing the feature pipeline doesn't already expose:
    - history_days: derived from day_index (state.daily_observations),
      the same value risk_service/incident_service already resolve via
      backend.services.lookups.resolve_day_index — not re-derived, just
      read back as "how many days of this merchant's history exist up to
      and including this date."
    - feature_coverage_status: read directly off the already-built feature
      row (state.features), checking for missing values across the exact
      column set the loaded model artifact was trained on
      (state.feature_columns) — no new feature computation.
    - the two history thresholds are ml/features/config.py's own
      WINDOW_MEDIUM/WINDOW_LONG constants, imported directly — never
      redeclared, so this policy can never silently drift from the actual
      feature pipeline's own window definitions.

Why these two signals and no others: ml/features' own primitives use
`rolling(window, min_periods=1)` / `expanding(min_periods=1)` (see
docs/architecture/feature_engineering.md "Known limitations"), which means
every feature value is always numerically present, even when computed on
far less data than its nominal window — "a 60d feature computed at
day_index=2 is really a 3-day average." That existing, documented
limitation is precisely the thing a confidence signal should surface, and
history_days vs. the pipeline's own window sizes is the correct,
already-true way to surface it — not a new statistic invented for this
task.
"""

from __future__ import annotations

import pandas as pd

from backend.api.state import AppState
from ml.features.config import WINDOW_LONG, WINDOW_MEDIUM

HISTORY_FULL_THRESHOLD_DAYS = WINDOW_LONG  # 60 — every trailing window (7d/28d/60d) is backed by its full size
HISTORY_PARTIAL_THRESHOLD_DAYS = WINDOW_MEDIUM  # 28 — the primary window used by the simulator/intervention controls

BASIS = (
    f"Deterministic policy: history_days (days of observed benchmark history available up to and including "
    f"this date) compared against the feature pipeline's own trailing-window sizes "
    f"(ml/features/config.py: WINDOW_MEDIUM={HISTORY_PARTIAL_THRESHOLD_DAYS}d, WINDOW_LONG={HISTORY_FULL_THRESHOLD_DAYS}d), "
    "plus whether every model input feature is present (non-missing) for this date. Not a statistical "
    "confidence interval, not a model-calibrated probability, and not independently validated — see "
    "docs/architecture/confidence_data_quality.md."
)

LIMITATIONS = [
    "This confidence assessment is a deterministic prototype heuristic based on observed history length and "
    "feature completeness — not a statistical confidence interval, not a model-calibrated probability, and "
    "not independently validated.",
    "This is a synthetic benchmark. Real-world validation of both the risk model and this confidence heuristic "
    "is still pending.",
]


def _feature_coverage(state: AppState, merchant_id: str, day_index: int) -> tuple[str, list[str]]:
    row = state.features[(state.features["merchant_id"] == merchant_id) & (state.features["day_index"] == day_index)]
    if row.empty:
        # Should be unreachable in practice: callers only ever pass a
        # day_index already resolved via resolve_day_index against
        # daily_observations, and every such day has a matching feature
        # row. Treated as "incomplete" rather than raising, so a genuine
        # data gap degrades the confidence signal instead of 500ing the
        # whole risk response.
        return "incomplete", list(state.feature_columns)
    values = row.iloc[0][state.feature_columns]
    missing = [col for col in state.feature_columns if pd.isna(values[col])]
    return ("incomplete" if missing else "complete"), missing


def assess_confidence(state: AppState, merchant_id: str, day_index: int) -> dict:
    history_days = day_index + 1  # day_index is 0-based; day 0 already means 1 observed day
    feature_coverage_status, missing_features = _feature_coverage(state, merchant_id, day_index)

    reasons: list[str] = []

    if feature_coverage_status == "incomplete":
        confidence_level = "limited"
        reasons.append(
            f"{len(missing_features)} of {len(state.feature_columns)} model input features are missing for "
            "this date (feature_coverage_status: incomplete)."
        )
    elif history_days >= HISTORY_FULL_THRESHOLD_DAYS:
        confidence_level = "high"
        reasons.append(
            f"This merchant has {history_days} days of observed history available as of this date, at or "
            f"beyond the feature pipeline's longest trailing window ({HISTORY_FULL_THRESHOLD_DAYS}d) — every "
            "trailing-window feature (7d/28d/60d) is backed by its full intended window, not a shortened one."
        )
        reasons.append(f"All {len(state.feature_columns)} model input features are present for this date.")
    elif history_days >= HISTORY_PARTIAL_THRESHOLD_DAYS:
        confidence_level = "medium"
        reasons.append(
            f"This merchant has {history_days} days of observed history — enough for the feature pipeline's "
            f"primary {HISTORY_PARTIAL_THRESHOLD_DAYS}-day windows, but short of its longest "
            f"{HISTORY_FULL_THRESHOLD_DAYS}-day window, which is still computed on a shorter-than-intended "
            "history for this date."
        )
        reasons.append(f"All {len(state.feature_columns)} model input features are present for this date.")
    else:
        confidence_level = "limited"
        reasons.append(
            f"This merchant has only {history_days} days of observed history available as of this date — "
            f"short even of the feature pipeline's primary {HISTORY_PARTIAL_THRESHOLD_DAYS}-day window. "
            "Trailing-window and deviation-from-baseline features for this date are computed on much less "
            "data than their nominal window size."
        )

    return {
        "confidence_level": confidence_level,
        "history_days": history_days,
        "history_window_partial_days": HISTORY_PARTIAL_THRESHOLD_DAYS,
        "history_window_full_days": HISTORY_FULL_THRESHOLD_DAYS,
        "feature_coverage_status": feature_coverage_status,
        "reasons": reasons,
        "limitations": list(LIMITATIONS),
        "basis": BASIS,
        "provenance": "derived",
    }
