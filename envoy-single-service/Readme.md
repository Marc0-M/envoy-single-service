# envoy-single-service Helm Chart

Expose a single microservice through Kubernetes Gateway API using Envoy Gateway.

This chart renders:
- `HTTPRoute` (always)
- `ReferenceGrant` (always)
- `BackendTLSPolicy` (only when `backend.tlsEnabled=true`)
- `Gateway` (only when `gateway.create=true`)
- `BackendTrafficPolicy` (only when `backendTrafficPolicy.create=true`)

## What This Chart Does

The chart routes traffic from a shared Gateway listener to one backend service.

Derived conventions in templates:
- Gateway namespace: `common-gw-<env>`
- Backend namespace: `<group>-<env>`
- Default backend service name: `service-<microservice>`
- Default path prefix: `/<microservice>`

## Envoy Gateway Shared Prerequisites

This guide captures the shared setup needed before deploying `envoy-single-service` releases with Jenkins or Helm.

The chart assumes each subenvironment has:

- a shared Gateway namespace named `common-gw-<env>`
- a Gateway named `gw-<env>` in that namespace
- a TLS Secret named `gateway-tls-secret` in the same namespace as the Gateway
- backend CA Secrets in each backend application namespace when backend TLS validation is enabled
- optional AWS LoadBalancer annotations on the Envoy Gateway Service that receives external or internal traffic

Examples below use the `accp` family, which expands to:

```text
accp, accpb, accpc
```

### Recommended Order

1. Confirm Gateway API and Envoy Gateway are installed.
2. Create the `common-gw-<env>` namespaces.
3. Create or refresh the `gateway-tls-secret` TLS Secret in each Gateway namespace.
4. Create the Gateway object in each Gateway namespace.
5. Create backend CA Secrets in each backend namespace.
6. Add AWS LoadBalancer annotations to the actual Envoy Gateway LoadBalancer Service, if required.
7. Validate that Gateway, Secret, and backend CA resources exist before deploying microservice routes.

### 1. Gateway Namespaces

Use `kubectl apply` style commands so the step can be safely repeated:

```bash
for env in accp accpb accpc; do
  kubectl create namespace "common-gw-${env}" --dry-run=client -o yaml | kubectl apply -f -
done
```

Avoid plain `kubectl create ns ...` in repeatable runbooks or pipelines because it fails when the namespace already exists.

### 2. Gateway TLS Secret

The Gateway listener references a Kubernetes TLS Secret named `gateway-tls-secret`.

The Secret must exist in the same namespace as the Gateway unless you intentionally configure cross-namespace references with `ReferenceGrant`. Our standard setup keeps the Secret and Gateway together.

```bash
for env in accp accpb accpc; do
  kubectl -n "common-gw-${env}" create secret tls gateway-tls-secret \
    --cert=tls.crt \
    --key=tls.key \
    --dry-run=client -o yaml | kubectl apply -f -
done
```

Expected Secret type:

```bash
kubectl -n common-gw-accp get secret gateway-tls-secret -o jsonpath='{.type}{"\n"}'
```

Expected output:

```text
kubernetes.io/tls
```

### 3. Gateway Objects

Each subenvironment gets one Gateway in its matching `common-gw-<env>` namespace.

Example for `accpb`:

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

Apply one Gateway per subenvironment:

```bash
kubectl apply -f accp-gw.yaml
kubectl apply -f accpb-gw.yaml
kubectl apply -f accpc-gw.yaml
```

Or generate them with the optional bootstrap script described later in this guide.

Validation:

```bash
kubectl -n common-gw-accp get gateway gw-accp
kubectl -n common-gw-accpb get gateway gw-accpb
kubectl -n common-gw-accpc get gateway gw-accpc
kubectl -n common-gw-accp describe gateway gw-accp
```

Look for `Accepted=True` and `Programmed=True` when the controller has reconciled the Gateway.

### 4. Backend CA Secrets

When the chart uses `backend.tlsEnabled=true`, `BackendTLSPolicy` expects a CA bundle Secret in the backend namespace.

The Secret must contain the file key `ca.crt`.

Standard backend CA secret mapping:

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

Example for `accp`:

```bash
kubectl -n annuity-services-accp create secret generic annuity-backend-ca --from-file=ca.crt=./ca.crt --dry-run=client -o yaml | kubectl apply -f -
kubectl -n digtran-services-accp create secret generic digtran-backend-ca --from-file=ca.crt=./ca.crt --dry-run=client -o yaml | kubectl apply -f -
kubectl -n document-services-accp create secret generic document-backend-ca --from-file=ca.crt=./ca.crt --dry-run=client -o yaml | kubectl apply -f -
kubectl -n garwin-int-apps-accp create secret generic garwin-backend-ca --from-file=ca.crt=./ca.crt --dry-run=client -o yaml | kubectl apply -f -
kubectl -n garwin-services-accp create secret generic garwin-backend-ca --from-file=ca.crt=./ca.crt --dry-run=client -o yaml | kubectl apply -f -
kubectl -n generic-internal-service-accp create secret generic generic-backend-ca --from-file=ca.crt=./ca.crt --dry-run=client -o yaml | kubectl apply -f -
kubectl -n lifecad-services-accp create secret generic lifecad-backend-ca --from-file=ca.crt=./ca.crt --dry-run=client -o yaml | kubectl apply -f -
kubectl -n portal-services-accp create secret generic portal-backend-ca --from-file=ca.crt=./ca.crt --dry-run=client -o yaml | kubectl apply -f -
```

Repeat the same pattern for `accpb` and `accpc` if those backend namespaces exist.

Validation example:

```bash
kubectl -n portal-services-accp get secret portal-backend-ca -o jsonpath='{.data.ca\.crt}{"\n"}' | wc -c
```

