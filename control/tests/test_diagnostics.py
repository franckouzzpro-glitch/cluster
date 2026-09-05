"""Tests for diagnostic classification."""

import unittest

from control.diagnostics import (
    classify_ansible_failure,
)


class DiagnosticTests(unittest.TestCase):

    def test_auth_failure(self):
        result = {
            "rc": 4,
            "stdout": (
                "Permission denied (publickey)"
            ),
            "stderr": "",
        }

        self.assertEqual(
            classify_ansible_failure(
                result
            ),
            "ssh_auth_failed",
        )

    def test_inventory_failure(self):
        result = {
            "rc": 0,
            "stdout": "",
            "stderr": (
                "No inventory was parsed"
            ),
        }

        self.assertEqual(
            classify_ansible_failure(
                result
            ),
            "inventory_error",
        )

    def test_network_failure(self):
        result = {
            "rc": 4,
            "stdout": (
                "Connection timed out"
            ),
            "stderr": "",
        }

        self.assertEqual(
            classify_ansible_failure(
                result
            ),
            "host_unreachable",
        )


if __name__ == "__main__":
    unittest.main()
