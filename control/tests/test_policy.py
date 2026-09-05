"""Tests for explainable placement policy."""

import unittest

from control.core import (
    NoMatchingNodeError,
    load_nodes,
    place,
)


class PlacementPolicyTests(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.nodes = load_nodes()

    def test_gpu_free_vram_priority(self):
        runtime = {
            "nodegpu1": {
                "reachable": True,
                "gpu": {
                    "available": True,
                    "reason": "ok",
                    "vram_free_mb": 7000,
                    "utilization_percent": 20,
                    "temperature_c": 60,
                },
            },
            "nodegpu2": {
                "reachable": True,
                "gpu": {
                    "available": True,
                    "reason": "ok",
                    "vram_free_mb": 3000,
                    "utilization_percent": 0,
                    "temperature_c": 40,
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

    def test_gpu_unavailable_rejected(self):
        runtime = {
            "nodegpu1": {
                "reachable": True,
                "gpu": {
                    "available": False,
                    "reason": (
                        "metrics_unavailable"
                    ),
                },
            },
            "nodegpu2": {
                "reachable": True,
                "gpu": {
                    "available": True,
                    "reason": "ok",
                    "vram_free_mb": 1000,
                    "utilization_percent": 5,
                    "temperature_c": 45,
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

    def test_docker_runtime_required(self):
        runtime = {
            "nodegpu1": {
                "reachable": True,
                "docker_available": False,
                "docker": {
                    "reason": "not_found",
                },
                "gpu": {
                    "available": True,
                    "reason": "ok",
                    "vram_free_mb": 7000,
                    "utilization_percent": 0,
                    "temperature_c": 50,
                },
            },
        }

        with self.assertRaises(
            NoMatchingNodeError
        ):
            place(
                self.nodes,
                [
                    "docker_host",
                    "cuda_worker",
                ],
                runtime,
            )

    def test_unreachable_reason_preserved(self):
        runtime = {
            "nodegpu1": {
                "reachable": False,
                "connectivity": {
                    "reason": (
                        "ssh_auth_failed"
                    ),
                },
            },
            "nodegpu2": {
                "reachable": True,
                "gpu": {
                    "available": True,
                    "reason": "ok",
                    "vram_free_mb": 1000,
                    "utilization_percent": 5,
                    "temperature_c": 45,
                },
            },
        }

        result = place(
            self.nodes,
            ["cuda_worker"],
            runtime,
        )

        nodegpu1 = next(
            item
            for item
            in result["evaluations"]
            if item["name"]
            == "nodegpu1"
        )

        self.assertIn(
            (
                "node_unreachable:"
                "ssh_auth_failed"
            ),
            nodegpu1[
                "rejection_reasons"
            ],
        )


if __name__ == "__main__":
    unittest.main()
