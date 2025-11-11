import os
import csv
import json
from rdflib import Graph, RDF, RDFS, Namespace
from openai import OpenAI


from dotenv import load_dotenv
load_dotenv()

# ========== CONFIGURATION ==========
AIACT_FILE = "annex_4.ttl"
ENTITY_FILE = "output/aidoc-entities.csv"
OUTPUT_FILE = "reports/semantic_mapping.json"

OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.1:8b")
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434") + "/v1/"
print(f"Using Ollama URL: {OLLAMA_URL}, Model: {OLLAMA_MODEL}")

client = OpenAI(
    base_url=OLLAMA_URL,
    # required but ignored
    api_key='ollama',
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
            "label": str(label),
            "text": str(description)
        })

print(f"Loaded {len(requirements)} Annex IV requirements and {len(ontology_entities)} ontology entities.")

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
3. Any missing concepts or terms that should be added.

Return the result as strict JSON with the following structure:
{{
  "coverage_score": float,
  "matched_terms": [list of ontology term labels],
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
            "missing": [f"Error: {str(e)}"]
        }

    results.append({
        "requirement": req["label"],
        "requirement_id": req["id"],
        "coverage_score": result.get("coverage_score", 0),
        "matched_terms": result.get("matched_terms", []),
        "missing": result.get("missing", [])
    })
    print(f"Debug info for {req['label']}: {result}")


# ========== SAVE RESULTS ==========
with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
    json.dump(results, f, indent=2, ensure_ascii=False)

print(f"✅ Semantic mapping complete — results saved to {OUTPUT_FILE}")
