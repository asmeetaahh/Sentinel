"""
Constants for the causal feature-engineering pipeline.

Nothing here reads or references events.csv or labels.csv — see
build_features.py for the structural guarantee (only merchants.csv and
daily_observations.csv are ever loaded).
"""

from __future__ import annotations

# Canonical trailing-window sizes (days), used throughout. Chosen to match
# the generator's own trailing baseline window (28d, see
# ml/data_generation/labels.py) plus a short (7d) and long (60d) horizon for
# multi-scale comparison, as suggested by the task brief.
WINDOW_SHORT = 7
WINDOW_MEDIUM = 28
WINDOW_LONG = 60
WINDOWS = (WINDOW_SHORT, WINDOW_MEDIUM, WINDOW_LONG)

# Metrics carried through the dedicated velocity/acceleration group (group 8)
# and the deviation-from-baseline group (group 9). Deliberately a curated
# subset of the most decision-relevant metrics, not "every column" — see
# docs/architecture/feature_engineering.md for the rationale (avoiding
# feature-count explosion).
VELOCITY_RATE_METRICS = ["chargeback_rate", "refund_rate", "fulfillment_on_time_rate"]
# gmv/transaction_count velocity is handled directly in build_features()
# (scale metrics use velocity_ratio, not velocity_diff) rather than via a
# generic loop over this list — kept here only as documentation of which
# metrics get ratio-style (relative growth) velocity treatment.
DEVIATION_METRICS = ["chargeback_rate", "refund_rate", "gmv", "fulfillment_on_time_rate", "new_customer_rate"]

# Numerical safety floors — prevent division blowups on near-zero
# denominators (e.g. a merchant's very first weeks with zero chargebacks).
STD_FLOOR = 1e-4
RATIO_DENOM_FLOOR = 1.0  # gmv/transaction_count are always >= 1 by construction, so this floor is a defensive no-op in practice
Z_SCORE_CLIP = 10.0

# Recency feature cap (days) — bounds days_since_last_chargeback so a
# merchant that has never had one doesn't produce an unbounded value.
RECENCY_CAP_DAYS = 90

PAYMENT_METHODS = ["card", "upi", "netbanking", "wallet", "bnpl"]
