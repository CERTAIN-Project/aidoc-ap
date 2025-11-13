import os
import json
import requests
import datetime
import pandas as pd
from rdflib import Graph, RDFS, Namespace, URIRef, Literal
from rdflib.namespace import PROV, XSD, OWL, RDF
import uuid
from openai import OpenAI

from dotenv import load_dotenv
load_dotenv()


AIDOC_FILE = "aidoc-ap.ttl"
REFERENCE_DIR = "reference_ontologies/"
INPUT_DIR = "reports/alignment_structural"
os.makedirs("reports/alignment_semantic", exist_ok=True)
OUTPUT_DIR = "reports/alignment_semantic"

OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.1:8b")
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434") + "/v1/"
print(f"Using Ollama URL: {OLLAMA_URL}, Model: {OLLAMA_MODEL}")
CONF_THRESHOLD = 0.5

client = OpenAI(
    base_url=OLLAMA_URL,
    api_key=os.getenv("OLLAMA_API_KEY")
)

# ==========================
# LOAD GRAPHS
# ==========================
AIDOC = Graph().parse(AIDOC_FILE, format="turtle")
SKOS = Namespace("http://www.w3.org/2004/02/skos/core#")
ALIGN = Namespace("https://w3id.org/aidoc-ap/alignment#")
agent_uri = URIRef("https://w3id.org/aidoc-ap/alignment#LLMAlignmentBot")

# Helper: fetch label + comment/definition
def describe_entity(g, iri):
    label = g.value(iri, RDFS.label)
    comment = g.value(iri, RDFS.comment)
    definition = g.value(iri, SKOS.definition)
    return {
        "label": str(label) if label else iri.split("#")[-1],
        "comment": str(comment or definition or "")
    }

# ==========================
# PREFIXES
# ==========================
prefixes = """@prefix aidoc: <https://w3id.org/aidoc-ap#> .
@prefix skos: <http://www.w3.org/2004/02/skos/core#> .
@prefix prov: <http://www.w3.org/ns/prov#> .
"""

# ==========================
# LLM PROMPT TEMPLATE
# ==========================
prompt_template = """
You are an expert in ontology alignment and semantic interoperability.

Compare these two ontology concepts.

**AIDOC concept:**
Label: {aidoc_label}
Description: {aidoc_comment}

**{REF} concept:**
Label: {ref_label}
URI: {ref_uri}
Description: {ref_comment}

Lexical similarity score (0–1): {similarity}

Decide whether these two terms are:
- equivalentClass
- broader
- narrower
- related
- unrelated

If related, specify the appropriate SKOS or OWL relation (e.g., skos:closeMatch, skos:broadMatch, owl:equivalentClass).

Return JSON in this format only:
{{
  "relation": "skos:closeMatch",
  "confidence": 0.9,
  "comment": "They both describe risk assessment processes but differ in scope."
}}
"""

def query_ollama(prompt):
    chat_completion = client.chat.completions.create(
        messages=[
            {
                'role': 'user',
                'content': prompt,
            }
        ],
        model=OLLAMA_MODEL,
    )
    response = chat_completion.choices[0].message.content
    response = response.replace("```json", "")
    response = response.replace("```", "")
    json_result = json.loads(response)
    return json_result

