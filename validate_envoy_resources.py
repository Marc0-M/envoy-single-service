
"""Validate envoy-single-service resources created by the Jenkins pipeline.

The script discovers chart-created HTTPRoutes, ReferenceGrants, and
BackendTLSPolicies across the cluster, validates their referenced Gateways,
Secrets, and Services, and reports whether the installed resources look healthy.

Examples:
  ./validate_envoy_resources.py
  ./validate_envoy_resources.py --env devb
  ./validate_envoy_resources.py --context dev
"""

import argparse
import json
import subprocess
import sys
from collections import defaultdict
from typing import Dict, Iterable, List, Optional, Sequence, Tuple


CHART_LABEL = "helm.sh/chart"
CHART_PREFIX = "envoy-single-service-"
MANAGED_BY_LABEL = "app.kubernetes.io/managed-by"
APP_NAME_LABEL = "app.kubernetes.io/name"


def run_kubectl(args: Sequence[str]) -> dict:
    try:
        completed = subprocess.run(
            ["kubectl", *args],
            check=True,
            capture_output=True,
            text=True,
        )
    except subprocess.CalledProcessError as exc:
        stderr = exc.stderr.strip() or exc.stdout.strip() or str(exc)
        print(f"ERROR: kubectl {' '.join(args)} failed: {stderr}", file=sys.stderr)
        sys.exit(2)

    try:
        return json.loads(completed.stdout)
    except json.JSONDecodeError as exc:
        print(
            f"ERROR: failed to parse kubectl {' '.join(args)} JSON output: {exc}",
            file=sys.stderr,
        )
        sys.exit(2)


def suffix_strip(value: str, suffix: str) -> str:
    return value[: -len(suffix)] if value.endswith(suffix) else value


def base_name(kind: str, name: str) -> str:
    if kind == "HTTPRoute":
        return suffix_strip(name, "-route")
    if kind == "ReferenceGrant":
        return suffix_strip(name, "-refgrant")
    if kind == "BackendTLSPolicy":
        return suffix_strip(name, "-btlsp")
    return name


def chart_managed(item: dict) -> bool:
    labels = item.get("metadata", {}).get("labels", {})
    chart = labels.get(CHART_LABEL, "")
    return chart.startswith(CHART_PREFIX) and labels.get(MANAGED_BY_LABEL) == "Helm"


def release_key(kind: str, item: dict) -> str:
    labels = item.get("metadata", {}).get("labels", {})
    app_name = labels.get(APP_NAME_LABEL, "")
    if app_name:
        return app_name

    metadata = item.get("metadata", {})
    return base_name(kind, metadata.get("name", ""))


def env_matches(namespace: str, env_filter: Optional[str]) -> bool:
    if not env_filter:
        return True
    return namespace.endswith(f"-{env_filter}") or namespace == f"common-gw-{env_filter}"


def get_condition(conditions: Iterable[dict], cond_type: str) -> Optional[dict]:
    for condition in conditions or []:
        if condition.get("type") == cond_type:
            return condition
    return None


def is_true_condition(conditions: Iterable[dict], cond_type: str) -> bool:
    condition = get_condition(conditions, cond_type)
    return bool(condition and condition.get("status") == "True")


def format_issue(level: str, message: str) -> str:
    return f"[{level}] {message}"


def lookup_index(items: Iterable[dict]) -> Dict[Tuple[str, str], dict]:
    index: Dict[Tuple[str, str], dict] = {}
    for item in items:
        meta = item.get("metadata", {})
        index[(meta.get("namespace", ""), meta.get("name", ""))] = item
    return index


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Validate envoy-single-service resources across namespaces."
    )
    parser.add_argument(
        "--env",
        help="Only validate resources for a specific environment such as devb or devc.",
    )
    parser.add_argument(
        "--context",
        help="Optional kubectl context to use.",
    )
    parser.add_argument(
        "--export-ok",
        action="store_true",
        help="Print OK checks in addition to warnings and failures.",
    )
    return parser.parse_args()


