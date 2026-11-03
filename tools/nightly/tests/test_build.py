import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import build_combined  # noqa: E402

IDENT = ["-c", "user.name=T", "-c", "user.email=t@t.invalid", "-c", "init.defaultBranch=main"]


def g(cwd, *args):
    return subprocess.run(["git", *IDENT, *args], cwd=cwd, check=True, capture_output=True, text=True).stdout.strip()


class Fixture:
    """A bare 'origin', a seed clone to make PRs, and the nightly clone."""

    def __init__(self, root: Path):
        self.origin = root / "origin.git"
        g(root, "init", "-q", "--bare", str(self.origin))
        self.seed = root / "seed"
        g(root, "clone", "-q", str(self.origin), str(self.seed))
        g(self.seed, "checkout", "-q", "-b", "main")
        mig = self.seed / "services/api/migrations/versions"
        mig.mkdir(parents=True)
        (mig / "0001.py").write_text('revision = "0001"\ndown_revision = None\n')
        (self.seed / "a.txt").write_text("a\n")
        g(self.seed, "add", "-A")
        g(self.seed, "commit", "-q", "-m", "init")
        g(self.seed, "push", "-q", "origin", "main")
        self.clone = root / "clone"
        g(root, "clone", "-q", str(self.origin), str(self.clone))

    def pr(self, number: int, files: dict) -> str:
        g(self.seed, "checkout", "-q", "-B", f"pr{number}", "origin/main")
        for name, content in files.items():
            path = self.seed / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content)
        g(self.seed, "add", "-A")
        g(self.seed, "commit", "-q", "-m", f"pr {number}")
        sha = g(self.seed, "rev-parse", "HEAD")
        g(self.seed, "push", "-q", "origin", f"HEAD:refs/pull/{number}/head")
        return sha


def sel(*items):
    return {"selected": [{"number": n, "title": f"T{n}", "head": h} for n, h in items], "dropped": []}


class Build(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.fx = Fixture(Path(self.tmp.name))

    def tearDown(self):
        self.tmp.cleanup()

    def test_merges_in_order_and_records_heads(self):
        h1 = self.fx.pr(1, {"b.txt": "b\n"})
        h2 = self.fx.pr(2, {"c.txt": "c\n"})
        res = build_combined.build(str(self.fx.clone), sel((1, h1), (2, h2)), "nightly/test")
        self.assertEqual([m["number"] for m in res["merged"]], [1, 2])
        self.assertEqual(res["dropped"], [])
        self.assertEqual(res["migration_problems"], [])
        self.assertTrue((self.fx.clone / "b.txt").exists() and (self.fx.clone / "c.txt").exists())
        self.assertEqual(g(self.fx.clone, "rev-parse", "--abbrev-ref", "HEAD"), "nightly/test")

    def test_conflict_is_dropped_and_clone_is_clean(self):
        h1 = self.fx.pr(1, {"a.txt": "one\n"})
        h2 = self.fx.pr(2, {"a.txt": "two\n"})
        h3 = self.fx.pr(3, {"d.txt": "d\n"})
        res = build_combined.build(str(self.fx.clone), sel((1, h1), (2, h2), (3, h3)), "nightly/test")
        self.assertEqual([m["number"] for m in res["merged"]], [1, 3])
        self.assertEqual(res["dropped"][0]["number"], 2)
        self.assertIn("a.txt", res["dropped"][0]["reason"])
        self.assertEqual(g(self.fx.clone, "status", "--porcelain"), "")

    def test_moved_head_is_dropped(self):
        self.fx.pr(1, {"b.txt": "b\n"})
        res = build_combined.build(str(self.fx.clone), sel((1, "0" * 40)), "nightly/test")
        self.assertEqual(res["merged"], [])
        self.assertIn("moved", res["dropped"][0]["reason"])

    def test_missing_head_is_dropped(self):
        res = build_combined.build(str(self.fx.clone), sel((9, "a" * 40)), "nightly/test")
        self.assertIn("fetched", res["dropped"][0]["reason"])

    def test_migration_fork_is_reported(self):
        m = "services/api/migrations/versions/"
        h1 = self.fx.pr(1, {m + "0002.py": 'revision = "0002"\ndown_revision = "0001"\n'})
        h2 = self.fx.pr(2, {m + "0003.py": 'revision = "0003"\ndown_revision = "0001"\n'})
        res = build_combined.build(str(self.fx.clone), sel((1, h1), (2, h2)), "nightly/test")
        self.assertTrue(res["migration_problems"])

    def test_empty_selection_leaves_branch_at_main(self):
        res = build_combined.build(str(self.fx.clone), sel(), "nightly/test")
        self.assertEqual(res["tip"], res["base"])


if __name__ == "__main__":
    unittest.main()
