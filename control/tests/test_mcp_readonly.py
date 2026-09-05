"""Contract tests for the read-only MCP facade."""

import unittest
from pathlib import Path

import control.mcp_server as server


SOURCE = Path("control/mcp_server.py")


class MCPReadonlyContractTests(unittest.TestCase):

    def test_expected_tools_only(self):
        tools = {
            "cluster_list_nodes",
            "cluster_get_node",
            "cluster_find_capability",
            "cluster_get_runtime_state",
            "cluster_get_facts",
            "cluster_get_node_facts",
            "cluster_place_workload",
            "cluster_plan_workload",
        }

        source = SOURCE.read_text(
            encoding="utf-8"
        )

        for tool in tools:
            self.assertIn(
                f"def {tool}",
                source,
            )

    def test_no_mutating_terms(self):
        source = SOURCE.read_text(
            encoding="utf-8"
        ).lower()

        forbidden = [
            "subprocess.run",
            "os.system",
            "ansible-playbook",
            "restart_service",
            "deploy_service",
            "ssh ",
        ]

        for term in forbidden:
            self.assertNotIn(
                term,
                source,
            )


if __name__ == "__main__":
    unittest.main()
