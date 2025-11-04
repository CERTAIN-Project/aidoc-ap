from rdflib import Graph, RDF, RDFS, Namespace
import csv
import os
from pathlib import Path

# --- configuration ---
os.makedirs("output", exist_ok=True)
INPUT_FILE = "aidoc-ap.ttl"
OUTPUT_FILE = "output/aidoc-entities.csv"

# --- load graph ---
g = Graph()
g.parse(INPUT_FILE, format="turtle")

# --- common namespaces ---
OWL = Namespace("http://www.w3.org/2002/07/owl#")
SKOS = Namespace("http://www.w3.org/2004/02/skos/core#")

# --- helper function to safely get literal values ---
def first_literal(subject, predicates):
    for p in predicates:
        for o in g.objects(subject, p):
            return str(o)
    return ""

# --- gather entities ---
entities = []

for s in g.subjects(RDF.type, OWL.Class):
    entities.append({
        "type": "Class",
        "iri": str(s),
        "label": first_literal(s, [RDFS.label]),
        "comment": first_literal(s, [RDFS.comment, SKOS.definition])
    })

for s in g.subjects(RDF.type, OWL.ObjectProperty):
    entities.append({
        "type": "ObjectProperty",
        "iri": str(s),
        "label": first_literal(s, [RDFS.label]),
        "comment": first_literal(s, [RDFS.comment, SKOS.definition])
    })

for s in g.subjects(RDF.type, OWL.DatatypeProperty):
    entities.append({
        "type": "DatatypeProperty",
        "iri": str(s),
        "label": first_literal(s, [RDFS.label]),
        "comment": first_literal(s, [RDFS.comment, SKOS.definition])
    })

# --- write to CSV ---
Path(OUTPUT_FILE).parent.mkdir(parents=True, exist_ok=True)

with open(OUTPUT_FILE, "w", newline="", encoding="utf-8") as f:
    writer = csv.DictWriter(f, fieldnames=["type", "iri", "label", "comment"])
    writer.writeheader()
    writer.writerows(entities)

print(f"✅ Extracted {len(entities)} entities to {OUTPUT_FILE}")
