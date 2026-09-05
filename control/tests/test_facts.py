"""Tests for deterministic facts and provenance."""

import unittest

from control.core import load_nodes
from control.facts import (
    build_cluster_facts,
    build_gpu_derived,
)


class FactsTests(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.nodes = load_nodes()

    def test_nodecpu_core_count_is_not_multiplied(self):
        facts = build_cluster_facts(
            self.nodes
        )

        cpu = (
            facts["nodes"]
            ["nodecpu"]
            ["inventory"]
            ["cpu"]
        )

        self.assertEqual(
            cpu["physical_cores"]["value"],
            16,
        )

        self.assertEqual(
            cpu["logical_threads"]["value"],
            32,
        )

    def test_nodegpu1_core_count_is_not_multiplied(self):
        facts = build_cluster_facts(
            self.nodes
        )

        cpu = (
            facts["nodes"]
            ["nodegpu1"]
            ["inventory"]
            ["cpu"]
        )

        self.assertEqual(
            cpu["physical_cores"]["value"],
            28,
        )

        self.assertEqual(
            cpu["logical_threads"]["value"],
            56,
        )

    def test_desired_roles_are_not_runtime_services(self):
        facts = build_cluster_facts(
            self.nodes
        )

        roles = (
            facts["nodes"]
            ["nodenas"]
            ["semantics"]
            ["desired_roles"]
        )

        self.assertEqual(
            roles["provenance"]["kind"],
            "inventory",
        )

        self.assertIn(
            "not proof",
            roles["meaning"],
        )

    def test_nodegpu2_vram_percentages(self):
        derived = build_gpu_derived(
            {
                "vram_total_mb": 12227,
                "vram_used_mb": 11525,
                "vram_free_mb": 419,
            }
        )

        self.assertEqual(
            derived[
                "vram_free_percent"
            ]["value"],
            3.43,
        )

        self.assertEqual(
            derived[
                "vram_used_percent"
            ]["value"],
            94.26,
        )

    def test_gpu_values_are_not_forced_to_sum(self):
        derived = build_gpu_derived(
            {
                "vram_total_mb": 12227,
                "vram_used_mb": 11525,
                "vram_free_mb": 419,
            }
        )

        self.assertEqual(
            derived[
                "vram_unaccounted_mb"
            ]["value"],
            283,
        )

    def test_derived_value_has_control_layer_provenance(self):
        derived = build_gpu_derived(
            {
                "vram_total_mb": 8192,
                "vram_used_mb": 14,
                "vram_free_mb": 7775,
            }
        )

        provenance = (
            derived[
                "vram_free_percent"
            ]["provenance"]
        )

        self.assertEqual(
            provenance["kind"],
            "derived",
        )

        self.assertEqual(
            provenance["authority"],
            "control_layer",
        )

        self.assertTrue(
            provenance["derived"]
        )


if __name__ == "__main__":
    unittest.main()
