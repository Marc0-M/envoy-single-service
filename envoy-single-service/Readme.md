# envoy-single-service

Expose one Kubernetes Service through Envoy Gateway by rendering Gateway API resources with a small, reusable Helm chart.

This repository contains the chart, two Jenkins pipelines, a prerequisite bootstrap script, and a cluster validator for the Envoy Gateway rollout.

## Repository Contents

| Path | Purpose |
| --- | --- |
| `envoy-single-service/Chart.yaml` | Helm chart metadata. Current chart version is `0.1.0`. |
| `envoy-single-service/values.yaml` | Default chart values used by local Helm rendering. |
| `envoy-single-service/values.schema.json` | Helm values schema for required fields and supported environment names. |
| `envoy-single-service/templates/httproute.yaml` | Main `HTTPRoute` template. Includes `rules.timeouts.request`. |
| `envoy-single-service/templates/referencegrant.yaml` | Allows the `HTTPRoute` in `common-gw-<env>` to reference the backend Service in `<group>-<env>`. |
| `envoy-single-service/templates/backendtlspolicy.yaml` | Creates `BackendTLSPolicy` when `backend.tlsEnabled=true`. |
| `envoy-single-service/templates/backendtrafficpolicy.yaml` | Optionally creates Envoy Gateway `BackendTrafficPolicy` for cookie-based consistent hashing. |
| `envoy-single-service/templates/gateway.yaml` | Optionally creates a Gateway when `gateway.create=true`. Shared Gateways are normally created as prerequisites instead. |
| `envoy-single-service/templates/_helpers.tpl` | Central naming, namespace, Service, path, and label helpers. |
| `envoy-single-service/templates/NOTES.txt` | Helm post-install notes with generated resource names and check commands. |
| `Jenkinsfile` | Main selected-microservice deploy pipeline. Uses `helm upgrade --install`. |
| `Jenkinsfile-bulk-upgrade` | Bulk upgrade pipeline for already-installed `envoy-single-service` releases. Uses `helm upgrade --reuse-values`. |
| `bootstrap_envoy_prereqs.sh` | Optional root-level script to create Gateway namespaces, TLS Secrets, Gateways, backend CA Secrets, and optional Service annotations. |
| `validate_envoy_resources.py` | Cluster validator for chart-managed HTTPRoutes, ReferenceGrants, BackendTLSPolicies, Gateways, Secrets, and Services. |
| `shared-gateway-manifests/` | Shared Gateway-level policies that must be applied per environment when backend services need correct forwarded client IP headers. |
| `microservices_dict.json` | Microservice catalog reference grouped by backend namespace prefix. |

All command examples in this README assume you are running from the repository root unless.

## What The Chart Renders

The chart always renders an `HTTPRoute` and a `ReferenceGrant`. It conditionally renders TLS, traffic policy, and Gateway resources depending on values.

| Resource | Template | Namespace | Created When | Notes |
| --- | --- | --- | --- | --- |
| `HTTPRoute` | `templates/httproute.yaml` | `common-gw-<env>` | Always | Routes `pathPrefix` to the backend Service and sets `rules.timeouts.request`. |
| `ReferenceGrant` | `templates/referencegrant.yaml` | `<group>-<env>` | Always | Required because the route lives in the Gateway namespace and points to a Service in the backend namespace. |
| `BackendTLSPolicy` | `templates/backendtlspolicy.yaml` | `<group>-<env>` | `backend.tlsEnabled=true` | Configures backend TLS validation using `backend.caSecretName` and `backend.hostname`. |
| `BackendTrafficPolicy` | `templates/backendtrafficpolicy.yaml` | `common-gw-<env>` | `backendTrafficPolicy.create=true` | Envoy Gateway extension for cookie-based consistent hash session affinity. |
| `Gateway` | `templates/gateway.yaml` | `common-gw-<env>` | `gateway.create=true` | Normally pre-created once per subenvironment and reused by many routes. |

The helpers derive these names and namespaces:

