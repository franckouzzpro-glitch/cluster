#!/usr/bin/env python3
"""Read-only MCP facade for the cluster control layer."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]

if str(REPO_ROOT) not in sys.path:
    sys.path.insert(
        0,
        str(REPO_ROOT),
    )

from mcp.server import MCPServer

from control.core import (
    ClusterError,
    NoMatchingNodeError,
    UnknownNodeError,
    build_plan,
    get_node,
    load_nodes,
    load_runtime_context,
    place,
)
from control.facts import (
    build_cluster_facts,
    build_node_facts,
)
from control.policy import PolicyError


mcp = MCPServer(
    "cluster-control-readonly",
    instructions=(
        "Read-only interface to the home cluster. "
        "Never performs SSH, Ansible execution, "
        "service changes, deployments, restarts, "
        "file modifications, or shell commands. "
        "For factual hardware/runtime claims, "
        "prefer cluster_get_facts. "
        "Never recalculate declared CPU core/thread "
        "counts. Never treat desired_roles as proof "
        "that services are currently active. "
        "Never infer a cause from a tool error that "
        "the tool did not explicitly return. "
        "Only placement.decision.decision_reasons "
        "may be presented as causal placement reasons."
    ),
)


def public_node(
    name: str,
    node: dict[str, Any],
) -> dict[str, Any]:
    return {
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
        "capabilities": node.get(
            "capabilities",
            {},
        ),
        "observed": node.get(
            "observed",
            {},
        ),
    }


def structured_error(
    exc: Exception,
) -> dict[str, Any]:
    if isinstance(
        exc,
        NoMatchingNodeError,
    ):
        code = "NO_MATCHING_NODE"

    elif isinstance(
        exc,
        UnknownNodeError,
    ):
        code = "UNKNOWN_NODE"

    elif isinstance(
        exc,
        PolicyError,
    ):
        code = "POLICY_ERROR"

    elif isinstance(
        exc,
        ClusterError,
    ):
        code = "CLUSTER_ERROR"

    else:
        code = "CONTROL_LAYER_ERROR"

    return {
        "ok": False,
        "error": {
            "code": code,
            "type": (
                exc.__class__.__name__
            ),
            "message": str(exc),
            "cause_contract": (
                "The message above is the only "
                "cause information supplied by "
                "the control layer. Do not infer "
                "additional causes."
            ),
        },
    }


def non_executing_boundary() -> dict[str, Any]:
    return {
        "performed": False,
        "allowed": False,
        "reason": (
            "PLAN/read-only mode is strictly "
            "non-executing."
        ),
    }


@mcp.tool()
def cluster_list_nodes() -> dict[str, Any]:
    """List declared cluster nodes and public inventory data."""
    nodes = load_nodes()

    return {
        "nodes": [
            public_node(
                name,
                node,
            )
            for name, node
            in nodes.items()
        ]
    }


@mcp.tool()
def cluster_get_node(
    name: str,
) -> dict[str, Any]:
    """Return declared inventory and runtime state for one node."""
    nodes = load_nodes()

    try:
        node = get_node(
            nodes,
            name,
        )
    except (
        UnknownNodeError,
        ClusterError,
    ) as exc:
        return structured_error(
            exc
        )

    runtime_nodes, runtime_info = (
        load_runtime_context()
    )

    return {
        "ok": True,
        "node": public_node(
            name,
            node,
        ),
        "runtime": runtime_nodes.get(
            name
        ),
        "runtime_snapshot": (
            runtime_info
        ),
    }


@mcp.tool()
def cluster_find_capability(
    capability: str,
) -> dict[str, Any]:
    """Find nodes declaring a logical capability."""
    nodes = load_nodes()

    matches = {
        name: node
        for name, node
        in nodes.items()
        if (
            node
            .get(
                "capabilities",
                {},
            )
            .get(
                capability
            )
            is True
        )
    }

    return {
        "capability": capability,
        "matches": [
            public_node(
                name,
                node,
            )
            for name, node
            in matches.items()
        ],
    }


@mcp.tool()
def cluster_get_runtime_state() -> dict[str, Any]:
    """Return the latest locally collected runtime snapshot."""
    runtime_nodes, runtime_info = (
        load_runtime_context()
    )

    return {
        "snapshot": runtime_info,
        "nodes": runtime_nodes,
    }


@mcp.tool()
def cluster_get_facts() -> dict[str, Any]:
    """Return normalized facts with explicit provenance.

    Use this tool for factual cluster claims.

    Inventory facts are declared values and must not be
    recomputed by the LLM. Runtime facts are observations
    from the current snapshot. Derived values are calculated
    by the control layer. desired_roles are not proof that
    services are currently active.

    Facts are not placement causes. Only
    placement.decision.decision_reasons can explain why
    a workload was selected for a node.
    """
    nodes = load_nodes()

    runtime_nodes, runtime_info = (
        load_runtime_context()
    )

    return build_cluster_facts(
        nodes,
        runtime_nodes,
        runtime_info,
    )


@mcp.tool()
def cluster_get_node_facts(
    name: str,
) -> dict[str, Any]:
    """Return normalized facts for exactly one node.

    Prefer this tool when making factual claims about a
    specific node. Returning one node at a time prevents
    facts from different nodes from being associated with
    the wrong identity.

    Inventory values must not be recomputed.
    Runtime values belong only to this node.
    Derived values are calculated by the control layer.
    desired_roles are not proof of active services.
    """
    nodes = load_nodes()

    if name not in nodes:
        return structured_error(
            UnknownNodeError(
                f"Unknown node: {name}"
            )
        )

    runtime_nodes, runtime_info = (
        load_runtime_context()
    )

    return {
        "schema_version": 1,
        "node": build_node_facts(
            name,
            nodes[name],
            runtime_nodes.get(name),
            runtime_info,
        ),
        "runtime_snapshot": runtime_info,
        "contract": (
            "Every fact in this response belongs "
            f"only to node {name}. Do not associate "
            "values from another node with this response."
        ),
    }


@mcp.tool()
def cluster_place_workload(
    required_capabilities: list[str],
) -> dict[str, Any]:
    """Evaluate deterministic placement.

    required_capabilities must contain only capabilities
    actually required by this workload phase.

    Explain selection using only decision.decision_reasons.
    Never invent causes from unrelated facts or errors.
    """
    nodes = load_nodes()

    runtime_nodes, runtime_info = (
        load_runtime_context()
    )

    try:
        result = place(
            nodes,
            required_capabilities,
            runtime_nodes,
            runtime_info=runtime_info,
        )
    except (
        NoMatchingNodeError,
        PolicyError,
        ClusterError,
    ) as exc:
        response = structured_error(
            exc
        )
        response["execution"] = (
            non_executing_boundary()
        )
        return response

    result = dict(result)
    result["ok"] = True
    result["execution"] = (
        non_executing_boundary()
    )

    return result


@mcp.tool()
def cluster_plan_workload(
    intent: str,
    required_capabilities: list[str],
) -> dict[str, Any]:
    """Build a deterministic PLAN without executing anything.

    required_capabilities must describe only capabilities
    required by the requested workload phase.

    This tool never runs SSH, shell commands, Ansible,
    deployments, restarts, service changes, or file writes.

    On failure, only the structured error may be used to
    explain the cause. Do not infer another cause.

    plan_id identifies a proposal only and is never
    authorization to execute it.
    """
    nodes = load_nodes()

    runtime_nodes, runtime_info = (
        load_runtime_context()
    )

    try:
        result = build_plan(
            nodes,
            intent,
            required_capabilities,
            runtime_nodes,
            runtime_info=runtime_info,
        )
    except (
        NoMatchingNodeError,
        PolicyError,
        ClusterError,
    ) as exc:
        response = structured_error(
            exc
        )
        response["mode"] = "PLAN"
        response["verdict"] = "INVALID"
        response["execution"] = (
            non_executing_boundary()
        )
        return response

    result = dict(result)
    result["ok"] = True

    return result


if __name__ == "__main__":
    mcp.run()
