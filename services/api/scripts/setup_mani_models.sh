#!/usr/bin/env bash
# Sets up the local Ollama models for Mani Bond: the embedding model, and a chat model with a
# 16,384-token context. The chat call goes through Ollama's OpenAI-compatible endpoint, which ignores
# a per-request context size, so the size is built into a model of its own. Run it once per machine.
#
#   scripts/setup_mani_models.sh                                  # qwen3:14b -> qwen3-14b-16k (the default)
#   scripts/setup_mani_models.sh gemma4:12b-it-q8_0 gemma4-12b-16k   # another base model and a name for it
#
# Then point Mani at the new name with MANI_CHAT_MODEL (the first form needs nothing: it is the default).
set -euo pipefail

BASE="${1:-qwen3:14b}"
NAME="${2:-qwen3-14b-16k}"

ollama pull qwen3-embedding:8b
ollama pull "$BASE"
MODELFILE="$(mktemp)"
trap 'rm -f "$MODELFILE"' EXIT
printf 'FROM %s\nPARAMETER num_ctx 16384\n' "$BASE" > "$MODELFILE"
ollama create "$NAME" -f "$MODELFILE"
ollama list | grep -E "$NAME|qwen3-embedding"
