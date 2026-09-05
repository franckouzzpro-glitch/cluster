#!/usr/bin/env python3
"""Read-only MCP facade for the cluster control layer."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]

if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from mcp.server import MCPServer

from control.core import (
    get_node,
    load_nodes,
    load_runtime_context,
    place,
)


mcp = MCPServer(
    "cluster-control-readonly",
    instructions=(
        "Read-only interface to the home cluster. "
        "Never performs SSH, Ansible execution, "
        "service changes, deployments, restarts, "
        "file modifications, or shell commands."
    ),
)


def public_node(name: str, node: dict[str, Any]) -> dict[str, Any]:
    return {
        "name": name,
        "address": node.get("address"),
        "platform": node.get("platform"),
        "desired_roles": node.get("desired_roles", []),
        "capabilities": node.get("capabilities", {}),
        "observed": node.get("observed", {}),
    }


@mcp.tool()
def cluster_list_nodes() -> dict[str, Any]:
    """List declared cluster nodes and their public inventory data."""
    nodes = load_nodes()

    return {
        "nodes": [
            public_node(name, node)
            for name, node in nodes.items()
        ]
    }


@mcp.tool()
def cluster_get_node(name: str) -> dict[str, Any]:
    """Return declared inventory and runtime state for one node."""
    nodes = load_nodes()

    node = get_node(nodes, name)

    runtime_nodes, runtime_info = load_runtime_context()

    return {
        "node": public_node(name, node),
        "runtime": runtime_nodes.get(name),
        "runtime_snapshot": runtime_info,
    }


@mcp.tool()
def cluster_find_capability(capability: str) -> dict[str, Any]:
    """Find nodes declaring a given logical capability."""
    nodes = load_nodes()

    matches = {
        name: node
        for name, node in nodes.items()
        if (
            node
            .get("capabilities", {})
            .get(capability) is True
        )
    }

    return {
        "capability": capability,
        "matches": [
            public_node(name, node)
            for name, node in matches.items()
        ],
    }


@mcp.tool()
def cluster_get_runtime_state() -> dict[str, Any]:
    """Return the latest locally collected runtime snapshot."""
    runtime_nodes, runtime_info = load_runtime_context()

    return {
        "snapshot": runtime_info,
        "nodes": runtime_nodes,
    }


@mcp.tool()
def cluster_place_workload(
    required_capabilities: list[str],
) -> dict[str, Any]:
    """Evaluate placement using versioned policy and fresh runtime state.

    Explain selection using only decision.decision_reasons.
    Never invent reasons from unrelated candidate metadata.
    Factors marked not_needed, tie, unavailable, or unsupported
    are not reasons for the selected node.
    """
    nodes = load_nodes()

    runtime_nodes, runtime_info = load_runtime_context()

    return place(
        nodes,
        required_capabilities,
        runtime_nodes,
        runtime_info=runtime_info,
    )


if __name__ == "__main__":
    mcp.run()
