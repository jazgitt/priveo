import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import deploy  # noqa: E402


class SmokeStep(unittest.TestCase):
    def run_json(self, conclusion):
        return {"jobs": [{"name": "test / deploy", "steps": [
            {"name": "Deploy", "conclusion": "success"},
            {"name": "Smoke test", "conclusion": conclusion}]}]}

    def test_reads_smoke_test_conclusion(self):
        self.assertEqual(deploy.smoke_step(self.run_json("success")), "success")
        self.assertEqual(deploy.smoke_step(self.run_json("failure")), "failure")

    def test_missing_step(self):
        self.assertEqual(deploy.smoke_step({"jobs": []}), "not found")


if __name__ == "__main__":
    unittest.main()
