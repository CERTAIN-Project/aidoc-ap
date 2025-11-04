import rdflib
from rdflib import RDFS, OWL
from difflib import SequenceMatcher
import csv
import os
from pathlib import Path

LEFT_FILE = "aidoc-ap.ttl"
RIGHT_FILE = "reference_ontologies/"
OUTPUT_DIR = "reports/alignment_structural/"
os.makedirs(OUTPUT_DIR, exist_ok=True)
Path("reports").mkdir(exist_ok=True)

def similarity(a, b):
    return SequenceMatcher(None, a.lower(), b.lower()).ratio()

def extract_entities(g):
    entities = {}
    for s in g.subjects(rdflib.RDF.type, OWL.Class):
        label = g.value(s, RDFS.label)
        if label:
            entities[str(s)] = str(label)
    return entities

left_g = rdflib.Graph().parse(LEFT_FILE, format="turtle")

for fname in Path(RIGHT_FILE).glob("*.ttl"):
    right_g = rdflib.Graph().parse(fname, format="turtle")

    left_classes = extract_entities(left_g)
    right_classes = extract_entities(right_g)

    alignments = []

    for l_iri, l_label in left_classes.items():
        for r_iri, r_label in right_classes.items():
            score = similarity(l_label, r_label)
            # print(f"Comparing '{l_label}' to '{r_label}' → similarity: {score:.3f}")
            
            if score > 0.75:  # adjustable threshold
                alignments.append({
                    "aidoc_iri": l_iri,
                    "aidoc_label": l_label,
                    f"{Path(fname).stem}_iri": r_iri,
                    f"{Path(fname).stem}_label": r_label,
                    "similarity": round(score, 3)
                })
    if alignments:
        with open(os.path.join(OUTPUT_DIR, f"{Path(fname).stem}_alignment.csv"), "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=alignments[0].keys())
            writer.writeheader()
            writer.writerows(alignments)

    print(f"Found {len(alignments)} potential lexical alignments → {os.path.join(OUTPUT_DIR, f'{Path(fname).stem}_alignment.csv')}")

print("✅ Structural alignment completed.")