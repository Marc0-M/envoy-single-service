# Shared Gateway Manifests

This folder contains reusable manifests for the shared Gateways in:
- `dev`
- `devb`
- `devc`
- `intg`
- `intgb`
- `intgc`
- `accp`
- `accpb`
- `accpc`
- `proda`
- `prodb`
- `dr`

Each environment folder contains:
- `00-envoy-service-annotation.yaml`: template to enable NLB client IP preservation on the generated Envoy `Service` in `envoy-system`
- `01-clienttrafficpolicy.yaml`: trusts `X-Forwarded-For` on the shared `Gateway`
- `02-envoyextensionpolicy.yaml`: copies `X-Forwarded-For` into `X-Original-Forwarded-For` with a gateway-wide Lua filter

Recommended apply order:
1. Replace `metadata.name` in `00-envoy-service-annotation.yaml` with the generated Envoy `Service` name for that Gateway.
2. Apply `00-envoy-service-annotation.yaml`.
3. Apply `01-clienttrafficpolicy.yaml`.
4. Apply `02-envoyextensionpolicy.yaml`.
5. Test a valid routed URL and confirm the backend receives both `X-Forwarded-For` and `X-Original-Forwarded-For`.

Helpful lookups:
```bash
kubectl get svc -n envoy-system | grep "common-gw-<env>"
kubectl get clienttrafficpolicy -n common-gw-<env> trust-all-xff -o yaml
kubectl get envoyextensionpolicy -n common-gw-<env> copy-xff-to-xoff -o yaml
```
