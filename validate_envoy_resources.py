
"""
Example:
  ./validate_envoy_resources.py --env devb
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


def run_kubectl_optional(args: Sequence[str]) -> dict:
    try:
        completed = subprocess.run(
            ["kubectl", *args],
            check=True,
            capture_output=True,
            text=True,
        )
    except subprocess.CalledProcessError as exc:
        command = " ".join(args)
        stderr = exc.stderr.strip() or exc.stdout.strip() or str(exc)
        optional_errors = (
            "the server doesn't have a resource type",
            "unable to recognize",
            "no matches for kind",
            "NotFound",
        )
        if any(fragment in stderr for fragment in optional_errors):
            print(
                f"INFO: kubectl {command} skipped because the resource type is not available in this cluster.",
                file=sys.stderr,
            )
            return {"apiVersion": "v1", "items": []}
        print(f"ERROR: kubectl {command} failed: {stderr}", file=sys.stderr)
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
    if kind == "BackendTrafficPolicy":
        return suffix_strip(name, "-btp")
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
        "backendtrafficpolicies": run_kubectl_optional([*context_args, "get", "backendtrafficpolicies.gateway.envoyproxy.io", "-A", "-o", "json"]),
        "gateways": run_kubectl([*context_args, "get", "gateways.gateway.networking.k8s.io", "-A", "-o", "json"]),
        "services": run_kubectl([*context_args, "get", "services", "-A", "-o", "json"]),
        "secrets": run_kubectl([*context_args, "get", "secrets", "-A", "-o", "json"]),
    }

def discover_releases(data: Dict[str, dict], env_filter: Optional[str]) -> Dict[str, dict]:
    releases: Dict[str, dict] = defaultdict(
        lambda: {
            "route": None,
            "refgrant": None,
            "btlsp": None,
            "btp": None,
            "gateway": None,
        }
    )

    resources = [
        ("route", "HTTPRoute", data["httproutes"].get("items", [])),
        ("refgrant", "ReferenceGrant", data["referencegrants"].get("items", [])),
        ("btlsp", "BackendTLSPolicy", data["backendtlspolicies"].get("items", [])),
        ("btp", "BackendTrafficPolicy", data["backendtrafficpolicies"].get("items", [])),
        ("gateway", "Gateway", data["gateways"].get("items", [])),
    ]

    for resource_key, kind, items in resources:
        for item in items:
            namespace = item.get("metadata", {}).get("namespace", "")
            if not chart_managed(item) or not env_matches(namespace, env_filter):
                continue
            releases[release_key(kind, item)][resource_key] = item

    return releases


def first_resource(release: dict) -> Optional[dict]:
    for key in ("btlsp", "refgrant", "route", "btp", "gateway"):
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


def infer_group(release: dict) -> str:
    namespace = backend_namespace(release)
    if namespace and namespace != "<unknown>" and "-" in namespace:
        return namespace.rsplit("-", 1)[0]

    resource = first_resource(release)
    if resource:
        app_name = resource.get("metadata", {}).get("labels", {}).get(APP_NAME_LABEL, "")
        env_name = infer_env(release)
        if app_name and env_name and app_name.endswith(f"-{env_name}"):
            return app_name[: -(len(env_name) + 1)].rsplit("-", 1)[0]

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


def core_resource_count(release: dict) -> int:
    return sum(1 for key in ("route", "refgrant", "btlsp") if release.get(key))


def resource_present(value: Optional[dict]) -> str:
    return "yes" if value else "no"


def session_affinity_state(release: dict) -> str:
    if release.get("btp"):
        return "enabled"
    if infer_group(release) == "garwin-int-apps":
        return "missing-required"
    return "-"


def summarize_status(issue_messages: Sequence[str]) -> str:
    if any(message.startswith("[FAIL]") for message in issue_messages):
        return "FAIL"
    if any(message.startswith("[WARN]") for message in issue_messages):
        return "WARN"
    return "OK"


def print_inventory(namespace_groups: Dict[str, List[dict]]) -> None:
    headers = [
        ("MICROSERVICE", 34),
        ("CORE", 6),
        ("BTP", 5),
        ("STICKY", 16),
        ("CHART_GW", 8),
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
                f"{entry['core_count']}/3".ljust(6),
                entry["btp"].ljust(5),
                entry["sticky"][:16].ljust(16),
                entry["chart_gateway"].ljust(8),
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
    btp = release.get("btp")
    chart_gateway = release.get("gateway")

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
    group_name = infer_group(release)

    if chart_gateway:
        gateway_meta = chart_gateway.get("metadata", {})
        gateway_name = gateway_meta.get("name")
        gateway_ns = gateway_meta.get("namespace")
        ok.append(f"{release_key}: chart-managed Gateway exists at {gateway_ns}/{gateway_name}")
        route_targets_chart_gateway = any(
            parent_ref.get("name") == gateway_name
            and parent_ref.get("namespace", route_ns) == gateway_ns
            for parent_ref in route.get("spec", {}).get("parentRefs", [])
        )
        if route_targets_chart_gateway:
            ok.append(f"{release_key}: HTTPRoute points to chart-managed Gateway {gateway_ns}/{gateway_name}")
        else:
            issues.append(
                format_issue(
                    "WARN",
                    f"{release_key}: chart-managed Gateway {gateway_ns}/{gateway_name} exists but is not referenced by the HTTPRoute",
                )
            )

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

    if btp:
        btp_ns = btp["metadata"]["namespace"]
        ok.append(f"{release_key}: BackendTrafficPolicy exists in {btp_ns}")

        if btp_ns != route_ns:
            issues.append(
                format_issue(
                    "FAIL",
                    f"{release_key}: BackendTrafficPolicy namespace {btp_ns} does not match HTTPRoute namespace {route_ns}",
                )
            )

        target_refs = btp.get("spec", {}).get("targetRefs", [])
        route_target_matches = any(
            target_ref.get("kind") == "HTTPRoute" and target_ref.get("name") == route_name
            for target_ref in target_refs
        )
        if route_target_matches:
            ok.append(f"{release_key}: BackendTrafficPolicy targets HTTPRoute {route_ns}/{route_name}")
        else:
            issues.append(
                format_issue(
                    "FAIL",
                    f"{release_key}: BackendTrafficPolicy does not target HTTPRoute {route_ns}/{route_name}",
                )
            )

        load_balancer = btp.get("spec", {}).get("loadBalancer", {})
        if load_balancer.get("type") == "ConsistentHash":
            ok.append(f"{release_key}: BackendTrafficPolicy loadBalancer.type=ConsistentHash")
        else:
            issues.append(
                format_issue(
                    "WARN",
                    f"{release_key}: BackendTrafficPolicy loadBalancer.type is {load_balancer.get('type')!r}, expected 'ConsistentHash' for sticky routing",
                )
            )

        consistent_hash = load_balancer.get("consistentHash", {})
        if consistent_hash.get("type") == "Cookie":
            ok.append(f"{release_key}: BackendTrafficPolicy consistentHash.type=Cookie")
        else:
            issues.append(
                format_issue(
                    "WARN",
                    f"{release_key}: BackendTrafficPolicy consistentHash.type is {consistent_hash.get('type')!r}, expected 'Cookie' for session affinity",
                )
            )

        cookie = consistent_hash.get("cookie", {})
        cookie_name = cookie.get("name")
        if cookie_name:
            ok.append(f"{release_key}: BackendTrafficPolicy cookie name is {cookie_name}")
        else:
            issues.append(format_issue("FAIL", f"{release_key}: BackendTrafficPolicy cookie.name is missing"))

        cookie_ttl = cookie.get("ttl")
        if cookie_ttl:
            ok.append(f"{release_key}: BackendTrafficPolicy cookie ttl is {cookie_ttl}")
        else:
            issues.append(format_issue("WARN", f"{release_key}: BackendTrafficPolicy cookie.ttl is missing"))

        ancestors = btp.get("status", {}).get("ancestors", [])
        if ancestors:
            accepted_conditions = [
                get_condition(entry.get("conditions", []), "Accepted") for entry in ancestors
            ]
            accepted_conditions = [condition for condition in accepted_conditions if condition]
            if accepted_conditions:
                if any(condition.get("status") == "True" for condition in accepted_conditions):
                    ok.append(f"{release_key}: BackendTrafficPolicy Accepted=True")
                else:
                    condition = accepted_conditions[0]
                    issues.append(
                        format_issue(
                            "FAIL",
                            f"{release_key}: BackendTrafficPolicy Accepted is not True ({condition.get('reason')}: {condition.get('message')})",
                        )
                    )

            resolved_conditions = [
                get_condition(entry.get("conditions", []), "ResolvedRefs") for entry in ancestors
            ]
            resolved_conditions = [condition for condition in resolved_conditions if condition]
            if resolved_conditions:
                if any(condition.get("status") == "True" for condition in resolved_conditions):
                    ok.append(f"{release_key}: BackendTrafficPolicy ResolvedRefs=True")
                else:
                    condition = resolved_conditions[0]
                    issues.append(
                        format_issue(
                            "FAIL",
                            f"{release_key}: BackendTrafficPolicy ResolvedRefs is not True ({condition.get('reason')}: {condition.get('message')})",
                        )
                    )
        else:
            issues.append(format_issue("WARN", f"{release_key}: BackendTrafficPolicy has no status.ancestors yet"))
    elif group_name == "garwin-int-apps":
        issues.append(
            format_issue(
                "WARN",
                f"{release_key}: garwin-int-apps microservices should enable BackendTrafficPolicy for session affinity, but no BackendTrafficPolicy was found",
            )
        )

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
    session_affinity_reminders: List[Tuple[str, str, str]] = []

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
                "core_count": core_resource_count(releases[release_key]),
                "btp": resource_present(releases[release_key].get("btp")),
                "sticky": session_affinity_state(releases[release_key]),
                "chart_gateway": resource_present(releases[release_key].get("gateway")),
                "gateway": gateway_names(releases[release_key]),
                "route_uri": route_uris(releases[release_key]),
                "backend_host": backend_host(releases[release_key]),
                "status": summarize_status(issue_messages),
            }
        )

        if infer_group(releases[release_key]) == "garwin-int-apps" and not releases[release_key].get("btp"):
            session_affinity_reminders.append(
                (
                    release_key,
                    backend_namespace(releases[release_key]),
                    infer_microservice_name(release_key, releases[release_key]),
                )
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

    if session_affinity_reminders:
        print("\nSession Affinity Reminders")
        print(
            "The following garwin-int-apps releases do not have BackendTrafficPolicy resources. "
            "These microservices should enable session affinity."
        )
        for release_key, namespace, microservice in session_affinity_reminders:
            print(f"- {release_key} ({namespace}, microservice={microservice})")

    print("\nSummary")
    print(f"Checked releases: {checked}")
    print(f"Failures: {failures}")
    print(f"Warnings: {warnings}")

    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
