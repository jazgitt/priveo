import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import migration_safety as ms  # noqa: E402

SAFE = '''revision = "1"
down_revision = "0"

def upgrade():
    op.add_column("t", sa.Column("x", sa.String(), nullable=True))
    op.create_table("n", sa.Column("id", sa.Integer()))

def downgrade():
    op.drop_column("t", "x")
'''


class Safety(unittest.TestCase):
    def test_add_nullable_and_create_table_is_safe_even_if_downgrade_drops(self):
        r = ms.check_migration(SAFE)
        self.assertEqual(r, {"block": [], "warn": []})

    def test_drop_column_blocks(self):
        r = ms.check_migration("def upgrade():\n    op.drop_column('t', 'x')\n\ndef downgrade():\n    pass\n")
        self.assertEqual(len(r["block"]), 1)

    def test_drop_table_and_rename_block(self):
        r = ms.check_migration("def upgrade():\n    op.drop_table('t')\n    op.rename_table('a','b')\n")
        self.assertEqual(len(r["block"]), 2)

    def test_column_rename_blocks(self):
        r = ms.check_migration("def upgrade():\n    op.alter_column('t', 'a', new_column_name='b')\n")
        self.assertTrue(r["block"])

    def test_not_null_without_default_warns(self):
        r = ms.check_migration("def upgrade():\n    op.add_column('t', sa.Column('x', sa.Integer(), nullable=False))\n")
        self.assertTrue(r["warn"])
        self.assertFalse(r["block"])

    def test_not_null_with_default_is_fine(self):
        r = ms.check_migration(
            "def upgrade():\n    op.add_column('t', sa.Column('x', sa.Integer(), nullable=False, server_default='0'))\n")
        self.assertEqual(r["warn"], [])


if __name__ == "__main__":
    unittest.main()
