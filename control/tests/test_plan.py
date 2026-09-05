"""Tests for deterministic non-executing plans."""

import unittest

from control.core import (
    build_plan,
)


class PlanTests(unittest.TestCase):
    def setUp(self):
        self.nodes = {
            "nodegpu1": {
                "capabilities": {
                    "cuda_worker": True,
                }
            },
            "nodegpu2": {
                "capabilities": {
                    "cuda_worker": True,
                }
            },
        }

        self.runtime = {
            "nodegpu1": {
                "reachable": True,
                "gpu": {
                    "available": True,
                    "vram_free_mb": 7000,
                    "utilization_percent": 0,
                    "temperature_c": 45,
                },
            },
            "nodegpu2": {
                "reachable": True,
                "gpu": {
                    "available": True,
                    "vram_free_mb": 1000,
                    "utilization_percent": 0,
                    "temperature_c": 44,
                },
            },
        }

        self.runtime_info = {
            "status": "fresh",
            "age_seconds": 1,
            "generated_at": (
                "2026-09-05T21:08:47+00:00"
            ),
        }

        self.policy = {
            "runtime": {
                "required": True,
                "max_age_seconds": 300,
            },
            "eligibility": {
                "require_reachable": True,
                "require_runtime_gpu_for_gpu_jobs": True,
                "require_runtime_docker_for_docker_jobs": True,
            },
            "gpu": {
                "ranking": [
                    "gpu_free_vram_desc",
                    "gpu_utilization_asc",
                    "gpu_temperature_asc",
                    "inventory_order",
                ],
                "limits": {
                    "max_temperature_c": 80,
                },
            },
            "general": {
                "ranking": [
                    "inventory_order",
                ],
            },
        }

    def make_plan(self):
        return build_plan(
            self.nodes,
            "Run a CUDA workload",
            ["cuda_worker"],
            self.runtime,
            policy=self.policy,
            runtime_info=self.runtime_info,
        )

    def test_plan_is_valid(self):
        plan = self.make_plan()

        self.assertEqual(
            plan["verdict"],
            "VALID",
        )

    def test_plan_never_executes(self):
        plan = self.make_plan()

        self.assertFalse(
            plan["execution"]["performed"]
        )

        self.assertFalse(
            plan["execution"]["allowed"]
        )

    def test_plan_selects_expected_node(self):
        plan = self.make_plan()

        self.assertEqual(
            plan["selected"],
            "nodegpu1",
        )

    def test_plan_id_is_deterministic(self):
        first = self.make_plan()
        second = self.make_plan()

        self.assertEqual(
            first["plan_id"],
            second["plan_id"],
        )

    def test_plan_id_ignores_runtime_age(self):
        first = self.make_plan()

        self.runtime_info["age_seconds"] = 42

        second = self.make_plan()

        self.assertEqual(
            first["plan_id"],
            second["plan_id"],
        )

    def test_plan_id_changes_with_snapshot(self):
        first = self.make_plan()

        self.runtime_info["generated_at"] = (
            "2026-09-05T21:09:47+00:00"
        )

        second = self.make_plan()

        self.assertNotEqual(
            first["plan_id"],
            second["plan_id"],
        )


    def test_plan_id_changes_with_intent(self):
        first = self.make_plan()

        second = build_plan(
            self.nodes,
            "Run a different CUDA workload",
            ["cuda_worker"],
            self.runtime,
            policy=self.policy,
            runtime_info=self.runtime_info,
        )

        self.assertNotEqual(
            first["plan_id"],
            second["plan_id"],
        )


if __name__ == "__main__":
    unittest.main()
