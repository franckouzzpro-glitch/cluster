"""Tests for node-scoped fact binding."""

import unittest

from control.core import load_nodes
from control.facts import build_node_facts


class NodeFactsTests(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.nodes = load_nodes()

    def test_nodecpu_identity_and_cpu_stay_bound(self):
        facts = build_node_facts(
            "nodecpu",
            self.nodes["nodecpu"],
            {},
            {},
        )

        self.assertEqual(
            facts[
                "identity"
            ][
                "name"
            ][
                "value"
            ],
            "nodecpu",
        )

        cpu = facts[
            "inventory"
        ][
            "cpu"
        ]

        self.assertEqual(
            cpu[
                "physical_cores"
            ][
                "value"
            ],
            16,
        )

        self.assertEqual(
            cpu[
                "logical_threads"
            ][
                "value"
            ],
            32,
        )

    def test_nodenas_values_are_distinct(self):
        facts = build_node_facts(
            "nodenas",
            self.nodes["nodenas"],
            {},
            {},
        )

        cpu = facts[
            "inventory"
        ][
            "cpu"
        ]

        self.assertEqual(
            cpu[
                "physical_cores"
            ][
                "value"
            ],
            6,
        )

        self.assertEqual(
            cpu[
                "logical_threads"
            ][
                "value"
            ],
            12,
        )


if __name__ == "__main__":
    unittest.main()
