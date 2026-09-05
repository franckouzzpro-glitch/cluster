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


def node_summary(name, node):
    return {
        "name": name,
        "address": node.get("address"),
        "platform": node.get("platform"),
        "desired_roles": node.get("desired_roles", []),
        "capabilities": active_capabilities(node),
        "observed": node.get("observed", {}),
    }


def print_json(data):
    print(json.dumps(data, indent=2, ensure_ascii=False))


def list_nodes(nodes, as_json=False):
    if as_json:
        print_json([
            node_summary(name, node)
            for name, node in nodes.items()
        ])
        return

    for name, node in nodes.items():
        roles = ", ".join(node.get("desired_roles", []))
        print(f"{name:10} {node['address']:15} {node['platform']:8} {roles}")


def show_node(nodes, name, as_json=False):
    if name not in nodes:
        raise SystemExit(f"Unknown node: {name}")

    result = node_summary(name, nodes[name])

    if as_json:
        print_json(result)
        return

    print_json(result)


def find_capability(nodes, capability, as_json=False):
    matches = [
        name
        for name, node in nodes.items()
        if node.get("capabilities", {}).get(capability) is True
    ]

    if not matches:
        raise SystemExit(f"No node provides capability: {capability}")

    if as_json:
        print_json({
            "capability": capability,
            "matches": matches,
        })
        return

    for name in matches:
        print(name)


def place(nodes, required_capabilities, as_json=False):
    candidates = []

    for name, node in nodes.items():
        capabilities = node.get("capabilities", {})

        if all(capabilities.get(capability) is True
               for capability in required_capabilities):
            candidates.append({
                "name": name,
                "address": node.get("address"),
                "platform": node.get("platform"),
                "capabilities": active_capabilities(node),
            })

    if not candidates:
        raise SystemExit(
            "No node satisfies required capabilities: "
            + ", ".join(required_capabilities)
        )

    result = {
        "required_capabilities": required_capabilities,
        "candidates": candidates,
        "selected": candidates[0]["name"],
        "selection_policy": "first_matching_node",
    }

    if as_json:
        print_json(result)
        return

    print(f"Selected: {result['selected']}")
    print("Candidates:")
    for candidate in candidates:
        print(f"  - {candidate['name']}")


def main():
    parser = argparse.ArgumentParser(
        description="Read-only cluster control layer"
    )

    parser.add_argument(
        "--json",
        action="store_true",
        help="Return machine-readable JSON",
    )

    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("nodes", help="List cluster nodes")

    node_parser = sub.add_parser("node", help="Show one node")
    node_parser.add_argument("name")

    find_parser = sub.add_parser(
        "find",
        help="Find nodes providing a capability",
    )
    find_parser.add_argument("capability")

    place_parser = sub.add_parser(
        "place",
        help="Select nodes matching required capabilities",
    )
    place_parser.add_argument(
        "--require",
        action="append",
        required=True,
        dest="required_capabilities",
        help="Required capability. May be repeated.",
    )

    args = parser.parse_args()
    nodes = load_nodes()

    if args.command == "nodes":
        list_nodes(nodes, args.json)

    elif args.command == "node":
        show_node(nodes, args.name, args.json)

    elif args.command == "find":
        find_capability(nodes, args.capability, args.json)

    elif args.command == "place":
        place(nodes, args.required_capabilities, args.json)


if __name__ == "__main__":
    main()
