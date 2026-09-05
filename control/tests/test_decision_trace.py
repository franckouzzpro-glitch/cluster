"""Tests for deterministic placement explanations."""

import unittest

from control.core import build_decision_trace


class DecisionTraceTests(unittest.TestCase):
    def setUp(self):
        self.runtime = {
            "nodegpu1": {
                "gpu": {
                    "vram_free_mb": 7775,
                    "utilization_percent": 0,
                    "temperature_c": 46,
                }
            },
            "nodegpu2": {
                "gpu": {
                    "vram_free_mb": 443,
                    "utilization_percent": 3,
                    "temperature_c": 45,
                }
            },
        }

        self.candidates = [
            {"name": "nodegpu1"},
            {"name": "nodegpu2"},
        ]

        self.rules = [
            "gpu_free_vram_desc",
            "gpu_utilization_asc",
            "gpu_temperature_asc",
            "inventory_order",
        ]

        self.inventory_index = {
            "nodegpu1": 0,
            "nodegpu2": 1,
        }

    def trace(self):
        return build_decision_trace(
            self.candidates,
            self.rules,
            self.runtime,
            self.inventory_index,
        )

    def test_selected_node(self):
        self.assertEqual(
            self.trace()["selected"],
            "nodegpu1",
        )

    def test_free_vram_is_only_decision_reason(self):
        reasons = self.trace()[
            "decision_reasons"
        ]

        self.assertEqual(
            len(reasons),
            1,
        )

        self.assertEqual(
            reasons[0]["criterion"],
            "gpu_free_vram_desc",
        )

        self.assertEqual(
            reasons[0]["selected_value"],
            7775,
        )

    def test_later_gpu_rules_are_not_needed(self):
        factors = {
            item["criterion"]: item
            for item in self.trace()["factors"]
        }

        self.assertEqual(
            factors[
                "gpu_utilization_asc"
            ]["outcome"],
            "not_needed",
        )

        self.assertEqual(
            factors[
                "gpu_temperature_asc"
            ]["outcome"],
            "not_needed",
        )

    def test_temperature_cannot_be_claimed_as_reason(self):
        criteria = {
            item["criterion"]
            for item in self.trace()[
                "decision_reasons"
            ]
        }

        self.assertNotIn(
            "gpu_temperature_asc",
            criteria,
        )

    def test_docker_cannot_be_claimed_as_reason(self):
        serialized = str(
            self.trace()[
                "decision_reasons"
            ]
        ).lower()

        self.assertNotIn(
            "docker",
            serialized,
        )


if __name__ == "__main__":
    unittest.main()
