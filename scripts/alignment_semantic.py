import os
import json
import datetime
import time
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

OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "gemma3:27b")
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434") + "/v1/"
CONF_THRESHOLD = float(os.getenv("CONF_THRESHOLD", "0.75"))
TEMPERATURE = float(os.getenv("LLM_TEMPERATURE", "0.0"))
SEED = int(os.getenv("LLM_SEED", "42"))
print(f"Using Ollama URL: {OLLAMA_URL}, Model: {OLLAMA_MODEL}, "
      f"Threshold: {CONF_THRESHOLD}, Temperature: {TEMPERATURE}, Seed: {SEED}")

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

Decide which single relation holds between the AIDOC concept and the {REF} concept.
Use exactly one of the following relations, applying these definitions:

- owl:equivalentClass — the two concepts denote the same class: every instance of
  one is necessarily an instance of the other.
- skos:closeMatch — the concepts are sufficiently similar that they can be used
  interchangeably in some applications, but their meanings are not identical.
- skos:broadMatch — the {REF} concept has a broader (more general) meaning that
  subsumes the AIDOC concept.
- skos:narrowMatch — the {REF} concept has a narrower (more specific) meaning
  that is subsumed by the AIDOC concept.
- skos:relatedMatch — the concepts are associatively related, but neither
  equivalent nor in a hierarchical (broader/narrower) relation.
- unrelated — no meaningful semantic relation between the concepts.

Also return a score between 0.0 and 1.0 expressing how strongly the given labels
and descriptions support the chosen relation. This score is used only as a
heuristic to rank and filter candidate mappings for subsequent human review;
it is not treated as a calibrated probability.

Return JSON in this format only:
{{
  "relation": "skos:closeMatch",
  "confidence": 0.9,
  "comment": "They both describe risk assessment processes but differ in scope."
}}
"""

def query_ollama(prompt, max_attempts=4):
    # Retries with backoff: the shared server serialises requests per port, so
    # transient timeouts/connection errors are expected under load.
    last_err = None
    for attempt in range(1, max_attempts + 1):
        try:
            chat_completion = client.chat.completions.create(
                messages=[
                    {
                        'role': 'user',
                        'content': prompt,
                    }
                ],
                model=OLLAMA_MODEL,
                temperature=TEMPERATURE,
                seed=SEED,
            )
            response = chat_completion.choices[0].message.content
            response = response.replace("```json", "")
            response = response.replace("```", "")
            return json.loads(response)
        except Exception as e:
            last_err = e
            if attempt < max_attempts:
                wait = 5 * 3 ** (attempt - 1)  # 5s, 15s, 45s
                print(f"  retry {attempt}/{max_attempts - 1} after error: {e} (waiting {wait}s)")
                time.sleep(wait)
    raise last_err

for fname in os.listdir(INPUT_DIR):
    if not fname.endswith("_alignment.csv"):
        continue

    REF = Graph().parse(REFERENCE_DIR + fname.replace('_alignment.csv','.ttl'), format="turtle")
    STRUCTURAL_FILE = os.path.join(INPUT_DIR, fname)
    OUTPUT_FILE = os.path.join(OUTPUT_DIR, fname.replace("_alignment.csv", "-alignments.ttl"))
    CURATION_FILE = os.path.join(OUTPUT_DIR, fname.replace("_alignment.csv", "-curation.csv"))
    df = pd.read_csv(STRUCTURAL_FILE)

    # All LLM judgments (incl. below-threshold and unrelated) are recorded for
    # expert curation and false-negative analysis; the TTL output only contains
    # mappings at or above CONF_THRESHOLD.
    curation_rows = []

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
    alignment_graph.add((activity_uri, PROV.used, URIRef(f"https://ollama.com/library/{OLLAMA_MODEL}")))
    # ==========================

    for _, row in df.iterrows():
        aidoc_iri = row["aidoc_iri"]
        ref_iri = row[f"{fname.replace('_alignment.csv','')}_iri"]
        aidoc_uri = URIRef(aidoc_iri)
        ref_uri = URIRef(ref_iri)
        similarity = row.get("similarity", 0.0)

        # Only keep alignments where the source term is from the AIDOC namespace
        if not str(aidoc_uri).startswith("https://w3id.org/aidoc-ap#"):
            continue

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

            curation_rows.append({
                "aidoc_iri": str(aidoc_uri),
                "aidoc_label": aidoc_desc["label"],
                "ref_iri": str(ref_uri),
                "ref_label": ref_desc["label"],
                "lexical_similarity": similarity,
                "llm_relation": relation_str,
                "llm_confidence": conf,
                "llm_rationale": rationale,
                "above_threshold": conf >= CONF_THRESHOLD,
                "curator_decision": "",   # accept | reject | modify
                "curator_relation": "",   # filled if decision == modify
                "curator_name": "",
                "curator_notes": "",
            })

            if conf >= CONF_THRESHOLD and relation_str.strip().lower() != "unrelated":

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
    pd.DataFrame(curation_rows).to_csv(CURATION_FILE, index=False)

    print(f"Semantic alignment with descriptions saved as Turtle → {OUTPUT_FILE}")
    print(f"Curation sheet (all {len(curation_rows)} LLM judgments) → {CURATION_FILE}")

print("✅ Semantic alignment completed.")