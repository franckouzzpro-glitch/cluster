"""Tests for structured MCP error semantics."""

import unittest

from control.core import (
    NoMatchingNodeError,
)
from control.mcp_server import (
    non_executing_boundary,
    structured_error,
)


class MCPErrorTests(unittest.TestCase):

    def test_no_matching_node_has_structured_code(self):
        result = structured_error(
            NoMatchingNodeError(
                "No eligible node"
            )
        )

        self.assertFalse(
            result["ok"]
        )

        self.assertEqual(
            result["error"]["code"],
            "NO_MATCHING_NODE",
        )

    def test_error_contract_forbids_inferred_cause(self):
        result = structured_error(
            NoMatchingNodeError(
                "No eligible node"
            )
        )

        self.assertIn(
            "Do not infer",
            result[
                "error"
            ][
                "cause_contract"
            ],
        )

    def test_boundary_is_non_executing(self):
        result = (
            non_executing_boundary()
        )

        self.assertFalse(
            result["performed"]
        )

        self.assertFalse(
            result["allowed"]
        )


if __name__ == "__main__":
    unittest.main()
