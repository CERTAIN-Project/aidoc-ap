"""Merge per-curator exports from the curation UI (docs/curation.html).

Takes two or more curation_<name>_<batch>.json files, computes agreement
(Cohen's kappa on accept/modify/reject), writes:

  reports/curation_merged.csv        long format: one row per pair x curator
  reports/curation_consensus.csv     one row per pair with consensus decision
                                     (empty + CONFLICT note where curators disagree)

and fills the consensus back into reports/alignment_semantic/*-curation.csv
(columns curator_decision/curator_relation/curator_name/curator_notes), so
that scripts/analyze_curation.py works on the merged result.

Usage:
    python scripts/merge_curation.py curation_SN_*.json curation_TD_*.json [...]
"""

import glob
import itertools
import json
import os
import sys
from collections import defaultdict

import pandas as pd

CURATION_DIRS = [
    ("reports/alignment_semantic", ""),        # main candidate set
    ("reports/alignment_fn_band", "fn-band/"), # below-threshold FN sample
]


def kappa(pairs):
    """Cohen's kappa for two label sequences given as list of (a, b)."""
    if not pairs:
        return float("nan")
    labels = sorted({x for p in pairs for x in p})
    n = len(pairs)
    po = sum(1 for a, b in pairs if a == b) / n
    pe = sum(
        (sum(1 for a, _ in pairs if a == l) / n) *
        (sum(1 for _, b in pairs if b == l) / n)
        for l in labels)
    return (po - pe) / (1 - pe) if pe < 1 else 1.0


def main():
    files = sys.argv[1:]
    if len(files) < 2:
        sys.exit("Usage: merge_curation.py <export1.json> <export2.json> [...]")

    per_pair = defaultdict(dict)   # id -> curator -> decision dict
    batches = set()
    for f in files:
        with open(f, encoding="utf-8") as fh:
            p = json.load(fh)
        batches.add(p.get("batch_id"))
        for pid, d in p["decisions"].items():
            per_pair[pid][p["curator"]] = d
    if len(batches) > 1:
        print(f"⚠️  exports come from different batches: {batches}")

    curators = sorted({c for v in per_pair.values() for c in v})
    print(f"{len(per_pair)} curated pairs from {len(files)} exports, curators: {', '.join(curators)}")

    # ---- long format ----
    long_rows = []
    for pid, byc in sorted(per_pair.items()):
        onto, aidoc_iri, ref_iri = pid.split("|", 2)
        for cur, d in byc.items():
            long_rows.append({
                "id": pid, "ontology": onto, "aidoc_iri": aidoc_iri, "ref_iri": ref_iri,
                "curator": cur, "decision": d["decision"],
                "relation": d.get("relation"), "note": d.get("note"), "ts": d.get("ts"),
            })
    os.makedirs("reports", exist_ok=True)
    pd.DataFrame(long_rows).to_csv("reports/curation_merged.csv", index=False)

    # ---- pairwise agreement ----
    for c1, c2 in itertools.combinations(curators, 2):
        pairs = [(v[c1]["decision"], v[c2]["decision"])
                 for v in per_pair.values() if c1 in v and c2 in v]
        if pairs:
            agree = sum(1 for a, b in pairs if a == b)
            print(f"  {c1} vs {c2}: n={len(pairs)}, agreement={agree/len(pairs):.2%}, "
                  f"kappa={kappa(pairs):.3f}")

    # ---- consensus ----
    cons_rows, conflicts = [], 0
    for pid, byc in sorted(per_pair.items()):
        onto, aidoc_iri, ref_iri = pid.split("|", 2)
        decs = {d["decision"] for d in byc.values()}
        rels = {d.get("relation") for d in byc.values() if d.get("relation")}
        notes = "; ".join(filter(None, (d.get("note") for d in byc.values())))
        if len(decs) == 1 and (len(rels) <= 1):
            cons_rows.append({
                "id": pid, "ontology": onto, "aidoc_iri": aidoc_iri, "ref_iri": ref_iri,
                "consensus": decs.pop(), "relation": rels.pop() if rels else None,
                "curators": "+".join(sorted(byc)), "notes": notes, "conflict": False,
            })
        else:
            conflicts += 1
            cons_rows.append({
                "id": pid, "ontology": onto, "aidoc_iri": aidoc_iri, "ref_iri": ref_iri,
                "consensus": None, "relation": None,
                "curators": "+".join(sorted(byc)),
                "notes": "CONFLICT: " + "; ".join(
                    f"{c}={d['decision']}{('→' + d['relation']) if d.get('relation') else ''}"
                    for c, d in sorted(byc.items())) + ("; " + notes if notes else ""),
                "conflict": True,
            })
    cons = pd.DataFrame(cons_rows)
    cons.to_csv("reports/curation_consensus.csv", index=False)
    print(f"consensus: {len(cons) - conflicts} agreed, {conflicts} conflicts "
          f"→ reports/curation_consensus.csv")
    if conflicts:
        print("  Konflikte im Team auflösen (Konsensverfahren laut "
              "publication/curation_protocol.md), die betroffenen Urteile im "
              "UI korrigieren, neu exportieren und dieses Skript erneut ausführen.")

    # ---- write consensus back into the *-curation.csv sheets ----
    by_id = {r["id"]: r for r in cons_rows}
    sheets = [(f, prefix)
              for d, prefix in CURATION_DIRS
              for f in sorted(glob.glob(os.path.join(d, "*-curation.csv")))]
    for f, prefix in sheets:
        try:
            df = pd.read_csv(f)
        except pd.errors.EmptyDataError:
            continue
        for col in ("curator_decision", "curator_relation", "curator_name", "curator_notes"):
            df[col] = df[col].astype("string")
        onto = prefix + os.path.basename(f).replace("-curation.csv", "")
        changed = 0
        for i, row in df.iterrows():
            pid = f"{onto}|{row['aidoc_iri']}|{row['ref_iri']}"
            r = by_id.get(pid)
            if not r:
                continue
            df.at[i, "curator_decision"] = r["consensus"] or ""
            df.at[i, "curator_relation"] = r["relation"] or ""
            df.at[i, "curator_name"] = r["curators"]
            df.at[i, "curator_notes"] = r["notes"] or ""
            changed += 1
        if changed:
            df.to_csv(f, index=False)
            print(f"  {f}: {changed} rows updated")


if __name__ == "__main__":
    main()
