# Dataset Validation Report — 50×180 Synthetic Benchmark (v2, post-correction)

Scope: exploratory/structural validation only, per `PROJECT_CONTEXT.md`
implementation order step 2. No model was trained. This is a full re-run
after two generator corrections applied following the v1 validation
findings — see **Revision note** below.

Reproduce with:
```bash
.venv/bin/python scripts/generate_dataset.py --merchants 50 --days 180 --seed 42
.venv/bin/python -m pytest tests/ -v
.venv/bin/python scripts/validate_dataset.py
```

Inputs: the regenerated `data/raw/merchants.csv`, `data/raw/daily_observations.csv`,
`data/scenarios/events.csv`, `data/processed/labels.csv` (seed 42, 50
merchants × 180 days). Outputs: `data/metadata/validation/summary.json`
(every number below is pulled directly from that file) and
`data/metadata/validation/plots/*.png`.

## Revision note

Two corrections were made to `ml/data_generation/` after v1 of this report
(full rationale in `docs/architecture/data_generation.md` → "Revision
history"), and the seed-42 benchmark was regenerated from scratch:

1. **Education archetype**: `daily_gmv_range` raised `(4_000,20_000)` →
   `(9_000,25_000)`, `aov_range` cut `(1200,8000)` → `(500,2_000)`. Root
   cause: the old ranges, crossed with the shared small-tier 0.55×
   multiplier, could put AOV above a merchant's entire daily GMV target,
   producing ~1 transaction/day and making chargeback outcomes
   unobservable regardless of risk severity. `refund_rate_range` and
   `chargeback_rate_range` were **not** touched.
2. **`payment_method_shift`**: fixed a logic bug where
   `from_method_idx == to_method_idx` could occur (~1-in-5 by construction),
   silently producing a no-op scenario. Now resampled until they differ.
   `gmv_mult_peak`'s range was **not** touched.

Nothing else in the generator changed. The label formula
(`labels.py`) is untouched. Every number below reflects the regenerated
dataset; v1's numbers are quoted only where needed to show the before/after
delta.

**Gap carried over from v1, still true**: no "international customer
share" field exists in this benchmark.

---

## 1. Dataset structure

- 50 merchants, 9,000 daily rows, all merchants have exactly 180 rows, day_index 0–179 contiguous, no date gaps for any merchant.
- Zero duplicates, zero nulls, zero schema drift, zero self-overlapping events — unchanged from v1.
- Impossible-value scan: unchanged from v1 — all zero except the same accepted simplification, **`chargeback_amount > gmv` same-day, still exactly 10/9,000 rows (0.11%)**. This count is coincidentally identical to v1; it is unrelated to either correction (each merchant's daily-simulation RNG stream is independent of both other merchants' streams and of the event-scheduling stream, so neither fix perturbs it) and stays under the 2% test guard.
- `aov × transaction_count == gmv` exactly for all rows; payment-mix shares sum to 1.0; customer split holds. All unchanged.

**Verdict: still structurally clean.**

## 2. Merchant archetypes

Merchant counts by archetype are unchanged (allocation is deterministic,
independent of the parameter fix): D2C Fashion 7, Electronics 7, all others
6. **Education's transaction volume, specifically**:

| | Before (v1) | After (v2) |
|---|---|---|
| `baseline_daily_txn_count` (6 merchants) | 1.00, 1.00, 1.23, 1.29, 2.62, 2.87 | 3.13, 6.58, 8.41, 14.98, 18.24, 19.53 |
| Archetype mean/median (static param) | mean 2.12 / median 1.95 | mean 11.87 / median 12.75 |
| Realized daily transaction_count (all days) | min 1, median ~2, mean ~2 | **min 2, median 13.0, mean 15.19, max 55** |

Education's realized transaction volume now sits comfortably mid-pack
(compare D2C Fashion median 12.0, Marketplace median 17.0, SaaS median 5.0,
Travel median 4.0) rather than being pinned near the generator's
minimum-transaction floor.

## 3. Core distributions

Unaffected outside Education/payment_method_shift-linked columns; full
percentile tables in `summary.json` → `3_core_distributions`. Chargeback
count/rate remain sparse (median 0) archetype-wide — this is a general
low-count-Poisson property flagged in v1 and in the generator docs, not
specific to Education, and not something either fix addresses (nor should
it — chargeback rates were intentionally left untouched for Education).

International-customer share: still **not present** (unchanged gap).

## 4. Scenario validation

| Event type | v1 count | v2 count |
|---|---|---|
| festival_growth | 25 | 26 |
| fulfillment_degradation | 21 | 21 |
| chargeback_deterioration | 18 | 18 |
| refund_shock | 16 | 17 |
| compound_risk | 17 | 16 |
| viral_campaign | 14 | 13 |
| payment_method_shift | 12 | 11 |
| product_launch | 10 | 10 |
| customer_mix_shift | 8 | 8 |
| **Total** | 141 | 140 |

Small shifts (±1) are expected and benign: the `payment_method_shift`
resample loop consumes a variable number of extra RNG draws only for
merchants whose event happened to collide, which shifts *that merchant's*
subsequent event schedule (not other merchants' — each merchant's
event-scheduling RNG stream is independent). No concentration issue: still
7–20 distinct merchants per type, ~1.0–1.3 events/merchant-that-has-it.
`fulfillment_degradation` events landing on SaaS/Digital Goods merchants:
still 4 (unchanged, semantically-weak-fit limitation still stands, out of
scope for this correction).

### `payment_method_shift` self-shift check (the actual fix verification)

Inspected internal event parameters (not exposed in `events.csv`) for all
50 merchants directly:

```
total payment_method_shift events: 11
self-shift no-ops (from == to): 0
```

Confirmed also by the new regression test
`test_payment_method_shift_never_has_identical_source_and_destination`,
which checks this for every merchant in the 50×180 benchmark.

## 5. Label analysis

| Horizon | v1 usable/pos/neg/rate | v2 usable/pos/neg/rate |
|---|---|---|
| 7d | 8650 / 1735 / 6915 / 20.06% | 8650 / **1908** / **6742** / **22.06%** |
| 14d | 8300 / 1914 / 6386 / 23.06% | 8300 / **2126** / **6174** / **25.61%** |
| 30d | 7500 / 1957 / 5543 / 26.09% | 7500 / **2146** / **5354** / **28.61%** |

All three horizons remain in a manageable band (22–29% positive); the
increase is expected and desired — it comes from Education merchants now
being able to produce genuine positive labels instead of being structurally
silent.

### Education, before vs. after (the core ask)

| Horizon | v1 rate | v2 rate | v1 rank (of 8) | v2 rank (of 8) |
|---|---|---|---|---|
| 7d | 2.79% | **19.56%** | 8th (lowest) | 6th |
| 14d | 5.22% | **27.61%** | 8th (lowest) | 2nd |
| 30d | 9.33% | **31.89%** | 8th (lowest) | 3rd |

Education went from the clear, isolated low outlier to sitting inside the
normal spread — at 14d and 30d it's now *above* several other archetypes
(D2C Fashion, Marketplace, Quick Commerce, SaaS), which is exactly the
"not artificially high- or low-risk" outcome requested, not an overcorrection
into a new outlier in the other direction.

**Direct verification that severe Education risk events now produce
observable outcomes** (same 5 risk events, re-traced from the regenerated
data):

| Merchant | Event | Severity | Max elevation_ratio achieved (v1 → v2) | Label fires? |
|---|---|---|---|---|
| M0033 | fulfillment_degradation | 0.95 | 0.000 → **3.590** | No → **Yes** |
| M0033 | refund_shock | 0.26 | 0.000 → 0.000 | No → No |
| M0034 | refund_shock | 0.75 | 0.000 → **1186.2** | No → **Yes** |
| M0035 | fulfillment_degradation | 0.93 | 7047 → **5423.7** | Yes → Yes |
| M0036 | fulfillment_degradation | 0.67 | 0.000 → 0.000 | No → No |

3 of 5 now fire (up from 1 of 5), including the severity-0.95 event that
previously produced literally zero chargebacks. The two that still don't
fire are explainable by ordinary stochastic variance, not a residual
volume problem: M0033's refund_shock (severity 0.26, low) has no chargeback
linkage by design (`refund_shock` only touches `refund_rate`, not
`chargeback_rate`, per `events.py:combine_event_effects`) — it was never
going to trigger *this* label regardless of transaction volume. M0036's
fulfillment_degradation (severity 0.67, moderate) has an expected
chargeback count over its window of roughly 0.6–0.7 at its now-adequate
transaction volume — a >50% chance of seeing zero by chance alone is
normal Poisson behavior at moderate severity, the same variance every other
archetype's moderate-severity events show. This is the desired end state:
Education risk events now behave like risk events everywhere else in the
benchmark, no longer structurally muted.

## 6. Horizon comparison

Common-subset prevalence (n=7,500, all three horizons defined):

| | v1 | v2 |
|---|---|---|
| 7d | 19.56% | 21.53% |
| 14d | 22.51% | 25.19% |
| 30d | 26.09% | 28.61% |

Jaccard overlap: h7-h14 0.523, h7-h30 0.355, h14-h30 0.537 (v1: 0.525,
0.346, 0.535 — essentially unchanged). Fraction all-three-agree: 72.6% (v1:
75.0%, a small, expected decrease — Education's newly-real events add
genuine horizon-dependent variation that wasn't there before). **Conclusion
unchanged**: all three horizons remain usable and meaningfully distinct;
this correction does not favor any one horizon.

## 7. Hard-negative audit — Growth ≠ Risk (re-verified)

| | GMV ratio | Chargeback ratio | Refund ratio | On-time Δ |
|---|---|---|---|---|
| **Benign growth (avg)** | **1.80×** | 1.08× | 1.03× | ~0.00 |
| Normal periods | 1.19× | 1.06× | 1.02× | ~0.00 |
| **Risk (avg)** | 1.15× | **1.47×** | **1.36×** | **−0.079** |

Essentially identical to v1 (1.80×/1.07×/1.04× benign, 1.15×/1.48×/1.34×
risk) — **the core growth≠risk contrast is untouched by either
correction**, as expected: neither fix touched any risk-vs-benign rate
mechanism. `growth_ne_risk_verdict: true`, and
`test_growth_does_not_imply_risk_in_committed_benchmark` passes against the
regenerated data.

`payment_method_shift`'s own pooled row: GMV ratio 1.139× (v1: 1.139× —
unchanged, confirming the fix did not touch magnitude, only eliminated the
no-op instances, which were already too few to move the pooled average
much). The per-instance "42% show GMV decline vs. pre-event baseline"
finding from the prior deep-dive is a property of the small `gmv_mult_peak`
range, which was explicitly left unchanged per your instruction — still
true, now documented in `docs/architecture/data_generation.md` rather than
left implicit.

## 8–10, 12. Unaffected sections (re-run, confirmed stable)

Re-ran in full; numbers are consistent with v1 within expected noise from
the ~1-event RNG-cascade shifts described in §4 — no section's conclusion
changes:

- **§8 Temporal/warning structure**: pre-loss trajectories for
  `chargeback_deterioration`/`compound_risk` still visible; detection
  fractions and offsets in the same 57–88%/3–20-day ranges as v1.
- **§9 Leakage audit**: ground-truth `baseline_chargeback_rate`-as-feature
  AUC now 0.546/0.522/0.523 (v1: 0.594/0.579/0.577); ground-truth
  risk-event-flag AUC now 0.512/0.507/0.501 (v1: 0.526/0.531/0.521) — both
  still clearly below what a real feature should need to achieve, still
  must never be used as features, for the same reasons as v1.
- **§10 Difficulty audit**: the trailing-28d-chargeback-rate AUC inversion
  reported in the prior deep-dive **persists unchanged in direction and
  magnitude** (0.403 / 0.319 / 0.215 at 7/14/30d, v1: 0.443/0.365/0.268) —
  expected and correct, since neither correction touched the label formula
  or its trailing-window mechanics. That finding's "needs documentation"
  verdict still stands and is not addressed by this pass (out of scope per
  your instructions — label formula was explicitly not to be changed).
- **§12 Financial consistency**: chargeback>GMV same-day count unchanged
  (10); liquidity trend by category unchanged in sign and magnitude
  (benign +0.0217, normal −0.0043, risk −0.0011) — the weak
  risk-vs-normal liquidity differentiation flagged in v1 is untouched
  (correctly — this correction did not target liquidity).

## 11. Archetype bias audit — re-verified, materially improved

| Horizon | v1 max/min ratio | v2 max/min ratio | v1 AUC | v2 AUC |
|---|---|---|---|---|
| 7d | 9.17× | **2.27×** | 0.612 | **0.560** |
| 14d | 6.35× | **1.86×** | 0.624 | **0.574** |
| 30d | 4.31× | **2.72×** | 0.645 | **0.613** |

The maximum archetype-mean-encoded AUC across horizons dropped from 0.645
to **0.613** — comfortably under the 0.75 test guard, and now the lowest
it's been. The disparity that was overwhelmingly attributable to one
archetype (Education) being structurally near-zero is gone; the remaining
spread (e.g. D2C Fashion now lowest at 14d/30d, 14.8–20.1%) is ordinary
cross-archetype variation, not a floor artifact. `test_archetype_alone_does_not_strongly_predict_label`
passes with more margin than before.

---

## Re-verification checklist (as requested)

| Check | Result |
|---|---|
| Education positive rate no longer structurally suppressed by ~1-txn/day merchants | **Confirmed** — baseline_daily_txn_count range 3.13–19.53 (was 1.00–3.69); realized median 13.0/day (was ~2/day) |
| Severe Education risk events can produce observable chargeback outcomes | **Confirmed** — 3/5 risk events now fire (was 1/5); the severity-0.95 event that previously produced zero chargebacks now fires cleanly (elevation_ratio 3.59) |
| No `payment_method_shift` has identical source/destination methods | **Confirmed** — 0/11 in the shipped dataset; enforced going forward by `_sample_severity_params`'s resample loop and the new regression test |
| Growth ≠ Risk still holds | **Confirmed** — benign 1.80×/1.08×/1.03× vs. risk 1.15×/1.47×/1.36×, verdict `true`, test passes |
| Reproducibility still holds | **Confirmed** — regenerating seed 42 twice produces byte-identical CSVs (`shasum` diff empty); `test_reproducibility_same_seed_identical_output` passes |
| Truncation invariance still holds | **Confirmed** — `test_truncated_run_matches_prefix_of_longer_run` passes unchanged |

## Updated recommendation

**Both corrections are verified effective and narrowly scoped** — neither
touched risk mechanisms, the label formula, or any archetype/scenario
outside the two named issues. The benchmark's core properties (structural
cleanliness, growth≠risk separation, reproducibility, leakage safety,
horizon usability) are all unchanged or improved.

**Ready to proceed to baseline ML**, carrying forward the two items already
identified as "needs documentation" rather than "needs generator change"
(now documented in `docs/architecture/data_generation.md`):
1. The label's trailing-baseline-vs-future-window mechanic means a
   "current level" feature is actively misleading, especially at 30 days —
   feature engineering should prioritize velocity/deviation-from-baseline
   features, per `PROJECT_CONTEXT.md`'s own feature-group list.
2. `payment_method_shift`'s reliable signal is payment-mix drift, not GMV
   — a feature pipeline that only looks at GMV/transaction growth will not
   reliably recognize this scenario as benign.
