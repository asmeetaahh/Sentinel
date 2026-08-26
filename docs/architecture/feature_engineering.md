# Causal Feature Engineering Pipeline

Source: [`ml/features/`](../../ml/features/)
Regenerate with: [`scripts/build_features.py`](../../scripts/build_features.py)
Tests: [`tests/test_feature_engineering.py`](../../tests/test_feature_engineering.py)

## What this is

Transforms `data/raw/daily_observations.csv` into one row of merchant-level
features per `(merchant_id, day_index)`, using **only** information
available at or before that day. This is a pure transformation step: it
does not train a model, does not read the label table, and does not decide
which prediction horizon matters — per `PROJECT_CONTEXT.md`, horizon
selection happens at the evaluation stage, and features here are computed
independently of any horizon so the same feature row can be joined against
7d/14d/30d labels later.

## Quick start

```bash
.venv/bin/python scripts/build_features.py
.venv/bin/python -m pytest tests/test_feature_engineering.py -v
```

Writes `data/processed/features.csv` (one row per merchant-day, 55 feature
columns plus `merchant_id`/`date`/`day_index`) and
`data/metadata/feature_manifest.json` (the machine-readable version of the
table below).

## Design principles

- **Causal only.** Every feature is a trailing window ending at t
  (inclusive) or an expanding window over `day_index <= t`. Nothing
  centered, forward-looking, or computed over the whole series at once.
- **No scenario or label access.** The pipeline never imports or reads
  `events.csv` or `labels.csv` — not "filters them out afterward," never
  opens them at all. Enforced by a source-code-literal test, not just a
  column check (see Testing below).
- **Two merchants.csv columns only.** `merchant_id` and `signup_date` — no
  `baseline_*` column. Those are generator ground-truth parameters, not
  observable to a real system, and the dataset-validation leakage audit
  (`docs/research/dataset_validation_report.md`) quantified how much
  "cheating" using them directly would buy (AUC 0.52–0.58) — exactly what
  this pipeline must not do.
- **Volume-weighted rates, not means-of-daily-rates.** `refund_rate_28d` is
  `sum(refund_count)/sum(transaction_count)` over the window, not the mean
  of 28 daily ratios. Dataset validation found daily-grain rates are
  zero-inflated for low-volume merchants (median `chargeback_rate` is
  exactly 0 across every archetype) — averaging daily ratios directly would
  let a single high-ratio, low-volume day dominate a window's estimate.
  Volume-weighting fixes that.
- **Multiple time scales (7d/28d/60d).** Matches the generator's own
  trailing-label window (28d) plus a short and a long comparison scale,
  which is what the velocity/acceleration and deviation groups below are
  built from.
