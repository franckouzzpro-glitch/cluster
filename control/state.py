"""Runtime observed state helpers."""

from datetime import datetime, timezone
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parent.parent
DEFAULT_STATE_FILE = ROOT / "runtime" / "state.yml"


def empty_state():
    return {
        "cluster_state": {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "nodes": {},
        }
    }


def save_state(data, path=DEFAULT_STATE_FILE):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)

    with path.open("w", encoding="utf-8") as f:
        yaml.safe_dump(
            data,
            f,
            sort_keys=False,
            allow_unicode=True,
        )


def load_state(path=DEFAULT_STATE_FILE):
    path = Path(path)

    if not path.exists():
        return empty_state()

    with path.open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}

    return data
