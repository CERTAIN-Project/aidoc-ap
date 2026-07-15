"""Pre-aggregate the GitHub Pages data into JSON so the pages load fast.

The alignments and coverage pages originally parsed Turtle files client-side
(N3.js from a CDN, sequential fetches, no caching) which caused slow loads.
This script converts the published TTL resources into the JSON files the
pages prefer; the TTL path remains as a fallback.

Outputs:
    docs/alignments.json                       curated mappings for alignments.html
                                               (relation, curation outcome, LLM-suggested
                                               relation, editorial notes, source TTL)
    docs/resources/aidoc-ap-alignments.ttl     union of all curated alignment TTLs
                                               ("download all" target)
    docs/resources/coverage-data.json          measurements + runs + requirement labels

Run after every update of docs/resources/*.ttl:
    python scripts/export_pages_data.py
"""

import csv
import glob
import json
import os
from collections import defaultdict

from rdflib import Graph, RDF, RDFS, Namespace

PROV = Namespace("http://www.w3.org/ns/prov#")
ALIGN = Namespace("https://w3id.org/aidoc-ap/alignment#")
DQV = Namespace("http://www.w3.org/ns/dqv#")
COV = Namespace("https://w3id.org/aidoc-ap/coverage#")
DCT = Namespace("http://purl.org/dc/terms/")
AIACT = Namespace("https://w3id.org/aidoc-ap/requirements#")


def lit(g, s, p):
    v = g.value(s, p)
    return str(v) if v is not None else None


# Display names for the curated alignment files (bucket -> vocabulary label).
VOCAB_LABELS = {
    "airo": "AIRO", "vair": "VAIR", "rains": "RAINS", "dpv": "DPV",
    "dpv-ai": "DPV-AI", "dpv-aiact": "DPV-AIAct", "dpv-tech": "DPV-TECH",
    "mlschema": "MLSchema", "ml-onto": "ML-Onto", "mex-core": "MEX-Core",
    "prov-o": "PROV-O", "mcro": "MCRO",
}

COMBINED_TTL = "docs/resources/aidoc-ap-alignments.ttl"


def export_alignments():
    maps = []
    combined = Graph()
    combined.bind("prov", PROV)
    combined.bind("skos", "http://www.w3.org/2004/02/skos/core#")
    combined.bind("align", ALIGN)
    combined.bind("aidoc", "https://w3id.org/aidoc-ap#")
    for f in sorted(glob.glob("docs/resources/*-alignments.ttl")):
        if os.path.abspath(f) == os.path.abspath(COMBINED_TTL):
            continue
        bucket = os.path.basename(f).replace("-alignments.ttl", "")
        g = Graph().parse(f, format="turtle")
        combined += g
        started = {str(a): lit(g, a, PROV.startedAtTime)
                   for a in g.subjects(RDF.type, PROV.Activity)}
        for m in g.subjects(RDF.type, ALIGN.Mapping):
            tgt = lit(g, m, ALIGN.target) or ""
            run = lit(g, m, PROV.wasGeneratedBy)
            maps.append({
                "mapping": str(m),
                "source": lit(g, m, ALIGN.source),
                "relation": lit(g, m, ALIGN.relation),
                "target": tgt,
                "vocab": VOCAB_LABELS.get(bucket, bucket.upper()),
                "outcome": lit(g, m, ALIGN.curationOutcome),
                "llm_relation": lit(g, m, ALIGN.llmSuggestedRelation),
                "editorial_note": lit(g, m, ALIGN.editorialNote),
                "agent": lit(g, m, PROV.wasAttributedTo),
                "generated_at": started.get(run),
                "file": f"resources/{os.path.basename(f)}",
            })
    maps.sort(key=lambda m: (m["vocab"], m["source"]))
    with open("docs/alignments.json", "w", encoding="utf-8") as f:
        json.dump(maps, f, indent=1, ensure_ascii=False)
    combined.serialize(destination=COMBINED_TTL, format="turtle")
    print(f"✅ {len(maps)} curated mappings → docs/alignments.json, {COMBINED_TTL}")


def export_coverage():
    g = Graph().parse("docs/resources/semantic_mapping.ttl", format="turtle")
    runs = []
    for a in g.subjects(RDF.type, PROV.Activity):
        runs.append({
            "id": str(a),
            "startedAt": lit(g, a, PROV.startedAtTime),
            "endedAt": lit(g, a, PROV.endedAtTime),
            "label": lit(g, a, RDFS.label) or str(a).rsplit("/", 1)[-1],
        })
    measurements = []
    for m in g.subjects(RDF.type, DQV.QualityMeasurement):
        req = g.value(m, COV.forRequirement)
        req_id = str(req).split("#")[-1] if req else None
        score = g.value(m, DQV.value)
        measurements.append({
            "measurementUri": str(m),
            "requirement_id": req_id,
            "coverage_score": float(score) if score is not None else 0.0,
            "matched_terms": [str(t).split("#")[-1].replace("_", " ")
                              for t in g.objects(m, COV.matchedTerm)],
            "missing": [str(t) for t in g.objects(m, COV.missingLabel)],
            "reasoning": lit(g, m, COV.reasoning) or "",
            "run": lit(g, m, PROV.wasGeneratedBy),
            "agent": lit(g, m, PROV.wasAttributedTo),
        })

    rg = Graph().parse("annex_4.ttl", format="turtle")
    requirements = {}
    for s in rg.subjects(RDF.type, AIACT.Requirement):
        rid = str(s).split("#")[-1]
        requirements[rid] = {
            "id": rid,
            "label": lit(rg, s, RDFS.label) or rid,
            "description": lit(rg, s, DCT.description) or "",
        }

    out = {"runs": runs, "measurements": measurements, "requirements": requirements}
    os.makedirs("docs/resources", exist_ok=True)
    with open("docs/resources/coverage-data.json", "w", encoding="utf-8") as f:
        json.dump(out, f, indent=1, ensure_ascii=False)
    print(f"✅ {len(measurements)} measurements, {len(runs)} runs, "
          f"{len(requirements)} requirements → docs/resources/coverage-data.json")


