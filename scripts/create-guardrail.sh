#!/usr/bin/env bash
# Create G_strong in the CURRENT account (no member assume-role).
#
#   ./scripts/create-guardrail.sh
#
# Writes GUARDRAIL_ID / VERSION to stdout. Copy into .env as GASC_GUARDRAIL_ID.
set -euo pipefail

die() { echo "error: $*" >&2; exit 1; }

REGION="${AWS_REGION:-us-east-1}"
NAME="${GASC_GUARDRAIL_NAME:-gasc-strong}"
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
POLICY="${ROOT}/scripts/guardrail-content-policy.json"

command -v aws >/dev/null || die "aws CLI required"
[[ -f "${POLICY}" ]] || die "missing ${POLICY}"

echo "Caller:"
aws sts get-caller-identity --output table
echo

existing="$(aws bedrock list-guardrails --region "${REGION}" \
  --query "guardrails[?name=='${NAME}'].id | [0]" --output text 2>/dev/null || true)"

if [[ -n "${existing}" && "${existing}" != "None" ]]; then
  GID="${existing}"
  echo "Reusing guardrail ${NAME} id=${GID}"
else
  echo "Creating guardrail ${NAME} in ${REGION}…"
  GID="$(aws bedrock create-guardrail \
    --region "${REGION}" \
    --name "${NAME}" \
    --description "GASC G_strong. Freeze filters after E0b." \
    --blocked-input-messaging "This request was blocked by the shared safety guardrail." \
    --blocked-outputs-messaging "This request was blocked by the shared safety guardrail." \
    --content-policy-config "file://${POLICY}" \
    --query guardrailId --output text)"
  echo "Created ${GID}"
fi

VER="$(aws bedrock create-guardrail-version \
  --region "${REGION}" \
  --guardrail-identifier "${GID}" \
  --description gasc-e0 \
  --query version --output text 2>/dev/null || true)"
if [[ -z "${VER}" || "${VER}" == "None" ]]; then
  VER="$(aws bedrock list-guardrails --region "${REGION}" \
    --query "guardrails[?id=='${GID}'].version | [0]" --output text)"
fi
VER="${VER:-DRAFT}"

echo
echo "Put these in .env:"
echo "GASC_GUARDRAIL_ID=${GID}"
echo "GASC_GUARDRAIL_VERSION=${VER}"
