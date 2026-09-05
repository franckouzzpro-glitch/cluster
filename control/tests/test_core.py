"""Tests for the read-only Cluster Control Layer."""

import unittest

from control.core import (
    NoMatchingNodeError,
    UnknownNodeError,
    find_nodes,
    get_node,
    load_nodes,
    place,
)


class ClusterCoreTests(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.nodes = load_nodes()

    def test_expected_nodes_exist(self):
        self.assertEqual(
            set(self.nodes),
            {
                "nodenas",
                "nodecpu",
                "nodegpu1",
                "nodegpu2",
            },
        )

    def test_control_plane(self):
        self.assertEqual(
            find_nodes(self.nodes, "control_plane"),
            ["nodecpu"],
        )

    def test_storage_provider(self):
        self.assertEqual(
            find_nodes(self.nodes, "storage_provider"),
            ["nodenas"],
        )

    def test_cuda_workers(self):
        self.assertEqual(
            find_nodes(self.nodes, "cuda_worker"),
            ["nodegpu1", "nodegpu2"],
        )

    def test_heavy_gpu_placement(self):
        result = place(
            self.nodes,
            ["heavy_gpu_worker"],
        )

        self.assertEqual(
            result["selected"],
            "nodegpu2",
        )

    def test_docker_cuda_placement(self):
        result = place(
            self.nodes,
            ["docker_host", "cuda_worker"],
        )

        self.assertEqual(
            result["selected"],
            "nodegpu1",
        )

    def test_unknown_node(self):
        with self.assertRaises(UnknownNodeError):
            get_node(
                self.nodes,
                "node-does-not-exist",
            )

    def test_impossible_placement(self):
        with self.assertRaises(NoMatchingNodeError):
            place(
                self.nodes,
                [
                    "storage_provider",
                    "heavy_gpu_worker",
                ],
            )


if __name__ == "__main__":
    unittest.main()
