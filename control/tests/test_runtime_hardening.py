"""Tests for V0.9 runtime hardening."""

import unittest

from control.diagnostics import (
    classify_ansible_failure,
)
from control.state import (
    preserve_last_seen,
    runtime_status,
)


class RuntimeHardeningTests(
    unittest.TestCase
):

    def test_timeout_classification(self):
        result = {
            "rc": 124,
            "stdout": "",
            "stderr": "",
            "timed_out": True,
        }

        self.assertEqual(
            classify_ansible_failure(
                result
            ),
            "timeout",
        )

    def test_last_seen_updates_on_success(self):
        observed_at = (
            "2026-09-05T20:00:00+00:00"
        )

        result = preserve_last_seen(
            {
                "last_seen": (
                    "2026-09-05T19:00:00+00:00"
                )
            },
            True,
            observed_at,
        )

        self.assertEqual(
            result,
            observed_at,
        )

    def test_last_seen_preserved_on_failure(self):
        previous = (
            "2026-09-05T19:00:00+00:00"
        )

        result = preserve_last_seen(
            {
                "last_seen": previous
            },
            False,
            (
                "2026-09-05T20:00:00+00:00"
            ),
        )

        self.assertEqual(
            result,
            previous,
        )

    def test_runtime_status_missing(self):
        self.assertEqual(
            runtime_status(
                {},
                {
                    "age_seconds": None
                },
                300,
            ),
            "missing",
        )

    def test_runtime_status_fresh(self):
        self.assertEqual(
            runtime_status(
                {
                    "nodecpu": {}
                },
                {
                    "age_seconds": 20
                },
                300,
            ),
            "fresh",
        )

    def test_runtime_status_stale(self):
        self.assertEqual(
            runtime_status(
                {
                    "nodecpu": {}
                },
                {
                    "age_seconds": 301
                },
                300,
            ),
            "stale",
        )


if __name__ == "__main__":
    unittest.main()
