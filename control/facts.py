"""Deterministic facts and provenance for the Cluster Control Layer.

This module exists to keep arithmetic, source semantics, and factual
normalization out of the LLM.

Inventory values are never re-interpreted or re-multiplied.
Runtime values are kept distinct from declared inventory values.
Derived values are calculated here and carry explicit provenance.
"""

from __future__ import annotations

from typing import Any


FACTS_SCHEMA_VERSION = 1


def inventory_fact(
    value: Any,
    path: str,
    unit: str | None = None,
) -> dict[str, Any]:
    result = {
        "value": value,
        "provenance": {
            "kind": "inventory",
            "path": path,
            "authority": "declared",
            "derived": False,
        },
    }

    if unit is not None:
        result["unit"] = unit

    return result


def runtime_fact(
    value: Any,
    path: str,
    generated_at: str | None,
    unit: str | None = None,
) -> dict[str, Any]:
    result = {
        "value": value,
        "provenance": {
            "kind": "runtime",
            "path": path,
            "authority": "observed",
            "derived": False,
            "snapshot_generated_at": generated_at,
        },
    }

    if unit is not None:
        result["unit"] = unit

    return result


def derived_fact(
    value: Any,
    *,
    inputs: list[str],
    formula: str,
    unit: str | None = None,
) -> dict[str, Any]:
    result = {
        "value": value,
        "provenance": {
            "kind": "derived",
            "authority": "control_layer",
            "derived": True,
            "inputs": inputs,
            "formula": formula,
        },
    }

    if unit is not None:
        result["unit"] = unit

    return result


def percent(
    value: Any,
    total: Any,
) -> float | None:
    if not isinstance(
        value,
        (int, float),
    ):
        return None

    if not isinstance(
        total,
        (int, float),
    ):
        return None

    if total <= 0:
        return None

    return round(
        100.0 * value / total,
        2,
    )


def build_gpu_derived(
    runtime_gpu: dict[str, Any],
) -> dict[str, Any]:
    total = runtime_gpu.get(
        "vram_total_mb"
    )
    used = runtime_gpu.get(
        "vram_used_mb"
    )
    free = runtime_gpu.get(
        "vram_free_mb"
    )

    result: dict[str, Any] = {}

    free_percent = percent(
        free,
        total,
    )

    if free_percent is not None:
        result["vram_free_percent"] = (
            derived_fact(
                free_percent,
                inputs=[
                    "runtime.gpu.vram_free_mb",
                    "runtime.gpu.vram_total_mb",
                ],
                formula=(
                    "100 * vram_free_mb "
                    "/ vram_total_mb"
                ),
                unit="percent",
            )
        )

    used_percent = percent(
        used,
        total,
    )

    if used_percent is not None:
        result["vram_used_percent"] = (
            derived_fact(
                used_percent,
                inputs=[
                    "runtime.gpu.vram_used_mb",
                    "runtime.gpu.vram_total_mb",
                ],
                formula=(
                    "100 * vram_used_mb "
                    "/ vram_total_mb"
                ),
                unit="percent",
            )
        )

    if all(
        isinstance(
            value,
            (int, float),
        )
        for value in (
            total,
            used,
            free,
        )
    ):
        unaccounted = (
            total
            - used
            - free
        )

        result[
            "vram_unaccounted_mb"
        ] = derived_fact(
            unaccounted,
            inputs=[
                "runtime.gpu.vram_total_mb",
                "runtime.gpu.vram_used_mb",
                "runtime.gpu.vram_free_mb",
            ],
            formula=(
                "vram_total_mb "
                "- vram_used_mb "
                "- vram_free_mb"
            ),
            unit="MB",
        )

    return result


