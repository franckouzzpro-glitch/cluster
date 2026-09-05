"""Read-only core for the Cluster Control Layer."""

from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parent.parent
DEFAULT_CAPABILITIES_FILE = ROOT / "inventory" / "capabilities.yml"


class ClusterError(Exception):
    """Base exception for cluster control errors."""


class UnknownNodeError(ClusterError):
    """Requested node does not exist."""


class NoMatchingNodeError(ClusterError):
    """No node satisfies the requested capabilities."""


def load_nodes(path=DEFAULT_CAPABILITIES_FILE):
    """Load the logical cluster inventory."""
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
    """Return enabled capabilities for a node."""
    return sorted(
        name
        for name, enabled in node.get("capabilities", {}).items()
        if enabled is True
    )


def node_summary(name, node):
    """Return a stable representation of a node."""
    return {
        "name": name,
        "address": node.get("address"),
        "platform": node.get("platform"),
        "desired_roles": node.get("desired_roles", []),
        "capabilities": active_capabilities(node),
        "observed": node.get("observed", {}),
    }


def list_nodes(nodes):
    """Return summaries for every cluster node."""
    return [
        node_summary(name, node)
        for name, node in nodes.items()
    ]


def get_node(nodes, name):
    """Return one node or raise UnknownNodeError."""
    if name not in nodes:
        raise UnknownNodeError(f"Unknown node: {name}")

    return node_summary(name, nodes[name])


def find_nodes(nodes, capability):
    """Return nodes providing a capability."""
    return [
        name
        for name, node in nodes.items()
        if node.get("capabilities", {}).get(capability) is True
    ]


def place(nodes, required_capabilities):
    """
    Return placement candidates.

    V0 policy:
    - every requested capability is mandatory
    - inventory order is preserved
    - first matching node is selected
    """
    required = list(dict.fromkeys(required_capabilities))

    candidates = []

    for name, node in nodes.items():
        capabilities = node.get("capabilities", {})

        if all(capabilities.get(capability) is True
               for capability in required):
            candidates.append({
                "name": name,
                "address": node.get("address"),
                "platform": node.get("platform"),
                "capabilities": active_capabilities(node),
            })

    if not candidates:
        raise NoMatchingNodeError(
            "No node satisfies required capabilities: "
            + ", ".join(required)
        )

    return {
        "required_capabilities": required,
        "candidates": candidates,
        "selected": candidates[0]["name"],
        "selection_policy": "first_matching_node",
    }