def get_cluster_data(context: Optional[str]) -> Dict[str, dict]:
    context_args: List[str] = ["--context", context] if context else []
    return {
        "httproutes": run_kubectl([*context_args, "get", "httproutes.gateway.networking.k8s.io", "-A", "-o", "json"]),
        "referencegrants": run_kubectl([*context_args, "get", "referencegrants.gateway.networking.k8s.io", "-A", "-o", "json"]),
        "backendtlspolicies": run_kubectl([*context_args, "get", "backendtlspolicies.gateway.networking.k8s.io", "-A", "-o", "json"]),
        "gateways": run_kubectl([*context_args, "get", "gateways.gateway.networking.k8s.io", "-A", "-o", "json"]),
        "services": run_kubectl([*context_args, "get", "services", "-A", "-o", "json"]),
        "secrets": run_kubectl([*context_args, "get", "secrets", "-A", "-o", "json"]),
    }


def discover_releases(data: Dict[str, dict], env_filter: Optional[str]) -> Dict[str, dict]:
    releases: Dict[str, dict] = defaultdict(lambda: {"route": None, "refgrant": None, "btlsp": None})

    resources = [
        ("route", "HTTPRoute", data["httproutes"].get("items", [])),
        ("refgrant", "ReferenceGrant", data["referencegrants"].get("items", [])),
        ("btlsp", "BackendTLSPolicy", data["backendtlspolicies"].get("items", [])),
    ]

    for resource_key, kind, items in resources:
        for item in items:
            namespace = item.get("metadata", {}).get("namespace", "")
            if not chart_managed(item) or not env_matches(namespace, env_filter):
                continue
            releases[release_key(kind, item)][resource_key] = item

    return releases


def first_resource(release: dict) -> Optional[dict]:
    for key in ("btlsp", "refgrant", "route"):
        resource = release.get(key)
        if resource:
            return resource
    return None


def backend_namespace(release: dict) -> str:
    if release.get("btlsp"):
        return release["btlsp"]["metadata"]["namespace"]
    if release.get("refgrant"):
        return release["refgrant"]["metadata"]["namespace"]
    route = release.get("route")
    if route:
        for rule in route.get("spec", {}).get("rules", []):
            for backend_ref in rule.get("backendRefs", []):
                return backend_ref.get("namespace", route["metadata"]["namespace"])
    return "<unknown>"


def infer_env(release: dict) -> str:
    namespace = backend_namespace(release)
    if "-" in namespace:
        return namespace.rsplit("-", 1)[-1]
    return ""


def infer_microservice_name(release_key: str, release: dict) -> str:
    resource = first_resource(release)
    if resource:
        instance = resource.get("metadata", {}).get("labels", {}).get("app.kubernetes.io/instance", "")
        env_name = infer_env(release)
        if instance and env_name and instance.endswith(f"-{env_name}"):
            return instance[: -(len(env_name) + 1)]
        if instance:
            return instance

    route = release.get("route")
    if route:
        for rule in route.get("spec", {}).get("rules", []):
            for backend_ref in rule.get("backendRefs", []):
                service_name = backend_ref.get("name", "")
                if service_name.startswith("service-"):
                    return service_name[len("service-") :]
                if service_name:
                    return service_name

    return release_key


def gateway_names(release: dict) -> str:
    route = release.get("route")
    if not route:
        return "-"
    names = sorted({ref.get("name", "") for ref in route.get("spec", {}).get("parentRefs", []) if ref.get("name")})
    return ",".join(names) if names else "-"


def route_uris(release: dict) -> str:
    route = release.get("route")
    if not route:
        return "-"
    values: List[str] = []
    for rule in route.get("spec", {}).get("rules", []):
        for match in rule.get("matches", []):
            path = match.get("path", {}).get("value")
            if path and path not in values:
                values.append(path)
    return ",".join(values) if values else "-"


def backend_host(release: dict) -> str:
    btlsp = release.get("btlsp")
    if not btlsp:
        return "-"
    return btlsp.get("spec", {}).get("validation", {}).get("hostname", "-")


def crd_count(release: dict) -> int:
    return sum(1 for key in ("route", "refgrant", "btlsp") if release.get(key))


def summarize_status(issue_messages: Sequence[str]) -> str:
    if any(message.startswith("[FAIL]") for message in issue_messages):
        return "FAIL"
    if any(message.startswith("[WARN]") for message in issue_messages):
        return "WARN"
    return "OK"


