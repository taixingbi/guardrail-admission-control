#!/usr/bin/env bash
# Direct Bedrock smoke (no Lambda).
#
#   ./scripts/smoke-bedrock.sh
#   ./scripts/smoke-bedrock.sh nova-micro
#   GASC_GUARDRAIL_ID=xx ./scripts/smoke-bedrock.sh apply-guardrail
set -euo pipefail

die() { echo "error: $*" >&2; exit 1; }

REGION="${AWS_REGION:-us-east-1}"
GLIGHT="${GASC_GLIGHT_MODEL:-us.amazon.nova-micro-v1:0}"
LLM="${GASC_LLM_MODEL:-us.meta.llama4-maverick-17b-instruct-v1:0}"
GID="${GASC_GUARDRAIL_ID:-}"
GVER="${GASC_GUARDRAIL_VERSION:-DRAFT}"

command -v aws >/dev/null || die "aws CLI required"
command -v python3 >/dev/null || die "python3 required"

if [[ -f .env ]]; then
  set -a
  # shellcheck disable=SC1091
  source .env
  set +a
  GID="${GASC_GUARDRAIL_ID:-${GID}}"
  GVER="${GASC_GUARDRAIL_VERSION:-${GVER}}"
  GLIGHT="${GASC_GLIGHT_MODEL:-${GLIGHT}}"
  LLM="${GASC_LLM_MODEL:-${LLM}}"
fi

TARGETS=("${@:-nova-micro apply-guardrail llama4-maverick}")
if [[ "${#}" -eq 0 ]]; then
  TARGETS=(nova-micro apply-guardrail llama4-maverick)
fi

converse() {
  local model="$1"
  echo "=== ${model} ==="
  aws bedrock-runtime converse \
    --region "${REGION}" \
    --model-id "${model}" \
    --messages '[{"role":"user","content":[{"text":"Say hello in one short sentence."}]}]' \
    --inference-config '{"maxTokens":32,"temperature":0}' \
    --query 'output.message.content[0].text' --output text
  echo
}

apply() {
  [[ -n "${GID}" ]] || die "set GASC_GUARDRAIL_ID (run ./scripts/create-guardrail.sh)"
  echo "=== apply-guardrail ${GID} version=${GVER} ==="
  aws bedrock-runtime apply-guardrail \
    --region "${REGION}" \
    --guardrail-identifier "${GID}" \
    --guardrail-version "${GVER}" \
    --source INPUT \
    --content '[{"text":{"text":"Hello"}}]' \
    --query '{action:action,usage:usage}' --output json
  echo
}

echo "Caller:"
aws sts get-caller-identity --output table
echo

for t in "${TARGETS[@]}"; do
  case "${t}" in
    nova-micro|g_light) converse "${GLIGHT}" ;;
    llama4-maverick|llama4|llm) converse "${LLM}" ;;
    apply-guardrail|g_strong|guardrail) apply ;;
    *) die "unknown target ${t}" ;;
  esac
done
