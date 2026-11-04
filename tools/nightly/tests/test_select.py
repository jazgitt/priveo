import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import migrations  # noqa: E402
import select_prs  # noqa: E402

MAIN = {"0001": (), "0002": ("0001",), "0003": ("0002",)}


def pr(number, labels=("nightly",), **kw):
    base = {"number": number, "title": f"PR {number}", "isDraft": False, "baseRefName": "main",
            "labels": [{"name": n} for n in labels], "mergeable": "MERGEABLE",
            "headRefOid": f"sha{number}", "headRefName": f"b{number}", "isCrossRepository": False}
    base.update(kw)
    return base


class MigrationText(unittest.TestCase):
    def test_parse(self):
        text = 'revision = "0046"\ndown_revision = "0045"\n'
        self.assertEqual(migrations.parse_migration(text), ("0046", ("0045",)))
        self.assertEqual(migrations.parse_migration('revision = "9"\ndown_revision = None\n'), ("9", ()))
        merged = 'revision: str = "9"\ndown_revision = ("7", "8")\n'
        self.assertEqual(migrations.parse_migration(merged), ("9", ("7", "8")))
        self.assertIsNone(migrations.parse_migration("print('hi')"))

    def test_heads_and_check(self):
        self.assertEqual(migrations.heads(MAIN), ["0003"])
        self.assertEqual(migrations.check_chain(MAIN), [])
        forked = {**MAIN, "0004a": ("0003",), "0004b": ("0003",)}
        self.assertIn("0004a", migrations.check_chain(forked)[0])
        self.assertTrue(migrations.check_chain({"0002": ("0001",)}))


class Clashes(unittest.TestCase):
    def test_clean_chain_of_two(self):
        r = migrations.clashes(MAIN, {5: {"0004": ("0003",)}, 6: {"0005": ("0004",)}})
        self.assertEqual(r, {})

    def test_same_revision_number(self):
        r = migrations.clashes(MAIN, {5: {"0004": ("0003",)}, 6: {"0004": ("0003",)}})
        self.assertEqual(list(r), [6])
        self.assertIn("already exists in #5", r[6])

    def test_fork_two_heads(self):
        r = migrations.clashes(MAIN, {5: {"0004": ("0003",)}, 6: {"0005": ("0003",)}})
        self.assertEqual(list(r), [6])
        self.assertIn("two heads", r[6])

    def test_stale_base(self):
        r = migrations.clashes(MAIN, {7: {"0009": ("0008",)}})
        self.assertIn("0008", r[7])

    def test_revision_already_on_main(self):
        r = migrations.clashes(MAIN, {7: {"0003": ("0002",)}})
        self.assertIn("main", r[7])

    def test_rejected_pr_does_not_block_later_one(self):
        r = migrations.clashes(MAIN, {5: {"0004": ("0009",)}, 6: {"0004": ("0003",)}})
        self.assertEqual(list(r), [5])

    def test_pr_with_internal_chain(self):
        r = migrations.clashes(MAIN, {5: {"0004": ("0003",), "0005": ("0004",)}})
        self.assertEqual(r, {})


class Selection(unittest.TestCase):
    def reasons(self, result):
        return {d["number"]: d["reason"] for d in result["dropped"]}

    def test_eligibility_rules(self):
        prs = [
            pr(1), pr(2, isDraft=True), pr(3, baseRefName="dev"), pr(4, labels=()),
            pr(5, labels=("nightly", "hold")), pr(6, labels=("nightly", "no-nightly")),
            pr(7, labels=("nightly", "needs-human")), pr(8, mergeable="CONFLICTING"),
            pr(9, isCrossRepository=True), pr(10, mergeable="UNKNOWN"),
        ]
        res = select_prs.select(prs, MAIN, {})
        self.assertEqual([s["number"] for s in res["selected"]], [1, 10])
        reasons = self.reasons(res)
        self.assertEqual(sorted(reasons), [2, 3, 4, 5, 6, 7, 8, 9])
        self.assertIn("draft", reasons[2])
        self.assertIn("`hold`", reasons[5])
        self.assertIn("fork", reasons[9])
        self.assertFalse(any(d["comment"] for d in res["dropped"]))

    def test_order_is_ascending_whatever_the_input(self):
        res = select_prs.select([pr(30), pr(10), pr(20)], MAIN, {})
        self.assertEqual([s["number"] for s in res["selected"]], [10, 20, 30])

    def test_migration_clash_drops_later_pr_and_asks_for_comment(self):
        res = select_prs.select(
            [pr(11), pr(12), pr(13)], MAIN,
            {11: {"0004": ("0003",)}, 12: {"0004": ("0003",)}, 13: {}})
        self.assertEqual([s["number"] for s in res["selected"]], [11, 13])
        dropped = res["dropped"]
        self.assertEqual(dropped[0]["number"], 12)
        self.assertTrue(dropped[0]["comment"])

    def test_records_head_and_migrations(self):
        res = select_prs.select([pr(11)], MAIN, {11: {"0004": ("0003",)}})
        self.assertEqual(res["selected"][0]["head"], "sha11")
        self.assertEqual(res["selected"][0]["migrations"], ["0004"])

    def test_nothing_eligible_is_empty_not_error(self):
        res = select_prs.select([], MAIN, {})
        self.assertEqual(res, {"selected": [], "dropped": []})


if __name__ == "__main__":
    unittest.main()
