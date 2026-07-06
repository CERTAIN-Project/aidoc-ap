#!/usr/bin/env bash
# Wartet bis (a) ein Apertus-Modell am Ollama-Server registriert ist und
# (b) kein anderer Coverage-Lauf mehr läuft, und startet dann dessen
# Coverage-Zellen. Gibt nach 12 h auf.
set -euo pipefail
cd "$(dirname "$0")/.."
set -a; [ -f .env ] && source .env; set +a

DEADLINE=$(( $(date +%s) + 12*3600 ))
MODEL=""

while [ "$(date +%s)" -lt "$DEADLINE" ]; do
    MODEL=$(curl -s -H "Authorization: Bearer ${OLLAMA_API_KEY:-}" \
        "$OLLAMA_URL/api/tags" | python3 -c "
import json,sys
try:
    for m in json.load(sys.stdin)['models']:
        if 'apertus' in m['name'].lower():
            print(m['name']); break
except Exception:
    pass" || true)
    if [ -n "$MODEL" ]; then
        if pgrep -f "run_coverage_multirun" > /dev/null; then
            echo "$(date '+%H:%M') apertus ($MODEL) da, aber Hauptlauf aktiv — warte..."
        else
            echo "$(date '+%H:%M') starte Coverage für $MODEL"
            COVERAGE_MODELS="$MODEL" ./scripts/run_experiments.sh coverage
            exit 0
        fi
    else
        echo "$(date '+%H:%M') apertus noch nicht registriert"
    fi
    sleep 600
done
echo "Timeout: Apertus war nach 12 h nicht verfügbar."
exit 1