def print_inventory(namespace_groups: Dict[str, List[dict]]) -> None:
    headers = [
        ("MICROSERVICE", 34),
        ("ALL_3_CRDS", 10),
        ("CRDS", 5),
        ("GATEWAY", 22),
        ("ROUTE_URI", 26),
        ("BACKEND_HOST", 42),
        ("STATUS", 6),
    ]

    for namespace in sorted(namespace_groups):
        print(f"\nNamespace: {namespace}")
        header_line = "  ".join(label.ljust(width) for label, width in headers)
        print(header_line)
        print("  ".join("-" * width for _, width in headers))

        for entry in sorted(namespace_groups[namespace], key=lambda item: item["microservice"]):
            row = [
                entry["microservice"][:34].ljust(34),
                ("yes" if entry["all_three"] else "no").ljust(10),
                f"{entry['crd_count']}/3".ljust(5),
                entry["gateway"][:22].ljust(22),
                entry["route_uri"][:26].ljust(26),
                entry["backend_host"][:42].ljust(42),
                entry["status"].ljust(6),
            ]
            print("  ".join(row))


def validate_release(
    release_key: str,
    release: dict,
    service_index: Dict[Tuple[str, str], dict],
    secret_index: Dict[Tuple[str, str], dict],
    gateway_index: Dict[Tuple[str, str], dict],
) -> Tuple[List[str], List[str]]:
    ok: List[str] = []
    issues: List[str] = []

    route = release.get("route")
    refgrant = release.get("refgrant")
    btlsp = release.get("btlsp")

    if not route:
        issues.append(format_issue("FAIL", f"{release_key}: missing HTTPRoute"))
        return ok, issues
    ok.append(f"{release_key}: HTTPRoute exists in {route['metadata']['namespace']}")

    if not refgrant:
        issues.append(format_issue("FAIL", f"{release_key}: missing ReferenceGrant"))
    else:
        ok.append(f"{release_key}: ReferenceGrant exists in {refgrant['metadata']['namespace']}")

    route_ns = route["metadata"]["namespace"]
    route_name = route["metadata"]["name"]

    parent_refs = route.get("spec", {}).get("parentRefs", [])
    if not parent_refs:
        issues.append(format_issue("FAIL", f"{release_key}: HTTPRoute has no parentRefs"))
    else:
        for parent_ref in parent_refs:
            gateway_name = parent_ref.get("name")
            gateway_ns = parent_ref.get("namespace", route_ns)
            gateway = gateway_index.get((gateway_ns, gateway_name))
            if not gateway:
                issues.append(
                    format_issue(
                        "FAIL",
                        f"{release_key}: referenced Gateway {gateway_ns}/{gateway_name} does not exist",
                    )
                )
                continue

            gateway_conditions = gateway.get("status", {}).get("conditions", [])
            if is_true_condition(gateway_conditions, "Accepted"):
                ok.append(f"{release_key}: Gateway {gateway_ns}/{gateway_name} Accepted=True")
            else:
                issues.append(
                    format_issue(
                        "FAIL",
                        f"{release_key}: Gateway {gateway_ns}/{gateway_name} Accepted is not True",
                    )
                )

            programmed_condition = get_condition(gateway_conditions, "Programmed")
            if programmed_condition and programmed_condition.get("status") != "True":
                issues.append(
                    format_issue(
                        "WARN",
                        f"{release_key}: Gateway {gateway_ns}/{gateway_name} Programmed={programmed_condition.get('status')} ({programmed_condition.get('reason')}: {programmed_condition.get('message')})",
                    )
                )
            elif programmed_condition:
                ok.append(f"{release_key}: Gateway {gateway_ns}/{gateway_name} Programmed=True")

            for listener in gateway.get("spec", {}).get("listeners", []):
                tls = listener.get("tls", {})
                for cert_ref in tls.get("certificateRefs", []):
                    if cert_ref.get("kind", "Secret") != "Secret":
                        continue
                    cert_name = cert_ref.get("name")
                    cert_ns = cert_ref.get("namespace", gateway_ns)
                    if secret_index.get((cert_ns, cert_name)):
                        ok.append(f"{release_key}: listener secret {cert_ns}/{cert_name} exists")
                    else:
                        issues.append(
                            format_issue(
                                "FAIL",
                                f"{release_key}: listener secret {cert_ns}/{cert_name} is missing",
                            )
                        )

    route_status_parents = route.get("status", {}).get("parents", [])
    if route_status_parents:
        route_accepted = any(
            is_true_condition(parent.get("conditions", []), "Accepted")
            for parent in route_status_parents
        )
        route_resolved = any(
            is_true_condition(parent.get("conditions", []), "ResolvedRefs")
            for parent in route_status_parents
        )
        if route_accepted:
            ok.append(f"{release_key}: HTTPRoute Accepted=True")
        else:
            issues.append(format_issue("FAIL", f"{release_key}: HTTPRoute Accepted is not True"))
        if route_resolved:
            ok.append(f"{release_key}: HTTPRoute ResolvedRefs=True")
        else:
            issues.append(format_issue("FAIL", f"{release_key}: HTTPRoute ResolvedRefs is not True"))
    else:
        issues.append(format_issue("WARN", f"{release_key}: HTTPRoute has no status.parents yet"))

    service_refs: List[Tuple[str, str]] = []
    for rule in route.get("spec", {}).get("rules", []):
        for backend_ref in rule.get("backendRefs", []):
            service_name = backend_ref.get("name")
            service_ns = backend_ref.get("namespace", route_ns)
            service_refs.append((service_ns, service_name))
            if service_index.get((service_ns, service_name)):
                ok.append(f"{release_key}: backend Service {service_ns}/{service_name} exists")
            else:
                issues.append(
                    format_issue(
                        "FAIL",
                        f"{release_key}: backend Service {service_ns}/{service_name} is missing",
                    )
                )

    if refgrant:
        grant_ns = refgrant["metadata"]["namespace"]
        grant_from = refgrant.get("spec", {}).get("from", [])
        grant_to = refgrant.get("spec", {}).get("to", [])
        route_allowed = any(
            entry.get("kind") == "HTTPRoute" and entry.get("namespace") == route_ns
            for entry in grant_from
        )
        if route_allowed:
            ok.append(f"{release_key}: ReferenceGrant allows HTTPRoute from {route_ns}")
        else:
            issues.append(
                format_issue(
                    "FAIL",
                    f"{release_key}: ReferenceGrant does not allow HTTPRoute from {route_ns}",
                )
            )

        for service_ns, service_name in service_refs:
            if service_ns != grant_ns:
                issues.append(
                    format_issue(
                        "FAIL",
                        f"{release_key}: backend Service {service_ns}/{service_name} does not match ReferenceGrant namespace {grant_ns}",
                    )
                )
                continue

            grant_matches = any(
                entry.get("kind") == "Service" and entry.get("name") == service_name
                for entry in grant_to
            )
            if grant_matches:
                ok.append(f"{release_key}: ReferenceGrant allows Service {grant_ns}/{service_name}")
            else:
                issues.append(
                    format_issue(
                        "FAIL",
                        f"{release_key}: ReferenceGrant does not allow Service {grant_ns}/{service_name}",
                    )
                )

    if btlsp:
        btlsp_ns = btlsp["metadata"]["namespace"]
        conditions_by_ancestor = btlsp.get("status", {}).get("ancestors", [])
        if conditions_by_ancestor:
            btlsp_accepted = any(
                is_true_condition(entry.get("conditions", []), "Accepted")
                for entry in conditions_by_ancestor
            )
            btlsp_resolved = any(
                is_true_condition(entry.get("conditions", []), "ResolvedRefs")
                for entry in conditions_by_ancestor
            )
            if btlsp_accepted:
                ok.append(f"{release_key}: BackendTLSPolicy Accepted=True")
            else:
                issues.append(format_issue("FAIL", f"{release_key}: BackendTLSPolicy Accepted is not True"))
            if btlsp_resolved:
                ok.append(f"{release_key}: BackendTLSPolicy ResolvedRefs=True")
            else:
                issues.append(format_issue("FAIL", f"{release_key}: BackendTLSPolicy ResolvedRefs is not True"))
        else:
            issues.append(format_issue("WARN", f"{release_key}: BackendTLSPolicy has no status.ancestors yet"))

        for target_ref in btlsp.get("spec", {}).get("targetRefs", []):
            if target_ref.get("kind") != "Service":
                continue
            service_name = target_ref.get("name")
            if service_index.get((btlsp_ns, service_name)):
                ok.append(f"{release_key}: BackendTLSPolicy target Service {btlsp_ns}/{service_name} exists")
            else:
                issues.append(
                    format_issue(
                        "FAIL",
                        f"{release_key}: BackendTLSPolicy target Service {btlsp_ns}/{service_name} is missing",
                    )
                )

        for cert_ref in btlsp.get("spec", {}).get("validation", {}).get("caCertificateRefs", []):
            if cert_ref.get("kind", "Secret") != "Secret":
                issues.append(
                    format_issue(
                        "WARN",
                        f"{release_key}: BackendTLSPolicy CA reference kind {cert_ref.get('kind')} not checked by this script",
                    )
                )
                continue
            secret_name = cert_ref.get("name")
            secret_ns = cert_ref.get("namespace", btlsp_ns)
            secret = secret_index.get((secret_ns, secret_name))
            if not secret:
                issues.append(
                    format_issue(
                        "FAIL",
                        f"{release_key}: BackendTLSPolicy secret {secret_ns}/{secret_name} is missing",
                    )
                )
                continue
            if "ca.crt" in secret.get("data", {}):
                ok.append(f"{release_key}: BackendTLSPolicy secret {secret_ns}/{secret_name} has ca.crt")
            else:
                issues.append(
                    format_issue(
                        "FAIL",
                        f"{release_key}: BackendTLSPolicy secret {secret_ns}/{secret_name} is missing ca.crt",
                    )
                )
    else:
        issues.append(format_issue("WARN", f"{release_key}: BackendTLSPolicy not found (TLS may be disabled)"))

    return ok, issues


