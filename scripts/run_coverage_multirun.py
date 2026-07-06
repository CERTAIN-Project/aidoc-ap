"""Multi-run harness for the LLM-based coverage evaluation (semantic_mapping.py).

Runs the full experiment matrix
    model x ontology iteration x temperature x run
with each run in a fresh process (and each requirement in a fresh single-turn
request), then aggregates mean and standard deviation of the coverage scores.

The temperature sweep (default: 0.0 and 1.0) quantifies the effect of the
sampling temperature on coverage-score stability, directly addressing the
reviewers' questions about the original temperature-1.0 setting.

Usage:
    python scripts/run_coverage_multirun.py

Configuration via environment variables (or .env):
    COVERAGE_MODELS   comma-separated Ollama models
                      (default: "gemma3:27b,llama3.3:70b,gpt-oss:120b")
    ITERATIONS        comma-separated ontology iterations (default: "1,2,3");
                      iteration k uses the archived entity catalogue
                      reports/experiments/entities_iter<k>_gemma3_27b.csv
                      (identical across models); "current" uses
                      reports/aidoc-entities.csv
    TEMPERATURES      comma-separated temperatures (default: "0.0,1.0")
    N_RUNS            runs per cell (default: 3)
    OLLAMA_URL        Ollama endpoint (default: http://localhost:11434)

Outputs:
    reports/semantic_mapping_<model>_iter<k>_T<t>_run<i>.json / .ttl  (per run)
    reports/coverage_multirun_summary.csv                             (aggregated)
"""

import csv
import json
import os
import re
import statistics
import subprocess
import sys

from dotenv import load_dotenv
load_dotenv()

MODELS = [m.strip() for m in os.getenv(
    "COVERAGE_MODELS", "gemma3:27b,llama3.3:70b,gpt-oss:120b").split(",") if m.strip()]
ITERATIONS = [it.strip() for it in os.getenv("ITERATIONS", "1,2,3").split(",") if it.strip()]
TEMPERATURES = [t.strip() for t in os.getenv("TEMPERATURES", "0.0,1.0").split(",") if t.strip()]
N_RUNS = int(os.getenv("N_RUNS", "3"))

SUMMARY_FILE = "reports/coverage_multirun_summary.csv"
SCRIPT = os.path.join(os.path.dirname(__file__), "semantic_mapping.py")


def sanitize(s: str) -> str:
    return re.sub(r"[^A-Za-z0-9]+", "_", s).strip("_")


def entity_file(iteration: str) -> str:
    if iteration == "current":
        return "reports/aidoc-entities.csv"
    # the archived per-iteration catalogues are identical across models
    return f"reports/experiments/entities_iter{iteration}_gemma3_27b.csv"


def main():
    for it in ITERATIONS:
        if not os.path.exists(entity_file(it)):
            sys.exit(f"Entity catalogue for iteration '{it}' not found: {entity_file(it)}")

    cells = [(m, it, t, i)
             for m in MODELS for it in ITERATIONS
             for t in TEMPERATURES for i in range(1, N_RUNS + 1)]
    print(f"Experiment matrix: {len(MODELS)} models x {len(ITERATIONS)} iterations "
          f"x {len(TEMPERATURES)} temperatures x {N_RUNS} runs = {len(cells)} runs")

    run_files = {}  # (model, iteration, temperature, run_idx) -> json path

    for model, it, temp, i in cells:
        tag = f"{sanitize(model)}_iter{it}_T{sanitize(temp)}_run{i}"
        json_out = f"reports/semantic_mapping_{tag}.json"
        if os.path.exists(json_out):
            print(f"[skip] {json_out} already exists")
            run_files[(model, it, temp, i)] = json_out
            continue

        env = os.environ.copy()
        env.update({
            "PYTHONUNBUFFERED": "1",
            "OLLAMA_MODEL": model,
            "RUN_TAG": tag,
            "ENTITY_FILE": entity_file(it),
            "LLM_TEMPERATURE": temp,
            # vary the seed across runs so that run-to-run variance is
            # meaningful even at low temperature
            "LLM_SEED": str(42 + i),
        })
        print(f"[run ] model={model} iter={it} T={temp} run={i}")
        result = subprocess.run([sys.executable, SCRIPT], env=env)
        if result.returncode != 0:
            print(f"[fail] model={model} iter={it} T={temp} run={i} "
                  f"exited with {result.returncode}")
            continue
        run_files[(model, it, temp, i)] = json_out

    # ========== AGGREGATION ==========
    per_cell = {}         # (model, iteration, temperature) -> per-run average coverage
    per_requirement = {}  # (model, iteration, temperature, req_id) -> scores

    n_errors = 0
    for (model, it, temp, i), path in run_files.items():
        if not os.path.exists(path):
            continue
        with open(path, encoding="utf-8") as f:
            results = json.load(f)
        # exclude requirements whose evaluation failed (recorded as coverage 0
        # with an "Error:" reasoning) so they do not distort the aggregates
        errors = [r for r in results if str(r.get("reasoning", "")).startswith("Error")]
        if errors:
            n_errors += len(errors)
            print(f"[warn] {path}: {len(errors)} failed requirement evaluations excluded")
        results = [r for r in results if r not in errors]
        scores = [float(r.get("coverage_score", 0)) for r in results]
        if not scores:
            continue
        per_cell.setdefault((model, it, temp), []).append(sum(scores) / len(scores))
        for r in results:
            key = (model, it, temp, r["requirement_id"])
            per_requirement.setdefault(key, []).append(float(r.get("coverage_score", 0)))

    os.makedirs("reports", exist_ok=True)
    with open(SUMMARY_FILE, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["level", "model", "iteration", "temperature", "requirement_id",
                         "n", "mean_coverage", "stdev_coverage", "min", "max"])
        for (model, it, temp), runs in sorted(per_cell.items()):
            writer.writerow([
                "cell", model, it, temp, "", len(runs),
                round(statistics.mean(runs), 4),
                round(statistics.stdev(runs), 4) if len(runs) > 1 else 0.0,
                round(min(runs), 4), round(max(runs), 4),
            ])
        for (model, it, temp, req_id), scores in sorted(per_requirement.items()):
            writer.writerow([
                "requirement", model, it, temp, req_id, len(scores),
                round(statistics.mean(scores), 4),
                round(statistics.stdev(scores), 4) if len(scores) > 1 else 0.0,
                round(min(scores), 4), round(max(scores), 4),
            ])

    if n_errors:
        print(f"\n⚠️  {n_errors} failed requirement evaluations were excluded; "
              f"re-run the affected cells (delete their JSON files) for complete data.")
    print(f"\n✅ Summary written to {SUMMARY_FILE}")
    for (model, it, temp), runs in sorted(per_cell.items()):
        sd = statistics.stdev(runs) if len(runs) > 1 else 0.0
        print(f"  {model} iter{it} T={temp}: mean={statistics.mean(runs):.4f} "
              f"stdev={sd:.4f} over {len(runs)} runs")


if __name__ == "__main__":
    main()