def build_node_facts(
    name: str,
    node: dict[str, Any],
    runtime_state: dict[str, Any] | None,
    runtime_info: dict[str, Any] | None,
) -> dict[str, Any]:
    runtime_state = (
        runtime_state or {}
    )
    runtime_info = (
        runtime_info or {}
    )

    generated_at = (
        runtime_info.get(
            "generated_at"
        )
    )

    observed = node.get(
        "observed",
        {},
    )

    compute = observed.get(
        "compute",
        {},
    )

    cpu = compute.get(
        "cpu",
        {},
    )

    inventory_gpu = compute.get(
        "gpu",
        {},
    )

    runtime_gpu = runtime_state.get(
        "gpu",
        {},
    )

    capabilities = node.get(
        "capabilities",
        {},
    )

    result: dict[str, Any] = {
        "identity": {
            "name": inventory_fact(
                name,
                "node.name",
            ),
            "address": inventory_fact(
                node.get(
                    "address"
                ),
                "address",
            ),
            "platform": inventory_fact(
                node.get(
                    "platform"
                ),
                "platform",
            ),
        },
        "semantics": {
            "desired_roles": {
                "value": node.get(
                    "desired_roles",
                    [],
                ),
                "meaning": (
                    "declared desired roles; "
                    "not proof that a service "
                    "is currently running"
                ),
                "provenance": {
                    "kind": "inventory",
                    "path": "desired_roles",
                    "authority": "declared",
                    "derived": False,
                },
            },
        },
        "inventory": {
            "cpu": {
                "model": inventory_fact(
                    cpu.get(
                        "model"
                    ),
                    (
                        "observed.compute."
                        "cpu.model"
                    ),
                ),
                "sockets": inventory_fact(
                    cpu.get(
                        "sockets"
                    ),
                    (
                        "observed.compute."
                        "cpu.sockets"
                    ),
                ),
                "physical_cores": (
                    inventory_fact(
                        cpu.get(
                            "physical_cores"
                        ),
                        (
                            "observed.compute."
                            "cpu.physical_cores"
                        ),
                        "cores",
                    )
                ),
                "logical_threads": (
                    inventory_fact(
                        cpu.get(
                            "logical_threads"
                        ),
                        (
                            "observed.compute."
                            "cpu.logical_threads"
                        ),
                        "threads",
                    )
                ),
            },
            "memory_gb": (
                inventory_fact(
                    compute.get(
                        "memory_gb"
                    ),
                    (
                        "observed.compute."
                        "memory_gb"
                    ),
                    "GB",
                )
            ),
            "gpu": {
                "vendor": inventory_fact(
                    inventory_gpu.get(
                        "vendor"
                    ),
                    (
                        "observed.compute."
                        "gpu.vendor"
                    ),
                ),
                "model": inventory_fact(
                    inventory_gpu.get(
                        "model"
                    ),
                    (
                        "observed.compute."
                        "gpu.model"
                    ),
                ),
                "vram_gb": inventory_fact(
                    inventory_gpu.get(
                        "vram_gb"
                    ),
                    (
                        "observed.compute."
                        "gpu.vram_gb"
                    ),
                    "GB",
                ),
                "cuda": inventory_fact(
                    inventory_gpu.get(
                        "cuda"
                    ),
                    (
                        "observed.compute."
                        "gpu.cuda"
                    ),
                ),
            },
            "capabilities": {
                key: inventory_fact(
                    value,
                    f"capabilities.{key}",
                )
                for key, value
                in capabilities.items()
            },
        },
        "runtime": {
            "reachable": runtime_fact(
                runtime_state.get(
                    "reachable"
                ),
                "runtime.reachable",
                generated_at,
            ),
            "docker_available": runtime_fact(
                runtime_state.get(
                    "docker_available"
                ),
                (
                    "runtime."
                    "docker_available"
                ),
                generated_at,
            ),
            "docker_reason": runtime_fact(
                runtime_state
                .get(
                    "docker",
                    {},
                )
                .get(
                    "reason"
                ),
                "runtime.docker.reason",
                generated_at,
            ),
            "gpu": {
                "available": runtime_fact(
                    runtime_gpu.get(
                        "available"
                    ),
                    (
                        "runtime.gpu."
                        "available"
                    ),
                    generated_at,
                ),
                "reason": runtime_fact(
                    runtime_gpu.get(
                        "reason"
                    ),
                    (
                        "runtime.gpu."
                        "reason"
                    ),
                    generated_at,
                ),
                "vram_total_mb": (
                    runtime_fact(
                        runtime_gpu.get(
                            "vram_total_mb"
                        ),
                        (
                            "runtime.gpu."
                            "vram_total_mb"
                        ),
                        generated_at,
                        "MB",
                    )
                ),
                "vram_used_mb": (
                    runtime_fact(
                        runtime_gpu.get(
                            "vram_used_mb"
                        ),
                        (
                            "runtime.gpu."
                            "vram_used_mb"
                        ),
                        generated_at,
                        "MB",
                    )
                ),
                "vram_free_mb": (
                    runtime_fact(
                        runtime_gpu.get(
                            "vram_free_mb"
                        ),
                        (
                            "runtime.gpu."
                            "vram_free_mb"
                        ),
                        generated_at,
                        "MB",
                    )
                ),
                "utilization_percent": (
                    runtime_fact(
                        runtime_gpu.get(
                            "utilization_percent"
                        ),
                        (
                            "runtime.gpu."
                            "utilization_percent"
                        ),
                        generated_at,
                        "percent",
                    )
                ),
                "temperature_c": (
                    runtime_fact(
                        runtime_gpu.get(
                            "temperature_c"
                        ),
                        (
                            "runtime.gpu."
                            "temperature_c"
                        ),
                        generated_at,
                        "C",
                    )
                ),
            },
        },
        "derived": {
            "gpu": build_gpu_derived(
                runtime_gpu
            ),
        },
    }

    return result


def build_cluster_facts(
    nodes: dict[str, Any],
    runtime_nodes: dict[str, Any] | None = None,
    runtime_info: dict[str, Any] | None = None,
) -> dict[str, Any]:
    runtime_nodes = (
        runtime_nodes or {}
    )
    runtime_info = (
        runtime_info or {}
    )

    return {
        "schema_version": (
            FACTS_SCHEMA_VERSION
        ),
        "contract": {
            "inventory": (
                "Declared inventory facts. "
                "Do not recalculate fields "
                "such as physical_cores or "
                "logical_threads."
            ),
            "runtime": (
                "Observed runtime facts from "
                "one snapshot. Runtime facts "
                "must not be confused with "
                "desired_roles."
            ),
            "derived": (
                "Arithmetic performed by the "
                "Cluster Control Layer. The "
                "LLM should quote these values "
                "instead of recomputing them."
            ),
            "desired_roles": (
                "Desired roles are declarations "
                "of intent and do not prove "
                "that a service is active."
            ),
            "placement": (
                "Facts are context, not causal "
                "placement reasons. Only "
                "placement.decision."
                "decision_reasons may be "
                "presented as causes of a "
                "placement decision."
            ),
        },
        "runtime_snapshot": runtime_info,
        "nodes": {
            name: build_node_facts(
                name,
                node,
                runtime_nodes.get(
                    name
                ),
                runtime_info,
            )
            for name, node
            in nodes.items()
        },
    }
