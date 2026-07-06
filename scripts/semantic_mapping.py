import os
import csv
import json
import re
import datetime
import shutil
import time
from rdflib import Graph, RDF, RDFS, Namespace, URIRef, Literal
from rdflib.namespace import XSD, SKOS, PROV
from openai import OpenAI


from dotenv import load_dotenv
load_dotenv()

# ========== CONFIGURATION ==========
AIACT_FILE = "annex_4.ttl"
# ENTITY_FILE can be overridden to evaluate historical ontology iterations
# (e.g. reports/experiments/entities_iter1_gemma3_27b.csv)
ENTITY_FILE = os.getenv("ENTITY_FILE", "reports/aidoc-entities.csv")
OUTPUT_FILE = "reports/semantic_mapping.ttl"
OUTPUT_JSON = "reports/semantic_mapping.json"

OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "gemma3:27b")
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434") + "/v1/"
TEMPERATURE = float(os.getenv("LLM_TEMPERATURE", "0.0"))
SEED = int(os.getenv("LLM_SEED", "42"))
# Optional tag to keep outputs of separate experiment runs apart
# (e.g. "gemma3_27b_run1"); empty tag preserves the default file names.
RUN_TAG = os.getenv("RUN_TAG", "").strip()
if RUN_TAG:
    OUTPUT_FILE = f"reports/semantic_mapping_{RUN_TAG}.ttl"
    OUTPUT_JSON = f"reports/semantic_mapping_{RUN_TAG}.json"
print(f"Using Ollama URL: {OLLAMA_URL}, Model: {OLLAMA_MODEL}, "
      f"Temperature: {TEMPERATURE}, Seed: {SEED}, Run tag: {RUN_TAG or '(none)'}")

client = OpenAI(
    base_url=OLLAMA_URL,
    api_key=os.getenv("OLLAMA_API_KEY")
)

os.makedirs("reports", exist_ok=True)

# ========== LOAD ONTOLOGY ENTITIES ==========
with open(ENTITY_FILE, "r", encoding="utf-8") as f:
    ontology_entities = csv.DictReader(f)
    ontology_entities = [row for row in ontology_entities]

# Simplify into readable text for the model
entity_text = "\n".join(
    [f"- {e['label']}: {e.get('comment','')}" for e in ontology_entities if e.get("label")]
)

# ========== LOAD ANNEX IV REQUIREMENTS ==========
g = Graph()
g.parse(AIACT_FILE, format="turtle")
AIACT = Namespace("https://w3id.org/aidoc-ap/requirements#")

requirements = []
for s in g.subjects(RDF.type, AIACT.Requirement):
    label = g.value(s, RDFS.label)
    description = g.value(s, Namespace("http://purl.org/dc/terms/").description)
    # associated competency questions are part of the evaluator input
    cqs = []
    for cq in g.objects(s, AIACT.hasCompetencyQuestion):
        cq_label = g.value(cq, RDFS.label)
        if cq_label:
            cqs.append(str(cq_label))
    if label and description:
        requirements.append({
            "id": str(s).split("#")[-1],
            "uri": str(s),
            "label": str(label),
            "text": str(description),
            "cqs": sorted(cqs)
        })

print(f"Loaded {len(requirements)} Annex IV requirements and {len(ontology_entities)} ontology entities.")

# ========== SETUP RDF GRAPH FOR OUTPUT ==========
coverage_graph = Graph()
DQV = Namespace("http://www.w3.org/ns/dqv#")
COV = Namespace("https://w3id.org/aidoc-ap/coverage#")
AIDOC = Namespace("https://w3id.org/aidoc-ap#")

coverage_graph.bind("dqv", DQV)
coverage_graph.bind("prov", PROV)
coverage_graph.bind("xsd", XSD)
coverage_graph.bind("cov", COV)
coverage_graph.bind("aidoc", AIDOC)
coverage_graph.bind("skos", SKOS)
coverage_graph.bind("aiact", AIACT)

# Define the metric once
metric_uri = COV.annexCoverageMetric
coverage_graph.add((metric_uri, RDF.type, DQV.Metric))
coverage_graph.add((metric_uri, SKOS.prefLabel, Literal("Annex IV Coverage Score", lang="en")))
coverage_graph.add((metric_uri, SKOS.definition, Literal("Heuristic coverage of a requirement by AIDOC-AP terms (0..1)", lang="en")))

