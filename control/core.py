"""Read-only core for the Cluster Control Layer."""

from pathlib import Path

import yaml

from control.policy import (
    PolicyError,
    load_policy,
)
from control.state import (
    load_state,
    runtime_metadata,
    runtime_status,
)


ROOT = Path(__file__).resolve().parent.parent

DEFAULT_CAPABILITIES_FILE = (
    ROOT
    / "inventory"
    / "capabilities.yml"
)

GPU_CAPABILITIES = {
    "gpu_worker",
    "cuda_worker",
    "heavy_gpu_worker",
}


class ClusterError(Exception):
    """Base exception for cluster control errors."""


class UnknownNodeError(ClusterError):
    """Requested node does not exist."""


class NoMatchingNodeError(ClusterError):
    """No node satisfies placement requirements."""


def load_nodes(
    path=DEFAULT_CAPABILITIES_FILE,
):
    path = Path(path)

    with path.open(
        "r",
        encoding="utf-8",
    ) as f:
        data = yaml.safe_load(f)

    try:
        nodes = data["cluster"]["nodes"]
    except (
        TypeError,
        KeyError,
    ) as exc:
        raise ClusterError(
            "Invalid capabilities inventory: "
            f"{path}"
        ) from exc

    if not isinstance(nodes, dict):
        raise ClusterError(
            "Invalid nodes section in "
            f"capabilities inventory: {path}"
        )

    return nodes


def active_capabilities(node):
    return sorted(
        name
        for name, enabled
        in node.get(
            "capabilities",
            {},
        ).items()
        if enabled is True
    )


def node_summary(
    name,
    node,
    state=None,
):
    result = {
        "name": name,
        "address": node.get(
            "address"
        ),
        "platform": node.get(
            "platform"
        ),
        "desired_roles": node.get(
            "desired_roles",
            [],
        ),
        "capabilities": (
            active_capabilities(node)
        ),
        "observed": node.get(
            "observed",
            {},
        ),
    }

    if state is not None:
        result["runtime"] = state

    return result


def list_nodes(
    nodes,
    runtime_nodes=None,
):
    runtime_nodes = (
        runtime_nodes or {}
    )

    return [
        node_summary(
            name,
            node,
            runtime_nodes.get(name),
        )
        for name, node
        in nodes.items()
    ]


def get_node(
    nodes,
    name,
    runtime_nodes=None,
):
    if name not in nodes:
        raise UnknownNodeError(
            f"Unknown node: {name}"
        )

    runtime_nodes = (
        runtime_nodes or {}
    )

    return node_summary(
        name,
        nodes[name],
        runtime_nodes.get(name),
    )


def find_nodes(
    nodes,
    capability,
):
    return [
        name
        for name, node
        in nodes.items()
        if (
            node
            .get(
                "capabilities",
                {},
            )
            .get(capability)
            is True
        )
    ]


def is_gpu_request(required):
    return bool(
        GPU_CAPABILITIES
        .intersection(required)
    )