| Item | Convention |
| --- | --- |
| Gateway namespace | `common-gw-<env>` |
| Backend namespace | `<group>-<env>` |
| Default Gateway name | Usually `gw-<env>` from the Jenkins pipelines or prerequisite script. |
| Default backend Service name | `service-<microservice>` unless `svc` is set. |
| Default path prefix | `/<microservice>` unless `pathPrefix` is set. |
| Base resource name | `<group>-<microservice>-<env>`, truncated to fit Kubernetes name limits. |
| HTTPRoute name | `<base>-route` |
| ReferenceGrant name | `<base>-refgrant` |
| BackendTLSPolicy name | `<base>-btlsp` |
| BackendTrafficPolicy name | `<base>-btp` |


## Request Timeout, Sticky Session & Gateway

### HTTPRoute Request Timeout

`templates/httproute.yaml` :

```yaml
rules:
  - timeouts:
      request: "60s"
```

The value comes from `timeouts.request` and defaults to `60s` in `values.yaml`. 

Set it through Jenkins:

```text
REQUEST_TIMEOUT=60s
```

### BackendTrafficPolicy For Sticky Routing

`templates/backendtrafficpolicy.yaml` is disabled by default and is created only when `backendTrafficPolicy.create=true`.

When enabled, it targets the generated `HTTPRoute` and configures Envoy Gateway cookie-based consistent hashing:

```yaml
loadBalancer:
  type: ConsistentHash
  consistentHash:
    type: Cookie
    cookie:
      name: "session-<microservice>"
      ttl: "30m"
      attributes:
        SameSite: "Lax"
```

The default cookie name is templated from `session-{{ .Values.microservice }}`. You can override the cookie settings with:

```bash
--set backendTrafficPolicy.create=true \
--set-string backendTrafficPolicy.cookie.name=session-my-service \
--set-string backendTrafficPolicy.cookie.ttl=30m \
--set-string backendTrafficPolicy.cookie.sameSite=Lax
```

This resource requires the Envoy Gateway extension CRD `backendtrafficpolicies.gateway.envoyproxy.io` to be installed in the cluster. If the CRD is missing, server-side dry-run and deployment will fail.

### Gateway Template

`templates/gateway.yaml` is available for special cases, but the normal operating model is to create one shared Gateway per subenvironment as a prerequisite:

```text
common-gw-dev/gw-dev
common-gw-devb/gw-devb
common-gw-devc/gw-devc
common-gw-accp/gw-accp
common-gw-accpb/gw-accpb
common-gw-accpc/gw-accpc
```

Keep `gateway.create=false` for the normal shared-Gateway model.

## Prerequisites

Before deploying any microservice route, each target subenvironment needs shared Gateway infrastructure and backend CA Secrets.

Required cluster pieces:

| Requirement | Expected Standard |
| --- | --- |
| Gateway API CRDs | `Gateway`, `HTTPRoute`, `ReferenceGrant`, and `BackendTLSPolicy` available. |
| Envoy Gateway | Envoy Gateway controller running and reconciling `GatewayClass envoy-gateway`. |
| Gateway namespace | `common-gw-<env>`. |
| Shared Gateway | `gw-<env>` in `common-gw-<env>` with HTTPS listener named `https`. |
| Shared Gateway manifests | Apply `shared-gateway-manifests/<env>/01-clienttrafficpolicy.yaml` and `shared-gateway-manifests/<env>/02-envoyextensionpolicy.yaml` when services need trusted client IP forwarding headers. |
| Gateway TLS Secret | `gateway-tls-secret` in `common-gw-<env>`. |
| Backend namespace | `<group>-<env>`. |
| Backend Service | Service exists in `<group>-<env>`, normally `service-<microservice>`. |
| Backend CA Secret | Secret exists in `<group>-<env>` with key `ca.crt` when backend TLS is enabled. |

Install or verify Envoy Gateway control plane:

```bash
ENVOY_GATEWAY_VERSION=v1.7.0

helm upgrade --install eg oci://docker.io/envoyproxy/gateway-helm \
  --version "${ENVOY_GATEWAY_VERSION}" \
  -n envoy-gateway-system \
  --create-namespace

kubectl wait --timeout=5m -n envoy-gateway-system deployment/envoy-gateway --for=condition=Available

kubectl get gatewayclass
kubectl get crd gateways.gateway.networking.k8s.io
kubectl get crd httproutes.gateway.networking.k8s.io
kubectl get crd referencegrants.gateway.networking.k8s.io
kubectl get crd backendtlspolicies.gateway.networking.k8s.io
kubectl get crd backendtrafficpolicies.gateway.envoyproxy.io || true
```

