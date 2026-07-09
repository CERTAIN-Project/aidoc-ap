"""False-negative analysis of the lexical candidate-generation step (reviewer R3.1).

The alignment pipeline only passes lexical candidate pairs with a combined
similarity >= 0.6 to the LLM classification step. To estimate how many
meaningful correspondences the candidate generation misses, this script

  1. enumerates all AIDOC x reference-ontology pairs in the band [0.5, 0.6)
     (i.e. just below the operating threshold),
  2. draws a seeded random sample of SAMPLE_SIZE pairs,
  3. classifies the sampled pairs with the exact same LLM prompt as
     alignment_semantic.py (the template is loaded from that file, not
     duplicated), and
  4. writes per-ontology curation sheets to reports/alignment_fn_band/
     with the same columns as the main curation sheets.

The expert curation of these sheets (accept/modify = a meaningful mapping
exists) yields the estimated false-negative rate of the candidate generation
reported in the paper. Analyze with:

    python scripts/analyze_curation.py reports/alignment_fn_band

Usage:
    python scripts/alignment_fn_band.py            # sample + classify
    python scripts/alignment_fn_band.py --dry-run  # only count/sample, no LLM calls
"""

import argparse
import ast
import json
import os
import random
import time
from collections import Counter
from pathlib import Path

import pandas as pd
from rdflib import Graph, RDFS, Namespace, URIRef
from openai import OpenAI
from dotenv import load_dotenv

from alignment_structural import extract_entities, similarity

load_dotenv()

AIDOC_FILE = "aidoc-ap.ttl"
REFERENCE_DIR = "reference_ontologies/"
OUTPUT_DIR = "reports/alignment_fn_band"

BAND_LOW, BAND_HIGH = 0.5, 0.6   # lexical band just below the 0.6 operating point
SAMPLE_SIZE = int(os.getenv("FN_SAMPLE_SIZE", "50"))
SAMPLE_SEED = int(os.getenv("FN_SAMPLE_SEED", "42"))

OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "gemma3:27b")
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434") + "/v1/"
TEMPERATURE = float(os.getenv("LLM_TEMPERATURE", "0.0"))
SEED = int(os.getenv("LLM_SEED", "42"))
CONF_THRESHOLD = float(os.getenv("CONF_THRESHOLD", "0.75"))

SKOS = Namespace("http://www.w3.org/2004/02/skos/core#")


def load_from_alignment_semantic(*names):
    """Load module-level string constants / functions from alignment_semantic.py
    without importing it (importing would execute the whole pipeline)."""
    src = Path(__file__).with_name("alignment_semantic.py").read_text()
    tree = ast.parse(src)
    found = {}
    for node in tree.body:
        if isinstance(node, ast.Assign):
            for tgt in node.targets:
                if isinstance(tgt, ast.Name) and tgt.id in names:
                    found[tgt.id] = ast.literal_eval(node.value)
        elif isinstance(node, ast.FunctionDef) and node.name in names:
            code = ast.get_source_segment(src, node)
            ns = {"json": json, "re": __import__("re")}
            exec(code, ns)
            found[node.name] = ns[node.name]
    missing = set(names) - set(found)
    if missing:
        raise RuntimeError(f"could not load {missing} from alignment_semantic.py")
    return [found[n] for n in names]


prompt_template, parse_relation_json = load_from_alignment_semantic(
    "prompt_template", "parse_relation_json")


def describe_entity(g, iri):
    label = g.value(iri, RDFS.label)
    comment = g.value(iri, RDFS.comment)
    definition = g.value(iri, SKOS.definition)
    return {
        "label": str(label) if label else str(iri).split("#")[-1].split("/")[-1],
        "comment": str(comment or definition or ""),
    }


