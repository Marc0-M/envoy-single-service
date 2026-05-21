#!/usr/bin/env bash
set -u

ENV_NAME="${1:-prodb}"
KUBE_CONTEXT="${KUBE_CONTEXT:-}"
GATEWAY_NAMESPACE="${GATEWAY_NAMESPACE:-common-gw-${ENV_NAME}}"
GATEWAY_NAME="${GATEWAY_NAME:-gw-${ENV_NAME}}"
ENVOYPROXY_NAME="${ENVOYPROXY_NAME:-envoy-aws-nlb-service-${ENV_NAME}}"
ENVOY_SYSTEM_NAMESPACE="${ENVOY_SYSTEM_NAMESPACE:-envoy-system}"
ENVOY_GATEWAY_NAMESPACE="${ENVOY_GATEWAY_NAMESPACE:-envoy-gateway-system}"
MANIFEST_DIR="${MANIFEST_DIR:-Header-forwarding-manifests/${ENV_NAME}}"
TAIL_LINES="${TAIL_LINES:-200}"

if [[ -n "$KUBE_CONTEXT" ]]; then
  KUBECTL=(kubectl --context "$KUBE_CONTEXT")
else
  KUBECTL=(kubectl)
fi

section() {
  printf '\n================================================================================\n'
  printf '%s\n' "$1"
  printf '================================================================================\n'
}

run() {
  printf '\n$ %s\n' "$*"
  "$@" 2>&1 || true
}

get_jsonpath() {
  local resource="$1"
  local jsonpath="$2"
  "${KUBECTL[@]}" get $resource -o "jsonpath=${jsonpath}" 2>/dev/null || true
}

print_manifest_if_exists() {
  local file="$1"
  if [[ -f "$file" ]]; then
    printf '\n--- %s ---\n' "$file"
    sed -n '1,220p' "$file"
  else
    printf '\n[WARN] Expected manifest file not found: %s\n' "$file"
  fi
}

compare_envoyproxy_service_annotations() {
  local svc_name="$1"

  if [[ -z "$svc_name" ]]; then
    printf '[WARN] No generated Envoy Service was found, so annotation comparison was skipped.\n'
    return 0
  fi

  if ! command -v python3 >/dev/null 2>&1; then
    printf '[WARN] python3 not found; skipping exact annotation comparison.\n'
    return 0
  fi

  local envoyproxy_json
  local service_json
  envoyproxy_json="$("${KUBECTL[@]}" -n "$GATEWAY_NAMESPACE" get envoyproxy "$ENVOYPROXY_NAME" -o json 2>/dev/null || true)"
  service_json="$("${KUBECTL[@]}" -n "$ENVOY_SYSTEM_NAMESPACE" get svc "$svc_name" -o json 2>/dev/null || true)"

  if [[ -z "$envoyproxy_json" || -z "$service_json" ]]; then
    printf '[WARN] Could not read EnvoyProxy or Service JSON; skipping exact annotation comparison.\n'
    return 0
  fi

  ENVOYPROXY_JSON="$envoyproxy_json" SERVICE_JSON="$service_json" python3 - <<'PY'
import json
import os

ep = json.loads(os.environ["ENVOYPROXY_JSON"])
svc = json.loads(os.environ["SERVICE_JSON"])

desired = (
    ep.get("spec", {})
      .get("provider", {})
      .get("kubernetes", {})
      .get("envoyService", {})
      .get("annotations", {})
) or {}
actual = svc.get("metadata", {}).get("annotations", {}) or {}

keys = sorted(desired)
print("Expected EnvoyProxy annotations vs generated Service annotations:")
if not keys:
    print("[WARN] EnvoyProxy has no spec.provider.kubernetes.envoyService.annotations entries.")

for key in keys:
    expected = str(desired.get(key, ""))
    current = str(actual.get(key, ""))
    status = "OK" if expected == current else "MISMATCH"
    print("%-8s %s" % (status, key))
    if status != "OK":
        print("         expected: %s" % expected)
        print("         actual:   %s" % (current if current else "<missing>"))
PY
}

section "Diagnostic Context"
printf 'Date:                    %s\n' "$(date)"
printf 'Target env:              %s\n' "$ENV_NAME"
printf 'Kube context override:   %s\n' "${KUBE_CONTEXT:-<current kubectl context>}"
printf 'Gateway namespace:       %s\n' "$GATEWAY_NAMESPACE"
printf 'Gateway name:            %s\n' "$GATEWAY_NAME"
printf 'EnvoyProxy name:         %s\n' "$ENVOYPROXY_NAME"
printf 'Envoy system namespace:  %s\n' "$ENVOY_SYSTEM_NAMESPACE"
printf 'Envoy gateway namespace: %s\n' "$ENVOY_GATEWAY_NAMESPACE"
printf 'Manifest dir:            %s\n' "$MANIFEST_DIR"

run "${KUBECTL[@]}" config current-context
run "${KUBECTL[@]}" version --short

