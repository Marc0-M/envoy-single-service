#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'USAGE'
Bootstrap Envoy Gateway prerequisites for envoy-single-service.

Creates, per subenvironment:
  - common-gw-<env> namespace
  - gateway TLS Secret in common-gw-<env>
  - Gateway gw-<env> in common-gw-<env>
  - backend CA Secrets in backend namespaces such as annuity-services-<env>

Usage:
  ./bootstrap_envoy_prereqs.sh \
    --env-family accp \
    --tls-crt ./tls.crt \
    --tls-key ./tls.key \
    --ca-crt ./ca.crt \
    --context accp

Common options:
  --env-family <dev|intg|accp|prod|single-env>
  --envs <comma-list>                 Override subenvironment expansion.
  --context <kubectl-context>          Optional kubectl context.
  --tls-crt <path>                     Gateway listener certificate file.
  --tls-key <path>                     Gateway listener private key file.
  --ca-crt <path>                      Backend CA bundle file; key in Secret will be ca.crt.
  --gateway-class <name>               Default: envoy-gateway.
  --gateway-secret <name>              Default: gateway-tls-secret.
  --gateway-name-prefix <prefix>       Default: gw. Creates <prefix>-<env>.
  --create-backend-namespaces          Create backend namespaces if missing. Default: skip missing.
  --backend-secret <group:secret>      Add/override backend CA secret mapping. Repeatable.
  --annotation-file <path>             Optional file of service annotation key=value lines.
  --annotate-service <namespace/name>  Optional Service to annotate. Supports {env}. Repeatable.
  --dry-run                            Use server-side dry-run where possible.
  -h, --help

Default backend CA mappings:
  annuity-services:annuity-backend-ca
  digtran-services:digtran-backend-ca
  document-services:document-backend-ca
  garwin-int-apps:garwin-backend-ca
  garwin-services:garwin-backend-ca
  generic-internal-service:generic-backend-ca
  lifecad-services:lifecad-backend-ca
  portal-services:portal-backend-ca

Annotation file example:
  service.beta.kubernetes.io/aws-load-balancer-access-log-enabled=true
  service.beta.kubernetes.io/aws-load-balancer-access-log-s3-bucket-name=ven-accp-lb-logging
  service.beta.kubernetes.io/aws-load-balancer-access-log-s3-bucket-prefix=k8s-eg-{env}
  service.beta.kubernetes.io/aws-load-balancer-backend-protocol=ssl
  service.beta.kubernetes.io/aws-load-balancer-cross-zone-load-balancing-enabled=true
  service.beta.kubernetes.io/aws-load-balancer-internal=true
  service.beta.kubernetes.io/aws-load-balancer-security-groups=sg-xxxxxxxxxxxxxxxxx
  service.beta.kubernetes.io/aws-load-balancer-ssl-cert=arn:aws:acm:us-east-1:123456789012:certificate/xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
  service.beta.kubernetes.io/aws-load-balancer-ssl-ports=443
  service.beta.kubernetes.io/aws-load-balancer-subnets=subnet-aaa,subnet-bbb
  service.beta.kubernetes.io/aws-load-balancer-type=nlb-ip
USAGE
}

log() {
  printf '[INFO] %s\n' "$*"
}

warn() {
  printf '[WARN] %s\n' "$*" >&2
}

die() {
  printf '[ERROR] %s\n' "$*" >&2
  exit 1
}

ENV_FAMILY=""
ENVS_CSV=""
KUBE_CONTEXT=""
TLS_CRT=""
TLS_KEY=""
CA_CRT=""
GATEWAY_CLASS="envoy-gateway"
GATEWAY_SECRET="gateway-tls-secret"
GATEWAY_NAME_PREFIX="gw"
CREATE_BACKEND_NAMESPACES=false
ANNOTATION_FILE=""
DRY_RUN=false

BACKEND_SECRET_MAPPINGS=(
  'annuity-services:annuity-backend-ca'
  'digtran-services:digtran-backend-ca'
  'document-services:document-backend-ca'
  'garwin-int-apps:garwin-backend-ca'
  'garwin-services:garwin-backend-ca'
  'generic-internal-service:generic-backend-ca'
  'lifecad-services:lifecad-backend-ca'
  'portal-services:portal-backend-ca'
)
ANNOTATE_SERVICES=()

