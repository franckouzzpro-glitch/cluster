"""Read-only core for the Cluster Control Layer."""

from pathlib import Path

import yaml

from control.state import load_state


ROOT = Path(__file__).resolve().parent.parent
DEFAULT_CAPABILITIES_FILE = ROOT / "inventory" / "capabilities.yml"


class ClusterError(Exception):
    """Base exception for cluster control errors."""


class UnknownNodeError(ClusterError):
    """Requested node does not exist."""


class NoMatchingNodeError(ClusterError):
    """No node satisfies the requested capabilities."""


def load_nodes(path=DEFAULT_CAPABILITIES_FILE):
    path = Path(path)

    with path.open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f)

    try:
        nodes = data["cluster"]["nodes"]
    except (TypeError, KeyError) as exc:
        raise ClusterError(
            f"Invalid capabilities inventory: {path}"
        ) from exc

    if not isinstance(nodes, dict):
        raise ClusterError(
            f"Invalid nodes section in capabilities inventory: {path}"
        )

    return nodes


def active_capabilities(node):
    return sorted(
        name
        for name, enabled in node.get("capabilities", {}).items()
        if enabled is True
    )


def node_summary(name, node, state=None):
    result = {
        "name": name,
        "address": node.get("address"),
        "platform": node.get("platform"),
        "desired_roles": node.get("desired_roles", []),
        "capabilities": active_capabilities(node),
        "observed": node.get("observed", {}),
    }

    if state is not None:
        result["runtime"] = state

    return result


def list_nodes(nodes, runtime_nodes=None):
    runtime_nodes = runtime_nodes or {}

    return [
        node_summary(
            name,
            node,
            runtime_nodes.get(name),
        )
        for name, node in nodes.items()
    ]


def get_node(nodes, name, runtime_nodes=None):
    if name not in nodes:
        raise UnknownNodeError(f"Unknown node: {name}")

    runtime_nodes = runtime_nodes or {}

    return node_summary(
        name,
        nodes[name],
        runtime_nodes.get(name),
    )


def find_nodes(nodes, capability):
    return [
        name
        for name, node in nodes.items()
        if node.get("capabilities", {}).get(capability) is True
    ]


def candidate_score(name, node, runtime_state):
    score = 0
    reasons = []

    if runtime_state.get("reachable") is True:
        score += 100
        reasons.append("reachable")
    else:
        reasons.append("unreachable")

    gpu = runtime_state.get("gpu", {})

    if gpu.get("available") is True:
        free_mb = gpu.get("vram_free_mb", 0)
        score += free_mb / 1024
        reasons.append(
            f"gpu_free_vram_mb={free_mb}"
        )

        utilization = gpu.get(
            "utilization_percent",
            100,
        )
        score += max(0, 100 - utilization) / 10
        reasons.append(
            f"gpu_utilization_percent={utilization}"
        )

    return {
        "name": name,
        "score": round(score, 2),
        "reasons": reasons,
    }


def place(
    nodes,
    required_capabilities,
    runtime_nodes=None,
):
    required = list(dict.fromkeys(required_capabilities))
    runtime_nodes = runtime_nodes or {}

    candidates = []

    for name, node in nodes.items():
        capabilities = node.get("capabilities", {})

        if not all(
            capabilities.get(capability) is True
            for capability in required
        ):
            continue

        runtime_state = runtime_nodes.get(name, {})

        if runtime_nodes:
            if runtime_state.get("reachable") is not True:
                continue

            if (
                "docker_host" in required
                and runtime_state.get("docker_available") is not True
            ):
                continue

        scored = candidate_score(
            name,
            node,
            runtime_state,
        )

        candidates.append({
            "name": name,
            "address": node.get("address"),
            "platform": node.get("platform"),
            "capabilities": active_capabilities(node),
            "runtime": runtime_state,
            "score": scored["score"],
            "score_reasons": scored["reasons"],
        })

    if not candidates:
        raise NoMatchingNodeError(
            "No node satisfies required capabilities "
            "and runtime constraints: "
            + ", ".join(required)
        )

    candidates.sort(
        key=lambda candidate: candidate["score"],
        reverse=True,
    )

    return {
        "required_capabilities": required,
        "candidates": candidates,
        "selected": candidates[0]["name"],
        "selection_policy": (
            "capabilities+runtime+gpu_free_vram"
        ),
    }


def load_runtime_nodes():
    state = load_state()

    return (
        state
        .get("cluster_state", {})
        .get("nodes", {})
    )