The `BackendTrafficPolicy` CRD is only required when `backendTrafficPolicy.create=true`.

## Shared Gateway Manifests Prerequisite

The `shared-gateway-manifests/` folder belongs to the shared Gateway layer, not to an individual microservice route. Apply these manifests before deploying routes that depend on correct client IP forwarding behavior.

Each supported environment has its own folder:

```text
shared-gateway-manifests/dev/
shared-gateway-manifests/devb/
shared-gateway-manifests/devc/
shared-gateway-manifests/intg/
shared-gateway-manifests/intgb/
shared-gateway-manifests/intgc/
shared-gateway-manifests/accp/
shared-gateway-manifests/accpb/
shared-gateway-manifests/accpc/
shared-gateway-manifests/proda/
shared-gateway-manifests/prodb/
shared-gateway-manifests/dr/
```

Each folder contains two Gateway-level policies:

| File | Resource | Reason |
| --- | --- | --- |
| `01-clienttrafficpolicy.yaml` | `ClientTrafficPolicy` | Tells Envoy Gateway to trust the incoming `X-Forwarded-For` header on the shared Gateway. Without this, backend services may see the Envoy/NLB/proxy address instead of the real caller chain. |
| `02-envoyextensionpolicy.yaml` | `EnvoyExtensionPolicy` | Copies `X-Forwarded-For` into `X-Original-Forwarded-For` using a Gateway-wide Lua filter, so backend services can read the original forwarded chain from a stable header. |

This is a prerequisite because `envoy-single-service` creates per-service resources such as `HTTPRoute`, `ReferenceGrant`, and optional backend policies. It does not configure Gateway-wide client IP handling. If these shared manifests are missing, the route can still work, but applications and logs that depend on original client IP headers can be wrong or incomplete.

Apply them in this order for the target environment:

```bash
kubectl apply -f shared-gateway-manifests/<env>/01-clienttrafficpolicy.yaml
kubectl apply -f shared-gateway-manifests/<env>/02-envoyextensionpolicy.yaml
```

Example for `accp`:

```bash
kubectl apply -f shared-gateway-manifests/accp/01-clienttrafficpolicy.yaml
kubectl apply -f shared-gateway-manifests/accp/02-envoyextensionpolicy.yaml
```

Verify the policies:

```bash
kubectl -n common-gw-<env> get clienttrafficpolicy trust-all-xff -o yaml
kubectl -n common-gw-<env> get envoyextensionpolicy copy-xff-to-xoff -o yaml
```

After applying them, test a routed URL and confirm the backend receives both:

```text
X-Forwarded-For
X-Original-Forwarded-For
```

Important: these manifests target a specific shared Gateway name and namespace, usually `gw-<env>` in `common-gw-<env>`. If your Gateway name is customized, update the `targetRefs.name` value before applying.

## Prerequisite Bootstrap Script

The root script can create or refresh the common Gateway prerequisites for an environment family.

Dry-run first:

```bash
./bootstrap_envoy_prereqs.sh \
  --env-family accp \
  --context accp \
  --tls-crt ./tls.crt \
  --tls-key ./tls.key \
  --ca-crt ./ca.crt \
  --dry-run
```

Apply for the `accp` family, which expands to `accp`, `accpb`, and `accpc`:

```bash
./bootstrap_envoy_prereqs.sh \
  --env-family accp \
  --context accp \
  --tls-crt ./tls.crt \
  --tls-key ./tls.key \
  --ca-crt ./ca.crt
```

If backend namespaces do not exist yet and should be created by the script:

```bash
./bootstrap_envoy_prereqs.sh \
  --env-family accp \
  --context accp \
  --tls-crt ./tls.crt \
  --tls-key ./tls.key \
  --ca-crt ./ca.crt \
  --create-backend-namespaces
```

Supported environment family expansion:

| `--env-family` | Target subenvironments |
| --- | --- |
| `dev` | `dev`, `devb`, `devc` |
| `intg` | `intg`, `intgb`, `intgc` |
| `accp` | `accp`, `accpb`, `accpc` |
| `prod` | `proda`, `prodb` |
| `dr` | `dr` |

Default backend CA Secret mapping used by the script and expected by the pipelines:

| Backend namespace prefix | Secret name |
| --- | --- |
| `annuity-services` | `annuity-backend-ca` |
| `digtran-services` | `digtran-backend-ca` |
| `document-services` | `document-backend-ca` |
| `garwin-int-apps` | `garwin-backend-ca` |
| `garwin-services` | `garwin-backend-ca` |
| `generic-internal-service` | `generic-backend-ca` |
| `lifecad-services` | `lifecad-backend-ca` |
| `portal-services` | `portal-backend-ca` |

Override or add mappings with repeatable `--backend-secret group:secret` arguments.

## Manual Prerequisite Commands

Use these if you do not want to run the bootstrap script.

Create Gateway namespaces. Example for `accp`:

```bash
for env in accp accpb accpc; do
  kubectl create namespace "common-gw-${env}" --dry-run=client -o yaml | kubectl apply -f -
done
```

Create the Gateway TLS Secret in each Gateway namespace:

```bash
for env in accp accpb accpc; do
  kubectl -n "common-gw-${env}" create secret tls gateway-tls-secret \
    --cert=tls.crt \
    --key=tls.key \
    --dry-run=client -o yaml | kubectl apply -f -
done
```

Create one Gateway per subenvironment. Example for `accpb`:

```yaml
apiVersion: gateway.networking.k8s.io/v1
kind: Gateway
metadata:
  name: gw-accpb
  namespace: common-gw-accpb
spec:
  gatewayClassName: envoy-gateway
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
            name: gateway-tls-secret
```

Create backend CA Secrets. Example for `accpb`:

```bash
kubectl -n annuity-services-accpb create secret generic annuity-backend-ca --from-file=ca.crt=./ca.crt --dry-run=client -o yaml | kubectl apply -f -
kubectl -n digtran-services-accpb create secret generic digtran-backend-ca --from-file=ca.crt=./ca.crt --dry-run=client -o yaml | kubectl apply -f -
kubectl -n document-services-accpb create secret generic document-backend-ca --from-file=ca.crt=./ca.crt --dry-run=client -o yaml | kubectl apply -f -
kubectl -n garwin-int-apps-accpb create secret generic garwin-backend-ca --from-file=ca.crt=./ca.crt --dry-run=client -o yaml | kubectl apply -f -
kubectl -n garwin-services-accpb create secret generic garwin-backend-ca --from-file=ca.crt=./ca.crt --dry-run=client -o yaml | kubectl apply -f -
kubectl -n generic-internal-service-accpb create secret generic generic-backend-ca --from-file=ca.crt=./ca.crt --dry-run=client -o yaml | kubectl apply -f -
kubectl -n lifecad-services-accpb create secret generic lifecad-backend-ca --from-file=ca.crt=./ca.crt --dry-run=client -o yaml | kubectl apply -f -
kubectl -n portal-services-accpb create secret generic portal-backend-ca --from-file=ca.crt=./ca.crt --dry-run=client -o yaml | kubectl apply -f -
```

Repeat the same backend CA pattern for `accpb` and `accpc` if those namespaces exist.

## AWS LoadBalancer Annotations

AWS LoadBalancer annotations belong on the Kubernetes `Service` that exposes Envoy Gateway, not on the `Gateway`, `HTTPRoute`, or backend application Service.

Find the Service first:

```bash
kubectl get svc -A | grep -E 'LoadBalancer|envoy|gateway'
```

Example annotation file for the bootstrap script:

```bash
cat > accp-lb-annotations.env <<'EOF_ANNOTATIONS'
service.beta.kubernetes.io/aws-load-balancer-access-log-enabled=true
service.beta.kubernetes.io/aws-load-balancer-access-log-s3-bucket-name=ven-{env}-lb-logging
service.beta.kubernetes.io/aws-load-balancer-access-log-s3-bucket-prefix=k8s-eg-{env}
service.beta.kubernetes.io/aws-load-balancer-backend-protocol=ssl
service.beta.kubernetes.io/aws-load-balancer-cross-zone-load-balancing-enabled=true
service.beta.kubernetes.io/aws-load-balancer-internal=true
service.beta.kubernetes.io/aws-load-balancer-security-groups=sg-xxxxxxxxxxx
service.beta.kubernetes.io/aws-load-balancer-ssl-cert=arn:aws:acm:us-east-1:xxxxxxxxxxx:certificate/xxxxxxxxxxx-xxxxx-xxxxx-xxxxx-xxxxxxxxxxx
service.beta.kubernetes.io/aws-load-balancer-ssl-ports=443
service.beta.kubernetes.io/aws-load-balancer-subnets=subnet-xxxxxxxxxxx,subnet-xxxxxxxxxxx
service.beta.kubernetes.io/aws-load-balancer-type=nlb-ip
service.beta.kubernetes.io/aws-load-balancer-target-group-attributes: preserve_client_ip.enabled=true
EOF_ANNOTATIONS
```

