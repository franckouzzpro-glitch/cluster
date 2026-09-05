"""Tests for policy-as-data placement."""

import unittest
from datetime import (
    datetime,
    timezone,
)

from control.core import (
    NoMatchingNodeError,
    load_nodes,
    place,
)
from control.policy import (
    PolicyError,
    load_policy,
    validate_policy,
)


class PolicyDataTests(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.nodes = load_nodes()
        cls.policy = load_policy()

    def runtime_info(self, age=1):
        return {
            "generated_at": (
                datetime.now(
                    timezone.utc
                ).isoformat()
            ),
            "age_seconds": age,
        }

    def gpu_runtime(
        self,
        free1=7000,
        free2=3000,
        temp1=50,
        temp2=45,
    ):
        return {
            "nodegpu1": {
                "reachable": True,
                "docker_available": True,
                "gpu": {
                    "available": True,
                    "reason": "ok",
                    "vram_free_mb": free1,
                    "utilization_percent": 10,
                    "temperature_c": temp1,
                },
            },
            "nodegpu2": {
                "reachable": True,
                "docker_available": False,
                "gpu": {
                    "available": True,
                    "reason": "ok",
                    "vram_free_mb": free2,
                    "utilization_percent": 0,
                    "temperature_c": temp2,
                },
            },
        }

    def test_policy_loads(self):
        self.assertEqual(
            self.policy[
                "schema_version"
            ],
            1,
        )

    def test_stale_runtime_rejected(self):
        with self.assertRaises(
            NoMatchingNodeError
        ):
            place(
                self.nodes,
                ["cuda_worker"],
                self.gpu_runtime(),
                self.policy,
                self.runtime_info(
                    age=9999
                ),
            )

    def test_fresh_runtime_accepted(self):
        result = place(
            self.nodes,
            ["cuda_worker"],
            self.gpu_runtime(),
            self.policy,
            self.runtime_info(
                age=1
            ),
        )

        self.assertEqual(
            result["selected"],
            "nodegpu1",
        )

        self.assertTrue(
            result["runtime"]["fresh"]
        )

    def test_temperature_limit(self):
        result = place(
            self.nodes,
            ["cuda_worker"],
            self.gpu_runtime(
                free1=7000,
                free2=3000,
                temp1=95,
                temp2=45,
            ),
            self.policy,
            self.runtime_info(),
        )

        self.assertEqual(
            result["selected"],
            "nodegpu2",
        )

        nodegpu1 = next(
            item
            for item
            in result["evaluations"]
            if item["name"]
            == "nodegpu1"
        )

        self.assertIn(
            "gpu_temperature_limit:95>80",
            nodegpu1[
                "rejection_reasons"
            ],
        )

    def test_policy_ranking_can_change(self):
        policy = {
            **self.policy,
            "gpu": {
                **self.policy["gpu"],
                "ranking": [
                    "gpu_utilization_asc",
                    "gpu_free_vram_desc",
                    "inventory_order",
                ],
            },
        }

        result = place(
            self.nodes,
            ["cuda_worker"],
            self.gpu_runtime(
                free1=7000,
                free2=3000,
            ),
            policy,
            self.runtime_info(),
        )

        self.assertEqual(
            result["selected"],
            "nodegpu2",
        )

    def test_unknown_ranking_rejected(self):
        bad = {
            **self.policy,
            "gpu": {
                **self.policy["gpu"],
                "ranking": [
                    "warp_drive_desc"
                ],
            },
        }

        with self.assertRaises(
            PolicyError
        ):
            validate_policy(bad)


if __name__ == "__main__":
    unittest.main()
