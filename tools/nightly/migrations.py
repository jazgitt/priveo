"""Alembic migration chain helpers for the nightly pipeline (no database needed).

A migration file declares `revision = "0046"` and `down_revision = "0045"` (or None, or a
tuple for a merge migration). We read those two lines as text, so no import of the app is needed.
"""
from __future__ import annotations

import re

_REV = re.compile(r"""^revision\s*(?::[^=]+)?=\s*["']([^"']+)["']""", re.M)
_DOWN = re.compile(r"^down_revision\s*(?::[^=]+)?=\s*(.+)$", re.M)


def parse_migration(text: str) -> tuple[str, tuple[str, ...]] | None:
    """Return (revision, down_revisions) or None when the text is not a migration."""
    rev = _REV.search(text)
    down = _DOWN.search(text)
    if not rev or not down:
        return None
    return rev.group(1), tuple(re.findall(r"""["']([^"']+)["']""", down.group(1)))


def chain_from_texts(texts: list[str]) -> dict[str, tuple[str, ...]]:
    """Map revision -> down revisions for a list of migration file contents."""
    chain: dict[str, tuple[str, ...]] = {}
    for text in texts:
        parsed = parse_migration(text)
        if parsed:
            chain[parsed[0]] = parsed[1]
    return chain


def heads(chain: dict[str, tuple[str, ...]]) -> list[str]:
    """Revisions that no other revision follows."""
    parents = {d for downs in chain.values() for d in downs}
    return sorted(r for r in chain if r not in parents)


def check_chain(chain: dict[str, tuple[str, ...]]) -> list[str]:
    """Problems with a chain: more than one head, or a down revision that does not exist."""
    problems = []
    for rev, downs in sorted(chain.items()):
        for d in downs:
            if d not in chain:
                problems.append(f"{rev} follows {d}, which does not exist")
    hs = heads(chain)
    if len(hs) != 1:
        problems.append("expected one head, found " + (", ".join(hs) if hs else "none"))
    return problems


def clashes(
    main_chain: dict[str, tuple[str, ...]],
    pr_migrations: dict[int, dict[str, tuple[str, ...]]],
) -> dict[int, str]:
    """Decide which pull requests' new migrations clash.

    pr_migrations: PR number -> {revision: down revisions} for the migrations that PR adds.
    PRs are taken in ascending number. A PR is rejected, as a whole, with a reason when:
      - one of its revisions already exists (on main or in an earlier accepted PR);
      - one of its migrations follows a revision that does not exist yet (stale base);
      - one of its migrations follows a revision that already has a child (a fork: two heads).
    Returns {pr number: reason} for the rejected PRs. Accepted PRs add to the chain.
    """
    state = dict(main_chain)
    owner = {rev: "main" for rev in main_chain}
    children: dict[str, str] = {}
    for rev, downs in main_chain.items():
        for d in downs:
            children[d] = rev
    rejected: dict[int, str] = {}
    for number in sorted(pr_migrations):
        migs = pr_migrations[number]
        if not migs:
            continue
        reason = _reason(migs, state, owner, children)
        if reason:
            rejected[number] = reason
            continue
        for rev, downs in migs.items():
            state[rev] = downs
            owner[rev] = f"#{number}"
            for d in downs:
                children[d] = rev
    return rejected


def _reason(migs, state, owner, children) -> str | None:
    own = set(migs)
    for rev in sorted(migs):
        if rev in state:
            return f"migration {rev} already exists in {owner[rev]}; renumber it after the latest one"
    for rev in sorted(migs):
        for d in migs[rev]:
            if d in own:
                continue
            if d not in state:
                return f"migration {rev} follows {d}, which is not on main or in an earlier pull request"
            if d in children:
                return (f"migration {rev} follows {d}, which {children[d]} already follows "
                        f"({owner.get(children[d], '?')}); that would make two heads")
    return None
