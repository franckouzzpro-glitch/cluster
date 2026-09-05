#!/usr/bin/env python3
"""CLI for the Cluster Control Layer."""

import argparse
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


from control.core import (  # noqa: E402
    ClusterError,
    find_nodes,
    get_node,
    list_nodes,
    load_nodes,
    load_runtime_context,
    place,
)


def print_json(data):
    print(
        json.dumps(
            data,
            indent=2,
            ensure_ascii=False,
        )
    )


def main():
    parser = argparse.ArgumentParser(
        description=(
            "Read-only Cluster Control Layer"
        )
    )

    parser.add_argument(
        "--json",
        action="store_true",
        help=(
            "Return machine-readable JSON"
        ),
    )

    sub = parser.add_subparsers(
        dest="command",
        required=True,
    )

    sub.add_parser(
        "nodes",
        help="List cluster nodes",
    )

    node_parser = sub.add_parser(
        "node",
        help="Show one node",
    )
    node_parser.add_argument(
        "name"
    )

    find_parser = sub.add_parser(
        "find",
        help=(
            "Find nodes providing "
            "a capability"
        ),
    )

    find_parser.add_argument(
        "capability"
    )

    place_parser = sub.add_parser(
        "place",
        help=(
            "Select nodes matching "
            "required capabilities"
        ),
    )

    place_parser.add_argument(
        "--require",
        action="append",
        required=True,
        dest=(
            "required_capabilities"
        ),
        help=(
            "Required capability. "
            "May be repeated."
        ),
    )

    place_parser.add_argument(
        "--explain",
        action="store_true",
        help=(
            "Show accepted and rejected "
            "placement evaluations"
        ),
    )

    args = parser.parse_args()

    try:
        nodes = load_nodes()
        runtime_nodes, runtime_info = (
            load_runtime_context()
        )

        if args.command == "nodes":
            result = list_nodes(
                nodes,
                runtime_nodes,
                runtime_info=runtime_info,
            )

            if args.json:
                print_json(result)
            else:
                for node in result:
                    runtime = node.get(
                        "runtime",
                        {},
                    )

                    connectivity = (
                        runtime.get(
                            "connectivity",
                            {},
                        )
                    )

                    reachable = (
                        runtime.get(
                            "reachable",
                            "unknown",
                        )
                    )

                    reason = (
                        connectivity.get(
                            "reason",
                            "unknown",
                        )
                    )

                    roles = ", ".join(
                        node[
                            "desired_roles"
                        ]
                    )

                    print(
                        f"{node['name']:10} "
                        f"{node['address']:15} "
                        f"{node['platform']:8} "
                        f"reachable="
                        f"{reachable!s:7} "
                        f"reason="
                        f"{reason:18} "
                        f"{roles}"
                    )

        elif args.command == "node":
            result = get_node(
                nodes,
                args.name,
                runtime_nodes,
            )

            print_json(result)

        elif args.command == "find":
            matches = find_nodes(
                nodes,
                args.capability,
            )

            if not matches:
                raise ClusterError(
                    "No node provides "
                    "capability: "
                    f"{args.capability}"
                )

            if args.json:
                print_json({
                    "capability": (
                        args.capability
                    ),
                    "matches": matches,
                })
            else:
                for name in matches:
                    print(name)

        elif args.command == "place":
            result = place(
                nodes,
                args.required_capabilities,
                runtime_nodes,
                runtime_info=runtime_info,
            )

            if args.json:
                print_json(result)
            else:
                print(
                    "Selected: "
                    f"{result['selected']}"
                )

                print(
                    "Policy: "
                    f"{result['selection_policy']}"
                )

                print(
                    "Ranking: "
                    + " > ".join(
                        result[
                            "ranking_policy"
                        ]
                    )
                )

                print("Candidates:")

                for candidate in (
                    result["candidates"]
                ):
                    reasons = (
                        ", ".join(
                            candidate[
                                "ranking_reasons"
                            ]
                        )
                        or "stable-order"
                    )

                    print(
                        f"  {candidate['rank']}. "
                        f"{candidate['name']} "
                        f"[{reasons}]"
                    )

                if args.explain:
                    print(
                        "Evaluations:"
                    )

                    for item in (
                        result[
                            "evaluations"
                        ]
                    ):
                        if item[
                            "eligible"
                        ]:
                            status = (
                                "ELIGIBLE"
                            )
                            detail = (
                                ", ".join(
                                    item[
                                        "ranking_reasons"
                                    ]
                                )
                                or "accepted"
                            )
                        else:
                            status = (
                                "REJECTED"
                            )
                            detail = (
                                ", ".join(
                                    item[
                                        "rejection_reasons"
                                    ]
                                )
                            )

                        print(
                            f"  - "
                            f"{item['name']}: "
                            f"{status} "
                            f"[{detail}]"
                        )

    except ClusterError as exc:
        if args.json:
            print_json({
                "ok": False,
                "error": str(exc),
            })
        else:
            print(
                f"ERROR: {exc}",
                file=sys.stderr,
            )

        return 2

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