# Human-readable model names and pilot metadata for the UI.
MODEL_LABELS = {
    "gemma3:27b": "Gemma 3 27B",
    "llama3.3:70b": "Llama 3.3 70B",
    "gpt-oss:120b": "GPT-OSS 120B",
}
PILOT_META = {  # examples/<name> -> (display, application domain)
    "encom": ("Energy forecasting", "Critical infrastructure"),
    "biometrics": ("Biometric verification", "Biometrics / border management"),
    "bank": ("Investment recommendation", "Financial services"),
    "civicvoice": ("Civic participation", "Content clustering"),
    "hr-ai": ("HR / recruitment", "Employment"),
}


def _apertus_label(model):
    return "Apertus 70B" if "apertus" in model.lower() else MODEL_LABELS.get(model, model)


def export_experiments():
    """Export the coverage matrix and empirical CQ-answering results for the UI.

    The coverage matrix is aggregated directly from the per-cell run JSONs in
    reports/, so it is robust to the summary CSV being rewritten by a running
    experiment and automatically includes only models whose 3x3 (iteration x
    seed) cells at temperature 0 are complete."""
    import re
    import statistics

    out = {"coverage_by_model": [], "temperature": None, "cq_validation": [],
           "n_seeds": 3}

    # (model, temperature, iteration) -> list of per-run average coverage
    cells = defaultdict(list)
    pat = re.compile(r"semantic_mapping_(.+)_iter(\w+)_T([\d_]+)_run(\d+)\.json")
    for p in glob.glob("reports/semantic_mapping_*iter*_T*_run*.json"):
        m = pat.search(os.path.basename(p))
        if not m:
            continue
        model, it, temp = m.group(1), m.group(2), m.group(3).replace("_", ".")
        try:
            results = json.load(open(p, encoding="utf-8"))
        except Exception:
            continue
        scores = [float(r.get("coverage_score", 0)) for r in results
                  if not str(r.get("reasoning", "")).startswith("Error")]
        if scores:
            cells[(model, temp, it)].append(sum(scores) / len(scores))

    def tag_label(tag):
        t = tag.lower()
        if "apertus" in t:
            return "Apertus 70B"
        if t.startswith("gemma3_27b"):
            return "Gemma 3 27B"
        if t.startswith("gpt_oss_120b"):
            return "GPT-OSS 120B"
        if t.startswith("llama3_3_70b"):
            return "Llama 3.3 70B"
        return tag

    models = sorted({m for (m, t, i) in cells if t == "0.0"},
                    key=lambda m: ("apertus" in m.lower(), m))
    complete = []  # models with a full T=0 matrix, used for the fair averages
    for m in models:
        iters = {i: cells.get((m, "0.0", i), []) for i in ("1", "2", "3")}
        if not all(len(iters[i]) >= 3 for i in ("1", "2", "3")):
            continue  # skip models whose T=0 matrix is not yet complete
        complete.append(m)
        row = {"model": tag_label(m)}
        for i in ("1", "2", "3"):
            row[f"iter{i}"] = round(statistics.mean(iters[i]), 3)
            row[f"iter{i}_std"] = round(statistics.pstdev(iters[i]), 3)
        row["gain"] = round(row["iter3"] - row["iter1"], 3)
        out["coverage_by_model"].append(row)

    # temperature comparison over the complete models only (fair T=0 vs T=1.0)
    temp = {}
    for t in ("0.0", "1.0"):
        per_iter = {}
        for i in ("1", "2", "3"):
            vals = [statistics.mean(cells[(m, t, i)]) for m in complete
                    if cells.get((m, t, i))]
            if len(vals) == len(complete) and vals:
                per_iter[i] = round(sum(vals) / len(vals), 3)
        if per_iter:
            temp[t] = per_iter
    if temp:
        out["temperature"] = temp

    cqfile = "reports/cq_validation_summary.csv"
    if os.path.exists(cqfile):
        for r in csv.DictReader(open(cqfile)):
            disp, domain = PILOT_META.get(r["kg"], (r["kg"], ""))
            out["cq_validation"].append({
                "kg": r["kg"], "display": disp, "domain": domain,
                "answered": int(r["answered"]), "total": int(r["total_cqs"]),
                "share": float(r["share"]), "triples": int(r["triples"]),
            })
        out["cq_validation"].sort(key=lambda x: -x["answered"])

    os.makedirs("docs/resources", exist_ok=True)
    with open("docs/resources/experiments-data.json", "w", encoding="utf-8") as f:
        json.dump(out, f, indent=1, ensure_ascii=False)
    print(f"✅ {len(out['coverage_by_model'])} models, "
          f"{len(out['cq_validation'])} pilots → docs/resources/experiments-data.json")


if __name__ == "__main__":
    export_alignments()
    export_coverage()
    export_experiments()
