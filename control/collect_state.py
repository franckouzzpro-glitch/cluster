#!/usr/bin/env python3
"""Collect read-only runtime state from the cluster."""

import json
import os
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


from control.core import load_nodes  # noqa: E402
from control.state import save_state  # noqa: E402


INVENTORY = ROOT / "ansible" / "inventory.yml"
ANSIBLE_CONFIG = ROOT / "ansible" / "ansible.cfg"


def run_command(command):
    env = os.environ.copy()
    env["ANSIBLE_CONFIG"] = str(ANSIBLE_CONFIG)

    result = subprocess.run(
        command,
        cwd=ROOT,
        text=True,
        capture_output=True,
        env=env,
    )

    return {
        "rc": result.returncode,
        "stdout": result.stdout.strip(),
        "stderr": result.stderr.strip(),
    }


def run_ansible(host, module, args=None):
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


def host_actually_ran(result, host):
    """
    Ansible may return rc=0 even when a host pattern matches nothing.
    Require evidence that the requested host appeared in stdout.
    """
    if result["rc"] != 0:
        return False

    return bool(
        re.search(
            rf"(?m)^{re.escape(host)}\s+\|",
            result["stdout"],
        )
    )


def extract_ansible_payload(result):
    """
    Extract command stdout from standard Ansible ad-hoc output.

    Typical form:

        nodegpu1 | CHANGED | rc=0 >>
        8192, 14, 8178, 48, 0
    """
    if ">>" not in result["stdout"]:
        return ""

    return result["stdout"].split(">>", 1)[1].strip()


def ansible_ping(host, platform):
    if platform == "windows":
        module = "ansible.windows.win_ping"
    else:
        module = "ansible.builtin.ping"

    result = run_ansible(
        host,
        module,
    )

    return {
        "reachable": host_actually_ran(
            result,
            host,
        ),
        "source": "ansible",
    }


def docker_available(host, platform):
    if platform == "windows":
        return False

    result = run_ansible(
        host,
        "ansible.builtin.shell",
        "command -v docker >/dev/null 2>&1",
    )

    return (
        host_actually_ran(result, host)
        and result["rc"] == 0
    )


def parse_gpu_csv(payload):
    """
    Parse:
        total, used, free, temp, utilization
    """
    if not payload:
        return {
            "available": False,
        }

    for line in reversed(payload.splitlines()):
        line = line.strip()

        if not line:
            continue

        parts = [
            part.strip()
            for part in line.split(",")
        ]

        if len(parts) != 5:
            continue

        try:
            total, used, free, temp, util = [
                int(value)
                for value in parts
            ]
        except ValueError:
            continue

        return {
            "available": True,
            "vram_total_mb": total,
            "vram_used_mb": used,
            "vram_free_mb": free,
            "temperature_c": temp,
            "utilization_percent": util,
        }

    return {
        "available": False,
    }


def nvidia_metrics_linux(host):
    result = run_ansible(
        host,
        "ansible.builtin.shell",
        (
            "nvidia-smi "
            "--query-gpu=memory.total,memory.used,memory.free,"
            "temperature.gpu,utilization.gpu "
            "--format=csv,noheader,nounits"
        ),
    )

    if not host_actually_ran(result, host):
        return {
            "available": False,
        }

    return parse_gpu_csv(
        extract_ansible_payload(result)
    )


def nvidia_metrics_windows(host):
    result = run_ansible(
        host,
        "ansible.windows.win_shell",
        (
            "nvidia-smi.exe "
            "--query-gpu=memory.total,memory.used,memory.free,"
            "temperature.gpu,utilization.gpu "
            "--format=csv,noheader,nounits"
        ),
    )

    if not host_actually_ran(result, host):
        return {
            "available": False,
        }

    return parse_gpu_csv(
        extract_ansible_payload(result)
    )


def collect_node_state(name, node):
    platform = node.get("platform")

    state = {
        "reachable": False,
        "last_seen": datetime.now(
            timezone.utc
        ).isoformat(),
        "docker_available": False,
        "gpu": {
            "available": False,
        },
    }

    ping = ansible_ping(
        name,
        platform,
    )

    state["reachable"] = ping["reachable"]

    if not state["reachable"]:
        return state

    state["docker_available"] = docker_available(
        name,
        platform,
    )

    if (
        node
        .get("capabilities", {})
        .get("gpu_worker")
        is True
    ):
        if platform == "windows":
            state["gpu"] = nvidia_metrics_windows(
                name
            )
        else:
            state["gpu"] = nvidia_metrics_linux(
                name
            )

    return state


def main():
    if not INVENTORY.exists():
        raise SystemExit(
            f"Missing Ansible inventory: {INVENTORY}"
        )

    if not ANSIBLE_CONFIG.exists():
        raise SystemExit(
            f"Missing Ansible config: {ANSIBLE_CONFIG}"
        )

    nodes = load_nodes()

    data = {
        "cluster_state": {
            "generated_at": datetime.now(
                timezone.utc
            ).isoformat(),
            "nodes": {},
        }
    }

    for name, node in nodes.items():
        print(f"Collecting {name}...")

        data["cluster_state"]["nodes"][name] = (
            collect_node_state(
                name,
                node,
            )
        )

    save_state(data)

    print()
    print("Runtime state written to:")
    print("runtime/state.yml")
    print()

    print(json.dumps(
        data,
        indent=2,
        ensure_ascii=False,
    ))


if __name__ == "__main__":
    main()