# Activity and agent
# Use ISO timestamp with time to ensure uniqueness for multiple runs per day
run_timestamp_full = datetime.datetime.utcnow()
run_timestamp = run_timestamp_full.strftime("%Y-%m-%dT%H-%M-%S")  # Format: 2025-12-04T14-30-15
activity_uri = URIRef(f"https://w3id.org/aidoc-ap/coverage/llm-run/{run_timestamp}")
agent_uri = URIRef("https://w3id.org/aidoc-ap/alignment#LLMCoverageBot")

coverage_graph.add((activity_uri, RDF.type, PROV.Activity))
coverage_graph.add((activity_uri, RDFS.label, Literal(f"LLM Coverage Analysis using {OLLAMA_MODEL}")))
coverage_graph.add((activity_uri, PROV.startedAtTime, Literal(run_timestamp_full.isoformat() + "Z", datatype=XSD.dateTime)))
coverage_graph.add((activity_uri, COV.temperature, Literal(TEMPERATURE, datatype=XSD.decimal)))
coverage_graph.add((activity_uri, COV.seed, Literal(SEED, datatype=XSD.integer)))

coverage_graph.add((agent_uri, RDF.type, PROV.SoftwareAgent))
coverage_graph.add((agent_uri, RDFS.label, Literal(f"LLM Coverage Bot ({OLLAMA_MODEL})")))

ontology_version_uri = URIRef("https://w3id.org/aidoc-ap/1.0")

# ========== DEFINE LLM PROMPT ==========
prompt_template = """
You are an ontology and AI compliance expert.

Given the following AI Act requirement:
"{requirement_text}"

The requirement is operationalised through these competency questions, which a
knowledge graph using the ontology must be able to answer:
{competency_questions}

Compare it to the following ontology elements (classes, properties, or concepts):

{ontology_terms}

Identify:
1. The ontology terms that best represent this requirement.
2. A coverage score between 0.0 and 1.0 indicating how well the ontology covers this requirement.
3. A brief explanation (2-3 sentences) justifying the coverage score.
4. Any missing concepts or terms that should be added.

Return the result as strict JSON with the following structure:
{{
  "coverage_score": float,
  "matched_terms": [list of ontology term labels],
  "reasoning": "Brief explanation for the coverage score",
  "missing": [list of missing term suggestions]
}}
"""

# ========== RUN LLM COMPARISON ==========
def parse_coverage_json(text):
    """Robustly extract the coverage result from an LLM reply.

    As in the alignment step, malformed JSON (unescaped quotes/newlines in the
    free-text reasoning, trailing commas) is repaired rather than retried
    (deterministic at temperature 0). Falls back to regex-extracting the scalar
    coverage_score and the list fields so a single bad character in the
    reasoning does not discard an otherwise valid evaluation."""
    text = text.replace("```json", "").replace("```", "")
    i, j = text.find("{"), text.rfind("}")
    core = text[i:j + 1] if (i != -1 and j > i) else text
    for candidate in (core, re.sub(r",(\s*[}\]])", r"\1", core)):
        try:
            return json.loads(candidate)
        except Exception:
            pass
    score = re.search(r'"coverage_score"\s*:\s*([0-9]*\.?[0-9]+)', text)
    if score is None:
        raise ValueError(f"could not parse coverage_score from reply: {text[:160]!r}")

    def _list(field):
        m = re.search(r'"%s"\s*:\s*\[(.*?)\]' % field, text, re.S)
        return re.findall(r'"([^"]+)"', m.group(1)) if m else []

    reason = re.search(r'"reasoning"\s*:\s*"(.*?)"\s*[},]', text, re.S)
    return {
        "coverage_score": float(score.group(1)),
        "matched_terms": _list("matched_terms"),
        "reasoning": reason.group(1).replace('\n', ' ') if reason else "",
        "missing": _list("missing"),
    }


def query_ollama(prompt, max_attempts=4):
    # Each requirement is evaluated in a fresh, independent single-turn request;
    # no conversation state is carried over between requirements or runs.
    # Retry with backoff ONLY on API/transport errors; JSON parsing is handled
    # separately by parse_coverage_json and is not retried.
    last_err = None
    for attempt in range(1, max_attempts + 1):
        try:
            chat_completion = client.chat.completions.create(
                messages=[{'role': 'user', 'content': prompt}],
                model=OLLAMA_MODEL,
                temperature=TEMPERATURE,
                seed=SEED,
            )
        except Exception as e:
            last_err = e
            if attempt < max_attempts:
                wait = 5 * 3 ** (attempt - 1)  # 5s, 15s, 45s
                print(f"  retry {attempt}/{max_attempts - 1} after API error: {e} (waiting {wait}s)")
                time.sleep(wait)
            continue
        return parse_coverage_json(chat_completion.choices[0].message.content)
    raise last_err

