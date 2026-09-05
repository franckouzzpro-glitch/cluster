#!/usr/bin/env python3
"""CLI for the Cluster Control Layer."""

import argparse
import json
import sys
from pathlib import Path


# Allow execution as ./control/clusterctl.py from the repository root.
ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


from control.core import (  # noqa: E402
    ClusterError,
    find_nodes,
    get_node,
    list_nodes,
    load_nodes,
    place,
)


def print_json(data):
    print(json.dumps(data, indent=2, ensure_ascii=False))


def main():
    parser = argparse.ArgumentParser(
        description="Read-only Cluster Control Layer"
    )

    parser.add_argument(
        "--json",
        action="store_true",
        help="Return machine-readable JSON",
    )

    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser(
        "nodes",
        help="List cluster nodes",
    )

    node_parser = sub.add_parser(
        "node",
        help="Show one node",
    )
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

    try:
        nodes = load_nodes()

        if args.command == "nodes":
            result = list_nodes(nodes)

            if args.json:
                print_json(result)
            else:
                for node in result:
                    roles = ", ".join(node["desired_roles"])
                    print(
                        f"{node['name']:10} "
                        f"{node['address']:15} "
                        f"{node['platform']:8} "
                        f"{roles}"
                    )

        elif args.command == "node":
            result = get_node(nodes, args.name)
            print_json(result)

        elif args.command == "find":
            matches = find_nodes(nodes, args.capability)

            if not matches:
                raise ClusterError(
                    f"No node provides capability: {args.capability}"
                )

            if args.json:
                print_json({
                    "capability": args.capability,
                    "matches": matches,
                })
            else:
                for name in matches:
                    print(name)

        elif args.command == "place":
            result = place(
                nodes,
                args.required_capabilities,
            )

            if args.json:
                print_json(result)
            else:
                print(f"Selected: {result['selected']}")
                print("Candidates:")

                for candidate in result["candidates"]:
                    print(f"  - {candidate['name']}")

    except ClusterError as exc:
        if args.json:
            print_json({
                "ok": False,
                "error": str(exc),
            })
        else:
            print(f"ERROR: {exc}", file=sys.stderr)

        return 2

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
