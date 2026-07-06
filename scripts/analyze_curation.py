"""Aggregate expert curation of LLM-suggested alignments.

Reads the *-curation.csv sheets produced by alignment_semantic.py after the
curator columns (curator_decision: accept | reject | modify) have been filled
in, and reports:

  1. accepted / rejected / modified counts per reference ontology and overall
  2. precision of the LLM suggestions at increasing confidence thresholds
     (precision@t = accepted / curated among suggestions with confidence >= t;
      "modify" counts as a partial hit reported separately)
  3. estimated false-negative rate below the operating threshold, based on the
     curated below-threshold suggestions

Usage:
    python scripts/analyze_curation.py [reports/alignment_semantic]
"""

import glob
import os
import sys

import pandas as pd

CURATION_DIR = sys.argv[1] if len(sys.argv) > 1 else "reports/alignment_semantic"
OPERATING_THRESHOLD = float(os.getenv("CONF_THRESHOLD", "0.75"))
THRESHOLDS = [0.5, 0.6, 0.7, 0.75, 0.8, 0.9, 0.95]


def main():
    files = sorted(glob.glob(os.path.join(CURATION_DIR, "*-curation.csv")))
    if not files:
        sys.exit(f"No *-curation.csv files found in {CURATION_DIR}")

    frames = []
    for f in files:
        df = pd.read_csv(f)
        df["reference_ontology"] = os.path.basename(f).replace("-curation.csv", "")
        frames.append(df)
    data = pd.concat(frames, ignore_index=True)

    data["curator_decision"] = data["curator_decision"].fillna("").str.strip().str.lower()
    curated = data[data["curator_decision"].isin(["accept", "reject", "modify"])]
    pending = len(data) - len(curated)
    if pending:
        print(f"⚠️  {pending} of {len(data)} suggestions are not yet curated.\n")

    print("== Curation counts per reference ontology ==")
    counts = curated.groupby(["reference_ontology", "curator_decision"]).size().unstack(fill_value=0)
    print(counts.to_string(), "\n")

    total = curated["curator_decision"].value_counts()
    print("== Overall ==")
    print(total.to_string(), "\n")

    print("== Precision of LLM suggestions at confidence thresholds ==")
    print(f"{'threshold':>9} {'n':>5} {'accept':>7} {'modify':>7} {'reject':>7} "
          f"{'precision':>9} {'prec(+mod)':>10}")
    for t in THRESHOLDS:
        subset = curated[curated["llm_confidence"] >= t]
        n = len(subset)
        if n == 0:
            print(f"{t:>9} {0:>5}      —")
            continue
        acc = (subset["curator_decision"] == "accept").sum()
        mod = (subset["curator_decision"] == "modify").sum()
        rej = (subset["curator_decision"] == "reject").sum()
        print(f"{t:>9} {n:>5} {acc:>7} {mod:>7} {rej:>7} "
              f"{acc / n:>9.3f} {(acc + mod) / n:>10.3f}")

    below = curated[curated["llm_confidence"] < OPERATING_THRESHOLD]
    print(f"\n== False negatives below operating threshold ({OPERATING_THRESHOLD}) ==")
    if len(below) == 0:
        print("No curated suggestions below the threshold "
              "(curate a sample below the threshold to estimate false negatives).")
    else:
        fn = (below["curator_decision"].isin(["accept", "modify"])).sum()
        print(f"curated below threshold: {len(below)}, "
              f"judged meaningful (accept/modify): {fn} "
              f"→ estimated false-negative rate: {fn / len(below):.3f}")


if __name__ == "__main__":
    main()
