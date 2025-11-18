# AIDOC-AP – AI Documentation Application Profile

**AIDOC-AP** is an application profile for documenting AI systems and their lifecycle in a structured, machine-readable way, with a **primary focus on Annex IV of the EU AI Act**. It provides an ontology to represent technical documentation requirements such as system architecture, data, training/validation/testing procedures, risk and performance information.

The ontology is published under the persistent identifier: [`https://w3id.org/aidoc-ap#`](https://w3id.org/aidoc-ap).

This work is developed as part of the [**CERTAIN** project](https://certain-project.eu/) and is applied in CERTAIN use cases and pilots.


## Repository Contents

- `aidoc-ap.ttl`  
	OWL/RDF ontology (Turtle) for AIDOC-AP, including classes and properties to describe:
	- AI systems, models, datasets and other artifacts
	- lifecycle activities and agents (provider, deployer, auditor, etc.)
	- documentation artifacts relevant to Annex IV (e.g., risk documents, datasheets, visual documentation, transparency measures)

- `annex_4.ttl`  
	Extracted **Annex IV requirements** as a separate ontology, with:
	- 28 requirements as `aiact:Requirement`
	- textual descriptions (`dcterms:description`) and lifecycle phase annotations
	- associated **competency questions** that express what a knowledge graph should be able to answer for each requirement

- `reference_ontologies/`  
	Reference ontologies used for validation and alignment (e.g. AIRO, PROV-O, MLS, DCAT3, DQV, VAIR, MEX). See also the original ontology specifications:
	- AIRO: <https://w3id.org/airo>
	- PROV-O: <https://www.w3.org/TR/prov-o/>
	- MLS: <https://github.com/ML-Schema/core>
	- DCAT3: <https://www.w3.org/TR/vocab-dcat-3/>
	- DQV: <https://www.w3.org/TR/vocab-dqv/>
	- VAIR: <https://w3id.org/vair>
	- MEX: <http://mex.aksw.org/>

- `reports/`  
	Generated outputs from the scripts:
	- `alignment_structural/*.csv`: structural alignments between AIDOC-AP and reference ontologies
	- `alignment_semantic/*.ttl`: semantic alignments (LLM-supported) as RDF
	- `semantic_mapping.ttl` / `.json`: coverage assessment of AIDOC-AP against Annex IV requirements

- `docs/`  
	Generated ontology documentation (HTML), including:
	- class and property overviews
	- requirement views and coverage reports
	- alignment views

- `scripts/`  
	Python scripts for extracting entities, computing alignments and assessing coverage with respect to Annex IV:
	- `extract_entities.py`: extract AIDOC-AP entities into CSV
	- `alignment_structural.py`: compute structural alignments between AIDOC-AP and reference ontologies
	- `alignment_semantic.py`: compute LLM-based semantic alignments
	- `semantic_mapping.py`: Annex-IV coverage analysis using an LLM
	- `generate_alignment_manifest.py`: generate a manifest of all alignment files


## Methodology (Annex IV Focus)

The design of AIDOC-AP is driven by the technical documentation obligations in **Annex IV of the EU AI Act**. In particular:

- **Requirements modelling**  
	Annex IV requirements are represented in `annex_4.ttl` as `aiact:Requirement` with textual descriptions and lifecycle annotations. Each requirement is linked to one or more **competency questions (CQs)** that express what information the documentation should provide.

- **Ontology modelling**  
	AIDOC-AP provides classes and properties so that instances of the ontology can answer these CQs, e.g.:
	- system architecture and software components
	- data requirements and dataset descriptions
	- training, validation and testing data and procedures
	- data quality measures (cleaning, enrichment, labeling)
	- logging, risk, performance and transparency information

- **Alignments to reference ontologies**  
	To ensure interoperability, AIDOC-AP reuses related vocabularies (e.g. PROV-O, MLS, DCAT, DQV, FOAF, SKOS) and aligns key concepts to external ontologies such as AIRO, VAIR, MEX, PROV-O and MLS. Structural alignments are computed in `alignment_structural.py`, while `alignment_semantic.py` uses an LLM to propose semantic correspondences.

- **Annex IV coverage assessment**  
	The `semantic_mapping.py` script uses an LLM to compare each Annex IV requirement with the AIDOC-AP ontology terms. For each requirement, it produces:
	- a coverage score in the range `[0.0, 1.0]`
	- the list of AIDOC-AP terms that contribute to coverage
	- a short textual reasoning
	- suggestions for missing concepts
	These results are stored as DQV quality measurements in RDF and as a JSON file for easier inspection.


## Usage

### Using the ontology in your own KG

Add the following prefixes to your RDF data:

```turtle
@prefix aidoc: <https://w3id.org/aidoc-ap#> .
@prefix aiact: <https://w3id.org/aidoc-ap/requirements#> .
```

You can then:

- instantiate `aidoc:AISystem`, `aidoc:AIModel`, `aidoc:Dataset`, activities and documentation artifacts to describe a concrete AI system;
- use `aiact:Requirement` and the associated competency questions to check which Annex IV items your documentation covers.

### Running the analysis scripts

Assuming a Python virtual environment in `.venv` and dependencies installed:

```bash
cd /Users/sneumaier/Repos/aidoc-ap

# Structural alignments between AIDOC-AP and reference ontologies
.venv/bin/python scripts/alignment_structural.py

# LLM-based semantic alignments
.venv/bin/python scripts/alignment_semantic.py

# Annex IV coverage mapping
.venv/bin/python scripts/semantic_mapping.py
```

Generated results are written to the `reports/` folder.


## Project Context – CERTAIN

AIDOC-AP is developed **within the CERTAIN project** and applied in its use cases and pilots. CERTAIN investigates methods and tools to ensure compliance, transparency and accountability of AI systems. AIDOC-AP serves as the semantic backbone for representing AI system documentation a coverage of Annex IV requirements across different domains.

The project is funded by the European Union's Horizon Europe research and innovation programme HORIZON-CL4-2024-DATA-01-01 under grant agreement No. 101189650.


## Contact

This work is currently maintained by:

- **Sebastian Neumaier**  
	University of Applied Sciences St. Pölten (FH St. Pölten)  
	E-mail: `sebastian.neumaier@ustp.at`  
	GitHub: [sebneu](https://github.com/sebneu)

Please use GitHub issues in this repository for questions, bug reports or suggestions.


## License

- **Code and tooling**: [Apache License 2.0](LICENSE)
- **Ontology and documentation**: LICENSE-CC-BY.txt

Please retain attribution when reusing or modifying this work.
If you use AIDOC-AP in scientific publications or products, please cite it appropriately.