while [[ $# -gt 0 ]]; do
  case "$1" in
    --env-family)
      ENV_FAMILY="${2:-}"; shift 2 ;;
    --envs)
      ENVS_CSV="${2:-}"; shift 2 ;;
    --context)
      KUBE_CONTEXT="${2:-}"; shift 2 ;;
    --tls-crt)
      TLS_CRT="${2:-}"; shift 2 ;;
    --tls-key)
      TLS_KEY="${2:-}"; shift 2 ;;
    --ca-crt)
      CA_CRT="${2:-}"; shift 2 ;;
    --gateway-class)
      GATEWAY_CLASS="${2:-}"; shift 2 ;;
    --gateway-secret)
      GATEWAY_SECRET="${2:-}"; shift 2 ;;
    --gateway-name-prefix)
      GATEWAY_NAME_PREFIX="${2:-}"; shift 2 ;;
    --create-backend-namespaces)
      CREATE_BACKEND_NAMESPACES=true; shift ;;
    --backend-secret)
      BACKEND_SECRET_MAPPINGS+=("${2:-}"); shift 2 ;;
    --annotation-file)
      ANNOTATION_FILE="${2:-}"; shift 2 ;;
    --annotate-service)
      ANNOTATE_SERVICES+=("${2:-}"); shift 2 ;;
    --dry-run)
      DRY_RUN=true; shift ;;
    -h|--help)
      usage; exit 0 ;;
    *)
      die "Unknown argument: $1" ;;
  esac
done

[[ -n "$ENV_FAMILY" ]] || die '--env-family is required.'
[[ -n "$TLS_CRT" ]] || die '--tls-crt is required.'
[[ -n "$TLS_KEY" ]] || die '--tls-key is required.'
[[ -n "$CA_CRT" ]] || die '--ca-crt is required.'
[[ -f "$TLS_CRT" ]] || die "TLS cert file not found: $TLS_CRT"
[[ -f "$TLS_KEY" ]] || die "TLS key file not found: $TLS_KEY"
[[ -f "$CA_CRT" ]] || die "CA cert file not found: $CA_CRT"
if [[ -n "$ANNOTATION_FILE" && ! -f "$ANNOTATION_FILE" ]]; then
  die "Annotation file not found: $ANNOTATION_FILE"
fi

KUBE_ARGS=()
if [[ -n "$KUBE_CONTEXT" ]]; then
  KUBE_ARGS+=(--context "$KUBE_CONTEXT")
fi

kubectl_cmd() {
  kubectl "${KUBE_ARGS[@]}" "$@"
}

apply_manifest() {
  if [[ "$DRY_RUN" == true ]]; then
    kubectl_cmd apply --dry-run=server -f -
  else
    kubectl_cmd apply -f -
  fi
}

create_namespace() {
  local namespace="$1"
  log "Ensuring namespace ${namespace}"
  kubectl_cmd create namespace "$namespace" --dry-run=client -o yaml | apply_manifest
}

namespace_exists() {
  local namespace="$1"
  kubectl_cmd get namespace "$namespace" >/dev/null 2>&1
}

create_gateway_tls_secret() {
  local namespace="$1"
  log "Ensuring gateway TLS Secret ${namespace}/${GATEWAY_SECRET}"
  kubectl_cmd -n "$namespace" create secret tls "$GATEWAY_SECRET" \
    --cert="$TLS_CRT" \
    --key="$TLS_KEY" \
    --dry-run=client -o yaml | apply_manifest
}

create_gateway() {
  local env_name="$1"
  local namespace="common-gw-${env_name}"
  local gateway_name="${GATEWAY_NAME_PREFIX}-${env_name}"

  log "Ensuring Gateway ${namespace}/${gateway_name}"
  cat <<YAML | apply_manifest
apiVersion: gateway.networking.k8s.io/v1
kind: Gateway
metadata:
  name: ${gateway_name}
  namespace: ${namespace}
spec:
  gatewayClassName: ${GATEWAY_CLASS}
  listeners:
    - name: https
      protocol: HTTPS
      port: 443
      allowedRoutes:
        namespaces:
          from: All
      tls:
        mode: Terminate
        certificateRefs:
          - group: ""
            kind: Secret
            name: ${GATEWAY_SECRET}
YAML
}

