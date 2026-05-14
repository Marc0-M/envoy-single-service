#!/usr/bin/env bash
set -euo pipefail

NAMESPACE="envoy-system"
DRY_RUN=false

TARGET_ANNOTATION_KEY="service.beta.kubernetes.io/aws-load-balancer-target-group-attributes"
TARGET_ANNOTATION_VALUE="preserve_client_ip.enabled=true"

REQUIRED_ANNOTATION_KEYS=(
  "service.beta.kubernetes.io/aws-load-balancer-access-log-enabled"
  "service.beta.kubernetes.io/aws-load-balancer-access-log-s3-bucket-name"
  "service.beta.kubernetes.io/aws-load-balancer-access-log-s3-bucket-prefix"
  "service.beta.kubernetes.io/aws-load-balancer-backend-protocol"
  "service.beta.kubernetes.io/aws-load-balancer-cross-zone-load-balancing-enabled"
  "service.beta.kubernetes.io/aws-load-balancer-internal"
  "service.beta.kubernetes.io/aws-load-balancer-security-groups"
  "service.beta.kubernetes.io/aws-load-balancer-ssl-cert"
  "service.beta.kubernetes.io/aws-load-balancer-ssl-ports"
  "service.beta.kubernetes.io/aws-load-balancer-subnets"
  "service.beta.kubernetes.io/aws-load-balancer-type"
)

usage() {
  cat <<'EOF'
Usage:
  ./annotate_envoy_services_preserve_client_ip.sh [--dry-run]

What it does:
  - scans all Services in the target namespace
  - selects only Services that already have the standard AWS NLB annotations used by this repo
  - adds or updates:
      service.beta.kubernetes.io/aws-load-balancer-target-group-attributes=preserve_client_ip.enabled=true
  - prints a per-Service status report and a final summary

Options:
  --dry-run           report what would be changed without patching
  -h, --help          show this help
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --dry-run)
      DRY_RUN=true
      shift
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "Unknown argument: $1" >&2
      usage >&2
      exit 1
      ;;
  esac
done

if ! command -v kubectl >/dev/null 2>&1; then
  echo "kubectl is required but was not found in PATH." >&2
  exit 1
fi

if ! command -v python3 >/dev/null 2>&1; then
  echo "python3 is required but was not found in PATH." >&2
  exit 1
fi

KUBECTL_ARGS=(-n "$NAMESPACE")

services_json="$(kubectl "${KUBECTL_ARGS[@]}" get svc -o json)"

planned_rows=()
while IFS= read -r row; do
  planned_rows+=("$row")
done < <(
  SERVICES_JSON="$services_json" \
  REQUIRED_KEYS="$(printf '%s\n' "${REQUIRED_ANNOTATION_KEYS[@]}")" \
  TARGET_KEY="$TARGET_ANNOTATION_KEY" \
  TARGET_VALUE="$TARGET_ANNOTATION_VALUE" \
  python3 - <<'PY'
import json
import os

services_json = os.environ["SERVICES_JSON"]
required_keys = [line.strip() for line in os.environ["REQUIRED_KEYS"].splitlines() if line.strip()]
target_key = os.environ["TARGET_KEY"]
target_value = os.environ["TARGET_VALUE"]

data = json.loads(services_json)
items = sorted(data.get("items", []), key=lambda item: item["metadata"]["name"])

for item in items:
    name = item["metadata"]["name"]
    annotations = item["metadata"].get("annotations", {}) or {}
    missing = [key for key in required_keys if key not in annotations]
    current = annotations.get(target_key, "")

    if missing:
        action = "skip"
        status = "skipped_missing_required_annotations"
        detail = ",".join(missing)
        desired = current
    else:
        parts = [part.strip() for part in current.split(",") if part.strip()]
        updated_parts = []
        found_preserve_client_ip = False

        for part in parts:
            if part.startswith("preserve_client_ip.enabled="):
                updated_parts.append(target_value)
                found_preserve_client_ip = True
            else:
                updated_parts.append(part)

        if not found_preserve_client_ip:
            updated_parts.append(target_value)

        desired = ",".join(updated_parts)

        if desired == current:
            action = "noop"
            status = "already_configured"
            detail = current
        else:
            action = "patch"
            status = "eligible"
            detail = current

    print("\t".join([name, action, status, detail, desired]))
PY
)

if [[ ${#planned_rows[@]} -eq 0 ]]; then
  echo "No Services found in namespace ${NAMESPACE}."
  exit 0
fi

printf "Namespace: %s\n" "$NAMESPACE"
printf "Mode:      %s\n\n" "$([[ "$DRY_RUN" == true ]] && echo "dry-run" || echo "apply")"

printf "%-64s %-34s %s\n" "SERVICE" "STATUS" "DETAIL"
printf "%-64s %-34s %s\n" "-------" "------" "------"

patched_count=0
already_count=0
would_patch_count=0
skipped_count=0
failed_count=0

for row in "${planned_rows[@]}"; do
  IFS=$'\t' read -r service_name action status detail desired_value <<<"$row"
  final_status="$status"
  final_detail="$detail"

  if [[ "$action" == "patch" ]]; then
    if [[ "$DRY_RUN" == true ]]; then
      final_status="would_patch"
      final_detail="$desired_value"
      ((would_patch_count+=1))
    else
      if kubectl "${KUBECTL_ARGS[@]}" annotate svc "$service_name" \
        "${TARGET_ANNOTATION_KEY}=${desired_value}" \
        --overwrite >/dev/null 2>&1; then
        current_value="$(
          kubectl "${KUBECTL_ARGS[@]}" get svc "$service_name" \
            -o go-template="{{index .metadata.annotations \"$TARGET_ANNOTATION_KEY\"}}"
        )"
        if [[ "$current_value" == "$desired_value" ]]; then
          final_status="patched"
          final_detail="$current_value"
          ((patched_count+=1))
        else
          final_status="patch_verification_failed"
          final_detail="${current_value:-<empty>}"
          ((failed_count+=1))
        fi
      else
        final_status="patch_failed"
        final_detail="$desired_value"
        ((failed_count+=1))
      fi
    fi
  elif [[ "$action" == "noop" ]]; then
    ((already_count+=1))
  else
    ((skipped_count+=1))
    if [[ -n "$detail" ]]; then
      missing_count="$(awk -F',' '{print NF}' <<<"$detail")"
      final_detail="${missing_count} missing required annotations"
    else
      final_detail="missing required annotations"
    fi
  fi

  printf "%-64s %-34s %s\n" "$service_name" "$final_status" "$final_detail"
done

echo
printf "Summary: scanned=%d patched=%d already_configured=%d would_patch=%d skipped=%d failed=%d\n" \
  "${#planned_rows[@]}" \
  "$patched_count" \
  "$already_count" \
  "$would_patch_count" \
  "$skipped_count" \
  "$failed_count"
