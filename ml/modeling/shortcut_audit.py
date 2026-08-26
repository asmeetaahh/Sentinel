"""
Pre-modeling feature/shortcut audit (PROJECT_CONTEXT.md section 11).

Run BEFORE interpreting any model result — if this audit fails, the
downstream metrics are not trustworthy regardless of how good they look.
Nothing here selects or drops features based on label correlation; it only
verifies the feature set stays within its documented boundaries and flags
anything worth a human look.
"""

from __future__ import annotations

import numpy as np
from sklearn.metrics import roc_auc_score

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
    "archetype",  # archetype is a merchant identity attribute, deliberately excluded from features
]

SUSPICIOUSLY_HIGH_SINGLE_FEATURE_AUC = 0.97
DOMINANT_IMPORTANCE_SHARE_THRESHOLD = 0.5


def audit_feature_columns(feature_cols: list[str]) -> dict:
    violations = {col: [bad for bad in FORBIDDEN_SUBSTRINGS if bad in col] for col in feature_cols}
    violations = {k: v for k, v in violations.items() if v}
    return {
        "n_features": len(feature_cols),
        "merchant_id_present": "merchant_id" in feature_cols,
        "day_index_present": "day_index" in feature_cols,
        "raw_date_present": any(c == "date" or c == "as_of_date" for c in feature_cols),
        "forbidden_column_violations": violations,
        "passed": len(violations) == 0 and "merchant_id" not in feature_cols and "day_index" not in feature_cols,
    }


def single_feature_auc_audit(X: np.ndarray, y: np.ndarray, feature_cols: list[str]) -> dict:
    aucs = {}
    for i, col in enumerate(feature_cols):
        try:
            aucs[col] = float(roc_auc_score(y, X[:, i]))
        except ValueError:
            aucs[col] = float("nan")

    ranked = dict(sorted(aucs.items(), key=lambda kv: -abs(kv[1] - 0.5) if not np.isnan(kv[1]) else -1))
    top10 = dict(list(ranked.items())[:10])
    suspicious = {k: v for k, v in aucs.items() if not np.isnan(v) and max(v, 1 - v) >= SUSPICIOUSLY_HIGH_SINGLE_FEATURE_AUC}

    return {
        "top10_by_discriminative_power": top10,
        "suspiciously_high_single_feature_auc": suspicious,
        "any_suspicious": len(suspicious) > 0,
    }


def feature_importance_concentration_audit(importances_by_model: dict[str, dict[str, float]]) -> dict:
    result = {}
    for model_name, importances in importances_by_model.items():
        if not importances:
            continue
        total = sum(importances.values()) or 1.0
        top_feature, top_value = max(importances.items(), key=lambda kv: kv[1])
        share = top_value / total
        result[model_name] = {
            "top_feature": top_feature,
            "top_feature_importance_share": float(share),
            "dominant": bool(share >= DOMINANT_IMPORTANCE_SHARE_THRESHOLD),
        }
    return result


def run_full_audit(X_train: np.ndarray, y_train: np.ndarray, feature_cols: list[str], importances_by_model: dict) -> dict:
    column_audit = audit_feature_columns(feature_cols)
    auc_audit = single_feature_auc_audit(X_train, y_train, feature_cols)
    importance_audit = feature_importance_concentration_audit(importances_by_model)

    overall_pass = column_audit["passed"] and not auc_audit["any_suspicious"] and not any(
        v["dominant"] for v in importance_audit.values()
    )

    return {
        "column_audit": column_audit,
        "single_feature_auc_audit": auc_audit,
        "feature_importance_concentration_audit": importance_audit,
        "overall_pass": overall_pass,
    }
