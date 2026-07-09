# Empirical competency-question validation

LLM-independent coverage measure: all 50 Annex IV competency questions are
executed as SPARQL queries against each instantiated pilot knowledge graph in
`examples/`; a question counts as answered if the query returns a bound result.

- `cq_validation_summary.csv` — answered/50 per knowledge graph.
- `cq_validation_matrix.csv` — full CQ × knowledge-graph matrix (1 = answered).

Reproduce with `python scripts/run_cq_validation.py` (results here were
generated against ontology v1.1 with the class-based IntendedPurpose/Modality
modelling).