section "Local Manifests For This Environment"
print_manifest_if_exists "${MANIFEST_DIR}/00-envoyproxy.yaml"
print_manifest_if_exists "${MANIFEST_DIR}/01-clienttrafficpolicy.yaml"
print_manifest_if_exists "${MANIFEST_DIR}/02-envoyextensionpolicy.yaml"

section "Required CRDs"
for crd in \
  gateways.gateway.networking.k8s.io \
  httproutes.gateway.networking.k8s.io \
  referencegrants.gateway.networking.k8s.io \
  backendtlspolicies.gateway.networking.k8s.io \
  envoyproxies.gateway.envoyproxy.io \
  clienttrafficpolicies.gateway.envoyproxy.io \
  envoyextensionpolicies.gateway.envoyproxy.io; do
  run "${KUBECTL[@]}" get crd "$crd"
done

section "Namespaces"
run "${KUBECTL[@]}" get ns "$GATEWAY_NAMESPACE"
run "${KUBECTL[@]}" get ns "$ENVOY_SYSTEM_NAMESPACE"
run "${KUBECTL[@]}" get ns "$ENVOY_GATEWAY_NAMESPACE"

section "GatewayClass And Envoy Gateway Controller"
run "${KUBECTL[@]}" get gatewayclass -o wide
run "${KUBECTL[@]}" get pods -n "$ENVOY_GATEWAY_NAMESPACE" -o wide
run "${KUBECTL[@]}" get deploy -n "$ENVOY_GATEWAY_NAMESPACE" -o wide

section "Gateway Resource"
run "${KUBECTL[@]}" -n "$GATEWAY_NAMESPACE" get gateway "$GATEWAY_NAME" -o yaml
run "${KUBECTL[@]}" -n "$GATEWAY_NAMESPACE" describe gateway "$GATEWAY_NAME"

section "Gateway EnvoyProxy Attachment Check"
ATTACH_GROUP="$(get_jsonpath "-n $GATEWAY_NAMESPACE gateway $GATEWAY_NAME" '{.spec.infrastructure.parametersRef.group}')"
ATTACH_KIND="$(get_jsonpath "-n $GATEWAY_NAMESPACE gateway $GATEWAY_NAME" '{.spec.infrastructure.parametersRef.kind}')"
ATTACH_NAME="$(get_jsonpath "-n $GATEWAY_NAMESPACE gateway $GATEWAY_NAME" '{.spec.infrastructure.parametersRef.name}')"
printf 'Gateway parametersRef.group: %s\n' "${ATTACH_GROUP:-<missing>}"
printf 'Gateway parametersRef.kind:  %s\n' "${ATTACH_KIND:-<missing>}"
printf 'Gateway parametersRef.name:  %s\n' "${ATTACH_NAME:-<missing>}"

if [[ "$ATTACH_GROUP" == "gateway.envoyproxy.io" && "$ATTACH_KIND" == "EnvoyProxy" && "$ATTACH_NAME" == "$ENVOYPROXY_NAME" ]]; then
  printf '[OK] Gateway is attached to expected EnvoyProxy.\n'
else
  printf '[FAIL] Gateway is not attached to expected EnvoyProxy.\n'
  printf '       Expected: group=gateway.envoyproxy.io kind=EnvoyProxy name=%s\n' "$ENVOYPROXY_NAME"
fi

section "EnvoyProxy Resource"
run "${KUBECTL[@]}" -n "$GATEWAY_NAMESPACE" get envoyproxy "$ENVOYPROXY_NAME" -o yaml
run "${KUBECTL[@]}" -n "$GATEWAY_NAMESPACE" describe envoyproxy "$ENVOYPROXY_NAME"

section "ClientTrafficPolicy And EnvoyExtensionPolicy"
run "${KUBECTL[@]}" -n "$GATEWAY_NAMESPACE" get clienttrafficpolicy trust-all-xff -o yaml
run "${KUBECTL[@]}" -n "$GATEWAY_NAMESPACE" describe clienttrafficpolicy trust-all-xff
run "${KUBECTL[@]}" -n "$GATEWAY_NAMESPACE" get envoyextensionpolicy copy-xff-to-xoff -o yaml
run "${KUBECTL[@]}" -n "$GATEWAY_NAMESPACE" describe envoyextensionpolicy copy-xff-to-xoff

section "Generated Envoy Services"
run "${KUBECTL[@]}" get svc -n "$ENVOY_SYSTEM_NAMESPACE" -o wide
printf '\nServices owned by %s/%s based on labels:\n' "$GATEWAY_NAMESPACE" "$GATEWAY_NAME"
run "${KUBECTL[@]}" get svc -n "$ENVOY_SYSTEM_NAMESPACE" \
  -l "gateway.envoyproxy.io/owning-gateway-name=${GATEWAY_NAME},gateway.envoyproxy.io/owning-gateway-namespace=${GATEWAY_NAMESPACE}" \
  -o wide

