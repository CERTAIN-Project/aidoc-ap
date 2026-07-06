"""Pre-aggregate the GitHub Pages data into JSON so the pages load fast.

The alignments and coverage pages originally parsed Turtle files client-side
(N3.js from a CDN, sequential fetches, no caching) which caused slow loads.
This script converts the published TTL resources into the JSON files the
pages prefer; the TTL path remains as a fallback.

Outputs:
    docs/alignments.json                  mappings for alignments.html
    docs/runs.json                        PROV runs for alignments.html
    docs/resources/coverage-data.json     measurements + runs + requirement labels

Run after every update of docs/resources/*.ttl:
    python scripts/export_pages_data.py
"""

import glob
import json
import os

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


def export_alignments():
    maps, runs = [], {}
    for f in sorted(glob.glob("docs/resources/*-alignments.ttl")):
        g = Graph().parse(f, format="turtle")
        for a in g.subjects(RDF.type, PROV.Activity):
            runs[str(a)] = {
                "id": str(a),
                "startedAt": lit(g, a, PROV.startedAtTime),
                "endedAt": lit(g, a, PROV.endedAtTime),
                "used": lit(g, a, PROV.used),
            }
        for m in g.subjects(RDF.type, ALIGN.Mapping):
            tgt = lit(g, m, ALIGN.target) or ""
            ns = tgt.split("#")[0] if "#" in tgt else tgt.rsplit("/", 1)[0]
            conf = g.value(m, ALIGN.confidence)
            maps.append({
                "mapping": str(m),
                "source": lit(g, m, ALIGN.source),
                "relation": lit(g, m, ALIGN.relation),
                "target": tgt,
                "target_ns": ns,
                "confidence": float(conf) if conf is not None else None,
                "rationale": lit(g, m, ALIGN.rationale),
                "agent": lit(g, m, PROV.wasAttributedTo),
                "run": lit(g, m, PROV.wasGeneratedBy),
            })
    with open("docs/alignments.json", "w", encoding="utf-8") as f:
        json.dump(maps, f, indent=1, ensure_ascii=False)
    with open("docs/runs.json", "w", encoding="utf-8") as f:
        json.dump({"runs": list(runs.values())}, f, indent=1, ensure_ascii=False)
    print(f"✅ {len(maps)} mappings, {len(runs)} runs → docs/alignments.json, docs/runs.json")


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


if __name__ == "__main__":
    export_alignments()
    export_coverage()
