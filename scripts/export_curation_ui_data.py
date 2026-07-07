"""Bundle the alignment curation sheets into JSON for the curation web UI.

Reads reports/alignment_semantic/*-curation.csv (produced by
alignment_semantic.py) and writes docs/resources/curation-data.json,
which docs/curation.html loads.

Run this after every alignment (re-)run:
    python scripts/export_curation_ui_data.py
"""

import datetime
import glob
import json
import os
import sys

import pandas as pd

CURATION_DIR = "reports/alignment_semantic"
OUT_FILE = "docs/resources/curation-data.json"


def main():
    files = sorted(glob.glob(os.path.join(CURATION_DIR, "*-curation.csv")))
    if not files:
        sys.exit(f"No *-curation.csv files found in {CURATION_DIR}")

    items = []
    for f in files:
        onto = os.path.basename(f).replace("-curation.csv", "")
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
    print(f"✅ {len(items)} mappings from {len(files)} ontologies → {OUT_FILE} (batch {batch_id})")


if __name__ == "__main__":
    main()
