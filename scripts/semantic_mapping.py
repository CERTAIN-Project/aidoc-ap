import os
import csv
import json
import datetime
from rdflib import Graph, RDF, RDFS, Namespace, URIRef, Literal
from rdflib.namespace import XSD, SKOS, PROV
from openai import OpenAI


from dotenv import load_dotenv
load_dotenv()

# ========== CONFIGURATION ==========
AIACT_FILE = "annex_4.ttl"
ENTITY_FILE = "reports/aidoc-entities.csv"
OUTPUT_FILE = "reports/semantic_mapping.ttl"
OUTPUT_JSON = "reports/semantic_mapping.json"

OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.1:8b")
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434") + "/v1/"
print(f"Using Ollama URL: {OLLAMA_URL}, Model: {OLLAMA_MODEL}")

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
    if label and description:
        requirements.append({
            "id": str(s).split("#")[-1],
            "uri": str(s),
            "label": str(label),
            "text": str(description)
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
run_timestamp = datetime.datetime.utcnow().strftime("%Y-%m-%d")
activity_uri = URIRef(f"https://w3id.org/aidoc-ap/coverage/llm-run/{run_timestamp}")
agent_uri = URIRef("https://w3id.org/aidoc-ap/alignment#LLMCoverageBot")

coverage_graph.add((activity_uri, RDF.type, PROV.Activity))
coverage_graph.add((activity_uri, RDFS.label, Literal(f"LLM Coverage Analysis using {OLLAMA_MODEL}")))
coverage_graph.add((activity_uri, PROV.startedAtTime, Literal(datetime.datetime.utcnow().isoformat() + "Z", datatype=XSD.dateTime)))

coverage_graph.add((agent_uri, RDF.type, PROV.SoftwareAgent))
coverage_graph.add((agent_uri, RDFS.label, Literal(f"LLM Coverage Bot ({OLLAMA_MODEL})")))

ontology_version_uri = URIRef("https://w3id.org/aidoc-ap/1.0")

# ========== DEFINE LLM PROMPT ==========
prompt_template = """
You are an ontology and AI compliance expert.

Given the following AI Act requirement:
"{requirement_text}"

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

# Create a mapping from labels to URIs for matched terms
label_to_uri = {}
for entity in ontology_entities:
    if entity.get("label") and entity.get("iri"):
        label_to_uri[entity["label"]] = entity["iri"]

results = []

for req in requirements:
    prompt = prompt_template.format(
        requirement_text=req["text"],
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

    # Create RDF measurement
    measurement_uri = URIRef(f"https://w3id.org/aidoc-ap/coverage#{req['id']}")
    
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
# Save as TTL
coverage_graph.serialize(destination=OUTPUT_FILE, format="turtle")
print(f"✅ Semantic mapping (TTL) saved to {OUTPUT_FILE}")

# Save JSON for compatibility
with open(OUTPUT_JSON, "w", encoding="utf-8") as f:
    json.dump(results, f, indent=2, ensure_ascii=False)
print(f"✅ Semantic mapping (JSON) saved to {OUTPUT_JSON}")
