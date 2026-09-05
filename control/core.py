"""Read-only core for the Cluster Control Layer."""

from pathlib import Path

import yaml

from control.state import load_state


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
    runtime_enabled,
):
    capabilities = node.get(
        "capabilities",
        {},
    )

    missing_capabilities = [
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

    if missing_capabilities:
        result["eligible"] = False
        result[
            "rejection_reasons"
        ].append(
            "missing_capabilities="
            + ",".join(
                missing_capabilities
            )
        )

        return result

    if not runtime_enabled:
        result[
            "ranking_reasons"
        ].append(
            "runtime_state_not_available"
        )

        return result

    if (
        runtime_state
        .get("reachable")
        is not True
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

    if "docker_host" in required:
        if (
            runtime_state
            .get(
                "docker_available"
            )
            is not True
        ):
            docker_reason = (
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
                f"{docker_reason}"
            )

    if is_gpu_request(required):
        gpu = runtime_state.get(
            "gpu",
            {},
        )

        if gpu.get(
            "available"
        ) is not True:
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
        else:
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


def gpu_sort_key(candidate):
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

    return (
        -gpu.get(
            "vram_free_mb",
            0,
        ),
        gpu.get(
            "utilization_percent",
            100,
        ),
        gpu.get(
            "temperature_c",
            999,
        ),
    )


def place(
    nodes,
    required_capabilities,
    runtime_nodes=None,
):
    required = list(
        dict.fromkeys(
            required_capabilities
        )
    )

    runtime_nodes = (
        runtime_nodes or {}
    )

    runtime_enabled = bool(
        runtime_nodes
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
            runtime_enabled,
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

        if details:
            message += (
                f" ({details})"
            )

        raise NoMatchingNodeError(
            message
        )

    if (
        runtime_enabled
        and is_gpu_request(required)
    ):
        eligible.sort(
            key=gpu_sort_key
        )

        ranking_policy = [
            "required_capabilities",
            "reachable",
            "runtime_gpu_available",
            "gpu_free_vram_desc",
            "gpu_utilization_asc",
            "gpu_temperature_asc",
            "inventory_order",
        ]
    else:
        ranking_policy = [
            "required_capabilities",
            "reachable_if_runtime_available",
            "inventory_order",
        ]

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
            "runtime-policy-v1"
        ),
        "ranking_policy": (
            ranking_policy
        ),
        "candidates": candidates,
        "evaluations": evaluations,
    }


def load_runtime_nodes():
    state = load_state()

    return (
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