Apply annotations through the script. The `{env}` placeholder is replaced with each target subenvironment:

```bash
./bootstrap_envoy_prereqs.sh \
  --env-family accp \
  --context accp \
  --tls-crt ./tls.crt \
  --tls-key ./tls.key \
  --ca-crt ./ca.crt \
  --annotation-file ./accp-lb-annotations.env \
  --annotate-service 'envoy-gateway-system/envoy-gateway-{env}'
```

Adjust `envoy-gateway-system/envoy-gateway-{env}` to the real Service namespace and name in the cluster.

TLS model reminder: if the AWS NLB terminates TLS with ACM and then connects to Envoy with SSL, the ACM and SSL annotations are expected. If Envoy Gateway should be the only TLS termination point, use NLB TCP pass-through style configuration instead. Keep this consistent with the Gateway listener, which uses `protocol: HTTPS` and `tls.mode: Terminate` in the standard example.

## Chart Values

Required values:

| Value | Description |
| --- | --- |
| `microservice` | Microservice name. Used in default Service name, path, and labels. |
| `group` | Backend namespace prefix, such as `portal-services`. |
| `env` | Environment suffix, such as `dev`, `devb`, `accp`, `proda`, or `dr`. |
| `gateway.name` | Existing Gateway name, usually `gw-<env>`. |
| `backend.caSecretName` | Required by the schema; used as the backend CA Secret name when `backend.tlsEnabled=true`. |

Important optional values:

| Value | Default | Description |
| --- | --- | --- |
| `svc` | `service-<microservice>` | Backend Service name override. |
| `pathPrefix` | `/<microservice>` | Path prefix override. |
| `timeouts.request` | `60s` | Gateway API request timeout rendered into `HTTPRoute.spec.rules[].timeouts.request`. |
| `gateway.create` | `false` | Create a Gateway from this chart. Usually keep this disabled. |
| `gateway.listenerName` | `https` | Parent Gateway listener section name. |
| `gateway.gatewayClassName` | `envoy-gateway` | GatewayClass name used only when `gateway.create=true`. |
| `gateway.tlsSecretName` | empty | TLS Secret used only when `gateway.create=true`. |
| `backend.port` | `443` | Backend Service port. |
| `backend.tlsEnabled` | `true` | Create `BackendTLSPolicy`. |
| `backend.hostname` | `*` | Backend TLS SNI and certificate hostname. Jenkins requires a concrete hostname when TLS is enabled. |
| `backendTrafficPolicy.create` | `false` | Create Envoy Gateway `BackendTrafficPolicy`. |
| `backendTrafficPolicy.cookie.name` | `session-{{ .Values.microservice }}` | Cookie name for consistent hash when BackendTrafficPolicy is enabled. |
| `backendTrafficPolicy.cookie.ttl` | `30m` | Cookie TTL. |
| `backendTrafficPolicy.cookie.sameSite` | `Lax` | Cookie SameSite attribute. Allowed values are `Strict`, `Lax`, and `None`. |

Supported `env` values in `values.schema.json`:

```text
dev, devb, devc, intg, intgb, intgc, accp, accpb, accpc, proda, prodb, dr
```

## Helm Usage

Render locally from the repository root:

```bash
helm template annuity-webtransdb-api-dev ./envoy-single-service \
  --set-string microservice=annuity-webtransdb-api \
  --set-string group=annuity-services \
  --set-string env=dev \
  --set-string gateway.name=gw-dev \
  --set-string backend.caSecretName=annuity-backend-ca \
  --set-string backend.hostname=annuity-webtransdb-api-eks.dev.vaapps.net \
  --set-string timeouts.request=60s
```

Validate against the cluster API without applying:

