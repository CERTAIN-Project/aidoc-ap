"""Bundle the alignment curation sheets into JSON for the curation web UI.

Reads reports/alignment_semantic/*-curation.csv (produced by
alignment_semantic.py) plus, if present, the below-threshold sample
reports/alignment_fn_band/*-curation.csv (produced by alignment_fn_band.py;
exported with an "fn-band/" ontology prefix so the group is distinguishable
in the UI and routable by merge_curation.py), and writes
docs/resources/curation-data.json, which docs/curation.html loads.

Run this after every alignment (re-)run:
    python scripts/export_curation_ui_data.py
"""

import datetime
import glob
import json
import os
import sys

import pandas as pd

CURATION_DIRS = [
    ("reports/alignment_semantic", ""),        # main candidate set
    ("reports/alignment_fn_band", "fn-band/"), # below-threshold FN sample
]
OUT_FILE = "docs/resources/curation-data.json"


def main():
    sources = []
    for d, prefix in CURATION_DIRS:
        found = sorted(glob.glob(os.path.join(d, "*-curation.csv")))
        if not found and not prefix:
            sys.exit(f"No *-curation.csv files found in {d}")
        sources += [(f, prefix) for f in found]

    items = []
    for f, prefix in sources:
        onto = prefix + os.path.basename(f).replace("-curation.csv", "")
        try:
            df = pd.read_csv(f)
        except pd.errors.EmptyDataError:
            print(f"[warn] {f} is empty, skipped")
            continue
        for _, r in df.iterrows():
            items.append({
                "id": f"{onto}|{r['aidoc_iri']}|{r['ref_iri']}",
                "ontology": onto,
                "aidoc_iri": r["aidoc_iri"],
                "aidoc_label": r["aidoc_label"],
                "ref_iri": r["ref_iri"],
                "ref_label": r["ref_label"],
                "lexical_similarity": round(float(r["lexical_similarity"]), 3),
                # normalise to SKOS mapping relations: class-level equivalence is
                # not asserted at the interoperability layer (see paper, Sec. 5)
                "llm_relation": str(r["llm_relation"]).replace(
                    "owl:equivalentClass", "skos:exactMatch"),
                "llm_confidence": float(r["llm_confidence"]),
                "llm_rationale": r.get("llm_rationale", "") if pd.notna(r.get("llm_rationale")) else "",
            })

    batch_id = datetime.datetime.now().strftime("%Y-%m-%d_%H%M")
    data = {
        "batch_id": batch_id,
        "generated": datetime.datetime.now().isoformat(timespec="seconds"),
        "n_items": len(items),
        "items": items,
    }
    os.makedirs(os.path.dirname(OUT_FILE), exist_ok=True)
    with open(OUT_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=1, ensure_ascii=False)
    n_band = sum(1 for i in items if i["ontology"].startswith("fn-band/"))
    print(f"✅ {len(items)} mappings ({len(items) - n_band} main + {n_band} fn-band) "
          f"from {len(sources)} sheets → {OUT_FILE} (batch {batch_id})")


if __name__ == "__main__":
    main()
