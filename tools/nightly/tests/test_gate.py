import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import gate  # noqa: E402


def c(bucket, name="x"):
    return {"name": name, "bucket": bucket, "state": bucket.upper()}


class EvaluateChecks(unittest.TestCase):
    def test_all_pass_or_skipped(self):
        self.assertEqual(gate.evaluate_checks([c("pass"), c("skipping")], 10), "pass")

    def test_any_fail_or_cancel_fails_even_with_pending(self):
        self.assertEqual(gate.evaluate_checks([c("pass"), c("fail"), c("pending")], 10), "fail")
        self.assertEqual(gate.evaluate_checks([c("cancel")], 10), "fail")

    def test_pending_waits(self):
        self.assertEqual(gate.evaluate_checks([c("pass"), c("pending")], 10), "pending")

    def test_no_checks_waits_then_is_allowed(self):
        self.assertEqual(gate.evaluate_checks([], 10), "pending")
        self.assertEqual(gate.evaluate_checks([], 400), "none")


if __name__ == "__main__":
    unittest.main()
