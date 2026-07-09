# Coverage evaluation — multi-run matrix (revision experiments)

LLM-estimated Annex IV coverage, re-run for the SWJ revision with the corrected
setup: **temperature 0** (plus a temperature-1.0 comparison), **three seeded
runs** per cell (seeds 43–45), and each requirement evaluated in an
**independent single-turn request** (no accumulated context).

- `coverage_multirun_summary.csv` — one row per (model, iteration, temperature,
  run) with the average coverage score over all 22 requirements; source of the
  coverage tables in the paper.
- `semantic_mapping_<model>_iter<i>_T<t>_run<r>.json` — per-requirement scores,
  matched terms and explanations for each individual run.

Models (served locally via Ollama): Gemma 3 27B (Q4_K_M), Llama 3.3 70B
(Q4_K_M), GPT-OSS 120B (MXFP4), Apertus 70B (Q4_K_M).

Reproduce with `scripts/run_experiments.sh` (see `.env` for the server
configuration); the evaluator itself is `scripts/semantic_mapping.py`.

The sibling `../semantic_mapping_iter*.ttl` files are the original
(pre-revision) single runs kept for reference.
