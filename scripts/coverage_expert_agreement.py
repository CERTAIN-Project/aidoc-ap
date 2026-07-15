"""Expert-agreement study for the LLM coverage scores (revision item M6, R3.4).

Two modes:

1. `--make-sheet` writes a *blind* assessment sheet: a seeded random sample of
   Annex IV requirements with label, description and competency questions, and
   an empty `expert_score` column (0.0-1.0, same definition as the LLM score:
   how well does the *current* ontology support answering the CQs of this
   requirement). The sheet deliberately contains no LLM scores so the expert
   assessment is independent.

2. Default mode evaluates a filled sheet: it compares the expert scores with
   the per-requirement LLM coverage at iteration 3, temperature 0 (mean over
   the three seeded runs, per model and pooled over the four models) and
   reports the mean absolute deviation and a 3-category agreement
   (low < 0.5 <= medium < 0.8 <= high). Spearman's rank correlation is
   computed as supplementary output; note that the iteration-3 LLM scores are
   compressed into a narrow band, so a rank correlation over ten heavily tied
   values carries little signal.

Usage:
    python scripts/coverage_expert_agreement.py --make-sheet
    # ... expert fills experiments/coverage/expert_agreement/expert_sheet.csv ...
    python scripts/coverage_expert_agreement.py
"""

import argparse
import glob
import json
import os
import random
import re
import statistics
import sys

import pandas as pd
from rdflib import Graph, Namespace, RDF, RDFS

AIACT = Namespace("https://w3id.org/aidoc-ap/requirements#")
DCT = Namespace("http://purl.org/dc/terms/")

SHEET_DIR = "experiments/coverage/expert_agreement"
SHEET = os.path.join(SHEET_DIR, "expert_sheet.csv")
MULTIRUN_GLOB = "experiments/coverage/multirun/semantic_mapping_*_iter3_T0_0_run*.json"
SAMPLE_SIZE = 10
SEED = 42


def load_requirements():
    g = Graph().parse("annex_4.ttl", format="turtle")
    reqs = {}
    for s in g.subjects(RDF.type, AIACT.Requirement):
        rid = str(s).split("#")[-1]
        reqs[rid] = {
            "requirement_id": rid,
            "label": str(g.value(s, RDFS.label) or rid),
            "description": str(g.value(s, DCT.description) or ""),
        }
    # competency questions: any aiact:CompetencyQuestion whose id prefix matches reqN
    cq_by_req = {}
    for cq in g.subjects(RDF.type, AIACT.CompetencyQuestion):
        cqid = str(cq).split("#")[-1]          # e.g. cq6_2
        m = re.match(r"cq(\d+)_", cqid)
        if m:
            cq_by_req.setdefault(f"req{m.group(1)}", []).append(
                str(g.value(cq, RDFS.label) or cqid))
    for rid, r in reqs.items():
        r["competency_questions"] = " | ".join(sorted(cq_by_req.get(rid, [])))
    return reqs


def make_sheet():
    reqs = load_requirements()
    sample = sorted(random.Random(SEED).sample(sorted(reqs), SAMPLE_SIZE),
                    key=lambda r: int(re.sub(r"\D", "", r)))
    os.makedirs(SHEET_DIR, exist_ok=True)
    rows = [dict(reqs[r], expert_score="") for r in sample]
    pd.DataFrame(rows, columns=["requirement_id", "label", "description",
                                "competency_questions", "expert_score"]
                 ).to_csv(SHEET, index=False)
    print(f"✅ blind sheet with {len(rows)} of {len(reqs)} requirements "
          f"(seed {SEED}) → {SHEET}")
    print("   Fill expert_score (0.0-1.0) against ontology v1.2 WITHOUT looking "
          "at the LLM scores, then re-run without --make-sheet.")


def llm_scores():
    """(model, requirement_id) -> mean coverage over the three iter-3 T=0 runs."""
    per = {}
    pat = re.compile(r"semantic_mapping_(.+)_iter3_T0_0_run\d+\.json")
    for p in sorted(glob.glob(MULTIRUN_GLOB)):
        model = pat.search(os.path.basename(p)).group(1)
        for r in json.load(open(p, encoding="utf-8")):
            per.setdefault((model, r["requirement_id"]), []).append(
                float(r["coverage_score"]))
    return {k: statistics.mean(v) for k, v in per.items()}


def category(x):
    return "low" if x < 0.5 else ("medium" if x < 0.8 else "high")


def spearman(a, b):
    def ranks(v):
        order = sorted(range(len(v)), key=lambda i: v[i])
        r = [0.0] * len(v)
        i = 0
        while i < len(order):
            j = i
            while j + 1 < len(order) and v[order[j + 1]] == v[order[i]]:
                j += 1
            avg = (i + j) / 2 + 1
            for k in range(i, j + 1):
                r[order[k]] = avg
            i = j + 1
        return r
    ra, rb = ranks(a), ranks(b)
    ma, mb = statistics.mean(ra), statistics.mean(rb)
    num = sum((x - ma) * (y - mb) for x, y in zip(ra, rb))
    den = (sum((x - ma) ** 2 for x in ra) * sum((y - mb) ** 2 for y in rb)) ** 0.5
    return num / den if den else float("nan")


def evaluate():
    if not os.path.exists(SHEET):
        sys.exit(f"{SHEET} not found — run with --make-sheet first.")
    df = pd.read_csv(SHEET)
    if df.expert_score.isna().any() or (df.expert_score.astype(str) == "").any():
        sys.exit("expert_score column is not completely filled in.")
    df["expert_score"] = df.expert_score.astype(float)

    scores = llm_scores()
    models = sorted({m for m, _ in scores})
    print(f"{len(df)} requirements, models: {', '.join(models)}\n")
    rows = []
    for label, getter in (
            [(m, lambda r, m=m: scores.get((m, r))) for m in models]
            + [("pooled (4 models)",
                lambda r: statistics.mean(scores[(m, r)] for m in models
                                          if (m, r) in scores))]):
        llm = [getter(r) for r in df.requirement_id]
        if any(v is None for v in llm):
            continue
        mae = statistics.mean(abs(e - l) for e, l in zip(df.expert_score, llm))
        agree = sum(category(e) == category(l)
                    for e, l in zip(df.expert_score, llm)) / len(llm)
        rho = spearman(df.expert_score.tolist(), llm)
        rows.append((label, mae, agree, rho))
        print(f"  {label:28s} MAE = {mae:.3f}   "
              f"category agreement = {agree:.2f}   (Spearman ρ = {rho:5.3f})")
    out = os.path.join(SHEET_DIR, "agreement_results.csv")
    pd.DataFrame(rows, columns=["model", "mean_abs_deviation",
                                "category_agreement", "spearman_rho"]
                 ).to_csv(out, index=False)
    print(f"\n→ {out}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--make-sheet", action="store_true")
    args = ap.parse_args()
    make_sheet() if args.make_sheet else evaluate()
