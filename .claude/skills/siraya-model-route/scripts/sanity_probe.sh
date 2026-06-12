#!/usr/bin/env bash
# Sanity-probe Siraya Model Router before a real session.
#
# Checks:
#   1. SIRAYA_API_KEY is set
#   2. /v1/models returns 200 (auth + reachability OK)
#   3. Optional model arg is in the registry against this key
#
# Usage:
#   ./sanity_probe.sh                       # auth + reachability only
#   ./sanity_probe.sh deepseek-v4-flash     # also verify a specific model is available

set -euo pipefail

BASE_URL="${SIRAYA_BASE_URL:-https://llm.siraya.ai}"
MODEL_TO_CHECK="${1:-}"

if [[ -z "${SIRAYA_API_KEY:-}" ]]; then
  echo "ERROR: SIRAYA_API_KEY is not set." >&2
  exit 1
fi

# Auth + reachability
tmp="$(mktemp)"
http_code="$(curl -s -o "$tmp" -w "%{http_code}" \
  "$BASE_URL/v1/models" \
  -H "Authorization: Bearer $SIRAYA_API_KEY")"

if [[ "$http_code" != "200" ]]; then
  echo "ERROR: /v1/models returned HTTP $http_code" >&2
  cat "$tmp" >&2
  rm -f "$tmp"
  exit 1
fi

echo "OK  auth + reachability ($BASE_URL)"

# Optional: check a model ID
if [[ -n "$MODEL_TO_CHECK" ]]; then
  if grep -q "\"id\": *\"$MODEL_TO_CHECK\"" "$tmp"; then
    echo "OK  model registered: $MODEL_TO_CHECK"
  else
    echo "WARN model not found in registry: $MODEL_TO_CHECK" >&2
    echo "     (the key may not have access, or the ID is mistyped)" >&2
    rm -f "$tmp"
    exit 2
  fi
fi

rm -f "$tmp"