```bash
helm template annuity-webtransdb-api-dev ./envoy-single-service \
  --set-string microservice=annuity-webtransdb-api \
  --set-string group=annuity-services \
  --set-string env=dev \
  --set-string gateway.name=gw-dev \
  --set-string backend.caSecretName=annuity-backend-ca \
  --set-string backend.hostname=annuity-webtransdb-api-eks.dev.vaapps.net \
  --set-string timeouts.request=60s \
| kubectl --context dev apply --dry-run=server -f -
```

Install or upgrade from OCI:

```bash
helm upgrade --install annuity-webtransdb-api-dev oci://artifactory.tools.vaapps.net/envoy-single-service/envoy-single-service \
  --kube-context dev \
  --namespace default \
  --version 0.1.0 \
  --set-string microservice=annuity-webtransdb-api \
  --set-string group=annuity-services \
  --set-string env=dev \
  --set-string gateway.name=gw-dev \
  --set-string backend.caSecretName=annuity-backend-ca \
  --set-string backend.hostname=annuity-webtransdb-api-eks.dev.vaapps.net \
  --set-string timeouts.request=60s \
  --history-max 10
```

Enable sticky routing for a release:

```bash
helm upgrade --install garwin-jmt-app-dev oci://artifactory.tools.vaapps.net/envoy-single-service/envoy-single-service \
  --kube-context dev \
  --namespace default \
  --version 0.1.0 \
  --reuse-values \
  --set backendTrafficPolicy.create=true \
  --set-string timeouts.request=60s \
  --history-max 10
```

## Main Jenkins Pipeline

`Jenkinsfile` deploys selected microservices from one selected group and environment.

Key behavior:

| Behavior | Detail |
| --- | --- |
| Helm command | Uses `helm upgrade --install`. This is correct for both first install and later upgrades. |
| Validation | Renders each selected chart with `helm template` and runs `kubectl apply --dry-run=server -f -`. |
| Apply | Skipped when `VALIDATE_ONLY=true`; otherwise applies each selected release. |
| Gateway name | Defaults to `gw-<env>` unless `OVERRIDE_GATEWAY_NAME=true`. |
| Backend CA Secret | Derived from the group prefix, such as `portal-backend-ca` for `portal-services`. |
| Backend hostname | Required by the pipeline when `BACKEND_TLS_ENABLED=true`; wildcards are rejected. |
| BackendTrafficPolicy | Controlled by `CREATE_BACKEND_TRAFFIC_POLICY`. |
| Request timeout | Controlled by `REQUEST_TIMEOUT` and passed as `--set-string timeouts.request=<value>`. |
| Extra Helm arguments | `HELM_EXTRA_ARGS` is appended after sanitization. It rejects shell metacharacters and should be whitespace-separated Helm args only. |

`dr` is treated as a prod-account environment in the main pipeline, but it uses `us-west-2`. `proda` and `prodb` continue to use `us-east-1`.

Use `HELM_EXTRA_ARGS` in the main pipeline for one-off extra settings, for example:

```text
--set-string backendTrafficPolicy.cookie.ttl=45m --set-string backendTrafficPolicy.cookie.sameSite=Lax
```

If a value contains spaces or shell-sensitive characters, add a dedicated Jenkins parameter instead of forcing it through `HELM_EXTRA_ARGS`.

## Bulk Upgrade Pipeline

`Jenkinsfile-bulk-upgrade` upgrades already-installed `envoy-single-service` Helm releases across an environment family.

Key behavior:

| Behavior | Detail |
| --- | --- |
| Target discovery | Runs `helm list -A -o json` and selects releases whose chart starts with `envoy-single-service-`. |
| Environment expansion | `dev` means `dev`, `devb`, `devc`; `intg` means `intg`, `intgb`, `intgc`; `accp` means `accp`, `accpb`, `accpc`; `prod` means `proda`, `prodb`; `dr` targets only `dr`. |
| Release filter | Optional `RELEASE_FILTER` regex limits discovered release names. |
| Validation pass | Runs `helm upgrade --dry-run --debug` for every discovered release. |
| Apply pass | Runs only if every validation passes and `VALIDATE_ONLY=false`. |
| Helm command | Uses `helm upgrade --reuse-values`, because this pipeline only acts on releases that already exist. |
| Request timeout | Always passes `--set-string timeouts.request=<REQUEST_TIMEOUT>`. |
| Reports | Archives `discovered-envoy-single-service-releases.json`, `bulk-upgrade-report.json`, `bulk-upgrade-report.md`, and failure JSON files when needed. |

