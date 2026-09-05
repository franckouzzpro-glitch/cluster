"""Runtime observed state helpers."""

from datetime import (
    datetime,
    timezone,
)
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parent.parent

DEFAULT_STATE_FILE = (
    ROOT
    / "runtime"
    / "state.yml"
)


def utc_now():
    return datetime.now(
        timezone.utc
    )


def empty_state():
    return {
        "cluster_state": {
            "schema_version": 2,
            "generated_at": (
                utc_now().isoformat()
            ),
            "nodes": {},
        }
    }


def save_state(
    data,
    path=DEFAULT_STATE_FILE,
):
    path = Path(path)

    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    with path.open(
        "w",
        encoding="utf-8",
    ) as f:
        yaml.safe_dump(
            data,
            f,
            sort_keys=False,
            allow_unicode=True,
        )


def load_state(
    path=DEFAULT_STATE_FILE,
):
    path = Path(path)

    if not path.exists():
        return empty_state()

    with path.open(
        "r",
        encoding="utf-8",
    ) as f:
        return yaml.safe_load(f) or {}


def parse_timestamp(value):
    if not value:
        return None

    try:
        parsed = datetime.fromisoformat(
            value.replace(
                "Z",
                "+00:00",
            )
        )
    except (
        TypeError,
        ValueError,
    ):
        return None

    if parsed.tzinfo is None:
        parsed = parsed.replace(
            tzinfo=timezone.utc
        )

    return parsed.astimezone(
        timezone.utc
    )


def runtime_metadata(
    state,
    now=None,
):
    cluster_state = state.get(
        "cluster_state",
        {},
    )

    generated_at = (
        cluster_state.get(
            "generated_at"
        )
    )

    timestamp = parse_timestamp(
        generated_at
    )

    now = now or utc_now()

    age_seconds = None

    if timestamp is not None:
        age_seconds = max(
            0.0,
            (
                now - timestamp
            ).total_seconds(),
        )

    return {
        "schema_version": (
            cluster_state.get(
                "schema_version"
            )
        ),
        "generated_at": generated_at,
        "age_seconds": age_seconds,
    }
