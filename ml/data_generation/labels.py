"""
Future-label construction for the chargeback-elevation prediction task.

Leakage discipline (see PROJECT_CONTEXT.md "Data leakage"):
  - For a given as_of_date t, every "baseline_*_trailing" quantity is
    computed strictly from day_index in [t - L + 1, t] — data at/before t.
  - Every "future_*" quantity is computed strictly from day_index in
    (t, t + horizon_days] — data strictly after t.
  - Rows where the full future window does not exist within the generated
    run (t + horizon_days exceeds the last day) are dropped, never
    padded/estimated — we do not fabricate label information.
  - This table is kept entirely separate from daily_observations; nothing
    here is ever written back into that table.

Thresholds below (elevation ratio, materiality floors) are illustrative
synthetic modeling assumptions for benchmark construction, not calibrated
to real chargeback-loss statistics. See docs/data_generation.md.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from .config import (
    LABEL_ELEVATION_RATIO_THRESHOLD,
    LABEL_HORIZONS_DAYS,
    LABEL_MIN_ABSOLUTE_FLOOR,
    LABEL_MIN_GMV_FRACTION_FLOOR,
    LABEL_TRAILING_WINDOW_DAYS,
)


def build_labels(daily_df: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict] = []
    L = LABEL_TRAILING_WINDOW_DAYS

    for merchant_id, group in daily_df.groupby("merchant_id", sort=False):
        group = group.sort_values("day_index").reset_index(drop=True)
        n = len(group)

        gmv = group["gmv"].to_numpy()
        txn = group["transaction_count"].to_numpy(dtype=float)
        cb_amt = group["chargeback_amount"].to_numpy()
        cb_cnt = group["chargeback_count"].to_numpy(dtype=float)
        dates = group["date"].to_numpy()

        cum_gmv = np.concatenate([[0.0], np.cumsum(gmv)])
        cum_txn = np.concatenate([[0.0], np.cumsum(txn)])
        cum_cb_amt = np.concatenate([[0.0], np.cumsum(cb_amt)])
        cum_cb_cnt = np.concatenate([[0.0], np.cumsum(cb_cnt)])

        for t in range(n):
            L_eff = min(L, t + 1)
            a = t - L_eff + 1

            trailing_gmv_sum = cum_gmv[t + 1] - cum_gmv[a]
            trailing_cb_amt_sum = cum_cb_amt[t + 1] - cum_cb_amt[a]
            trailing_txn_sum = cum_txn[t + 1] - cum_txn[a]
            trailing_cb_cnt_sum = cum_cb_cnt[t + 1] - cum_cb_cnt[a]

            baseline_daily_gmv_trailing = trailing_gmv_sum / L_eff
            baseline_daily_cb_amt_trailing = trailing_cb_amt_sum / L_eff
            baseline_cb_rate_trailing = (
                trailing_cb_cnt_sum / trailing_txn_sum if trailing_txn_sum > 0 else 0.0
            )

            for h in LABEL_HORIZONS_DAYS:
                if t + h > n - 1:
                    continue  # incomplete future window — drop, never fabricate

                future_cb_amt = cum_cb_amt[t + h + 1] - cum_cb_amt[t + 1]
                future_cb_cnt = cum_cb_cnt[t + h + 1] - cum_cb_cnt[t + 1]
                future_txn = cum_txn[t + h + 1] - cum_txn[t + 1]
                future_cb_rate = future_cb_cnt / future_txn if future_txn > 0 else 0.0

                expected_amt = baseline_daily_cb_amt_trailing * h
                elevation_ratio_amount = future_cb_amt / max(expected_amt, 1.0)
                elevation_ratio_rate = future_cb_rate / max(baseline_cb_rate_trailing, 1e-4)

                materiality_floor = max(
                    LABEL_MIN_ABSOLUTE_FLOOR,
                    baseline_daily_gmv_trailing * h * LABEL_MIN_GMV_FRACTION_FLOOR,
                )
                label_elevated = int(
                    elevation_ratio_amount >= LABEL_ELEVATION_RATIO_THRESHOLD
                    and future_cb_amt >= materiality_floor
                )

                rows.append(
                    {
                        "merchant_id": merchant_id,
                        "as_of_date": dates[t],
                        "day_index": t,
                        "horizon_days": h,
                        "future_chargeback_amount": future_cb_amt,
                        "future_chargeback_rate": future_cb_rate,
                        "future_transaction_count": int(future_txn),
                        "baseline_daily_gmv_trailing": baseline_daily_gmv_trailing,
                        "baseline_daily_chargeback_amount_trailing": baseline_daily_cb_amt_trailing,
                        "baseline_chargeback_rate_trailing": baseline_cb_rate_trailing,
                        "elevation_ratio_amount": elevation_ratio_amount,
                        "elevation_ratio_rate": elevation_ratio_rate,
                        "label_elevated_chargeback": label_elevated,
                    }
                )

    from .schema import columns

    df = pd.DataFrame(rows)
    return df[columns("labels")]
