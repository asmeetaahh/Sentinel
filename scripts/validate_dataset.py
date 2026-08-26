#!/usr/bin/env python3
"""
Exploratory / structural validation of the synthetic merchant benchmark.

This is diagnosis only: it reads data/{raw,scenarios,processed}, runs the
checks in ml/validation/checks.py, and writes:
    data/metadata/validation/summary.json   (machine-readable)
    data/metadata/validation/plots/*.png    (a handful of diagnostic charts)

It never modifies the generator or the dataset itself.

Usage:
    python scripts/validate_dataset.py
    python scripts/validate_dataset.py --data-dir data
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import numpy as np

from ml.validation import checks, plots


def _to_native(obj):
    if isinstance(obj, dict):
        return {str(k): _to_native(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple, set)):
        return [_to_native(v) for v in obj]
    if isinstance(obj, (np.integer,)):
        return int(obj)
    if isinstance(obj, (np.floating,)):
        v = float(obj)
        return None if math.isnan(v) else v
    if isinstance(obj, float):
        return None if math.isnan(obj) else obj
    if isinstance(obj, (np.bool_, bool)):
        return bool(obj)
    return obj


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--data-dir", type=str, default=str(REPO_ROOT / "data"))
    args = parser.parse_args()

    data_dir = Path(args.data_dir)
    validation_dir = data_dir / "metadata" / "validation"
    plots_dir = validation_dir / "plots"
    plots_dir.mkdir(parents=True, exist_ok=True)

    print("Loading dataset ...")
    tables = checks.load_dataset(data_dir)

    print("Tagging active events onto daily observations ...")
    tagged_daily = checks.tag_active_event(tables["daily"], tables["events"])

    print("Running checks 1-12 ...")
    structure = checks.check_structure(tables)
    archetypes = checks.check_archetypes(tables)
    distributions = checks.check_core_distributions(tables)
    scenarios = checks.check_scenarios(tables, tagged_daily)
    labels = checks.check_labels(tables)
    horizon_comparison = checks.check_horizon_comparison(tables)

    import pandas as pd

    pooled = pd.DataFrame(scenarios["pooled_effect_table"])
    hard_negative_audit = checks.check_hard_negative_audit(pooled)

    temporal = checks.check_temporal_warning_structure(tables)
    leakage = checks.check_leakage_audit(tables)
    difficulty = checks.check_difficulty_audit(tables)
    archetype_bias = checks.check_archetype_bias(tables)
    financial = checks.check_financial_consistency(tables, tagged_daily)

    summary = {
        "1_structure": structure,
        "2_archetypes": archetypes,
        "3_core_distributions": distributions,
        "4_scenarios": scenarios,
        "5_labels": labels,
        "6_horizon_comparison": horizon_comparison,
        "7_hard_negative_audit": hard_negative_audit,
        "8_temporal_warning_structure": temporal,
        "9_leakage_audit": leakage,
        "10_difficulty_audit": difficulty,
        "11_archetype_bias": archetype_bias,
        "12_financial_consistency": financial,
    }

    summary_path = validation_dir / "summary.json"
    summary_path.write_text(json.dumps(_to_native(summary), indent=2))
    print(f"Wrote {summary_path}")

    print("Generating plots ...")
    plots.plot_growth_vs_risk(pooled, plots_dir / "growth_vs_risk.png")
    plots.plot_label_prevalence_by_horizon(labels, plots_dir / "label_prevalence_by_horizon.png")
    plots.plot_pre_event_trajectory(temporal, plots_dir / "pre_event_trajectory.png")
    plots.plot_archetype_positive_rate(archetype_bias, plots_dir / "archetype_positive_rate.png")
    print(f"Wrote plots to {plots_dir}")

    print("\n=== Headline numbers ===")
    print(f"Merchants: {structure['n_merchants']}, daily rows: {structure['n_daily_rows']}")
    print(f"Duplicates: {structure['duplicates']}")
    for h, v in labels["by_horizon"].items():
        print(f"Horizon {h}d: {v['positives']}/{v['usable_rows']} positive ({v['positive_rate']:.1%})")
    print(f"Growth != risk verdict: {hard_negative_audit['growth_ne_risk_verdict']}")
    print(f"Archetype-alone shortcut flag: {archetype_bias['archetype_alone_is_a_meaningful_shortcut']} (max AUC {archetype_bias['max_auc_across_horizons']:.3f})")
    print(f"Difficulty assessment: {difficulty['assessment']}")


if __name__ == "__main__":
    main()
