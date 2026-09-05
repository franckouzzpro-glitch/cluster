"""Tests for runtime-aware placement."""

import unittest

from control.core import (
    load_nodes,
    place,
)


class RuntimePlacementTests(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.nodes = load_nodes()

    def test_unreachable_node_is_excluded(self):
        runtime = {
            "nodegpu1": {
                "reachable": False,
            },
            "nodegpu2": {
                "reachable": True,
                "gpu": {
                    "available": True,
                    "vram_free_mb": 10000,
                    "utilization_percent": 5,
                },
            },
        }

        result = place(
            self.nodes,
            ["cuda_worker"],
            runtime,
        )

        self.assertEqual(
            result["selected"],
            "nodegpu2",
        )

    def test_more_free_vram_wins(self):
        runtime = {
            "nodegpu1": {
                "reachable": True,
                "gpu": {
                    "available": True,
                    "vram_free_mb": 7000,
                    "utilization_percent": 5,
                },
            },
            "nodegpu2": {
                "reachable": True,
                "gpu": {
                    "available": True,
                    "vram_free_mb": 2000,
                    "utilization_percent": 5,
                },
            },
        }

        result = place(
            self.nodes,
            ["cuda_worker"],
            runtime,
        )

        self.assertEqual(
            result["selected"],
            "nodegpu1",
        )


if __name__ == "__main__":
    unittest.main()
