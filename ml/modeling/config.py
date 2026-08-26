"""
Configuration for the baseline ML evaluation pipeline. Every number here is
a documented, sensible default chosen once — not tuned against results.
See docs/research/baseline_ml_report.md for the full writeup.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np

# ---------------------------------------------------------------------------
# Reproducibility
# ---------------------------------------------------------------------------

SEED = 42

# ---------------------------------------------------------------------------
# Inputs (produced by prior, already-validated pipeline stages — never
# regenerated or modified by this module)
# ---------------------------------------------------------------------------

DATA_DIR = Path("data")
FEATURES_PATH = DATA_DIR / "processed" / "features.csv"
LABELS_PATH = DATA_DIR / "processed" / "labels.csv"
MERCHANTS_PATH = DATA_DIR / "raw" / "merchants.csv"
EVENTS_PATH = DATA_DIR / "scenarios" / "events.csv"  # failure analysis only — never a model feature
FEATURE_MANIFEST_PATH = DATA_DIR / "metadata" / "feature_manifest.json"

OUTPUT_DIR = DATA_DIR / "metadata" / "modeling"
PLOTS_DIR = OUTPUT_DIR / "plots"

# ---------------------------------------------------------------------------
# Merchant-level split
# ---------------------------------------------------------------------------

SPLIT_FRACTIONS = {"train": 0.6, "val": 0.2, "test": 0.2}

# ---------------------------------------------------------------------------
# Temporal stress test
#
# day_index < CUTOFF is the "early" period (used for train/val and for the
# normal held-out test); day_index >= CUTOFF is the "late" period, used
# ONLY for the temporal stress test. The model never sees late-period rows
# during training, from ANY merchant — this isolates "does performance
# degrade under distribution shift over time" from "does it generalize to
# unseen merchants" (the ordinary test split already covers the latter).
# ---------------------------------------------------------------------------

TEMPORAL_CUTOFF_DAY_INDEX = 120  # out of 180 days generated (see data_generation.md)

# ---------------------------------------------------------------------------
# Horizons (all three evaluated — none assumed to be the winner)
# ---------------------------------------------------------------------------

HORIZONS = [7, 14, 30]

# ---------------------------------------------------------------------------
# Historical-threshold baseline (Model A)
# ---------------------------------------------------------------------------

BASELINE_SIGNAL_FEATURE = "chargeback_rate_deviation_z"
BASELINE_THRESHOLD_GRID = [round(x, 2) for x in np.arange(-3.0, 10.01, 0.25)]

# ---------------------------------------------------------------------------
# Model hyperparameters — sensible, documented, NOT tuned against test
# results. Chosen once before looking at any evaluation metric.
# ---------------------------------------------------------------------------

LOGISTIC_REGRESSION_PARAMS = dict(
    C=1.0,
    max_iter=2000,
    class_weight="balanced",
    solver="lbfgs",
    random_state=SEED,
)

RANDOM_FOREST_PARAMS = dict(
    n_estimators=300,
    max_depth=6,
    min_samples_leaf=20,
    class_weight="balanced_subsample",
    n_jobs=-1,
    random_state=SEED,
)

XGBOOST_PARAMS = dict(
    n_estimators=300,
    max_depth=4,
    learning_rate=0.05,
    subsample=0.8,
    colsample_bytree=0.8,
    reg_lambda=1.0,
    eval_metric="logloss",
    n_jobs=-1,
    random_state=SEED,
)

# ---------------------------------------------------------------------------
# False-positive cost — a modeling ASSUMPTION for illustrating trade-offs,
# not a real Razorpay economics figure. See docs/research/baseline_ml_report.md.
# ---------------------------------------------------------------------------

ASSUMED_COST_PER_FALSE_POSITIVE = 1.0  # synthetic unit: analyst review time / merchant friction
BENEFIT_PER_TRUE_POSITIVE_SENSITIVITY = [2.0, 5.0, 10.0]  # "how many FPs is one real catch worth?"

# ---------------------------------------------------------------------------
# Regression (secondary problem)
# ---------------------------------------------------------------------------

REGRESSION_TARGET = "future_chargeback_amount"
