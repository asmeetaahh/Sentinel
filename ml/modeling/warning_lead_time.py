"""
Warning lead time: PROJECT_CONTEXT.md's signature metric.

Definition (documented precisely, per the task brief):
  1. An "episode" is a maximal contiguous run of as_of_dates, for one
     merchant and one horizon, where label_elevated_chargeback == 1. This
     collapses a long run of positive labels into ONE event — a model that
     fires every day during a 20-day elevated run is not credited with 20
     independent warnings.
  2. onset_day = the first day_index in that run.
  3. We require a SUSTAINED alert leading into onset: starting at
     onset_day - 1 and walking backward one day at a time, we require the
     model's prediction to be positive on EVERY day, stopping at the first
     day it isn't (or at onset_day - horizon_days, whichever comes first —
     a prediction from further back belongs conceptually to a different
     forecast window). lead_time_days = onset_day - (first day of that
     contiguous run).
     - If onset_day - 1 itself is not positive, there is no sustained
       lead-in alert for this episode by this definition.

     This deliberately does NOT credit an isolated positive blip somewhere
     in the lookback window that is not connected to the onset (e.g. one
     positive day, then quiet for three weeks, then the episode begins) —
     an early version of this metric did exactly that and produced a median
     lead time equal to the horizon's maximum for most model/horizon
     combinations, which turned out to be a statistical artifact (a wide
     lookback window has many chances for some unrelated day to be
     positive by chance) rather than genuine early detection. Requiring
     contiguity all the way to the episode's start is a materially
     stricter, more honest definition of "the model was sounding the alarm
     right up until this episode began."
  4. If there is no sustained lead-in alert, we then check whether the
     model fires positive on onset_day itself or later WITHIN the episode's
     own run: if so, the episode is "detected_at_or_after_onset" (the model
     caught it, but not early — per the task brief, this must NOT be
     counted as a warning).
  5. If the model never fires positive anywhere in the lookback window or
     the run itself, the episode is "missed".

This uses only the label time series and the model's own predictions —
no scenario/event metadata.
"""

from __future__ import annotations

import numpy as np
import pandas as pd


def _episodes_for_merchant(day_index: np.ndarray, label: np.ndarray) -> list[tuple[int, int]]:
    """Returns list of (onset_day, end_day) inclusive, for contiguous
    label==1 runs, assuming day_index is sorted and contiguous (no gaps)
    for this merchant within the frame.
    """
    if len(day_index) == 0:
        return []
    block_id = np.cumsum(np.r_[1, np.diff(label) != 0])
    episodes = []
    for b in np.unique(block_id[label == 1]):
        days_in_block = day_index[block_id == b]
        episodes.append((int(days_in_block.min()), int(days_in_block.max())))
    return episodes


def compute_warning_lead_times(frame: pd.DataFrame, predicted: np.ndarray, horizon_days: int) -> dict:
    """
    frame: must contain merchant_id, day_index, label_elevated_chargeback,
    sorted by (merchant_id, day_index), aligned 1:1 with `predicted`
    (boolean array of the model's binary decision at the chosen threshold).
    """
    df = frame[["merchant_id", "day_index", "label_elevated_chargeback"]].copy()
    df["predicted"] = np.asarray(predicted).astype(bool)
    df = df.sort_values(["merchant_id", "day_index"]).reset_index(drop=True)

    early_lead_times = []
    late_offsets = []
    n_missed = 0
    episode_records = []

    for merchant_id, g in df.groupby("merchant_id", sort=False):
        day_index = g["day_index"].to_numpy()
        label = g["label_elevated_chargeback"].to_numpy()
        predicted_arr = g["predicted"].to_numpy()
        day_to_pos = {d: i for i, d in enumerate(day_index)}

        for onset_day, end_day in _episodes_for_merchant(day_index, label):
            lookback_start = max(onset_day - horizon_days, int(day_index.min()))

            # Sustained-alert check: walk backward from onset_day-1 and
            # require an unbroken run of positive predictions. The run's
            # start day is the warning day; lead_time is the gap to onset.
            run_start_day = None
            d = onset_day - 1
            if d >= lookback_start and d in day_to_pos and predicted_arr[day_to_pos[d]]:
                run_start_day = d
                d -= 1
                while d >= lookback_start and d in day_to_pos and predicted_arr[day_to_pos[d]]:
                    run_start_day = d
                    d -= 1

            if run_start_day is not None:
                lead_time = onset_day - run_start_day
                early_lead_times.append(lead_time)
                episode_records.append({"merchant_id": merchant_id, "onset_day": onset_day, "status": "early", "lead_time_days": lead_time})
                continue

            in_run_days = [d for d in range(onset_day, end_day + 1) if d in day_to_pos]
            late_hit_day = next((d for d in in_run_days if predicted_arr[day_to_pos[d]]), None)
            if late_hit_day is not None:
                offset = late_hit_day - onset_day
                late_offsets.append(offset)
                episode_records.append({"merchant_id": merchant_id, "onset_day": onset_day, "status": "detected_at_or_after_onset", "offset_days": offset})
            else:
                n_missed += 1
                episode_records.append({"merchant_id": merchant_id, "onset_day": onset_day, "status": "missed"})

    n_episodes = len(episode_records)
    result = {
        "n_episodes_total": n_episodes,
        "n_early_warning": len(early_lead_times),
        "n_detected_at_or_after_onset": len(late_offsets),
        "n_missed": n_missed,
        "median_warning_lead_time_days": float(np.median(early_lead_times)) if early_lead_times else None,
        "warning_lead_time_percentiles_days": (
            {p: float(np.percentile(early_lead_times, p)) for p in [10, 25, 50, 75, 90]} if early_lead_times else None
        ),
        "fraction_episodes_with_early_warning": (len(early_lead_times) / n_episodes) if n_episodes else None,
        "episodes": episode_records,
    }
    return result
