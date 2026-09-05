"""Placement policy loader and validation."""

from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parent.parent

DEFAULT_POLICY_FILE = (
    ROOT
    / "control"
    / "placement-policy.yml"
)

SUPPORTED_GPU_RANKING = {
    "gpu_free_vram_desc",
    "gpu_utilization_asc",
    "gpu_temperature_asc",
    "inventory_order",
}

SUPPORTED_GENERAL_RANKING = {
    "inventory_order",
}


class PolicyError(Exception):
    """Invalid or unsupported placement policy."""


def load_policy(path=DEFAULT_POLICY_FILE):
    path = Path(path)

    if not path.exists():
        raise PolicyError(
            f"Missing placement policy: {path}"
        )

    with path.open(
        "r",
        encoding="utf-8",
    ) as f:
        data = yaml.safe_load(f) or {}

    validate_policy(data)

    return data


def validate_policy(policy):
    if policy.get("schema_version") != 1:
        raise PolicyError(
            "Unsupported placement policy "
            "schema_version"
        )

    runtime = policy.get("runtime", {})

    max_age = runtime.get(
        "max_age_seconds"
    )

    if (
        not isinstance(max_age, int)
        or isinstance(max_age, bool)
        or max_age <= 0
    ):
        raise PolicyError(
            "runtime.max_age_seconds "
            "must be a positive integer"
        )

    gpu_ranking = (
        policy
        .get("gpu", {})
        .get("ranking", [])
    )

    if (
        not isinstance(gpu_ranking, list)
        or not gpu_ranking
    ):
        raise PolicyError(
            "gpu.ranking must be "
            "a non-empty list"
        )

    unknown_gpu = [
        rule
        for rule in gpu_ranking
        if rule
        not in SUPPORTED_GPU_RANKING
    ]

    if unknown_gpu:
        raise PolicyError(
            "Unsupported GPU ranking rule(s): "
            + ", ".join(unknown_gpu)
        )

    general_ranking = (
        policy
        .get("general", {})
        .get(
            "ranking",
            ["inventory_order"],
        )
    )

    unknown_general = [
        rule
        for rule in general_ranking
        if rule
        not in SUPPORTED_GENERAL_RANKING
    ]

    if unknown_general:
        raise PolicyError(
            "Unsupported general ranking rule(s): "
            + ", ".join(unknown_general)
        )

    max_temp = (
        policy
        .get("gpu", {})
        .get("limits", {})
        .get("max_temperature_c")
    )

    if (
        max_temp is not None
        and (
            not isinstance(
                max_temp,
                (int, float),
            )
            or isinstance(max_temp, bool)
        )
    ):
        raise PolicyError(
            "gpu.limits.max_temperature_c "
            "must be numeric"
        )