create_backend_ca_secret() {
  local group="$1"
  local secret_name="$2"
  local env_name="$3"
  local namespace="${group}-${env_name}"

  if ! namespace_exists "$namespace"; then
    if [[ "$CREATE_BACKEND_NAMESPACES" == true ]]; then
      create_namespace "$namespace"
    else
      warn "Skipping backend CA Secret ${namespace}/${secret_name}; namespace does not exist. Use --create-backend-namespaces to create it."
      return 0
    fi
  fi

  log "Ensuring backend CA Secret ${namespace}/${secret_name}"
  kubectl_cmd -n "$namespace" create secret generic "$secret_name" \
    --from-file=ca.crt="$CA_CRT" \
    --dry-run=client -o yaml | apply_manifest
}

read_annotations() {
  local env_name="$1"
  ANNOTATIONS=()

  [[ -n "$ANNOTATION_FILE" ]] || return 0

  while IFS= read -r raw_line || [[ -n "$raw_line" ]]; do
    local line="${raw_line%%#*}"
    line="${line#${line%%[![:space:]]*}}"
    line="${line%${line##*[![:space:]]}}"
    [[ -n "$line" ]] || continue
    [[ "$line" == *=* ]] || die "Invalid annotation line in ${ANNOTATION_FILE}: ${raw_line}"
    line="${line//\{env\}/$env_name}"
    ANNOTATIONS+=("$line")
  done < "$ANNOTATION_FILE"
}

annotate_service() {
  local service_spec="$1"
  local env_name="$2"
  local rendered_spec="${service_spec//\{env\}/$env_name}"
  local namespace="${rendered_spec%%/*}"
  local service="${rendered_spec#*/}"

  [[ "$rendered_spec" == */* ]] || die "--annotate-service must be namespace/name, got: ${service_spec}"
  read_annotations "$env_name"
  if [[ ${#ANNOTATIONS[@]} -eq 0 ]]; then
    warn "Skipping Service annotation for ${rendered_spec}; --annotation-file was not provided or had no annotations."
    return 0
  fi

  log "Annotating Service ${namespace}/${service} for ${env_name}"
  if [[ "$DRY_RUN" == true ]]; then
    kubectl_cmd -n "$namespace" annotate service "$service" "${ANNOTATIONS[@]}" --overwrite --dry-run=server -o yaml >/dev/null
  else
    kubectl_cmd -n "$namespace" annotate service "$service" "${ANNOTATIONS[@]}" --overwrite
  fi
}

expand_envs() {
  local env_family="$1"
  local envs_csv="$2"

  if [[ -n "$envs_csv" ]]; then
    printf '%s' "$envs_csv" | tr ',' '\n' | sed '/^$/d'
    return 0
  fi

  case "$env_family" in
    dev) printf '%s\n' dev devb devc ;;
    intg) printf '%s\n' intg intgb intgc ;;
    accp) printf '%s\n' accp accpb accpc ;;
    prod) printf '%s\n' proda prodb ;;
    *) printf '%s\n' "$env_family" ;;
  esac
}

TARGET_ENVS=()
while IFS= read -r env_name; do
  [[ -n "$env_name" ]] && TARGET_ENVS+=("$env_name")
done < <(expand_envs "$ENV_FAMILY" "$ENVS_CSV")
[[ ${#TARGET_ENVS[@]} -gt 0 ]] || die 'No target environments resolved.'

log "Target environments: ${TARGET_ENVS[*]}"
if [[ "$DRY_RUN" == true ]]; then
  warn 'Dry-run mode enabled; no resources will be persisted.'
fi

for env_name in "${TARGET_ENVS[@]}"; do
  gateway_namespace="common-gw-${env_name}"
  create_namespace "$gateway_namespace"
  create_gateway_tls_secret "$gateway_namespace"
  create_gateway "$env_name"

  for mapping in "${BACKEND_SECRET_MAPPINGS[@]}"; do
    [[ "$mapping" == *:* ]] || die "Invalid --backend-secret mapping: ${mapping}. Expected group:secret."
    group="${mapping%%:*}"
    secret_name="${mapping#*:}"
    create_backend_ca_secret "$group" "$secret_name" "$env_name"
  done

  for service_spec in "${ANNOTATE_SERVICES[@]}"; do
    annotate_service "$service_spec" "$env_name"
  done
done

log 'Prerequisite bootstrap completed.'