# Create a mapping from labels to URIs for matched terms
label_to_uri = {}
for entity in ontology_entities:
    if entity.get("label") and entity.get("iri"):
        label_to_uri[entity["label"]] = entity["iri"]

results = []

for req in requirements:
    cq_text = "\n".join(f"- {cq}" for cq in req["cqs"]) or "- (no competency questions defined)"
    prompt = prompt_template.format(
        requirement_text=req["text"],
        competency_questions=cq_text,
        ontology_terms=entity_text
    )

    try:
        result = query_ollama(prompt)
    except Exception as e:
        result = {
            "coverage_score": 0,
            "matched_terms": [],
            "reasoning": f"Error: {str(e)}",
            "missing": []
        }

    coverage_score = result.get("coverage_score", 0)
    matched_terms = result.get("matched_terms", [])
    reasoning = result.get("reasoning", "")
    missing = result.get("missing", [])
    
    # Filter matched terms to AIDOC namespace only for JSON output
    matched_terms = [
        t for t in matched_terms
        if t in label_to_uri and str(label_to_uri[t]).startswith(str(AIDOC))
    ]

    results.append({
        "requirement": req["label"],
        "requirement_id": req["id"],
        "coverage_score": coverage_score,
        "matched_terms": matched_terms,
        "reasoning": reasoning,
        "missing": missing
    })
    print(f"Processing {req['label']}: coverage={coverage_score}")

    # Create RDF measurement with unique URI per run
    # This allows multiple runs to coexist in the same TTL file
    measurement_uri = URIRef(f"https://w3id.org/aidoc-ap/coverage#{req['id']}-{run_timestamp}")
    
    coverage_graph.add((measurement_uri, RDF.type, DQV.QualityMeasurement))
    coverage_graph.add((measurement_uri, DQV.isMeasurementOf, metric_uri))
    coverage_graph.add((measurement_uri, DQV.computedOn, ontology_version_uri))
    coverage_graph.add((measurement_uri, DQV.value, Literal(coverage_score, datatype=XSD.decimal)))
    coverage_graph.add((measurement_uri, COV.forRequirement, URIRef(req["uri"])))
    
    # Add reasoning/explanation
    if reasoning:
        coverage_graph.add((measurement_uri, COV.reasoning, Literal(reasoning, lang="en")))
    
    # Add matched terms (restricted to AIDOC namespace)
    for term_label in matched_terms:
        if term_label in label_to_uri:
            term_uri = URIRef(label_to_uri[term_label])
            if str(term_uri).startswith(str(AIDOC)):
                coverage_graph.add((measurement_uri, COV.matchedTerm, term_uri))
    
    # Add missing labels
    for missing_label in missing:
        coverage_graph.add((measurement_uri, COV.missingLabel, Literal(missing_label)))
    
    # Provenance
    coverage_graph.add((measurement_uri, PROV.wasGeneratedBy, activity_uri))
    coverage_graph.add((measurement_uri, PROV.wasAttributedTo, agent_uri))

# Close activity
coverage_graph.add((activity_uri, PROV.endedAtTime, Literal(datetime.datetime.utcnow().isoformat() + "Z", datatype=XSD.dateTime)))

# ========== SAVE RESULTS ==========
# Load existing TTL file if it exists (to append new runs)
if os.path.exists(OUTPUT_FILE):
    print(f"Loading existing coverage data from {OUTPUT_FILE}")
    existing_graph = Graph()
    existing_graph.parse(OUTPUT_FILE, format="turtle")
    
    # Merge with existing data
    for triple in existing_graph:
        coverage_graph.add(triple)
    
    print(f"Merged with existing data ({len(existing_graph)} existing triples)")

# Save as TTL
coverage_graph.serialize(destination=OUTPUT_FILE, format="turtle")
print(f"✅ Semantic mapping (TTL) saved to {OUTPUT_FILE} ({len(coverage_graph)} total triples)")

# Copy to docs/resources for website (only for default runs, not tagged experiments)
if not RUN_TAG:
    docs_output = "docs/resources/semantic_mapping.ttl"
    os.makedirs(os.path.dirname(docs_output), exist_ok=True)
    shutil.copy2(OUTPUT_FILE, docs_output)
    print(f"✅ Copied to {docs_output} for website")

# Save JSON for compatibility (only current run)
with open(OUTPUT_JSON, "w", encoding="utf-8") as f:
    json.dump(results, f, indent=2, ensure_ascii=False)
print(f"✅ Semantic mapping (JSON) saved to {OUTPUT_JSON}")