def evaluate_candidate(
    name,
    node,
    required,
    runtime_state,
    runtime_usable,
    policy,
):
    capabilities = node.get(
        "capabilities",
        {},
    )

    missing = [
        capability
        for capability in required
        if capabilities.get(
            capability
        ) is not True
    ]

    result = {
        "name": name,
        "address": node.get(
            "address"
        ),
        "platform": node.get(
            "platform"
        ),
        "eligible": True,
        "rejection_reasons": [],
        "ranking_reasons": [],
        "runtime": runtime_state,
    }

    if missing:
        result["eligible"] = False
        result[
            "rejection_reasons"
        ].append(
            "missing_capabilities="
            + ",".join(missing)
        )

        return result

    runtime_policy = policy.get(
        "runtime",
        {},
    )

    if (
        runtime_policy.get(
            "required",
            True,
        )
        and not runtime_usable
    ):
        result["eligible"] = False
        result[
            "rejection_reasons"
        ].append(
            "runtime_state_unusable"
        )

        return result

    eligibility = policy.get(
        "eligibility",
        {},
    )

    if (
        runtime_usable
        and eligibility.get(
            "require_reachable",
            True,
        )
        and runtime_state.get(
            "reachable"
        ) is not True
    ):
        reason = (
            runtime_state
            .get(
                "connectivity",
                {},
            )
            .get(
                "reason",
                "unreachable",
            )
        )

        result["eligible"] = False
        result[
            "rejection_reasons"
        ].append(
            f"node_unreachable:{reason}"
        )

        return result

    if (
        "docker_host" in required
        and eligibility.get(
            "require_runtime_docker_for_docker_jobs",
            True,
        )
    ):
        if (
            not runtime_usable
            or runtime_state.get(
                "docker_available"
            ) is not True
        ):
            reason = (
                runtime_state
                .get(
                    "docker",
                    {},
                )
                .get(
                    "reason",
                    "unavailable",
                )
            )

            result["eligible"] = False
            result[
                "rejection_reasons"
            ].append(
                "docker_unavailable:"
                f"{reason}"
            )

    if (
        is_gpu_request(required)
        and eligibility.get(
            "require_runtime_gpu_for_gpu_jobs",
            True,
        )
    ):
        gpu = runtime_state.get(
            "gpu",
            {},
        )

        if (
            not runtime_usable
            or gpu.get(
                "available"
            ) is not True
        ):
            result["eligible"] = False
            result[
                "rejection_reasons"
            ].append(
                "gpu_unavailable:"
                + gpu.get(
                    "reason",
                    "unknown",
                )
            )

            return result

        max_temp = (
            policy
            .get("gpu", {})
            .get("limits", {})
            .get(
                "max_temperature_c"
            )
        )

        temperature = gpu.get(
            "temperature_c"
        )

        if (
            max_temp is not None
            and temperature is not None
            and temperature > max_temp
        ):
            result["eligible"] = False
            result[
                "rejection_reasons"
            ].append(
                "gpu_temperature_limit:"
                f"{temperature}>{max_temp}"
            )

            return result

        result[
            "ranking_reasons"
        ].extend([
            "gpu_free_vram_mb="
            f"{gpu.get('vram_free_mb', 0)}",
            "gpu_utilization_percent="
            f"{gpu.get('utilization_percent', 100)}",
            "gpu_temperature_c="
            f"{gpu.get('temperature_c', 999)}",
        ])

    return result


def ranking_value(
    candidate,
    rule,
    inventory_index,
):
    gpu = (
        candidate
        .get(
            "runtime",
            {},
        )
        .get(
            "gpu",
            {},
        )
    )

    if rule == "gpu_free_vram_desc":
        return -gpu.get(
            "vram_free_mb",
            0,
        )

    if rule == "gpu_utilization_asc":
        return gpu.get(
            "utilization_percent",
            100,
        )

    if rule == "gpu_temperature_asc":
        return gpu.get(
            "temperature_c",
            999,
        )

    if rule == "inventory_order":
        return inventory_index[
            candidate["name"]
        ]

    raise PolicyError(
        f"Unsupported ranking rule: {rule}"
    )


def sort_candidates(
    candidates,
    ranking_rules,
    inventory_index,
):
    return sorted(
        candidates,
        key=lambda candidate: tuple(
            ranking_value(
                candidate,
                rule,
                inventory_index,
            )
            for rule
            in ranking_rules
        ),
    )



def build_decision_trace(
    ranked_candidates,
    ranking_rules,
    runtime_nodes,
    inventory_index,
):
    """Explain which ranking criteria actually affected selection."""

    names = [
        item["name"]
        for item in ranked_candidates
    ]

    if not names:
        return {
            "selected": None,
            "decision_reasons": [],
            "factors": [],
        }

    selected = names[0]
    remaining = list(names)

    factors = []
    decision_reasons = []

    rule_specs = {
        "gpu_free_vram_desc": {
            "direction": "desc",
            "field": "vram_free_mb",
        },
        "gpu_utilization_asc": {
            "direction": "asc",
            "field": "utilization_percent",
        },
        "gpu_temperature_asc": {
            "direction": "asc",
            "field": "temperature_c",
        },
        "inventory_order": {
            "direction": "asc",
            "field": None,
        },
    }

    for rule in ranking_rules:
        spec = rule_specs.get(rule)

        if spec is None:
            factors.append(
                {
                    "criterion": rule,
                    "outcome": "unsupported",
                }
            )
            continue

        if len(remaining) <= 1:
            factors.append(
                {
                    "criterion": rule,
                    "outcome": "not_needed",
                    "leaders": list(remaining),
                }
            )
            continue

        values = {}

        for name in remaining:
            if rule == "inventory_order":
                value = inventory_index[name]
            else:
                value = (
                    runtime_nodes
                    .get(name, {})
                    .get("gpu", {})
                    .get(spec["field"])
                )

            values[name] = value

        if any(
            value is None
            for value in values.values()
        ):
            factors.append(
                {
                    "criterion": rule,
                    "outcome": "unavailable",
                    "values": values,
                    "leaders": list(remaining),
                }
            )
            continue

        if spec["direction"] == "desc":
            best_value = max(values.values())
        else:
            best_value = min(values.values())

        leaders = [
            name
            for name, value in values.items()
            if value == best_value
        ]

        if len(leaders) == len(remaining):
            outcome = "tie"

        elif len(leaders) == 1:
            outcome = "decisive"

        else:
            outcome = "narrowed"

        factor = {
            "criterion": rule,
            "direction": spec["direction"],
            "outcome": outcome,
            "values": values,
            "best_value": best_value,
            "leaders": leaders,
        }

        factors.append(factor)

        if outcome in {
            "decisive",
            "narrowed",
        }:
            decision_reasons.append(
                {
                    "criterion": rule,
                    "direction": spec["direction"],
                    "selected_value": values.get(
                        selected
                    ),
                    "compared_values": values,
                    "outcome": outcome,
                }
            )

            remaining = leaders

    return {
        "selected": selected,
        "decision_reasons": decision_reasons,
        "factors": factors,
        "contract": (
            "Only decision_reasons contributed "
            "to the selected node. Factors marked "
            "not_needed, tie, unavailable, or "
            "unsupported must not be presented "
            "as reasons for selection."
        ),
    }