for fname in os.listdir(INPUT_DIR):
    if not fname.endswith("_alignment.csv"):
        continue

    REF = Graph().parse(REFERENCE_DIR + fname.replace('_alignment.csv','.ttl'), format="turtle")
    STRUCTURAL_FILE = os.path.join(INPUT_DIR, fname)
    OUTPUT_FILE = os.path.join(OUTPUT_DIR, fname.replace("_alignment.csv", "_semantic_alignment.ttl"))  
    df = pd.read_csv(STRUCTURAL_FILE)

    # ==========================
    # Initialize RDF graph
    alignment_graph = Graph()
    alignment_graph.bind("prov", PROV)
    alignment_graph.bind("skos", SKOS)
    alignment_graph.bind("align", ALIGN)
    alignment_graph.bind("aidoc", "https://w3id.org/aidoc-ap#")

    alignment_graph.add((agent_uri, RDF.type, PROV.SoftwareAgent))
    alignment_graph.add((agent_uri, RDFS.label, Literal(f"LLM Alignment Step using {OLLAMA_MODEL}", datatype=XSD.string)))

    # Create activity node
    activity_uri = URIRef(f"https://w3id.org/aidoc-ap/alignment#{uuid.uuid4()}")
    alignment_graph.add((activity_uri, RDF.type, PROV.Activity))
    start_time = datetime.datetime.utcnow().replace(microsecond=0).isoformat() + "Z"
    alignment_graph.add((activity_uri, PROV.startedAtTime, Literal(start_time, datatype=XSD.dateTime)))
    alignment_graph.add((activity_uri, PROV.wasAssociatedWith, agent_uri))
    # ==========================

    for _, row in df.iterrows():
        aidoc_iri = row["aidoc_iri"]
        ref_iri = row[f"{fname.replace('_alignment.csv','')}_iri"]
        aidoc_uri = URIRef(aidoc_iri)
        ref_uri = URIRef(ref_iri)
        similarity = row.get("similarity", 0.0)

        aidoc_desc = describe_entity(AIDOC, aidoc_uri)
        ref_desc = describe_entity(REF, ref_uri)

        prompt = prompt_template.format(
            aidoc_label=aidoc_desc["label"],
            aidoc_comment=aidoc_desc["comment"],
            REF=fname.replace('_alignment.csv',''),
            ref_label=ref_desc["label"],
            ref_uri=ref_iri,
            ref_comment=ref_desc["comment"],
            similarity=similarity
        )

        try:
            result = query_ollama(prompt)
            relation_str = result.get("relation", "skos:relatedMatch")
            conf = float(result.get("confidence", 0.0))
            rationale = result.get("comment", "")

            if conf >= CONF_THRESHOLD:

                # --- Determine appropriate namespace for relation ---
                if relation_str.startswith("skos:"):
                    rel_uri = SKOS[relation_str.split(":")[-1]]
                elif relation_str.startswith("owl:"):
                    rel_uri = OWL[relation_str.split(":")[-1]]
                else:
                    # Default fallback to skos:relatedMatch
                    rel_uri = SKOS.relatedMatch

                # --- Add triples ---
                # add the semantic triple
                alignment_graph.add((aidoc_uri, rel_uri, ref_uri))

                # Create mapping node
                mapping_uri = URIRef(f"https://w3id.org/aidoc-ap/alignment#{uuid.uuid4()}")

                alignment_graph.add((mapping_uri, RDF.type, ALIGN.Mapping))
                alignment_graph.add((mapping_uri, RDF.type, PROV.Entity))
                alignment_graph.add((mapping_uri, ALIGN.source, aidoc_uri))
                alignment_graph.add((mapping_uri, ALIGN.target, ref_uri))
                alignment_graph.add((mapping_uri, ALIGN.relation, rel_uri))
                alignment_graph.add((mapping_uri, ALIGN.confidence, Literal(conf, datatype=XSD.float)))
                alignment_graph.add((mapping_uri, ALIGN.rationale, Literal(rationale, datatype=XSD.string)))

                # Link mapping to activity
                alignment_graph.add((mapping_uri, PROV.wasGeneratedBy, activity_uri))
                alignment_graph.add((mapping_uri, PROV.wasAttributedTo, agent_uri))

        except Exception as e:
            print(f"⚠️ Error on {aidoc_desc['label']} ↔ {ref_desc['label']}: {e}")

    # ==========================
    # SAVE OUTPUT
    # ==========================
    end_time = datetime.datetime.utcnow().replace(microsecond=0).isoformat() + "Z"
    alignment_graph.add((activity_uri, PROV.endedAtTime, Literal(end_time, datatype=XSD.dateTime)))

    alignment_graph.serialize(destination=OUTPUT_FILE, format="turtle")

    print(f"Semantic alignment with descriptions saved as Turtle → {OUTPUT_FILE}")

print("✅ Semantic alignment completed.")