- **Curated, not exhaustive.** 55 features, not "every rolling stat over
  every column × every window," per the 50–70 target and the explicit
  instruction to avoid feature-count explosion. Velocity/acceleration and
  deviation-from-baseline are computed for a deliberately chosen subset of
  the most decision-relevant metrics (`chargeback_rate`, `refund_rate`,
  `fulfillment_on_time_rate`, `gmv`, plus `transaction_count`/
  `new_customer_rate` where it's the natural pairing) rather than every raw
  column in the schema.
- **Liquidity stays interpretable.** `liquidity_to_gmv_ratio_28d` reads as
  "days of current GMV held as buffer," `pending_settlement_to_gmv_28d` and
  `liquidity_coefficient_of_variation_28d` are similarly named ratios — no
  feature here is a black-box "risk score" standing in for liquidity.

## Feature groups

55 features across the 9 groups required by `PROJECT_CONTEXT.md`:

### 1. Payment behavior (5)

| Feature | Definition | Source columns | Window | Kind |
|---|---|---|---|---|
| `payment_mix_hhi_7d` | Herfindahl-Hirschman index (sum of squared GMV-weighted payment-method shares) over trailing 7d. Higher = more concentrated in one method. | pct_pay_card, pct_pay_upi, pct_pay_netbanking, pct_pay_wallet, pct_pay_bnpl, gmv | 7d | level |
| `payment_mix_hhi_28d` | Herfindahl-Hirschman index (sum of squared GMV-weighted payment-method shares) over trailing 28d. Higher = more concentrated in one method. | pct_pay_card, pct_pay_upi, pct_pay_netbanking, pct_pay_wallet, pct_pay_bnpl, gmv | 28d | level |
| `payment_mix_hhi_60d` | Herfindahl-Hirschman index (sum of squared GMV-weighted payment-method shares) over trailing 60d. Higher = more concentrated in one method. | pct_pay_card, pct_pay_upi, pct_pay_netbanking, pct_pay_wallet, pct_pay_bnpl, gmv | 60d | level |
| `payment_mix_l1_drift_7v28` | Sum of |share_i(7d) - share_i(28d)| across payment methods — how much the mix has moved recently vs. the medium-term. | pct_pay_card, pct_pay_upi, pct_pay_netbanking, pct_pay_wallet, pct_pay_bnpl, gmv | 7d vs 28d | ratio |
| `payment_mix_l1_drift_28v60` | Sum of |share_i(28d) - share_i(60d)| across payment methods — medium-term vs. long-term mix drift. | pct_pay_card, pct_pay_upi, pct_pay_netbanking, pct_pay_wallet, pct_pay_bnpl, gmv | 28d vs 60d | ratio |

### 2. Refund behavior (5)

| Feature | Definition | Source columns | Window | Kind |
|---|---|---|---|---|
| `refund_rate_7d` | Volume-weighted refund rate over trailing 7d: sum(refund_count)/sum(transaction_count). Not a mean of daily rates, to avoid low-count distortion. | refund_count, transaction_count | 7d | level |
| `refund_rate_28d` | Volume-weighted refund rate over trailing 28d: sum(refund_count)/sum(transaction_count). Not a mean of daily rates, to avoid low-count distortion. | refund_count, transaction_count | 28d | level |
| `refund_rate_60d` | Volume-weighted refund rate over trailing 60d: sum(refund_count)/sum(transaction_count). Not a mean of daily rates, to avoid low-count distortion. | refund_count, transaction_count | 60d | level |
| `refund_amount_to_gmv_28d` | Dollar-weighted refund burden: sum(refund_amount)/sum(gmv) over trailing 28d. | refund_amount, gmv | 28d | ratio |
| `refund_count_28d` | Raw refund count over trailing 28d — exposure/confidence context for refund_rate_28d (a rate from 2 refunds is far less reliable than one from 50). | refund_count | 28d | level |

### 3. Chargeback behavior (6)

| Feature | Definition | Source columns | Window | Kind |
|---|---|---|---|---|
| `chargeback_rate_7d` | Volume-weighted chargeback rate over trailing 7d: sum(chargeback_count)/sum(transaction_count). | chargeback_count, transaction_count | 7d | level |
| `chargeback_rate_28d` | Volume-weighted chargeback rate over trailing 28d: sum(chargeback_count)/sum(transaction_count). | chargeback_count, transaction_count | 28d | level |
| `chargeback_rate_60d` | Volume-weighted chargeback rate over trailing 60d: sum(chargeback_count)/sum(transaction_count). | chargeback_count, transaction_count | 60d | level |
| `chargeback_amount_to_gmv_28d` | Dollar-weighted chargeback exposure: sum(chargeback_amount)/sum(gmv) over trailing 28d. | chargeback_amount, gmv | 28d | ratio |
| `chargeback_count_28d` | Raw chargeback count over trailing 28d — exposure/confidence context for chargeback_rate_28d. | chargeback_count | 28d | level |
| `days_since_last_chargeback` | Days since the most recent day (<=t) with chargeback_count>0 for this merchant, capped at 90. A recency signal that doesn't collapse to 0 on days with no observed chargebacks yet. | chargeback_count, day_index | expanding (capped) | level |

### 4. Fulfillment (4)

| Feature | Definition | Source columns | Window | Kind |
|---|---|---|---|---|
| `fulfillment_on_time_rate_7d` | Transaction-volume-weighted mean of fulfillment_on_time_rate over trailing 7d. | fulfillment_on_time_rate, transaction_count | 7d | level |
| `fulfillment_on_time_rate_28d` | Transaction-volume-weighted mean of fulfillment_on_time_rate over trailing 28d. | fulfillment_on_time_rate, transaction_count | 28d | level |
| `fulfillment_on_time_rate_60d` | Transaction-volume-weighted mean of fulfillment_on_time_rate over trailing 60d. | fulfillment_on_time_rate, transaction_count | 60d | level |
| `fulfillment_delay_avg_days_28d` | Transaction-volume-weighted mean fulfillment delay (days) over trailing 28d. | fulfillment_delay_avg_days, transaction_count | 28d | level |

### 5. Customer mix (4)

| Feature | Definition | Source columns | Window | Kind |
|---|---|---|---|---|
| `new_customer_rate_7d` | Volume-weighted new-customer share over trailing 7d: sum(new_customers)/sum(customer_count). | new_customers, customer_count | 7d | level |
| `new_customer_rate_28d` | Volume-weighted new-customer share over trailing 28d: sum(new_customers)/sum(customer_count). | new_customers, customer_count | 28d | level |
| `new_customer_rate_60d` | Volume-weighted new-customer share over trailing 60d: sum(new_customers)/sum(customer_count). | new_customers, customer_count | 60d | level |
| `customer_count_28d` | Mean daily distinct customer count over trailing 28d — activity scale context. | customer_count | 28d | level |

### 6. Financial state (4)

| Feature | Definition | Source columns | Window | Kind |
|---|---|---|---|---|
| `liquidity_balance_28d` | Mean daily liquidity_balance over trailing 28d (same units as gmv). | liquidity_balance | 28d | level |
| `liquidity_to_gmv_ratio_28d` | liquidity_balance_28d / mean(gmv, 28d) — buffer expressed as 'days of current GMV', directly interpretable. | liquidity_balance, gmv | 28d | ratio |
| `pending_settlement_to_gmv_28d` | mean(pending_settlement_amount, 28d) / mean(gmv, 28d) — settlement pipeline scale relative to volume. | pending_settlement_amount, gmv | 28d | ratio |
| `liquidity_coefficient_of_variation_28d` | std(liquidity_balance, 28d) / mean(liquidity_balance, 28d) — how stable the buffer has been recently. | liquidity_balance | 28d | ratio |

### 7. Merchant behavior (7)

| Feature | Definition | Source columns | Window | Kind |
|---|---|---|---|---|
| `gmv_level_28d` | Mean daily gmv over trailing 28d. | gmv | 28d | level |
| `transaction_count_level_28d` | Mean daily transaction_count over trailing 28d. | transaction_count | 28d | level |
| `gmv_coefficient_of_variation_28d` | std(gmv, 28d) / mean(gmv, 28d) — the merchant's own day-to-day noisiness, context for interpreting other deviations. | gmv | 28d | ratio |
| `merchant_tenure_days` | date - signup_date, in days. A real business-facing attribute (account age), not a generator ground-truth risk parameter — the only merchants.csv-derived feature in this pipeline. | date (daily_observations), signup_date (merchants) | n/a (point-in-time) | level |
| `is_weekend` | 1 if the observation date is Saturday/Sunday, else 0. | date | n/a (point-in-time) | level |
| `day_of_year_sin` | sin(2*pi*day_of_year/365.25) — cyclical calendar position, lets a model account for seasonality explicitly. | date | n/a (point-in-time) | level |
| `day_of_year_cos` | cos(2*pi*day_of_year/365.25) — paired with day_of_year_sin for a non-discontinuous yearly cycle encoding. | date | n/a (point-in-time) | level |

### 8. Temporal velocity/acceleration (14)

| Feature | Definition | Source columns | Window | Kind |
|---|---|---|---|---|
| `chargeback_rate_velocity_7v28` | chargeback_rate(7d) - chargeback_rate(28d) — short-term momentum (percentage points). | chargeback_count, transaction_count | 7d vs 28d | velocity |
| `chargeback_rate_velocity_28v60` | chargeback_rate(28d) - chargeback_rate(60d) — medium-term momentum (percentage points). | chargeback_count, transaction_count | 28d vs 60d | velocity |
| `chargeback_rate_acceleration` | velocity_7v28 - velocity_28v60 — is short-term momentum itself increasing (acceleration) or fading? | chargeback_count, transaction_count | 7d/28d/60d composite | acceleration |
| `refund_rate_velocity_7v28` | refund_rate(7d) - refund_rate(28d) — short-term momentum (percentage points). | refund_count, transaction_count | 7d vs 28d | velocity |
| `refund_rate_velocity_28v60` | refund_rate(28d) - refund_rate(60d) — medium-term momentum (percentage points). | refund_count, transaction_count | 28d vs 60d | velocity |
| `refund_rate_acceleration` | velocity_7v28 - velocity_28v60 — is short-term momentum itself increasing (acceleration) or fading? | refund_count, transaction_count | 7d/28d/60d composite | acceleration |
| `fulfillment_on_time_rate_velocity_7v28` | fulfillment_on_time_rate(7d) - fulfillment_on_time_rate(28d) — short-term momentum (percentage points). | fulfillment_on_time_rate, transaction_count | 7d vs 28d | velocity |
| `fulfillment_on_time_rate_velocity_28v60` | fulfillment_on_time_rate(28d) - fulfillment_on_time_rate(60d) — medium-term momentum (percentage points). | fulfillment_on_time_rate, transaction_count | 28d vs 60d | velocity |
| `fulfillment_on_time_rate_acceleration` | velocity_7v28 - velocity_28v60 — is short-term momentum itself increasing (acceleration) or fading? | fulfillment_on_time_rate, transaction_count | 7d/28d/60d composite | acceleration |
| `gmv_velocity_7v28` | mean(gmv,7d)/mean(gmv,28d) - 1 — relative GMV growth, short vs medium term. | gmv | 7d vs 28d | velocity |
| `gmv_velocity_28v60` | mean(gmv,28d)/mean(gmv,60d) - 1 — relative GMV growth, medium vs long term. | gmv | 28d vs 60d | velocity |
| `gmv_acceleration` | gmv_velocity_7v28 - gmv_velocity_28v60 — is GMV growth speeding up or slowing down? | gmv | 7d/28d/60d composite | acceleration |
| `transaction_count_velocity_7v28` | mean(transaction_count,7d)/mean(transaction_count,28d) - 1. | transaction_count | 7d vs 28d | velocity |
| `new_customer_rate_velocity_7v28` | new_customer_rate(7d) - new_customer_rate(28d). | new_customers, customer_count | 7d vs 28d | velocity |

### 9. Deviation from merchant-specific baseline (6)

| Feature | Definition | Source columns | Window | Kind |
|---|---|---|---|---|
| `chargeback_rate_deviation_z` | (current 7d chargeback_rate - this merchant's own expanding-history mean of its 28d chargeback_rate) / expanding std, clipped to [-10,10]. Uses only this merchant's own day_index<=t history. | chargeback_rate | 7d vs expanding(28d-smoothed) | deviation |
| `refund_rate_deviation_z` | (current 7d refund_rate - this merchant's own expanding-history mean of its 28d refund_rate) / expanding std, clipped to [-10,10]. Uses only this merchant's own day_index<=t history. | refund_rate | 7d vs expanding(28d-smoothed) | deviation |
| `gmv_deviation_z` | (current 7d gmv - this merchant's own expanding-history mean of its 28d gmv) / expanding std, clipped to [-10,10]. Uses only this merchant's own day_index<=t history. | gmv | 7d vs expanding(28d-smoothed) | deviation |
| `fulfillment_on_time_rate_deviation_z` | (current 7d fulfillment_on_time_rate - this merchant's own expanding-history mean of its 28d fulfillment_on_time_rate) / expanding std, clipped to [-10,10]. Uses only this merchant's own day_index<=t history. | fulfillment_on_time_rate | 7d vs expanding(28d-smoothed) | deviation |
| `new_customer_rate_deviation_z` | (current 7d new_customer_rate - this merchant's own expanding-history mean of its 28d new_customer_rate) / expanding std, clipped to [-10,10]. Uses only this merchant's own day_index<=t history. | new_customer_rate | 7d vs expanding(28d-smoothed) | deviation |
| `liquidity_deviation_z` | (current 7d liquidity_balance - this merchant's own expanding-history mean of its 28d liquidity_balance) / expanding std, clipped to [-10,10]. | liquidity_balance | 7d vs expanding(28d-smoothed) | deviation |

## Velocity vs. deviation — two different lenses, on purpose

`PROJECT_CONTEXT.md` lists "temporal velocity/acceleration" and "deviation
from merchant-specific baseline" as two separate feature groups, and this
pipeline keeps them conceptually distinct rather than folding one into the
other:

- **Velocity/acceleration** (group 8) answers "is this metric moving, and
  is that movement speeding up?" — a first difference (7d vs 28d, 28d vs
  60d) and a second difference (change in the two velocities).
- **Deviation from baseline** (group 9) answers "how unusual is the
  *current* value relative to what's normal for *this specific merchant*?"
  — a z-score of the current 7d value against this merchant's own
  expanding-history mean/std (of a 28d-smoothed series, so the baseline
  itself isn't dominated by single low-count days).

A merchant whose chargeback rate has been climbing steadily for months
might show near-zero velocity right now (it's already at its new, stable,
elevated level) but a large deviation-z (that level is still far from this
merchant's historical normal). The two groups are meant to catch different
shapes of the same underlying problem.

Rate-type velocities (`chargeback_rate`, `refund_rate`,
`fulfillment_on_time_rate`) are expressed as **plain differences**
(percentage points), not ratios — a ratio would blow up whenever the
longer-window rate is near zero, which is common at this benchmark's
transaction volumes. Scale metrics (`gmv`, `transaction_count`) use
**relative-growth ratios** instead, since they're always positive and
naturally vary by orders of magnitude across merchants.

## Handling low-count rates and payment-mix drift

Two requirements called out explicitly in the brief, both addressed
directly rather than as an afterthought:

- **Low-count chargeback/refund rates**: addressed by (a) volume-weighted
  aggregation instead of daily-rate averaging, (b) pairing every rate
  feature's 28d window with a raw count feature
  (`chargeback_count_28d`, `refund_count_28d`) so a downstream model or
  analyst can see how many observations back a given rate, and (c)
  `days_since_last_chargeback` as an alternative, count-independent lens on
  the same sparse process.
- **`payment_method_shift` observability**: addressed by
  `payment_mix_l1_drift_7v28`/`_28v60` — an L1 distance between
  GMV-weighted payment-method share vectors at two time scales. Dataset
  validation found this scenario's GMV signal is unreliable per-instance
  (~40% of instances showed a net GMV *decline* over the event window); the
  payment-mix drift is the scenario's actual, reliably observable signal,
  and these features expose it directly rather than depending on GMV/volume
  features to (incorrectly) catch it.

## Growth ≠ risk, preserved in the feature set

Per the generator's core validated property, the feature set deliberately
keeps **volume/growth features** (`gmv_level_28d`, `gmv_velocity_*`,
`transaction_count_level_28d`, `transaction_count_velocity_7v28`) and
**health features** (`chargeback_rate_*`, `refund_rate_*`,
`fulfillment_on_time_rate_*`) as separate, independent feature families. A
model trained on this feature set has the information needed to learn
"GMV rising + health flat = benign" as distinct from "health degrading,
GMV incidental" — collapsing these into a single combined score here would
have pre-judged that distinction instead of leaving it for the model to
learn.

## Leakage guarantees

1. **Structural**: `ml/features/*.py` contains no reference to `events.csv`
   or `labels.csv` as a string literal, and no reference to
   `label_elevated` — verified by
   `test_no_source_code_reference_to_events_or_labels_files`, which greps
   the actual source files, not just the runtime behavior.
2. **Column-level**: no output feature name contains `baseline_`,
   `event_type`, `event_id`, `severity_score`, `hard_negative`,
   `elevation_ratio`, or `future_chargeback` —
   `test_no_forbidden_baseline_columns_in_output`.
3. **Causal-by-construction**: every primitive in `ml/features/primitives.py`
   is a trailing (`rolling(window, min_periods=1)`) or expanding
   (`expanding()`) pandas operation ending at the current row, grouped by
   `merchant_id` — there is no code path that reaches a later row.
4. **Truncation invariance (the direct proof)**: computing features on only
   the first 60 days of `daily_observations.csv` reproduces byte-identical
   values to the first 60 rows of features computed on the full 180-day
   file (`test_truncation_invariance`). This is the same proof technique
   used for the generator itself
   (`ml/data_generation`'s `test_truncated_run_matches_prefix_of_longer_run`):
   if any feature depended on data past t, truncating the future tail of an
   already-fixed input would change that feature's value, and it does not.

## Known limitations / assumptions

- **Deviation z-scores are clipped to [-10, 10]** to avoid blowups when a
  merchant's expanding-history std is still tiny (early in its observed
  history). Empirically this clip binds on 0.7%–3.4% of rows per deviation
  feature in the 50×180 benchmark — rare, not a sign of systematic
  saturation, but worth knowing before treating an exact ±10 value as
  literal rather than "at least this extreme."
- **`merchant_tenure_days` is highly collinear with `day_index` plus a
  per-merchant offset** (all merchants have full history from a fixed
  signup date before the observation window) — it's included because
  account age is a standard, legitimate real-world risk-model input, but it
  carries little independent signal in this specific synthetic benchmark
  precisely because every merchant already has full history (see the
  generator's own "cold-start not modeled" limitation).
- **Windows near the start of a merchant's history are short by
  necessity** (`min_periods=1`): a `60d` feature computed at `day_index=2`
  is really a 3-day average. This is the same trade-off the generator's own
  label construction makes, not a new one introduced here.
- **HHI and payment-mix drift use GMV-dollar-weighted shares**, which is
  more correct than a plain mean-of-daily-shares when daily GMV varies, but
  is one specific aggregation choice among a few reasonable ones.
- **These 55 features are a starting catalog, not a claim that all 55 are
  useful.** Nothing here was selected or tuned by looking at label
  correlation or model performance — per the task's explicit instruction —
  so some may turn out to be weak or redundant once modeling starts. That
  determination belongs to the modeling/evaluation stage, not this one.