def place(
    nodes,
    required_capabilities,
    runtime_nodes=None,
    policy=None,
    runtime_info=None,
):
    required = list(
        dict.fromkeys(
            required_capabilities
        )
    )

    policy = policy or load_policy()

    runtime_nodes = (
        runtime_nodes or {}
    )

    runtime_info = (
        runtime_info or {}
    )

    runtime_policy = policy.get(
        "runtime",
        {},
    )

    max_age = runtime_policy.get(
        "max_age_seconds",
        300,
    )

    runtime_age = runtime_info.get(
        "age_seconds"
    )

    runtime_state_status = runtime_status(
        runtime_nodes,
        runtime_info,
        max_age,
    )

    runtime_present = (
        runtime_state_status
        != "missing"
    )

    runtime_fresh = (
        runtime_state_status
        == "fresh"
    )

    runtime_usable = (
        runtime_state_status
        == "fresh"
    )

    evaluations = []

    for name, node in nodes.items():
        evaluation = evaluate_candidate(
            name,
            node,
            required,
            runtime_nodes.get(
                name,
                {},
            ),
            runtime_usable,
            policy,
        )

        evaluations.append(
            evaluation
        )

    eligible = [
        item
        for item in evaluations
        if item["eligible"]
    ]

    if not eligible:
        declared_matches = [
            item
            for item in evaluations
            if not any(
                reason.startswith(
                    "missing_capabilities="
                )
                for reason
                in item[
                    "rejection_reasons"
                ]
            )
        ]

        details = "; ".join(
            (
                item["name"]
                + "="
                + ",".join(
                    item[
                        "rejection_reasons"
                    ]
                )
            )
            for item
            in declared_matches
        )

        message = (
            "No eligible node for: "
            + ", ".join(required)
        )

        if not runtime_present:
            message += (
                " [runtime state missing]"
            )
        elif not runtime_fresh:
            message += (
                " [runtime state stale]"
            )

        if details:
            message += (
                f" ({details})"
            )

        raise NoMatchingNodeError(
            message
        )

    if is_gpu_request(required):
        ranking_rules = (
            policy
            .get("gpu", {})
            .get(
                "ranking",
                [
                    "gpu_free_vram_desc",
                    "gpu_utilization_asc",
                    "gpu_temperature_asc",
                    "inventory_order",
                ],
            )
        )
    else:
        ranking_rules = (
            policy
            .get("general", {})
            .get(
                "ranking",
                ["inventory_order"],
            )
        )

    inventory_index = {
        name: index
        for index, name
        in enumerate(nodes)
    }

    eligible = sort_candidates(
        eligible,
        ranking_rules,
        inventory_index,
    )

    candidates = []

    for index, item in enumerate(
        eligible,
        start=1,
    ):
        candidate = dict(item)
        candidate["rank"] = index

        candidates.append(
            candidate
        )

    return {
        "required_capabilities": (
            required
        ),
        "selected": (
            candidates[0]["name"]
        ),
        "selection_policy": (
            "policy-as-data-v1"
        ),
        "policy": {
            "runtime_required": (
                runtime_policy.get(
                    "required",
                    True,
                )
            ),
            "runtime_max_age_seconds": (
                max_age
            ),
            "gpu_max_temperature_c": (
                policy
                .get("gpu", {})
                .get("limits", {})
                .get(
                    "max_temperature_c"
                )
            ),
        },
        "runtime": {
            "status": runtime_state_status,
            "present": runtime_present,
            "fresh": runtime_fresh,
            "age_seconds": runtime_age,
            "generated_at": (
                runtime_info.get("generated_at")
                if runtime_info
                else None
            ),
        },
        "ranking_policy": ranking_rules,
        "decision": build_decision_trace(
            candidates,
            ranking_rules,
            runtime_nodes,
            inventory_index,
        ),
        "candidates": candidates,
        "evaluations": evaluations,
    }



