# envoy-single-service

`envoy-single-service` is a small Helm chart that exposes one existing Kubernetes `Service` through Envoy Gateway using Kubernetes Gateway API resources.

Use this chart when a backend service already exists in its own namespace and you want to attach it to a shared Envoy Gateway with a clean `HTTPRoute`.

The chart is intentionally narrow. It does not deploy your application, Deployment, Service, TLS certificates, Envoy Gateway controller, or Gateway API CRDs. It only creates the routing resources needed to publish one service through an existing or chart-created Gateway.

## What This Chart Creates

The chart always creates:

| Resource | Namespace | Purpose |
| --- | --- | --- |
| `HTTPRoute` | `common-gw-<env>` | Routes traffic from the shared Gateway to your backend service. |
| `ReferenceGrant` | `<group>-<env>` | Allows the `HTTPRoute` in the Gateway namespace to reference a `Service` in the backend namespace. |

The chart can also create:

| Resource | Namespace | Created when | Purpose |
| --- | --- | --- | --- |
| `BackendTLSPolicy` | `<group>-<env>` | `backend.tlsEnabled=true` | Validates TLS when Envoy connects to the backend service over HTTPS. |
| `BackendTrafficPolicy` | `common-gw-<env>` | `backendTrafficPolicy.create=true` | Enables cookie-based consistent hashing for sticky routing. |
| `Gateway` | `common-gw-<env>` | `gateway.create=true` | Creates a Gateway if one is not already managed outside this chart. |

## Naming Rules

The chart derives names from three required values:

```text
group
microservice
env
```

For example:

```yaml
group: portal-services
microservice: audit-services
env: dev
```

This produces:

| Item | Result |
| --- | --- |
| Gateway namespace | `common-gw-dev` |
| Backend namespace | `portal-services-dev` |
| Default backend service | `service-audit-services` |
| Default path prefix | `/audit-services` |
| Base resource name | `portal-services-audit-services-dev` |
| HTTPRoute | `portal-services-audit-services-dev-route` |
| ReferenceGrant | `portal-services-audit-services-dev-refgrant` |
| BackendTLSPolicy | `portal-services-audit-services-dev-btlsp` |
| BackendTrafficPolicy | `portal-services-audit-services-dev-btp` |

Long names are truncated to stay inside Kubernetes resource name limits.

## Supported Environments

The values schema allows these environments:

```text
dev
devb
devc
intg
intgb
intgc
accp
accpb
accpc
proda
prodb
dr
```

If you use a different environment name, Helm validation will fail.

## Required Inputs

These values are required:

```yaml
group: portal-services
microservice: audit-services
env: dev

gateway:
  name: gw-dev

backend:
  caSecretName: portal-backend-ca
```

`backend.caSecretName` is required by the schema because backend TLS is enabled by default.

If your backend service does not use TLS, set:

```yaml
backend:
  tlsEnabled: false
  caSecretName: unused
```

The value still needs to be non-empty because the current schema requires it.

## Default Values

The chart defaults are in [values.yaml](values.yaml).

Important defaults:

```yaml
pathPrefix: ""
svc: ""

timeouts:
  request: 60s

gateway:
  create: false
  namespace: common-gw-{{ .Values.env }}
  listenerName: https
  port: 443

backend:
  port: 443
  tlsEnabled: true
  hostname: "*"

backendTrafficPolicy:
  create: false
```

If `pathPrefix` is empty, the chart uses:

```text
/<microservice>
```

If `svc` is empty, the chart uses:

```text
service-<microservice>
```

## Prerequisites

Before installing this chart, the cluster must already have:

| Prerequisite | Why it matters |
| --- | --- |
| Envoy Gateway installed | Reconciles `Gateway`, `HTTPRoute`, and Envoy Gateway extension resources. |
| Gateway API CRDs installed | Required for `Gateway`, `HTTPRoute`, `ReferenceGrant`, and `BackendTLSPolicy`. |
| Envoy Gateway extension CRDs installed | Required only if `BackendTrafficPolicy` is enabled. |
| Gateway namespace | Usually `common-gw-<env>`. |
| Shared Gateway | Usually `gw-<env>` in `common-gw-<env>`. |
| Backend namespace | Must be `<group>-<env>`. |
| Backend Service | Must exist before the route can send traffic. |
| Backend CA Secret | Required when `backend.tlsEnabled=true`. |

Quick checks:

```bash
kubectl get crd gateways.gateway.networking.k8s.io
kubectl get crd httproutes.gateway.networking.k8s.io
kubectl get crd referencegrants.gateway.networking.k8s.io
kubectl get crd backendtlspolicies.gateway.networking.k8s.io
kubectl get gatewayclass
```

If you plan to enable sticky routing, also check:

```bash
kubectl get crd backendtrafficpolicies.gateway.envoyproxy.io
```

## Install Example

This example exposes `service-audit-services` from namespace `portal-services-dev` through Gateway `gw-dev` in namespace `common-gw-dev`.

