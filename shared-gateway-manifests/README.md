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
- `01-clienttrafficpolicy.yaml`: trusts `X-Forwarded-For` on the shared `Gateway`
- `02-envoyextensionpolicy.yaml`: copies `X-Forwarded-For` into `X-Original-Forwarded-For` with a gateway-wide Lua filter

Recommended apply order:
1. Apply `01-clienttrafficpolicy.yaml`.
2. Apply `02-envoyextensionpolicy.yaml`.
3. Test a valid routed URL and confirm the backend receives both `X-Forwarded-For` and `X-Original-Forwarded-For`.

Helpful lookups:
```bash
kubectl get svc -n envoy-system | grep "common-gw-<env>"
kubectl get clienttrafficpolicy -n common-gw-<env> trust-all-xff -o yaml
kubectl get envoyextensionpolicy -n common-gw-<env> copy-xff-to-xoff -o yaml
```