`helm upgrade` versus `helm upgrade --install`: for an existing release, both perform an upgrade. The `--install` flag only changes behavior when the release does not exist. The bulk pipeline intentionally uses plain `helm upgrade` because it discovers existing releases first and should not create new releases by accident.

`dr` stays separate from the `prod` family in the bulk pipeline because it uses `us-west-2`, while `proda` and `prodb` use `us-east-1`. Keeping `dr` separate avoids mixing subenvironments that need different AWS region settings in one run.

For future bulk settings beyond `REQUEST_TIMEOUT`, add explicit Jenkins parameters and append safe `--set` or `--set-string` arguments in `buildHelmUpgradeCommand`. Avoid a generic raw extra-args box in the bulk pipeline unless you also add the same kind of sanitization used in the main `Jenkinsfile`.

## Validator

Run the validator after deploying or bulk-upgrading routes:

```bash
python3 validate_envoy_resources.py --context dev --env dev
python3 validate_envoy_resources.py --context accp --env accp
python3 validate_envoy_resources.py --context accp --env accpb --export-ok
```

The validator discovers chart-managed resources by Helm labels and checks:

| Check | What It Verifies |
| --- | --- |
| `HTTPRoute` exists | Route was created in `common-gw-<env>`. |
| `ReferenceGrant` exists | Backend namespace allows the route namespace to reference the Service. |
| Gateway exists | `parentRefs` point to an existing Gateway. |
| Gateway conditions | Gateway `Accepted` and `Programmed` conditions when present. |
| HTTPRoute conditions | Route `Accepted` and `ResolvedRefs` conditions when present. |
| Backend Service exists | Route backend reference points to a real Service. |
| BackendTLSPolicy exists | Warns if missing, which may be expected only when TLS is disabled. |
| CA Secret exists | BackendTLS CA Secret exists and contains `ca.crt`. |

Exit code is `1` when failures are found and `0` when there are no failures.

## Verification Commands

Check Helm values and rendered manifest stored in the release:

```bash
helm get values annuity-webtransdb-api-dev -n default --all
helm get manifest annuity-webtransdb-api-dev -n default | sed -n '/kind: HTTPRoute/,+45p'
```

Check live Kubernetes resources:

```bash
kubectl -n common-gw-dev get httproute annuity-services-annuity-webtransdb-api-dev-route -o yaml | sed -n '/timeouts:/,+3p'
kubectl -n common-gw-dev describe httproute annuity-services-annuity-webtransdb-api-dev-route
kubectl -n annuity-services-dev get referencegrant annuity-services-annuity-webtransdb-api-dev-refgrant
kubectl -n annuity-services-dev get backendtlspolicy annuity-services-annuity-webtransdb-api-dev-btlsp
```

Confirm the cluster schema supports HTTPRoute timeouts:

```bash
kubectl explain httproute.spec.rules.timeouts --api-version gateway.networking.k8s.io/v1
```

Confirm the Envoy Gateway BackendTrafficPolicy CRD exists before enabling sticky routing:

```bash
kubectl get crd backendtrafficpolicies.gateway.envoyproxy.io
kubectl explain backendtrafficpolicy.spec --api-version gateway.envoyproxy.io/v1alpha1
```

## When Helm Manifest And Live Resource Differ

Sometimes `helm get values` and `helm get manifest` show a setting, but `kubectl get ... -o yaml` does not show it on the live object. Use this sequence before assuming Helm failed.

First confirm you are looking at the same cluster and resource name:

```bash
kubectl config current-context
helm status annuity-webtransdb-api-dev -n default
helm get manifest annuity-webtransdb-api-dev -n default | grep -A 45 'kind: HTTPRoute'
kubectl -n common-gw-dev get httproute annuity-services-annuity-webtransdb-api-dev-route -o yaml | grep -A 3 timeouts || true
```

Then confirm the API server accepts the manifest Helm has stored:

```bash
helm get manifest annuity-webtransdb-api-dev -n default | kubectl apply --dry-run=server -f -
```

