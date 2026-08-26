# Synthetic Merchant Data Generator

Source: [`ml/data_generation/`](../../ml/data_generation/)
Regenerate with: [`scripts/generate_dataset.py`](../../scripts/generate_dataset.py)
Tests: [`tests/test_data_generation.py`](../../tests/test_data_generation.py)

## What this is

A reproducible, fully synthetic benchmark of merchant payment behavior, used
to develop and evaluate Sentinel's chargeback-risk models before any real
data is available. Every number in the dataset is generated from an explicit
random seed and a documented set of modeling assumptions below — **none of
it is real Razorpay, merchant, or industry data**, and none of it should be
cited as such.

This generator produces exactly four tables and nothing else (see
[Schema](#schema)). It does **not** do feature engineering, does not train
models, and does not decide which prediction horizon is "correct" — per
`PROJECT_CONTEXT.md`, that is left to the evaluation stage.

## Quick start

```bash
uv venv .venv && uv pip install --python .venv/bin/python -r requirements.txt

# Initial benchmark (50 merchants x 180 days, seed 42)
.venv/bin/python scripts/generate_dataset.py

# Larger run, same code path (see "Scaling" below)
.venv/bin/python scripts/generate_dataset.py --merchants 500 --days 365 --seed 42

# Tests
.venv/bin/python -m pytest tests/test_data_generation.py -v
```

Output lands under `data/`:

| Table | Path | Grain |
|---|---|---|
| Merchant static attributes | `data/raw/merchants.csv` | 1 row / merchant |
| Daily observations | `data/raw/daily_observations.csv` | 1 row / merchant / day |
| Event / scenario metadata | `data/scenarios/events.csv` | 1 row / scheduled event |
| Future labels | `data/processed/labels.csv` | 1 row / merchant / as-of-date / horizon |
| Machine-readable schema | `data/metadata/schema.json` | — |
| Run manifest (seed, counts, disclaimer) | `data/metadata/generation_manifest.json` | — |

## Generation process, end to end

For a run of `n_merchants` merchants over `n_days` days from `start_date`:

1. **Merchants** (`merchants.py`) — allocate merchants across the 8
   archetypes as evenly as possible (deterministic, not randomized), then
   draw each merchant's static baseline parameters once from an
   archetype-specific range (`archetypes.py`).
2. **Events** (`events.py`) — for each merchant independently, schedule a
   sequence of non-overlapping scenario events (see [Scenarios](#scenarios))
   using a renewal process (random gap, then an event, then another gap).
3. **Daily simulation** (`timeseries.py`) — for each merchant, walk
   `day_index = 0..n_days-1` in order. Each day's values come from the
   merchant's baseline combined with trend, weekly seasonality, annual
   seasonality, any currently-active event effects, and noise.
4. **Labels** (`labels.py`) — from the finished daily-observations table,
   compute future-window chargeback-elevation labels for the 7/14/30-day
   horizons, using only data at/before the as-of date to define "normal"
   and only data strictly after it to define the outcome.
5. **Write** (`io_utils.py`) — the four CSVs plus the schema and manifest
   JSON files.

Steps 2–3 happen per-merchant and never look at another merchant's data, so
the whole pipeline is trivially parallelizable if it's ever needed (not done
here — not needed at this scale).

## Merchant archetypes

Exactly the 8 required by `PROJECT_CONTEXT.md`, each with its own baseline
ranges for GMV, AOV, refund/chargeback rates, fulfillment speed, payment
mix, weekly pattern, and seasonal participation (`archetypes.py:ARCHETYPE_PARAMS`):

| Archetype | Notable modeling choices |
|---|---|
| D2C Fashion | High refund rate (returns/sizing), weekend-heavy, strong festive-season lift |
| Electronics | High AOV, moderate chargeback rate, festive + New Year sales lift |
| SaaS | Near-zero refunds/chargebacks, near-instant fulfillment, weekday-heavy, no strong seasonality |
| Travel | High AOV, cancellation-driven refunds, summer-travel seasonal peak |
| Marketplace | Large scale, moderate everything, broad festive participation |
| Education | Low chargebacks, admission-cycle seasonal peak, weekday-heavy |
| Quick Commerce | Low AOV/high frequency, near-instant fulfillment, monsoon dip |
| Digital Goods | Very low refunds/chargebacks, instant fulfillment, New Year sales lift |

Each merchant additionally gets a `business_tier` (small/mid/large, via a
GMV multiplier), an organic `annual_growth_rate`, a `volatility_factor`, a
`liquidity_buffer_days`, and a `settlement_cycle_days` — all drawn once at
merchant creation and held fixed for the run.

Seasonality is a sum of smooth Gaussian "bumps" over day-of-year
(`festive_autumn`, `new_year_sales`, `summer_travel`, `edu_admission`,
`monsoon_dip`), each archetype participating with its own weight — never a
hard cutoff, so seasonality itself never looks like a sudden event.

## Scenarios (events)

Nine event types, matching `PROJECT_CONTEXT.md` exactly
(`config.py:EVENT_TYPES`):

**Risk** (elevate refund/chargeback/fulfillment metrics):
- `chargeback_deterioration` — chargeback rate ramps up, usually gradually
- `refund_shock` — refund rate spikes, gradual or sudden
- `fulfillment_degradation` — on-time rate drops, delay rises, *and* a
  small linked chargeback increase (late delivery driving disputes)
- `customer_mix_shift` — new-customer share rises, followed by a **lagged**
  (10–20 day) chargeback increase — a deliberately hard, delayed signal
- `compound_risk` — one event bundling correlated refund, chargeback (lagged
  within the event), and mild fulfillment effects — the hardest positive case

**Benign growth / hard negatives** (GMV/volume rises, health stays normal):
- `festival_growth`, `viral_campaign`, `product_launch`, `payment_method_shift`

Every event has a `shape` (`gradual` or `sudden`) chosen per-instance from a
type-specific probability (`config.EVENT_GRADUAL_PROBABILITY`) — risk types
are gradual 80–90% of the time (never 100%: a fast-onset `refund_shock` is
still real), and `viral_campaign` is deliberately sudden 90% of the time so
the benchmark cannot be solved by "spike shape = risk."

Onset/decay uses a smoothstep ramp with a decay tail
(`events.py:get_intensity`) — there is no metric that jumps from baseline to
peak in a single day.

**Non-overlap.** Within one merchant's timeline, events never overlap each
other (`schedule_events_for_merchant` advances the schedule cursor past an
event's full recovery tail before drawing the next gap). This was a
deliberate fix during development: an earlier version let events overlap
freely, which silently let a concurrent risk event contaminate a
"hard-negative" benign-growth window's chargeback/refund rates (and vice
versa), undermining the very contrast the benchmark exists to test.
`compound_risk` remains the one intentional way to combine multiple risk
mechanisms in one window.

### Critical benchmark principle: growth ≠ risk

`festival_growth`, `viral_campaign`, `product_launch`, and
`payment_method_shift` apply **no** multiplier to refund rate, chargeback
rate, or fulfillment on-time rate — only to GMV, transaction volume, and
(for some) new-customer share. Pooled across the 50×180 benchmark
(`tests/test_data_generation.py::test_hard_negative_events_grow_without_elevating_risk`
and `..._festival_growth_is_a_clean_healthy_growth_example`), these windows
show GMV 1.1×–2.8× baseline while realized chargeback/refund rates stay
within roughly ±50% of the merchant's own baseline rate — the residual
noise being expected Poisson variance at low daily transaction/chargeback
counts, not a systematic effect. Risk events (`chargeback_deterioration`,
`refund_shock`) show a clearly larger, systematic elevation (>1.5×) over the
same pooling methodology. A model trained on this benchmark that just
predicts "risk whenever GMV/volume grows" should score poorly on the
benign-growth cases and is exactly the failure mode this benchmark is meant
to expose.

## Schema

Full machine-readable version: `data/metadata/schema.json` (generated from
`ml/data_generation/schema.py`, the single source of truth also used by the
generator and tests).

**`merchants`** — static attributes, 1 row/merchant: `merchant_id`,
`archetype`, `business_tier`, `signup_date`, `baseline_daily_gmv`,
`baseline_daily_txn_count`, `baseline_aov`, `baseline_refund_rate`,
`baseline_chargeback_rate`, `baseline_fulfillment_delay_days`,
`baseline_on_time_rate`, `baseline_new_customer_rate`,
`baseline_pct_pay_{card,upi,netbanking,wallet,bnpl}`, `annual_growth_rate`,
`volatility_factor`, `liquidity_buffer_days`, `settlement_cycle_days`,
`weekly_seasonality_profile`.

**`daily_observations`** — 1 row/merchant/day, the future feature source:
`merchant_id`, `date`, `day_index`, `gmv`, `transaction_count`, `aov`,
`refund_count`, `refund_amount`, `refund_rate`, `chargeback_count`,
`chargeback_amount`, `chargeback_rate`, `fulfillment_delay_avg_days`,
`fulfillment_on_time_rate`, `customer_count`, `new_customers`,
`returning_customers`, `new_customer_rate`,
`pct_pay_{card,upi,netbanking,wallet,bnpl}`, `liquidity_balance`,
`pending_settlement_amount`. 24 columns — deliberately not hundreds; see
[Feature-count discipline](#feature-count-discipline).

**`events`** — 1 row/scheduled event: `event_id`, `merchant_id`,
`event_type`, `category` (`risk`/`benign_growth`), `hard_negative` (bool),
`shape`, `start_date`, `end_date`, `recovery_end_date`, `duration_days`,
`severity_score`, `affects`, `description`.

**`labels`** — 1 row/merchant/as-of-date/horizon: `merchant_id`,
`as_of_date`, `day_index`, `horizon_days`, `future_chargeback_amount`,
`future_chargeback_rate`, `future_transaction_count`,
`baseline_daily_gmv_trailing`, `baseline_daily_chargeback_amount_trailing`,
`baseline_chargeback_rate_trailing`, `elevation_ratio_amount`,
`elevation_ratio_rate`, `label_elevated_chargeback`.

## Labels and leakage prevention

For a prediction date `t` and horizon `h` (7, 14, or 30 days):

- **Trailing baseline** (uses only day_index ≤ t): mean daily chargeback
  amount and volume-weighted chargeback rate over the trailing 28 days (or
  fewer, near the run start).
- **Future outcome** (uses only day_index in `(t, t+h]`): summed chargeback
  amount, volume-weighted chargeback rate, summed transaction count.
- **Label**: `label_elevated_chargeback = 1` if the future amount is at
  least 1.75× the trailing-baseline-implied expectation for that window
  *and* clears a materiality floor (`max(50, trailing_daily_gmv × h ×
  0.0005)`, to avoid flagging noise on near-zero-chargeback merchants).
  These thresholds are illustrative synthetic assumptions, not calibrated
  to any real loss-rate statistic.
- Rows where `t + h` exceeds the last generated day are **dropped**, never
  estimated from a partial window — see `labels.py`.
- All three horizons are generated unconditionally; nothing in the
  generator treats 14 days as primary. That choice is deferred to the
  evaluation stage, per `PROJECT_CONTEXT.md`.

Structural guarantees, enforced by tests:
- `daily_observations` never contains any label-derived column
  (`test_daily_observations_do_not_contain_future_derived_columns`).
- **Truncation invariance**: generating only the first 60 days of a run
  reproduces byte-identical values (merchants, daily observations, closed
  events, and labels whose full future window fits) to the first 60 days of
  a 120-day run with the same seed (`test_truncated_run_matches_prefix_of_longer_run`).
  This is the direct, mechanical proof that no day's value — and no label —
  depends on data that wouldn't yet exist at that point in time.

## Reproducibility

Every random draw traces back to `numpy.random.SeedSequence([seed,
purpose_code, *ids])` (`config.py:RNG_PURPOSE_*`), with a separate stream
per purpose:

- merchant static params: keyed by `(seed, merchant_idx)`
- event scheduling: keyed by `(seed, merchant_idx)`, using a **fixed**
  scheduling horizon (`EVENT_SCHEDULE_HORIZON_DAYS = 3650`) independent of
  the requested `n_days`
- daily simulation noise: one stream per merchant, keyed by `(seed,
  merchant_idx)`, consumed in a fixed draw order per day

Because none of these streams' draw *order or count* depends on `n_days`,
the same seed always produces the same dataset
(`test_reproducibility_same_seed_identical_output`), and a shorter run is
always a strict, unmodified prefix of a longer one — the property the
leakage tests above rely on.

`DEFAULT_START_DATE = 2024-01-01` is an arbitrary, fixed synthetic anchor —
it is not tied to any real calendar event and does not change between runs.

## Scaling

The generator is parametrized purely by `(seed, n_merchants, n_days,
start_date)` — the initial 50×180 benchmark and the ~500×365 final target
from `PROJECT_CONTEXT.md` run through the identical code path. A 500×365
run (182,500 daily rows, ~2,600 events, ~520,000 label rows) generates in
well under 10 seconds on a laptop; see `scripts/generate_dataset.py
--merchants 500 --days 365`. Archetype allocation is deterministic and
scales automatically (near-equal split across the 8 archetypes regardless
of `n_merchants`).

## Feature-count discipline

`daily_observations` has 24 non-key columns. This is intentionally lean:
`PROJECT_CONTEXT.md` targets ~50–70 *engineered* features downstream (rolling
stats, deviations from merchant baseline, velocity/acceleration, etc.),
built from this raw table in a later stage — not generated here. Adding
more raw columns now would just shift meaningless width earlier in the
pipeline.

## Known limitations / assumptions to keep in mind

- **All parameter ranges are synthetic modeling assumptions** chosen for
  plausibility and cross-archetype contrast, not calibrated to any real
  Razorpay, industry, or academic dataset. Treat every number as a
  hypothesis for the benchmark, never as a real-world statistic.
- **Currency units are unspecified** ("GMV units"), not INR or USD, to avoid
  implying real financial calibration.
- **Daily chargeback/refund rates are extremely noisy for low-volume
  merchants.** A merchant with ~5 transactions/day can show a 100%
  same-day chargeback rate from a single dispute; this is a genuine
  low-count Poisson effect, not a bug, but means daily-grain rate columns
  need rolling/volume-weighted aggregation before they're useful features
  (deferred to the feature-engineering stage).
- **All merchants have full history** within the observation window
  (signup predates `start_date` by 60–1500 days); cold-start / partial
  history onboarding is not modeled yet.
- **Liquidity is a simplified mean-reverting model**, not a ledger: it is
  not double-entry-consistent with settlement mechanics and should be
  treated as a directional proxy, not an accounting balance.
- **No inter-merchant correlation** beyond shared seasonality curves — a
  systemic shock affecting many merchants at once (e.g. a payment-gateway
  outage) is not modeled.
- The elevation-ratio label thresholds (1.75×, materiality floors) were
  picked once, for plausibility, and have **not** been tuned to make any
  particular model look good — per `PROJECT_CONTEXT.md`'s engineering
  philosophy, the benchmark must be able to expose failure, not just
  success.
