#!/usr/bin/env python3

import argparse
import json
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parent.parent
CAPABILITIES_FILE = ROOT / "inventory" / "capabilities.yml"


def load_nodes():
    with CAPABILITIES_FILE.open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f)

    return data["cluster"]["nodes"]


def active_capabilities(node):
    return sorted(
        name
        for name, enabled in node.get("capabilities", {}).items()
        if enabled is True
    )


def list_nodes(nodes):
    for name, node in nodes.items():
        roles = ", ".join(node.get("desired_roles", []))
        print(f"{name:10} {node['address']:15} {node['platform']:8} {roles}")


def show_node(nodes, name):
    if name not in nodes:
        raise SystemExit(f"Unknown node: {name}")

    node = nodes[name]

    result = {
        "name": name,
        "address": node.get("address"),
        "platform": node.get("platform"),
        "desired_roles": node.get("desired_roles", []),
        "capabilities": active_capabilities(node),
        "observed": node.get("observed", {}),
    }

    print(json.dumps(result, indent=2, ensure_ascii=False))


def find_capability(nodes, capability):
    matches = []

    for name, node in nodes.items():
        if node.get("capabilities", {}).get(capability) is True:
            matches.append(name)

    if not matches:
        raise SystemExit(f"No node provides capability: {capability}")

    for name in matches:
        print(name)


def main():
    parser = argparse.ArgumentParser(
        description="Read-only cluster control layer"
    )

    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("nodes", help="List cluster nodes")

    node_parser = sub.add_parser("node", help="Show one node")
    node_parser.add_argument("name")

    find_parser = sub.add_parser(
        "find",
        help="Find nodes providing a capability"
    )
    find_parser.add_argument("capability")

    args = parser.parse_args()
    nodes = load_nodes()

    if args.command == "nodes":
        list_nodes(nodes)

    elif args.command == "node":
        show_node(nodes, args.name)

    elif args.command == "find":
        find_capability(nodes, args.capability)


if __name__ == "__main__":
    main()
