#!/usr/bin/env python3
"""Collect read-only runtime state from the cluster."""

import json
import os
import re
import subprocess
import sys
from datetime import (
    datetime,
    timezone,
)
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


from control.core import load_nodes  # noqa: E402
from control.diagnostics import (  # noqa: E402
    classify_ansible_failure,
    short_error_detail,
)
from control.policy import load_policy  # noqa: E402
from control.state import (  # noqa: E402
    load_state,
    preserve_last_seen,
    save_state,
)


INVENTORY = ROOT / "ansible" / "inventory.yml"
ANSIBLE_CONFIG = ROOT / "ansible" / "ansible.cfg"


def now():
    return datetime.now(
        timezone.utc
    ).isoformat()


def command_timeout():
    policy = load_policy()

    return (
        policy
        .get("runtime", {})
        .get(
            "command_timeout_seconds",
            20,
        )
    )


def run_command(command):
    env = os.environ.copy()
    env["ANSIBLE_CONFIG"] = str(
        ANSIBLE_CONFIG
    )

    try:
        result = subprocess.run(
            command,
            cwd=ROOT,
            text=True,
            capture_output=True,
            env=env,
            timeout=command_timeout(),
        )

        return {
            "rc": result.returncode,
            "stdout": (
                result.stdout.strip()
            ),
            "stderr": (
                result.stderr.strip()
            ),
            "timed_out": False,
        }

    except subprocess.TimeoutExpired as exc:
        stdout = exc.stdout or ""
        stderr = exc.stderr or ""

        if isinstance(stdout, bytes):
            stdout = stdout.decode(
                errors="replace"
            )

        if isinstance(stderr, bytes):
            stderr = stderr.decode(
                errors="replace"
            )

        return {
            "rc": 124,
            "stdout": stdout.strip(),
            "stderr": stderr.strip(),
            "timed_out": True,
        }


def run_ansible(
    host,
    module,
    args=None,
):
    command = [
        "ansible",
        "-i",
        str(INVENTORY),
        host,
        "-m",
        module,
    ]

    if args is not None:
        command += [
            "-a",
            args,
        ]

    return run_command(command)


def host_actually_ran(
    result,
    host,
):
    return bool(
        re.search(
            rf"(?m)^{re.escape(host)}\\s+\\|",
            result.get(
                "stdout",
                "",
            ),
        )
    )


def extract_ansible_payload(
    result,
):
    stdout = result.get(
        "stdout",
        "",
    )

    if ">>" not in stdout:
        return ""

    return stdout.split(
        ">>",
        1,
    )[1].strip()


def connectivity_status(
    host,
    platform,
):
    module = (
        "ansible.windows.win_ping"
        if platform == "windows"
        else "ansible.builtin.ping"
    )

    result = run_ansible(
        host,
        module,
    )

    success = (
        result["rc"] == 0
        and not result["timed_out"]
        and host_actually_ran(
            result,
            host,
        )
        and '"ping": "pong"'
        in result["stdout"]
    )

    if success:
        return {
            "reachable": True,
            "connectivity": {
                "status": "reachable",
                "reason": "ok",
            },
        }

    return {
        "reachable": False,
        "connectivity": {
            "status": "unreachable",
            "reason": (
                classify_ansible_failure(
                    result
                )
            ),
            "detail": (
                short_error_detail(
                    result
                )
            ),
        },
    }


def docker_status(
    host,
    platform,
):
    if platform == "windows":
        return {
            "available": False,
            "reason": "not_declared",
        }

    result = run_ansible(
        host,
        "ansible.builtin.shell",
        "command -v docker >/dev/null 2>&1",
    )

    if (
        result["rc"] == 0
        and not result["timed_out"]
        and host_actually_ran(
            result,
            host,
        )
    ):
        return {
            "available": True,
            "reason": "ok",
        }

    return {
        "available": False,
        "reason": (
            classify_ansible_failure(
                result
            )
            if (
                result["rc"] != 0
                or result["timed_out"]
            )
            else "not_found"
        ),
    }


def parse_gpu_csv(
    payload,
):
    if not payload:
        return None

    for line in reversed(
        payload.splitlines()
    ):
        line = line.strip()

        if not line:
            continue

        parts = [
            item.strip()
            for item
            in line.split(",")
        ]

        if len(parts) != 5:
            continue

        try:
            total, used, free, temp, util = [
                int(value)
                for value
                in parts
            ]
        except ValueError:
            continue

        return {
            "vram_total_mb": total,
            "vram_used_mb": used,
            "vram_free_mb": free,
            "temperature_c": temp,
            "utilization_percent": util,
        }

    return None


