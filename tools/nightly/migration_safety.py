"""Step 5: migration safety checks (no database needed).

A migration runs before the new code goes live, so the previous API version keeps serving on the
new schema for a while (and again after a rollback). A migration is forward-safe when the previous
code still works on it. We check what can be seen from the text of upgrade():

  BLOCK (the pull request is dropped): drop_table, drop_column, drop_constraint, rename_table and a
        column rename. The previous version would break.
  WARN  (reported only): add_column NOT NULL without a server default, any alter_column.

The chain rule (exactly one head after merging) is checked by build_combined.chain_problems.
"""
from __future__ import annotations

import re

BLOCK = {
    "op.drop_table": "drops a table",
    "op.drop_column": "drops a column",
    "op.drop_constraint": "drops a constraint",
    "op.rename_table": "renames a table",
    "new_column_name": "renames a column",
}
_ADD_COLUMN = re.compile(r"add_column\((?P<body>.*?)\)\s*$", re.S | re.M)


def _upgrade_body(text: str) -> str:
    m = re.search(r"def upgrade\(\)[^:]*:(.*?)(?=^def downgrade|\Z)", text, re.S | re.M)
    return m.group(1) if m else text


def check_migration(text: str) -> dict:
    """{'block': [...], 'warn': [...]} for one migration file. Only upgrade() is read."""
    body = _upgrade_body(text)
    block, warn = [], []
    for key, why in BLOCK.items():
        if key in body:
            block.append(f"{why} ({key}); the previous API version would break on the new schema")
    for m in re.finditer(r"add_column\(", body):
        chunk = body[m.start(): m.start() + 400].split("\n\n")[0]
        if "nullable=False" in chunk and "server_default" not in chunk:
            warn.append("adds a NOT NULL column without a server default; inserts by the previous version fail")
    if "alter_column" in body:
        warn.append("alters a column; check the previous version still works")
    return {"block": block, "warn": warn}
