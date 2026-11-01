"""Which files the indexer finds: exactly the Appendix B list, never a secret, a test or a seed."""
import subprocess
from pathlib import Path

from app.mani.sources import discover, is_included

INCLUDED = {
    "CLAUDE.md": "doc", "README.md": "doc", "wiki/Priveo.md": "doc",
    "docs/reqs/customer-app-functional-requirements.md": "doc",
    "docs/agent/agent-architecure.md": "doc", "docs/architecture.md": "doc", "docs/tech-stack.md": "doc",
    "docs/design/admin-portal-ui-review.md": "doc", "docs/testing/test-data-plan.md": "doc",
    "docs/feature-status.json": "data",
    "docs/brand/tokens.json": "data",
    "services/api/app/billing/service.py": "code", "services/api/migrations/versions/0001_x.py": "code",
    "services/api/scripts/export_openapi.py": "code", "services/api/scripts/test_postgres.py": "code",
    "services/api/pyproject.toml": "config",
    "apps/web/src/App.tsx": "code", "apps/web/src/api/client.ts": "code",
    "apps/mobile/lib/main.dart": "code", "apps/mobile/lib/l10n/app_en.arb": "data",
    "tools/dev/check-local.sh": "code", "tools/coverage/report.py": "code",
}
EXCLUDED = [
    ".env", "services/api/.env", "services/api/.env.example", "apps/web/.env.local",
    "services/api/app/config.env", "services/api/app/secrets.py", "docs/reqs/credentials.md",
    "docs/hosting-assessment/README.md", "docs/build-plan.md", "packages/api-contract/openapi.json",
    "docs/prototype/prototype.html", "docs/prototype/notes.md",
    "docs/coverage/unit-test-coverage.md", "docs/design/Priveo Showroom Splash.html",
    "docs/brand/logo.png", "docs/other.md",
    "apps/mobile/lib/core/api/api.g.dart", "apps/mobile/lib/core/ui/tokens.g.dart",
    "apps/mobile/lib/l10n/app_localizations.dart", "apps/mobile/lib/l10n/app_localizations_en.dart",
    "apps/mobile/lib/l10n/fragments/auth.arb",
    "apps/web/package-lock.json", "tools/deploy/package-lock.json", "services/api/poetry.lock", "Gemfile.lock",
    "apps/web/node_modules/x/index.js", "tools/deploy/node_modules/y/index.js",
    "services/api/app/__pycache__/m.cpython-312.pyc", "services/api/app/__pycache__/m.py",
    "apps/web/dist/app.js", "apps/mobile/build/out.dart",
    ".claude/settings.json", ".claude/worktrees/w/README.md",
    "apps/mobile/ios/Podfile.lock", "apps/mobile/ios/Pods/x/README.md",
    "apps/mobile/ios/Runner.xcodeproj/project.pbxproj",
    ".github/workflows/ci.yml",
    "apps/web/e2e/auth.spec.ts", "apps/mobile/test/widget_test.dart", "apps/mobile/integration_test/a.dart",
    "services/api/tests/test_x.py", "services/api/tests/mani/fakes.py",
    "apps/web/src/App.test.tsx", "apps/web/src/api/client.test.ts", "apps/web/src/test/setup.ts",
    "apps/web/src/site/testSite.tsx",
    "services/api/app/identity/seed.py", "services/api/app/directory/seed.py",
    "services/api/scripts/test_data.py", "services/api/scripts/seed_shared_test_data.py",
    "services/api/scripts/smoke_test.py", "tools/test-data/api_smoke.py", "tools/test-data/scenarios.json",
    "services/api/app/logo.png", "services/api/app/data.bin",
]


def write(root: Path, rel: str) -> None:
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("# Title of " + rel + "\nbody\n" if rel.endswith(".md") else "x = 1\n")


def test_the_rules_pick_exactly_the_appendix_b_files():
    assert all(is_included(p) for p in INCLUDED)
    assert not any(is_included(p) for p in EXCLUDED)


def test_discover_in_a_git_repository(tmp_path):
    for rel in [*INCLUDED, *EXCLUDED]:
        write(tmp_path, rel)
    (tmp_path / ".gitignore").write_text("services/api/app/billing/ignored.py\n")
    write(tmp_path, "services/api/app/billing/ignored.py")
    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)
    subprocess.run(["git", "-C", str(tmp_path), "add", "--", "."], check=True)

    found = discover(tmp_path)
    assert {f.path: f.kind for f in found} == INCLUDED
    assert [f.path for f in found] == sorted(INCLUDED)  # a stable order
    assert next(f for f in found if f.path == "CLAUDE.md").title == "Title of CLAUDE.md"
    assert next(f for f in found if f.path == "wiki/Priveo.md").title == "Title of wiki/Priveo.md"
    assert next(f for f in found if f.path == "apps/web/src/App.tsx").title == "App.tsx"


def test_untracked_files_are_found_but_ignored_ones_are_not(tmp_path):
    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)
    (tmp_path / ".gitignore").write_text("services/api/app/billing/ignored.py\n")
    write(tmp_path, "services/api/app/billing/ignored.py")
    write(tmp_path, "services/api/app/billing/new.py")
    assert [f.path for f in discover(tmp_path)] == ["services/api/app/billing/new.py"]


def test_discover_without_git_walks_the_folder(tmp_path):
    for rel in [*INCLUDED, *EXCLUDED]:
        write(tmp_path, rel)
    assert {f.path for f in discover(tmp_path)} == set(INCLUDED)