def gpu_status_linux(host):
    result = run_ansible(
        host,
        "ansible.builtin.shell",
        (
            "nvidia-smi "
            "--query-gpu="
            "memory.total,"
            "memory.used,"
            "memory.free,"
            "temperature.gpu,"
            "utilization.gpu "
            "--format=csv,noheader,nounits"
        ),
    )

    metrics = parse_gpu_csv(
        extract_ansible_payload(
            result
        )
    )

    if (
        result["rc"] == 0
        and not result["timed_out"]
        and host_actually_ran(
            result,
            host,
        )
        and metrics
    ):
        return {
            "available": True,
            "reason": "ok",
            **metrics,
        }

    return {
        "available": False,
        "reason": (
            classify_ansible_failure(
                result
            )
            if (
                result["rc"] != 0
                or result["timed_out"]
            )
            else "metrics_unavailable"
        ),
    }


def gpu_status_windows(host):
    result = run_ansible(
        host,
        "ansible.windows.win_shell",
        (
            "nvidia-smi.exe "
            "--query-gpu="
            "memory.total,"
            "memory.used,"
            "memory.free,"
            "temperature.gpu,"
            "utilization.gpu "
            "--format=csv,noheader,nounits"
        ),
    )

    metrics = parse_gpu_csv(
        extract_ansible_payload(
            result
        )
    )

    if (
        result["rc"] == 0
        and not result["timed_out"]
        and host_actually_ran(
            result,
            host,
        )
        and metrics
    ):
        return {
            "available": True,
            "reason": "ok",
            **metrics,
        }

    return {
        "available": False,
        "reason": (
            classify_ansible_failure(
                result
            )
            if (
                result["rc"] != 0
                or result["timed_out"]
            )
            else "metrics_unavailable"
        ),
    }


def collect_node_state(
    name,
    node,
    previous_state=None,
):
    platform = node.get(
        "platform"
    )

    observed_at = now()

    state = {
        "observed_at": observed_at,
        "last_seen": None,
        "reachable": False,
        "connectivity": {
            "status": "unknown",
            "reason": "not_checked",
        },
        "docker_available": False,
        "docker": {
            "available": False,
            "reason": "not_checked",
        },
        "gpu": {
            "available": False,
            "reason": "not_applicable",
        },
    }

    connection = connectivity_status(
        name,
        platform,
    )

    state.update(connection)

    state["last_seen"] = (
        preserve_last_seen(
            previous_state,
            state["reachable"],
            observed_at,
        )
    )

    if not state["reachable"]:
        state["docker"]["reason"] = (
            "node_unreachable"
        )
        state["gpu"]["reason"] = (
            "node_unreachable"
        )

        return state

    docker = docker_status(
        name,
        platform,
    )

    state["docker"] = docker
    state["docker_available"] = (
        docker["available"]
    )

    capabilities = node.get(
        "capabilities",
        {},
    )

    if capabilities.get(
        "gpu_worker"
    ) is True:
        if platform == "windows":
            state["gpu"] = (
                gpu_status_windows(
                    name
                )
            )
        else:
            state["gpu"] = (
                gpu_status_linux(
                    name
                )
            )

    return state


def main():
    if not INVENTORY.exists():
        raise SystemExit(
            f"Missing Ansible inventory: "
            f"{INVENTORY}"
        )

    if not ANSIBLE_CONFIG.exists():
        raise SystemExit(
            f"Missing Ansible config: "
            f"{ANSIBLE_CONFIG}"
        )

    nodes = load_nodes()

    previous = load_state()

    previous_nodes = (
        previous
        .get(
            "cluster_state",
            {},
        )
        .get(
            "nodes",
            {},
        )
    )

    data = {
        "cluster_state": {
            "schema_version": 3,
            "generated_at": now(),
            "nodes": {},
        }
    }

    for name, node in nodes.items():
        print(
            f"Collecting {name}..."
        )

        data[
            "cluster_state"
        ][
            "nodes"
        ][
            name
        ] = collect_node_state(
            name,
            node,
            previous_nodes.get(
                name,
                {},
            ),
        )

    save_state(data)

    print()
    print(
        "Runtime state written to:"
    )
    print(
        "runtime/state.yml"
    )
    print()

    print(
        json.dumps(
            data,
            indent=2,
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main()