def canonical_plan_payload(
    intent,
    required_capabilities,
    placement_result,
):
    return {
        "intent": intent.strip(),
        "required_capabilities": list(
            required_capabilities
        ),
        "selected": placement_result.get(
            "selected"
        ),
        "selection_policy": placement_result.get(
            "selection_policy"
        ),
        "ranking_policy": placement_result.get(
            "ranking_policy"
        ),
        "decision_reasons": (
            placement_result
            .get("decision", {})
            .get("decision_reasons", [])
        ),
        "runtime_snapshot": {
            "generated_at": (
                placement_result
                .get("runtime", {})
                .get("generated_at")
            ),
        },
    }


def build_plan_id(payload):
    import hashlib
    import json

    encoded = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")

    return hashlib.sha256(
        encoded
    ).hexdigest()[:16]


def build_plan(
    nodes,
    intent,
    required_capabilities,
    runtime_nodes=None,
    policy=None,
    runtime_info=None,
):
    """Build a deterministic non-executing workload plan."""

    intent = str(intent).strip()

    if not intent:
        raise ClusterError(
            "Plan intent must not be empty."
        )

    required = list(
        dict.fromkeys(
            required_capabilities
        )
    )

    if not required:
        raise ClusterError(
            "Plan requires at least one capability."
        )

    placement_result = place(
        nodes,
        required,
        runtime_nodes,
        policy=policy,
        runtime_info=runtime_info,
    )

    payload = canonical_plan_payload(
        intent,
        required,
        placement_result,
    )

    plan_id = build_plan_id(
        payload
    )

    selected = placement_result[
        "selected"
    ]

    validations = [
        {
            "check": "intent_present",
            "status": "pass",
        },
        {
            "check": "capabilities_present",
            "status": "pass",
            "required_capabilities": (
                required
            ),
        },
        {
            "check": "runtime_fresh",
            "status": (
                "pass"
                if placement_result[
                    "runtime"
                ]["fresh"]
                else "fail"
            ),
        },
        {
            "check": "eligible_node_found",
            "status": "pass",
            "selected": selected,
        },
    ]

    verdict = "VALID"

    if any(
        item["status"] == "fail"
        for item in validations
    ):
        verdict = "INVALID"

    steps = [
        {
            "order": 1,
            "type": "validate",
            "description": (
                "Validate requested capabilities "
                "against declared inventory."
            ),
        },
        {
            "order": 2,
            "type": "placement",
            "description": (
                "Evaluate eligible nodes using "
                "versioned placement policy and "
                "fresh runtime state."
            ),
        },
        {
            "order": 3,
            "type": "target",
            "description": (
                f"Target selected node {selected}."
            ),
        },
        {
            "order": 4,
            "type": "approval_boundary",
            "description": (
                "Stop before execution. "
                "No command, SSH session, "
                "Ansible playbook, deployment, "
                "restart, or file modification "
                "is performed by this plan."
            ),
        },
    ]

    return {
        "plan_id": plan_id,
        "mode": "PLAN",
        "verdict": verdict,
        "intent": intent,
        "required_capabilities": required,
        "selected": selected,
        "placement": placement_result,
        "validations": validations,
        "steps": steps,
        "execution": {
            "performed": False,
            "allowed": False,
            "reason": (
                "PLAN mode is strictly "
                "non-executing."
            ),
        },
        "contract": (
            "This object describes an intended "
            "action only. It must never be treated "
            "as authorization to execute."
        ),
    }



def load_runtime_context():
    state = load_state()

    nodes = (
        state
        .get(
            "cluster_state",
            {},
        )
        .get(
            "nodes",
            {},
        )
    )

    return (
        nodes,
        runtime_metadata(state),
    )


def load_runtime_nodes():
    nodes, _ = load_runtime_context()

    return nodes
