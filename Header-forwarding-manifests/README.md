# Shared Gateway Manifests

This folder contains reusable Gateway-level manifests for:
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

These manifests are prerequisites for shared Envoy Gateway behavior. They are not part of an individual `envoy-single-service` Helm release.

Each environment folder contains:
- `00-envoyproxy.yaml`: configures the generated Envoy Gateway LoadBalancer `Service` annotations, including AWS NLB settings and `preserve_client_ip.enabled=true`
- `01-clienttrafficpolicy.yaml`: trusts incoming `X-Forwarded-For` on the shared `Gateway`
- `02-envoyextensionpolicy.yaml`: copies `X-Forwarded-For` into `X-Original-Forwarded-For` with a gateway-wide Lua filter

Recommended apply order:
1. Confirm the target cluster/context and review `00-envoyproxy.yaml` values for that environment.
2. Apply `00-envoyproxy.yaml`.
3. Attach the `EnvoyProxy` to the shared `Gateway`.
4. Apply `01-clienttrafficpolicy.yaml`.
5. Apply `02-envoyextensionpolicy.yaml`.
6. Test a valid routed URL and confirm the backend receives both `X-Forwarded-For` and `X-Original-Forwarded-For`.

Attach command:
```bash
kubectl -n common-gw-<env> patch gateway gw-<env> --type merge -p '{
  "spec": {
    "infrastructure": {
      "parametersRef": {
        "group": "gateway.envoyproxy.io",
        "kind": "EnvoyProxy",
        "name": "envoy-aws-nlb-service-<env>"
      }
    }
  }
}'
```

Apply example:
```bash
kubectl apply -f shared-gateway-manifests/<env>/00-envoyproxy.yaml
kubectl -n common-gw-<env> patch gateway gw-<env> --type merge -p '{"spec":{"infrastructure":{"parametersRef":{"group":"gateway.envoyproxy.io","kind":"EnvoyProxy","name":"envoy-aws-nlb-service-<env>"}}}}'
kubectl apply -f shared-gateway-manifests/<env>/01-clienttrafficpolicy.yaml
kubectl apply -f shared-gateway-manifests/<env>/02-envoyextensionpolicy.yaml
```

Helpful lookups:
```bash
kubectl get envoyproxy -n common-gw-<env> envoy-aws-nlb-service-<env> -o yaml
kubectl get gateway -n common-gw-<env> gw-<env> -o yaml
kubectl get svc -n envoy-system | grep "common-gw-<env>"
kubectl get svc -n envoy-system <generated-envoy-service-name> -o yaml | grep -A 14 annotations
kubectl get clienttrafficpolicy -n common-gw-<env> trust-all-xff -o yaml
kubectl get envoyextensionpolicy -n common-gw-<env> copy-xff-to-xoff -o yaml
```

Header test:
```bash
curl -vk "https://<gateway-host>/<valid-path>" \
  -H "x-request-id: header-test-001" \
  -H "x-forwarded-for: 198.51.100.10, 203.0.113.20"

kubectl logs -n envoy-system <envoy-gateway-pod> | grep header-test-001
```

Expected behavior:
- `X-Forwarded-For` is trusted by Envoy Gateway.
- `X-Original-Forwarded-For` is created from `X-Forwarded-For`.
- The generated Envoy `Service` keeps the AWS NLB annotations from `00-envoyproxy.yaml`.

Notes:
- All environment folders now include concrete AWS NLB annotation values captured for this repo.
- `prodb` currently uses the same values as `proda`; update it if that subenvironment has separate NLB annotation values.
- `dr` uses `us-west-2` annotation values and is intentionally separate from `proda` and `prodb`.
- If the generated Service does not show the expected annotations after patching the Gateway, check Gateway status and Envoy Gateway controller logs. Use `annotate_envoy_services_preserve_client_ip.sh` only as a temporary repair helper, not as the permanent source of truth.