def band_pairs():
    """All (ref_name, aidoc_iri, aidoc_label, ref_iri, ref_label, score) in the band."""
    aidoc_g = Graph().parse(AIDOC_FILE, format="turtle")
    aidoc_classes = {i: l for i, l in extract_entities(aidoc_g).items()
                     if i.startswith("https://w3id.org/aidoc-ap#")}
    pairs = []
    for fname in sorted(Path(REFERENCE_DIR).glob("*.ttl")):
        ref_g = Graph().parse(fname, format="turtle")
        ref_classes = extract_entities(ref_g)
        for a_iri, a_label in aidoc_classes.items():
            for r_iri, r_label in ref_classes.items():
                if a_iri == r_iri:
                    continue
                score = similarity(a_label, r_label)
                if BAND_LOW <= score < BAND_HIGH:
                    pairs.append((fname.stem, a_iri, a_label, r_iri, r_label,
                                  round(score, 3)))
    return pairs


def main(dry_run):
    pairs = band_pairs()
    per_ref = Counter(p[0] for p in pairs)
    print(f"Lexical pairs in band [{BAND_LOW}, {BAND_HIGH}): {len(pairs)}")
    print("  per reference ontology:",
          ", ".join(f"{k}={v}" for k, v in sorted(per_ref.items())))

    rng = random.Random(SAMPLE_SEED)
    sample = pairs if len(pairs) <= SAMPLE_SIZE else rng.sample(pairs, SAMPLE_SIZE)
    print(f"Seeded sample (seed={SAMPLE_SEED}): {len(sample)} pairs")
    if dry_run:
        return

    client = OpenAI(base_url=OLLAMA_URL, api_key=os.getenv("OLLAMA_API_KEY"))
    print(f"Using Ollama URL: {OLLAMA_URL}, Model: {OLLAMA_MODEL}, "
          f"Temperature: {TEMPERATURE}, Seed: {SEED}")

    aidoc_g = Graph().parse(AIDOC_FILE, format="turtle")
    ref_graphs = {}
    rows_per_ref = {}

    for n, (ref_name, a_iri, a_label, r_iri, r_label, score) in enumerate(sample, 1):
        if ref_name not in ref_graphs:
            ref_graphs[ref_name] = Graph().parse(
                REFERENCE_DIR + ref_name + ".ttl", format="turtle")
        a_desc = describe_entity(aidoc_g, URIRef(a_iri))
        r_desc = describe_entity(ref_graphs[ref_name], URIRef(r_iri))

        prompt = prompt_template.format(
            aidoc_label=a_desc["label"], aidoc_comment=a_desc["comment"],
            REF=ref_name, ref_label=r_desc["label"], ref_uri=r_iri,
            ref_comment=r_desc["comment"], similarity=score)

        result = {"relation": "", "confidence": 0.0, "comment": ""}
        for attempt in range(1, 4):
            try:
                reply = client.chat.completions.create(
                    messages=[{"role": "user", "content": prompt}],
                    model=OLLAMA_MODEL, temperature=TEMPERATURE, seed=SEED)
                result = parse_relation_json(reply.choices[0].message.content)
                break
            except Exception as e:
                print(f"  retry {attempt}/3 after error: {e}")
                time.sleep(5 * 3 ** (attempt - 1))

        conf = float(result.get("confidence", 0.0))
        rows_per_ref.setdefault(ref_name, []).append({
            "aidoc_iri": a_iri,
            "aidoc_label": a_desc["label"],
            "ref_iri": r_iri,
            "ref_label": r_desc["label"],
            "lexical_similarity": score,
            "llm_relation": result.get("relation", ""),
            "llm_confidence": conf,
            "llm_rationale": result.get("comment", ""),
            "above_threshold": conf >= CONF_THRESHOLD,
            "curator_decision": "",
            "curator_relation": "",
            "curator_name": "",
            "curator_notes": "",
        })
        print(f"[{n}/{len(sample)}] {a_desc['label']} ↔ {ref_name}:{r_desc['label']} "
              f"(lex {score}) → {result.get('relation')} @ {conf}")

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    for ref_name, rows in sorted(rows_per_ref.items()):
        out = os.path.join(OUTPUT_DIR, f"{ref_name}-curation.csv")
        pd.DataFrame(rows).to_csv(out, index=False)
        print(f"  {len(rows):3d} rows → {out}")
    print("✅ False-negative band sample classified; "
          "curate the sheets, then run: "
          "python scripts/analyze_curation.py reports/alignment_fn_band")


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--dry-run", action="store_true",
                    help="only count the band and print the sample, no LLM calls")
    args = ap.parse_args()
    main(args.dry_run)
