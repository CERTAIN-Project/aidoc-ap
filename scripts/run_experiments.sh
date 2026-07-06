#!/usr/bin/env bash
# Re-run of the AIDOC-AP experiments for the SWJ revision.
#
# Prerequisites: Ollama server reachable (see .env), models pulled.
# Usage:
#   ./scripts/run_experiments.sh preflight   # check server, models, inputs
#   ./scripts/run_experiments.sh alignment   # structural + semantic alignment (incl. DPV)
#   ./scripts/run_experiments.sh coverage    # full coverage matrix (model x iter x temp x run)
#   ./scripts/run_experiments.sh all

set -euo pipefail
cd "$(dirname "$0")/.."

PYTHON=".venv/bin/python"
[ -x "$PYTHON" ] || PYTHON="python3"
export PYTHONUNBUFFERED=1

# load .env for OLLAMA_URL
set -a; [ -f .env ] && source .env; set +a
OLLAMA_URL="${OLLAMA_URL:-http://localhost:11434}"

MODELS="${COVERAGE_MODELS:-gemma3:27b,llama3.3:70b,gpt-oss:120b}"
ALIGNMENT_MODEL="${ALIGNMENT_MODEL:-gemma3:27b}"
# lexical candidate threshold: deliberately below the 0.75 semantic threshold so
# that the LLM stage (and the below-threshold curation for the false-negative
# analysis) sees a wider candidate pool
STRUCTURAL_THRESHOLD="${STRUCTURAL_THRESHOLD:-0.6}"

preflight() {
    echo "== Preflight =="
    echo "-- Ollama server: $OLLAMA_URL"
    if ! curl -sf --connect-timeout 5 -H "Authorization: Bearer ${OLLAMA_API_KEY:-}" \
            "$OLLAMA_URL/api/tags" > /tmp/ollama_tags.json; then
        echo "FEHLER: Ollama-Server nicht erreichbar (VPN/FH-Netz bzw. OpenWebUI-Key prüfen)"; exit 1
    fi
    echo "   erreichbar."
    echo "-- Modelle:"
    for m in ${MODELS//,/ } "$ALIGNMENT_MODEL"; do
        if grep -q "\"$m\"" /tmp/ollama_tags.json; then
            echo "   [ok] $m"
        else
            echo "   [FEHLT] $m  -> auf dem Server: ollama pull $m"
        fi
    done
    echo "-- Inputs:"
    for f in annex_4.ttl aidoc-ap.ttl reports/aidoc-entities.csv \
             reports/experiments/entities_iter1_gemma3_27b.csv \
             reference_ontologies/dpv.ttl reference_ontologies/dpv-aiact.ttl; do
        [ -f "$f" ] && echo "   [ok] $f" || echo "   [FEHLT] $f"
    done
    echo "-- Python deps:"
    $PYTHON -c "import rdflib, pandas, openai, dotenv" && echo "   [ok] rdflib/pandas/openai/dotenv"
}

alignment() {
    echo "== Structural (lexical) alignment, threshold $STRUCTURAL_THRESHOLD =="
    $PYTHON scripts/alignment_structural.py --threshold "$STRUCTURAL_THRESHOLD"
    echo "== Semantic alignment (model: $ALIGNMENT_MODEL, T=0, threshold 0.75) =="
    OLLAMA_MODEL="$ALIGNMENT_MODEL" LLM_TEMPERATURE=0.0 \
        $PYTHON scripts/alignment_semantic.py
    echo "-> Kurations-CSVs: reports/alignment_semantic/*-curation.csv"
    echo "   (Protokoll: publication/curation_protocol.md; Auswertung: scripts/analyze_curation.py)"
}

coverage() {
    echo "== Coverage matrix: models=$MODELS, iters=\${ITERATIONS:-1,2,3}, T=\${TEMPERATURES:-0.0,1.0}, n=\${N_RUNS:-3} =="
    COVERAGE_MODELS="$MODELS" $PYTHON scripts/run_coverage_multirun.py
}

case "${1:-all}" in
    preflight) preflight ;;
    alignment) preflight && alignment ;;
    coverage)  preflight && coverage ;;
    all)       preflight && alignment && coverage ;;
    *) echo "Usage: $0 {preflight|alignment|coverage|all}"; exit 1 ;;
esac
