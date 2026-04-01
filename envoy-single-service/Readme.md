# envoy-single-service Helm Chart

Expose a single microservice through Kubernetes Gateway API using Envoy Gateway.

This chart renders:
- `HTTPRoute` (always)
- `ReferenceGrant` (always)
- `BackendTLSPolicy` (only when `backend.tlsEnabled=true`)
- `Gateway` (only when `gateway.create=true`)

## What This Chart Does

The chart routes traffic from a shared Gateway listener to one backend service.

Derived conventions in templates:
- Gateway namespace: `common-gw-<env>`
- Backend namespace: `<group>-<env>`
- Default backend service name: `service-<microservice>`
- Default path prefix: `/<microservice>`

## Prerequisites

1. Gateway API CRDs available in the cluster (GatwayClass & Gateway [Optional because it is included in the chart]).
2. Envoy Gateway installed (controller running).
3. Existing namespaces:
   - `common-gw-<env>`
   - `<group>-<env>`
4. Existing backend Kubernetes Service in `<group>-<env>`.
5. If `backend.tlsEnabled=true`, a CA secret must exist in `<group>-<env>`.
```bash
kubectl -n garwin-services-devc create secret generic garwin-backend-ca --from-file=ca.crt=./ca.crt
```
## Install Gateway API + Envoy Gateway

### Install with Envoy Gateway Helm chart (includes CRDs)

```bash
ENVOY_GATEWAY_VERSION=v1.7.0

helm install eg oci://docker.io/envoyproxy/gateway-helm \
  --version ${ENVOY_GATEWAY_VERSION} \
  -n envoy-gateway-system \
  --create-namespace

kubectl wait --timeout=5m -n envoy-gateway-system deployment/envoy-gateway --for=condition=Available
```

### Quick Control Plane Validation

```bash
kubectl get gatewayclass
kubectl get crd gateways.gateway.networking.k8s.io
kubectl get crd httproutes.gateway.networking.k8s.io
kubectl get crd referencegrants.gateway.networking.k8s.io
kubectl get crd backendtlspolicies.gateway.networking.k8s.io
```

## Chart Inputs

### Required values

- `microservice` (string)
- `group` (string)
- `env` (one of: `dev`, `devb`, `devc`, `intg`, `intgb`, `intgc`, `accp`, `accpb`, `accpc`, `proda`, `prodb`)
- `gateway.name` (string)
- `backend.caSecretName` (string)

### Important optional values

- `svc`: override backend Service name (default: `service-<microservice>`)
- `pathPrefix`: override route path (default: `/<microservice>`)
- `gateway.create`: create Gateway resource from this chart (`false` by default)
- `gateway.listenerName`: listener section on parent Gateway (default: `https`)
- `backend.port`: backend Service port (default: `443`)
- `backend.tlsEnabled`: create `BackendTLSPolicy` (default: `true`)
- `backend.hostname`: backend TLS SNI/hostname for validation (default: `*`)

## Deploy This Chart

### Validate the OCI chart from Artifactory (recommended)

```bash
helm registry login http://artifactory.tools.vaapps.net \
  --username "${USERNAME}" \
  --password "${TOKEN}"

helm show chart oci://artifactory.tools.vaapps.net/envoy-single-service/envoy-single-service --version 0.1.0
helm show values oci://artifactory.tools.vaapps.net/envoy-single-service/envoy-single-service --version 0.1.0

helm template preview oci://artifactory.tools.vaapps.net/envoy-single-service/envoy-single-service \
  --version 0.1.0 \
  --set env=devc \
  --set group=digtran-services \
  --set microservice=admin-common-services \
  --set gateway.name=https-gw-devc \
  --set backend.caSecretName=digtran-backend-ca \
  --set backend.hostname=dts-nlb-eks-c.dev.vaapps.net

helm upgrade --install preview oci://artifactory.tools.vaapps.net/envoy-single-service/envoy-single-service \
  --version 0.1.0 \
  --set env=devc \
  --set group=digtran-services \
  --set microservice=admin-common-services \
  --set gateway.name=https-gw-devc \
  --set backend.caSecretName=digtran-backend-ca \
  --set backend.hostname=dts-nlb-eks-c.dev.vaapps.net \
  --dry-run --debug

helm template preview oci://artifactory.tools.vaapps.net/envoy-single-service/envoy-single-service \
  --version 0.1.0 \
  --set env=devc \
  --set group=digtran-services \
  --set microservice=admin-common-services \
  --set gateway.name=https-gw-devc \
  --set backend.caSecretName=digtran-backend-ca \
  --set backend.hostname=dts-nlb-eks-c.dev.vaapps.net \
| kubectl apply --dry-run=server -f -
```

If you want to run `helm lint`, pull the OCI chart locally first:

```bash
helm pull oci://artifactory.tools.vaapps.net/envoy-single-service/envoy-single-service --version 0.1.0 --untar
helm lint envoy-single-service
```

### Install/upgrade

```bash
helm upgrade --install <release-name> oci://artifactory.tools.vaapps.net/envoy-single-service/envoy-single-service \
  --version 0.1.0 \
  --set env=<env> \
  --set group=<group> \
  --set microservice=<microservice> \
  --set gateway.name=<gateway-name> \
  --set backend.caSecretName=<ca-secret> \
  --set backend.hostname=<backend-hostname>
```

## Existing Commands

### Example 1

```bash
helm install admin-common-services-devc oci://artifactory.tools.vaapps.net/envoy-single-service/envoy-single-service   --version 0.1.0 --set microservice=admin-common-services --set group=digtran-services --set env=devc --set gateway.name=https-gw-devc   --set backend.caSecretName=digtran-backend-ca   --set backend.hostname=dts-nlb-eks-c.dev.vaapps.net
```

### Example 2

```bash
helm install report-services-devc oci://artifactory.tools.vaapps.net/envoy-single-service/envoy-single-service --set env=devc --set group=garwin-services   --set microservice=report-services  --set gateway.name=https-gw-devc  --set backend.port=443 --set backend.tlsEnabled=true --set backend.caSecretName=garwin-backend-ca --set backend.hostname=dts-grwn-nlb-eks-c.dev.vaapps.net --set pathPrefix=/grwn-report-services --set svc=service-garwin-report-services
```

## Verify Installation

Replace placeholders with your values:

```bash
kubectl -n common-gw-<env> get httproute
kubectl -n <group>-<env> get referencegrant
kubectl -n <group>-<env> get backendtlspolicy

kubectl -n common-gw-<env> describe httproute <group>-<microservice>-<env>-route
```

## Notes and Troubleshooting

1. The chart does not create namespaces.
2. `HTTPRoute` is created in the gateway namespace and points to a Service in another namespace; `ReferenceGrant` is required for this cross-namespace reference.
3. If using an existing shared Gateway (`gateway.create=false`), ensure:
   - Gateway exists in `common-gw-<env>`
   - Listener `sectionName` matches `gateway.listenerName`
4. If backend TLS is enabled, confirm the CA secret name is correct and present in `<group>-<env>`.