If dry-run succeeds, prefer rerunning the Helm upgrade first:

```bash
helm upgrade annuity-webtransdb-api-dev oci://artifactory.tools.vaapps.net/envoy-single-service/envoy-single-service \
  --kube-context dev \
  --namespace default \
  --version 0.1.0 \
  --reuse-values \
  --set-string timeouts.request=60s \
  --history-max 10 \
  --debug
```

If Helm history already contains the desired manifest and the live resource still needs repair, you can apply the stored Helm manifest directly:

```bash
helm get manifest annuity-webtransdb-api-dev -n default | kubectl apply -f -
```

Use the direct apply as a repair step, not as the normal deployment path. It applies every resource in that Helm release manifest. Because the manifest comes from Helm history, future Helm upgrades should remain consistent, but Jenkins or Helm should still be the long-term source of truth.

If the field disappears again after apply, check for these causes:

| Symptom | Likely Cause | Check |
| --- | --- | --- |
| Server dry-run rejects `timeouts` | Gateway API CRDs are too old for `HTTPRoute.spec.rules.timeouts`. | `kubectl explain httproute.spec.rules.timeouts --api-version gateway.networking.k8s.io/v1` |
| Server dry-run succeeds but live object omits field | Wrong cluster/context, wrong route name, or another controller/process overwrote the route. | Compare `kubectl config current-context`, Helm status, and resource `metadata.managedFields`. |
| Helm upgrade succeeds but resource is unchanged | The release manifest and live object are out of sync. | Run dry-run, rerun Helm with `--debug`, then repair with `helm get manifest | kubectl apply -f -` if needed. |
| BackendTrafficPolicy fails to apply | Envoy Gateway extension CRD is missing or wrong version. | `kubectl get crd backendtrafficpolicies.gateway.envoyproxy.io` |

## Final Prerequisite Checklist

Run this before deploying routes into a subenvironment family:

```bash
for env in accp accpb accpc; do
  kubectl -n "common-gw-${env}" get secret gateway-tls-secret
  kubectl -n "common-gw-${env}" get gateway "gw-${env}"
  kubectl -n "common-gw-${env}" describe gateway "gw-${env}" | grep -E 'Accepted|Programmed|ResolvedRefs' || true
done
```

Check representative backend CA Secrets:

```bash
kubectl -n annuity-services-accp get secret annuity-backend-ca
kubectl -n digtran-services-accp get secret digtran-backend-ca
kubectl -n document-services-accp get secret document-backend-ca
kubectl -n garwin-int-apps-accp get secret garwin-backend-ca
kubectl -n garwin-services-accp get secret garwin-backend-ca
kubectl -n generic-internal-service-accp get secret generic-backend-ca
kubectl -n lifecad-services-accp get secret lifecad-backend-ca
kubectl -n portal-services-accp get secret portal-backend-ca
```

Run the repo validator after deploying:

```bash
python3 validate_envoy_resources.py --context accp --env accp
python3 validate_envoy_resources.py --context accp --env accpb
python3 validate_envoy_resources.py --context accp --env accpc
```

## Troubleshooting

| Issue | What To Check |
| --- | --- |
| `Secret is not supplied by SDS` | Confirm Envoy Gateway can read the Gateway TLS Secret and any referenced backend CA Secrets. Check namespace, Secret name, Secret type, and controller RBAC. |
| `HTTPRoute Accepted=False` | Check Gateway name, Gateway namespace, listener `sectionName`, and whether the Gateway allows routes from the route namespace. |
| `HTTPRoute ResolvedRefs=False` | Check backend Service name, backend namespace, and ReferenceGrant permissions. |
| `BackendTLSPolicy ResolvedRefs=False` | Confirm the CA Secret exists in the backend namespace and contains `ca.crt`. |
| Gateway has no endpoint | Confirm the correct Envoy Gateway LoadBalancer Service exists and has the expected AWS annotations, subnets, security groups, and ACM ARN. |
| Bulk upgrade fails with nil pointer on old values | Ensure chart templates use safe defaults and pass required new values, such as `--set-string timeouts.request=60s`. The current templates are safe for missing `timeouts` and `backendTrafficPolicy`. |
| Sticky routing does not work | Confirm `BackendTrafficPolicy` was created, accepted by Envoy Gateway, and targets the generated HTTPRoute. |