```bash
helm upgrade --install portal-audit-dev . \
  --namespace common-gw-dev \
  --create-namespace \
  --set group=portal-services \
  --set microservice=audit-services \
  --set env=dev \
  --set gateway.name=gw-dev \
  --set backend.caSecretName=portal-backend-ca
```

The Helm release namespace is not what controls where all resources are created. Templates explicitly place:

```text
HTTPRoute              -> common-gw-dev
ReferenceGrant         -> portal-services-dev
BackendTLSPolicy       -> portal-services-dev
BackendTrafficPolicy   -> common-gw-dev
```

## Install With A Custom Service Name

Use `svc` when the Kubernetes Service does not follow the default `service-<microservice>` naming convention.

```bash
helm upgrade --install portal-audit-dev . \
  --namespace common-gw-dev \
  --create-namespace \
  --set group=portal-services \
  --set microservice=audit-services \
  --set env=dev \
  --set gateway.name=gw-dev \
  --set svc=audit-api \
  --set backend.caSecretName=portal-backend-ca
```

## Install With A Custom Path

Use `pathPrefix` when the public path should not be `/<microservice>`.

```bash
helm upgrade --install portal-audit-dev . \
  --namespace common-gw-dev \
  --create-namespace \
  --set group=portal-services \
  --set microservice=audit-services \
  --set env=dev \
  --set gateway.name=gw-dev \
  --set pathPrefix=/audit \
  --set backend.caSecretName=portal-backend-ca
```

This creates a route matching:

```text
/audit
```

## Backend TLS

Backend TLS is enabled by default:

```yaml
backend:
  port: 443
  tlsEnabled: true
  caSecretName: ""
  hostname: "*"
```

When enabled, the chart creates a `BackendTLSPolicy` in the backend namespace. The policy points at:

```text
Service: <svc or service-microservice>
Secret:  backend.caSecretName
```

The CA Secret must exist in the backend namespace and must contain:

```text
ca.crt
```

Example:

```bash
kubectl -n portal-services-dev create secret generic portal-backend-ca \
  --from-file=ca.crt=./ca.crt
```

If your backend listens with plain HTTP, disable backend TLS:

```bash
helm upgrade --install portal-audit-dev . \
  --namespace common-gw-dev \
  --create-namespace \
  --set group=portal-services \
  --set microservice=audit-services \
  --set env=dev \
  --set gateway.name=gw-dev \
  --set backend.tlsEnabled=false \
  --set backend.port=80 \
  --set backend.caSecretName=unused
```

## Request Timeout

The `HTTPRoute` includes a request timeout:

```yaml
rules:
  - timeouts:
      request: "60s"
```

Default:

```yaml
timeouts:
  request: 60s
```

Override it like this:

```bash
--set-string timeouts.request=120s
```

## Sticky Routing

Sticky routing is disabled by default.

Enable it with:

```bash
helm upgrade --install portal-audit-dev . \
  --namespace common-gw-dev \
  --create-namespace \
  --set group=portal-services \
  --set microservice=audit-services \
  --set env=dev \
  --set gateway.name=gw-dev \
  --set backend.caSecretName=portal-backend-ca \
  --set backendTrafficPolicy.create=true
```

By default, the cookie settings are:

```yaml
backendTrafficPolicy:
  cookie:
    name: session-{{ .Values.microservice }}
    ttl: 30m
    sameSite: Lax
```

Override them like this:

```bash
--set backendTrafficPolicy.create=true \
--set-string backendTrafficPolicy.cookie.name=session-audit \
--set-string backendTrafficPolicy.cookie.ttl=30m \
--set-string backendTrafficPolicy.cookie.sameSite=Lax
```

This creates a `BackendTrafficPolicy` that targets the generated `HTTPRoute`.

## Creating A Gateway With This Chart

The normal model is to reuse a shared Gateway that already exists.

Use:

```yaml
gateway:
  create: false
  name: gw-dev
```

Set `gateway.create=true` only for standalone or test environments where this chart should create the Gateway too.

Example:

```bash
helm upgrade --install portal-audit-dev . \
  --namespace common-gw-dev \
  --create-namespace \
  --set group=portal-services \
  --set microservice=audit-services \
  --set env=dev \
  --set gateway.create=true \
  --set gateway.name=gw-dev \
  --set gateway.tlsSecretName=gateway-tls-secret \
  --set backend.caSecretName=portal-backend-ca
```

The TLS Secret must already exist in the Gateway namespace:

```bash
kubectl -n common-gw-dev create secret tls gateway-tls-secret \
  --cert=./tls.crt \
  --key=./tls.key
```

## Render Locally Before Installing

Use `helm template` when you want to inspect the generated resources before applying them:

```bash
helm template portal-audit-dev . \
  --set group=portal-services \
  --set microservice=audit-services \
  --set env=dev \
  --set gateway.name=gw-dev \
  --set backend.caSecretName=portal-backend-ca
```

Run schema validation and chart linting:

```bash
helm lint . \
  --set group=portal-services \
  --set microservice=audit-services \
  --set env=dev \
  --set gateway.name=gw-dev \
  --set backend.caSecretName=portal-backend-ca
```

## Validate After Installing

Check the route:

```bash
kubectl -n common-gw-dev get httproute portal-services-audit-services-dev-route
kubectl -n common-gw-dev describe httproute portal-services-audit-services-dev-route
```

Check the cross-namespace grant:

```bash
kubectl -n portal-services-dev get referencegrant portal-services-audit-services-dev-refgrant
```

Check backend TLS policy:

```bash
kubectl -n portal-services-dev get backendtlspolicy portal-services-audit-services-dev-btlsp
```

Check sticky routing policy if enabled:

```bash
kubectl -n common-gw-dev get backendtrafficpolicy portal-services-audit-services-dev-btp
```

Check whether the shared Gateway accepted the route:

```bash
kubectl -n common-gw-dev get gateway gw-dev
kubectl -n common-gw-dev describe gateway gw-dev
```

## Upgrade

Change values with `helm upgrade`:

```bash
helm upgrade portal-audit-dev . \
  --namespace common-gw-dev \
  --set group=portal-services \
  --set microservice=audit-services \
  --set env=dev \
  --set gateway.name=gw-dev \
  --set pathPrefix=/audit-v2 \
  --set backend.caSecretName=portal-backend-ca
```

If you only want to reuse the current values and move to a new chart version:

```bash
helm upgrade portal-audit-dev . \
  --namespace common-gw-dev \
  --reuse-values
```

## Uninstall

Uninstall the Helm release:

```bash
helm uninstall portal-audit-dev --namespace common-gw-dev
```

This removes resources owned by the release. It does not delete your backend Deployment, backend Service, backend namespace, Gateway namespace, or shared Gateway unless those were created and owned by this release.

## Troubleshooting

### Helm says `microservice`, `group`, or `env` is missing

These values are required. Pass them with `--set` or a values file.

```bash
--set group=portal-services \
--set microservice=audit-services \
--set env=dev
```

### Helm says `gateway.name` is missing

Set the Gateway name that the `HTTPRoute` should attach to:

```bash
--set gateway.name=gw-dev
```

### Helm says `backend.caSecretName` is missing

The schema currently requires this field. If backend TLS is enabled, provide the real CA Secret name. If backend TLS is disabled, provide a non-empty placeholder:

```bash
--set backend.tlsEnabled=false \
--set backend.caSecretName=unused
```

### HTTPRoute is created but traffic does not work

Check these in order:

```bash
kubectl -n common-gw-dev describe httproute portal-services-audit-services-dev-route
kubectl -n common-gw-dev describe gateway gw-dev
kubectl -n portal-services-dev get svc service-audit-services
kubectl -n portal-services-dev get referencegrant portal-services-audit-services-dev-refgrant
```

Common causes:

| Symptom | Likely cause |
| --- | --- |
| Route is not accepted | Wrong `gateway.name` or listener name. |
| Backend reference is not resolved | Missing `ReferenceGrant`, wrong backend namespace, or wrong Service name. |
| TLS validation fails | Missing CA Secret, wrong `backend.hostname`, or backend certificate mismatch. |
| 404 from Envoy | Path prefix does not match the request path. |

### BackendTrafficPolicy fails to install

The Envoy Gateway `BackendTrafficPolicy` CRD is probably missing.

Check:

```bash
kubectl get crd backendtrafficpolicies.gateway.envoyproxy.io
```

Either install the Envoy Gateway extension CRDs or disable sticky routing:

```bash
--set backendTrafficPolicy.create=false
```

## Files In This Chart

| File | Purpose |
| --- | --- |
| [Chart.yaml](Chart.yaml) | Helm chart metadata. |
| [values.yaml](values.yaml) | Default values. |
| [values.schema.json](values.schema.json) | Helm values validation. |
| [templates/_helpers.tpl](templates/_helpers.tpl) | Naming and label helpers. |
| [templates/httproute.yaml](templates/httproute.yaml) | Main `HTTPRoute`. |
| [templates/referencegrant.yaml](templates/referencegrant.yaml) | Cross-namespace backend reference permission. |
| [templates/backendtlspolicy.yaml](templates/backendtlspolicy.yaml) | Backend TLS validation policy. |
| [templates/backendtrafficpolicy.yaml](templates/backendtrafficpolicy.yaml) | Optional sticky routing policy. |
| [templates/gateway.yaml](templates/gateway.yaml) | Optional Gateway. |
| [templates/NOTES.txt](templates/NOTES.txt) | Post-install notes. |

## Minimal Values File

Create `my-service-values.yaml`:

```yaml
group: portal-services
microservice: audit-services
env: dev

gateway:
  name: gw-dev

backend:
  caSecretName: portal-backend-ca
```

Install with:

```bash
helm upgrade --install portal-audit-dev . \
  --namespace common-gw-dev \
  --create-namespace \
  -f my-service-values.yaml
```
