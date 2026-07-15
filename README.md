# AIDOC-AP – AI Documentation Application Profile

**AIDOC-AP** is an application profile for documenting AI systems and their lifecycle in a structured, machine-readable way, **grounded in the technical documentation obligation of Article 11 and Annex IV of the EU AI Act**. It provides an ontology to represent technical documentation requirements such as system architecture, data, training/validation/testing procedures, risk and performance information.

- **Persistent identifier:** <https://w3id.org/aidoc-ap>
- **Documentation & resources:** <https://certain-project.github.io/aidoc-ap/>
- **Archived releases (DOI):** [10.5281/zenodo.17787787](http://doi.org/10.5281/zenodo.17787787)
- **Current ontology version:** 1.2

Developed as part of the [**CERTAIN** project](https://certain-project.eu/) and applied in CERTAIN use cases and pilots.


## Repository Layout

| Path | Content |
|---|---|
| [`aidoc-ap.ttl`](aidoc-ap.ttl) | The AIDOC-AP ontology (OWL/Turtle): AI systems, models, datasets; lifecycle activities and agents (provider, deployer, auditor); documentation artefacts relevant to Annex IV (technical documentation, datasheets, risk documents, transparency measures) |
| [`annex_4.ttl`](annex_4.ttl) | The 22 **Annex IV requirements** as `aiact:Requirement` individuals with descriptions, lifecycle annotations and the associated **competency questions** |
| [`sparql_competency_questions/`](sparql_competency_questions/) | The 50 competency questions as executable SPARQL queries |
| [`examples/`](examples/) | Five instantiated knowledge graphs based on CERTAIN pilot scenarios (energy, biometrics, finance, civic participation, HR) |
| [`reference_ontologies/`](reference_ontologies/) | Reference ontologies used for alignment: AIRO, VAIR, PROV-O, MLS, DCAT3, DQV, MEX, and DPV incl. its AI / TECH / AI Act extensions |
| [`scripts/`](scripts/) | The alignment, coverage and curation toolchain (see below) |
| [`experiments/`](experiments/) | Published experiment data: coverage multirun matrix, CQ validation results, expert curation records |
| [`docs/`](docs/) | GitHub Pages site: ontology documentation, requirement views, coverage and alignment reports; `docs/resources/` holds the **published curated alignment files** and coverage data |
| [`figures/`](figures/) | Ontology overview and pipeline diagrams (draw.io + PNG) |

Script outputs are written to a local `reports/` folder (not tracked); the published copies live under `experiments/` and `docs/resources/`.


## Methodology

AIDOC-AP is developed with an LLM-assisted, competency-question-driven pipeline (an extension of NeOn-GPT):

- **Requirements modelling** — Annex IV requirements are modelled in `annex_4.ttl`; each is linked to competency questions (CQs) that express what the documentation must be able to answer.
- **Ontology modelling** — AIDOC-AP provides the classes and properties needed to answer these CQs (architecture, data, training/validation/testing, quality, logging, risk, performance, transparency). Key concepts are grounded in DPV via `rdfs:subClassOf`.
- **Alignment** — lexical candidate generation (`alignment_structural.py`) followed by LLM-proposed correspondences (`alignment_semantic.py`); **every proposal is curated by three domain experts** (majority vote + adjudication). The curated mappings are published as SKOS mapping relations in `docs/resources/*-alignments.ttl`.
- **Coverage assessment** — `semantic_mapping.py` LLM-scores each Annex IV requirement against the ontology (stored as DQV quality measurements); `run_cq_validation.py` complements this with an LLM-independent check by executing all 50 CQs as SPARQL over the example knowledge graphs.


## Usage

### Using the ontology in your own KG

```turtle
@prefix aidoc: <https://w3id.org/aidoc-ap#> .
@prefix aiact: <https://w3id.org/aidoc-ap/requirements#> .
```

Instantiate `aidoc:AISystem`, `aidoc:AIModel`, `aidoc:Dataset`, activities and documentation artefacts to describe a concrete AI system, and use the `aiact:` requirements and CQs to check which Annex IV items your documentation covers (see `examples/` for complete instantiations).

### Reproducing the experiments

Assuming a Python virtual environment in `.venv` with dependencies installed:

```bash
# End-to-end driver (preflight, alignments, coverage matrix)
scripts/run_experiments.sh

# Individual steps
.venv/bin/python scripts/alignment_structural.py   # lexical candidates
.venv/bin/python scripts/alignment_semantic.py     # LLM relation classification
.venv/bin/python scripts/run_coverage_multirun.py  # coverage matrix (model × iteration × T × seed)
.venv/bin/python scripts/run_cq_validation.py      # SPARQL CQ answering over examples/
```

Curation toolchain: `export_curation_ui_data.py` (curation UI batches), `merge_curation.py` (3-curator merge, majority vote), `analyze_curation.py` (agreement/precision), `apply_curation_to_ttl.py` (curated alignment TTLs), `coverage_expert_agreement.py` (expert-agreement study), `export_pages_data.py` (Pages data).

All LLM experiments use locally hosted open-weight models (Gemma 3 27B, Llama 3.3 70B, GPT-OSS 120B, Apertus 70B) at temperature 0 with fixed seeds. The published experiment data in `experiments/` was produced against ontology v1.1; v1.2 renamed `aidoc:VisualDocumentation` to `aidoc:TechnicalDocumentation`, which the published alignment files reflect via a documented editorial migration (see `scripts/apply_curation_to_ttl.py`).


## Project Context – CERTAIN

AIDOC-AP is developed within the CERTAIN project, which investigates methods and tools to ensure compliance, transparency and accountability of AI systems. AIDOC-AP serves as the semantic backbone for representing AI system documentation and assessing coverage of Annex IV requirements across domains.

Funded by the European Union's Horizon Europe research and innovation programme HORIZON-CL4-2024-DATA-01-01 under grant agreement No. 101189650.


## Contact

Maintained by **Sebastian Neumaier**, University of Applied Sciences St. Pölten — `sebastian.neumaier@ustp.at` ([sebneu](https://github.com/sebneu)).
Please use GitHub issues for questions, bug reports or suggestions.


## License

- **Code and tooling:** [Apache License 2.0](LICENSE)
- **Ontology and documentation:** [CC BY 4.0](LICENSE-CC-BY.txt)

Please retain attribution when reusing or modifying this work, and cite AIDOC-AP when using it in scientific publications or products.