SVC_NAME="$("${KUBECTL[@]}" get svc -n "$ENVOY_SYSTEM_NAMESPACE" \
  -l "gateway.envoyproxy.io/owning-gateway-name=${GATEWAY_NAME},gateway.envoyproxy.io/owning-gateway-namespace=${GATEWAY_NAMESPACE}" \
  -o jsonpath='{.items[0].metadata.name}' 2>/dev/null || true)"

if [[ -n "$SVC_NAME" ]]; then
  printf '\nDetected generated Service: %s/%s\n' "$ENVOY_SYSTEM_NAMESPACE" "$SVC_NAME"
  run "${KUBECTL[@]}" -n "$ENVOY_SYSTEM_NAMESPACE" get svc "$SVC_NAME" -o yaml
  run "${KUBECTL[@]}" -n "$ENVOY_SYSTEM_NAMESPACE" describe svc "$SVC_NAME"
else
  printf '\n[FAIL] No generated Envoy Service found for labels owning-gateway-name=%s owning-gateway-namespace=%s\n' "$GATEWAY_NAME" "$GATEWAY_NAMESPACE"
  printf '[INFO] This usually means the Gateway is not programmed, the GatewayClass/controller did not reconcile it, or the Gateway is using a different naming/namespace pattern.\n'
fi

section "Annotation Comparison"
compare_envoyproxy_service_annotations "$SVC_NAME"

section "Generated Envoy Pods"
run "${KUBECTL[@]}" get pods -n "$ENVOY_SYSTEM_NAMESPACE" -o wide
if [[ -n "$SVC_NAME" ]]; then
  SELECTOR="$("${KUBECTL[@]}" -n "$ENVOY_SYSTEM_NAMESPACE" get svc "$SVC_NAME" -o jsonpath='{range $k,$v:=.spec.selector}{printf "%s=%s," $k $v}{end}' 2>/dev/null | sed 's/,$//' || true)"
  printf 'Detected Service selector: %s\n' "${SELECTOR:-<none>}"
  if [[ -n "$SELECTOR" ]]; then
    run "${KUBECTL[@]}" get pods -n "$ENVOY_SYSTEM_NAMESPACE" -l "$SELECTOR" -o wide
  fi
fi

section "HTTPRoutes Referencing Gateway"
run "${KUBECTL[@]}" get httproute -A -o wide
printf '\nPossible routes mentioning %s or %s:\n' "$GATEWAY_NAME" "$GATEWAY_NAMESPACE"
run sh -c "kubectl ${KUBE_CONTEXT:+--context \"$KUBE_CONTEXT\"} get httproute -A -o yaml | grep -n -C 4 -E 'name: ${GATEWAY_NAME}|namespace: ${GATEWAY_NAMESPACE}'"

section "Recent Events"
run "${KUBECTL[@]}" get events -n "$GATEWAY_NAMESPACE" --sort-by=.lastTimestamp
run "${KUBECTL[@]}" get events -n "$ENVOY_SYSTEM_NAMESPACE" --sort-by=.lastTimestamp
run "${KUBECTL[@]}" get events -n "$ENVOY_GATEWAY_NAMESPACE" --sort-by=.lastTimestamp

section "Envoy Gateway Controller Logs"
run "${KUBECTL[@]}" logs -n "$ENVOY_GATEWAY_NAMESPACE" deploy/envoy-gateway --tail="$TAIL_LINES"

section "Quick Summary"
if [[ "$ATTACH_GROUP" == "gateway.envoyproxy.io" && "$ATTACH_KIND" == "EnvoyProxy" && "$ATTACH_NAME" == "$ENVOYPROXY_NAME" ]]; then
  printf '[OK] Gateway EnvoyProxy attachment found.\n'
else
  printf '[FAIL] Gateway EnvoyProxy attachment missing or incorrect.\n'
fi

if [[ -n "$SVC_NAME" ]]; then
  HOSTNAME="$("${KUBECTL[@]}" -n "$ENVOY_SYSTEM_NAMESPACE" get svc "$SVC_NAME" -o jsonpath='{.status.loadBalancer.ingress[0].hostname}' 2>/dev/null || true)"
  IP="$("${KUBECTL[@]}" -n "$ENVOY_SYSTEM_NAMESPACE" get svc "$SVC_NAME" -o jsonpath='{.status.loadBalancer.ingress[0].ip}' 2>/dev/null || true)"
  printf '[OK] Generated Envoy Service found: %s/%s\n' "$ENVOY_SYSTEM_NAMESPACE" "$SVC_NAME"
  printf '     LoadBalancer hostname: %s\n' "${HOSTNAME:-<missing>}"
  printf '     LoadBalancer ip:       %s\n' "${IP:-<missing>}"
  if [[ -z "$HOSTNAME" && -z "$IP" ]]; then
    printf '[FAIL] Service exists but has no LoadBalancer endpoint yet. Check Service events and AWS Load Balancer Controller/Auto Mode events.\n'
  fi
else
  printf '[FAIL] Generated Envoy Service was not found.\n'
fi

printf '\nDone. Share this full output when asking for help.\n'