The byte count should be greater than zero.

### 5. AWS LoadBalancer Service Annotations

These annotations belong on the Kubernetes `Service` that exposes Envoy Gateway, not on the `Gateway`, `HTTPRoute`, or backend application Service unless that Service is intentionally the LoadBalancer.

First identify the Service that owns the AWS LoadBalancer:

```bash
kubectl get svc -A | grep -E 'LoadBalancer|envoy|gateway'
```

Then annotate the correct Service:

```bash
kubectl -n <service-namespace> annotate service <service-name> \
  service.beta.kubernetes.io/aws-load-balancer-access-log-enabled="true" \
  service.beta.kubernetes.io/aws-load-balancer-access-log-s3-bucket-name="ven-accp-lb-logging" \
  service.beta.kubernetes.io/aws-load-balancer-access-log-s3-bucket-prefix="k8s-eg-accpc" \
  service.beta.kubernetes.io/aws-load-balancer-backend-protocol="ssl" \
  service.beta.kubernetes.io/aws-load-balancer-cross-zone-load-balancing-enabled="true" \
  service.beta.kubernetes.io/aws-load-balancer-internal="true" \
  service.beta.kubernetes.io/aws-load-balancer-security-groups="sg-0e0b2323db8b91d02" \
  service.beta.kubernetes.io/aws-load-balancer-ssl-cert="arn:aws:acm:us-east-1:895013107628:certificate/31ac8bed-d83b-4219-b4ef-737b44ff2fdd" \
  service.beta.kubernetes.io/aws-load-balancer-ssl-ports="443" \
  service.beta.kubernetes.io/aws-load-balancer-subnets="subnet-063c61aa2ac7d7fbc,subnet-03a3db0d2b37568b2" \
  service.beta.kubernetes.io/aws-load-balancer-type="nlb-ip" \
  --overwrite
```

Important TLS note:

- If the AWS NLB terminates TLS with ACM and then connects to Envoy with SSL, the `aws-load-balancer-ssl-cert`, `aws-load-balancer-ssl-ports`, and `aws-load-balancer-backend-protocol=ssl` annotations are expected.
- If Envoy Gateway should be the only TLS termination point, use NLB TCP pass-through style configuration instead and avoid accidentally double-terminating TLS.
- Keep the TLS model consistent with the Gateway listener. The sample Gateway above uses `protocol: HTTPS` and `tls.mode: Terminate`, which means Envoy expects TLS on the listener.

The exact annotation set is environment-specific because S3 buckets, subnets, security groups, and ACM certificate ARNs are different per account and cluster.

### 6. Optional Bootstrap Script

The repo root includes an optional script:

```bash
./bootstrap_envoy_prereqs.sh
```

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

Apply for `accp`, `accpb`, and `accpc`:

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

To annotate Envoy Gateway LoadBalancer Services, create an annotation file:

```bash
cat > accp-lb-annotations.env <<'EOF_ANNOTATIONS'
service.beta.kubernetes.io/aws-load-balancer-access-log-enabled=true
service.beta.kubernetes.io/aws-load-balancer-access-log-s3-bucket-name=ven-accp-lb-logging
service.beta.kubernetes.io/aws-load-balancer-access-log-s3-bucket-prefix=k8s-eg-{env}
service.beta.kubernetes.io/aws-load-balancer-backend-protocol=ssl
service.beta.kubernetes.io/aws-load-balancer-cross-zone-load-balancing-enabled=true
service.beta.kubernetes.io/aws-load-balancer-internal=true
service.beta.kubernetes.io/aws-load-balancer-security-groups=sg-0e0b2323db8b91d02
service.beta.kubernetes.io/aws-load-balancer-ssl-cert=arn:aws:acm:us-east-1:895013107628:certificate/31ac8bed-d83b-4219-b4ef-737b44ff2fdd
service.beta.kubernetes.io/aws-load-balancer-ssl-ports=443
service.beta.kubernetes.io/aws-load-balancer-subnets=subnet-063c61aa2ac7d7fbc,subnet-03a3db0d2b37568b2
service.beta.kubernetes.io/aws-load-balancer-type=nlb-ip
EOF_ANNOTATIONS
```

Then run the script with explicit Service targets. The `{env}` placeholder is replaced with each target subenvironment:

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

Adjust `envoy-gateway-system/envoy-gateway-{env}` to the real Service namespace/name in your cluster.

### 7. Final Validation Checklist

Run these before deploying microservices through the chart:

```bash
for env in accp accpb accpc; do
  kubectl -n "common-gw-${env}" get secret gateway-tls-secret
  kubectl -n "common-gw-${env}" get gateway "gw-${env}"
  kubectl -n "common-gw-${env}" describe gateway "gw-${env}" | grep -E 'Accepted|Programmed|ResolvedRefs' || true
done
```

Check backend CA Secrets:

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

After microservice routes are deployed, run the validator:

```bash
python3 validate_envoy_resources.py --context accp --env accp
python3 validate_envoy_resources.py --context accp --env accpb
python3 validate_envoy_resources.py --context accp --env accpc
```

### Common Issues

- `Secret is not supplied by SDS`: confirm Envoy Gateway can read Secrets in Gateway and backend namespaces.
- `HTTPRoute Accepted=False`: check Gateway name, listener `sectionName`, and `ReferenceGrant` permissions.
- `BackendTLSPolicy ResolvedRefs=False`: confirm the CA Secret exists in the backend namespace and contains `ca.crt`.
- Gateway has no public/internal endpoint: confirm the correct LoadBalancer Service was annotated and that AWS subnets/security groups/ACM ARN are correct for the target account.

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