def main() -> int:
    args = parse_args()
    data = get_cluster_data(args.context)

    service_index = lookup_index(data["services"].get("items", []))
    secret_index = lookup_index(data["secrets"].get("items", []))
    gateway_index = lookup_index(data["gateways"].get("items", []))
    releases = discover_releases(data, args.env)

    if not releases:
        if args.env:
            print(f"No chart-managed envoy-single-service resources found for env '{args.env}'.")
        else:
            print("No chart-managed envoy-single-service resources found.")
        return 0

    failures = 0
    warnings = 0
    checked = 0

    namespace_groups: Dict[str, List[dict]] = defaultdict(list)
    detailed_issues: List[Tuple[str, List[str], List[str]]] = []

    for release_key in sorted(releases):
        checked += 1
        ok_messages, issue_messages = validate_release(
            release_key,
            releases[release_key],
            service_index,
            secret_index,
            gateway_index,
        )

        namespace_groups[backend_namespace(releases[release_key])].append(
            {
                "microservice": infer_microservice_name(release_key, releases[release_key]),
                "all_three": crd_count(releases[release_key]) == 3,
                "crd_count": crd_count(releases[release_key]),
                "gateway": gateway_names(releases[release_key]),
                "route_uri": route_uris(releases[release_key]),
                "backend_host": backend_host(releases[release_key]),
                "status": summarize_status(issue_messages),
            }
        )

        if issue_messages or args.export_ok:
            detailed_issues.append((release_key, ok_messages, issue_messages))

        for message in issue_messages:
            if message.startswith("[FAIL]"):
                failures += 1
            elif message.startswith("[WARN]"):
                warnings += 1

    print_inventory(namespace_groups)

    if detailed_issues:
        print("\nDetails")
        for release_key, ok_messages, issue_messages in detailed_issues:
            print(f"\n== {release_key} ==")
            if args.export_ok:
                for message in ok_messages:
                    print(message)
            for message in issue_messages:
                print(message)
            if args.export_ok and not issue_messages:
                print("All checks passed.")

    print("\nSummary")
    print(f"Checked releases: {checked}")
    print(f"Failures: {failures}")
    print(f"Warnings: {warnings}")

    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
