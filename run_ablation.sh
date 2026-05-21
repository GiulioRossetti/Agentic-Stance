#!/usr/bin/env bash
# run_ablation.sh — Run all four memory conditions for one topic, then generate all plots.
#
# Usage:
#   bash run_ablation.sh                        # uses TOPIC from .env (default: immigration)
#   bash run_ablation.sh climate                # run climate topic
#   bash run_ablation.sh immigration 100        # immigration, 100 iterations
#   bash run_ablation.sh immigration 50 1,2,3   # three seeds, comma-separated
#
# Output: data/{topic}/{condition}/   (single seed)
#         data/{topic}/seed_{n}/{condition}/  (multiple seeds)
# Plots:  data/{topic}/plots/
#
# To add a new topic: create topics/{slug}.py, then run:
#   bash run_ablation.sh {slug}

set -e

# ── Arguments ──────────────────────────────────────────────────────────────────
TOPIC_ARG="${1:-}"
N_ITERATIONS="${2:-50}"
SEEDS_ARG="${3:-42}"

# Resolve topic slug
if [ -n "$TOPIC_ARG" ]; then
    TOPIC_SLUG="$TOPIC_ARG"
else
    TOPIC_SLUG=$(grep -E '^TOPIC=' .env 2>/dev/null | cut -d= -f2- | awk '{print $1}')
    TOPIC_SLUG="${TOPIC_SLUG:-immigration}"
fi

# ── Settings (override any via env vars) ───────────────────────────────────────
PYTHON=".venv/bin/python"
LLM_PROVIDER="${LLM_PROVIDER:-ollama}"
LLM_MODEL="${LLM_MODEL:-llama3.2}"
N_AGENTS="${N_AGENTS:-12}"
MIN_TURNS="${MIN_TURNS:-2}"
MAX_TURNS="${MAX_TURNS:-5}"
CLOCK_ADVANCE_HOURS="${CLOCK_ADVANCE_HOURS:-24}"
CONDITIONS=("no_kg" "general_only" "tom_only" "full_kg")
IFS=',' read -ra SEEDS <<< "$SEEDS_ARG"

echo ""
echo "========================================================"
echo " GhostKG Opinion Dynamics — Ablation Run"
echo " Topic      : $TOPIC_SLUG"
echo " Iterations : $N_ITERATIONS per condition"
echo " Seeds      : ${SEEDS[*]}"
echo " Model      : $LLM_PROVIDER / $LLM_MODEL"
echo " Conditions : ${CONDITIONS[*]}"
echo "========================================================"

# ── Simulation runs ────────────────────────────────────────────────────────────
for SEED in "${SEEDS[@]}"; do
    for COND in "${CONDITIONS[@]}"; do

        if [ "${#SEEDS[@]}" -gt 1 ]; then
            OUT_DIR="data/${TOPIC_SLUG}/seed_${SEED}/${COND}"
        else
            OUT_DIR="data/${TOPIC_SLUG}/${COND}"
        fi

        echo ""
        echo "  [$COND | seed=$SEED | $(date '+%H:%M:%S')] → $OUT_DIR"

        PYTHONDONTWRITEBYTECODE=1 \
        TOPIC="$TOPIC_SLUG" \
        MEMORY_CONDITION="$COND" \
        OUTPUT_DIR="$OUT_DIR" \
        DB_PATH="${OUT_DIR}/simulation.db" \
        N_AGENTS="$N_AGENTS" \
        N_ITERATIONS="$N_ITERATIONS" \
        MIN_TURNS="$MIN_TURNS" \
        MAX_TURNS="$MAX_TURNS" \
        RANDOM_SEED="$SEED" \
        LLM_PROVIDER="$LLM_PROVIDER" \
        LLM_MODEL="$LLM_MODEL" \
        CLOCK_ADVANCE_HOURS="$CLOCK_ADVANCE_HOURS" \
        $PYTHON src/simulation.py

        echo "  Done: $COND (seed=$SEED)"
    done
done

# ── Plots (single-seed layout only) ───────────────────────────────────────────
if [ "${#SEEDS[@]}" -eq 1 ]; then
    echo ""
    echo "Generating plots → data/${TOPIC_SLUG}/plots/"

    DATA_IN="data/${TOPIC_SLUG}"
    PLOTS_OUT="data/${TOPIC_SLUG}/plots"

    PYTHONDONTWRITEBYTECODE=1 $PYTHON analysis/plots.py \
        --data-dir "$DATA_IN" --output-dir "$PLOTS_OUT"

    for COND in "${CONDITIONS[@]}"; do
        [ -f "${DATA_IN}/${COND}/results.csv" ] && \
        PYTHONDONTWRITEBYTECODE=1 $PYTHON analysis/plots.py \
            --data-dir "$DATA_IN" --output-dir "$PLOTS_OUT" --condition "$COND"
    done
fi

echo ""
echo "All done. Results in data/${TOPIC_SLUG}/"
