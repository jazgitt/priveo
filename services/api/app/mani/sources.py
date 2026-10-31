"""Which files Mani indexes. This is Appendix B of docs/agent/agent-architecure.md, written as
data so the owner can review it. Change the tables, not the code, when the list changes.

Discovery reads the working tree only. In a git repository it asks `git ls-files`, so
ignored files (.env, node_modules, build output) never appear; elsewhere it walks the folder
and skips the same names."""
import fnmatch
import subprocess
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Literal

# ---- The rules (review these) ---------------------------------------------------------------

# A file is a candidate when its path equals one of these or starts with one that ends in "/".
INCLUDE = (
    "CLAUDE.md", "README.md", "wiki/",
    "docs/reqs/", "docs/agent/",
    "docs/architecture.md", "docs/system-component-diagram.md", "docs/tech-stack.md",
    "docs/build-plan.md", "docs/build-and-release.md", "docs/security-backlog.md",
    "docs/hosting-assessment/", "docs/design/", "docs/testing/",
    "docs/feature-status.json", "docs/overnight-build-report.md",
    "services/api/app/", "services/api/migrations/", "services/api/scripts/",
    "services/api/pyproject.toml",
    "apps/web/src/", "apps/mobile/lib/",
    "packages/api-contract/openapi.json",
    "docs/brand/tokens.json", "tools/",
)

# Only text that helps an answer. Images, fonts and the like are never indexed.
EXTENSIONS = {
    ".md": "doc", ".txt": "doc",
    ".py": "code", ".dart": "code", ".ts": "code", ".tsx": "code", ".js": "code", ".mjs": "code",
    ".sh": "code", ".ps1": "code",
    ".toml": "config", ".yaml": "config", ".yml": "config",
    ".json": "data", ".arb": "data",
}

# Excluded by prefix ("/" at the end) or exact path. Each line says why.
EXCLUDE_PATHS = (
    "docs/prototype/",                      # large read-only prototype, owner decision 30-Oct
    "docs/coverage/",                       # generated audit data
    "docs/design/Priveo Showroom Splash.html",
    ".claude/",                             # local tooling and worktrees
    ".github/workflows/",                   # hold admin login literals
    "apps/web/e2e/", "apps/web/src/test/",  # browser tests and test helpers
    "apps/mobile/test/", "apps/mobile/integration_test/",
    "apps/mobile/ios/",                     # Pods and Xcode project files
    "services/api/tests/",                  # synthetic test data (D20)
    "services/api/app/identity/seed.py", "services/api/app/directory/seed.py",
    "services/api/scripts/test_data.py", "services/api/scripts/seed_shared_test_data.py",
    "services/api/scripts/smoke_test.py",
    "tools/test-data/",
    "docs/agent/mani-question-set-review.md",  # the evaluation answer key, owner decision 31-Oct
)

# Sections left out of an indexed file: path -> heading prefixes. A section runs from its heading
# to the next heading of the same or a higher level.
EXCLUDE_SECTIONS = {
    "docs/agent/agent-architecure.md": ("## Appendix A: question set",),  # the 50 questions
}

# Excluded when any folder in the path has one of these names.
EXCLUDE_DIRS = {
    "node_modules", "__pycache__", "build", "dist", ".dart_tool", ".venv", "venv", ".git",
    "Pods", ".gradle", ".next",
}

# Excluded by file name (fnmatch, case-insensitive).
EXCLUDE_NAMES = (
    ".env", ".env.*", "*.env", "*.pem", "*.key", "*.p12", "*.keystore", "*secret*", "*credentials*",
    "*.pyc", "*.lock", "package-lock.json", "pnpm-lock.yaml", "yarn.lock", "poetry.lock",
    "api.g.dart", "tokens.g.dart", "*.g.dart", "app_localizations*.dart",
    "*.test.ts", "*.test.tsx", "*.spec.ts", "*.spec.tsx", "*.test.js", "*.test.mjs",
    "*.xcodeproj", "*.xcworkspace", "*.pbxproj",
)
# Test helpers in the portal source, named test<Something> (testSite.tsx).
EXCLUDE_WEB_TEST_HELPERS = "apps/web/src/*/test[A-Z]*"

# The one l10n file that is indexed; the rest of the .arb fragments are merged into it.
ARB_INDEXED = "apps/mobile/lib/l10n/app_en.arb"
ARB_FRAGMENTS = "apps/mobile/lib/l10n/"

Kind = Literal["doc", "code", "config", "data"]


@dataclass(frozen=True)
class SourceFile:
    path: str  # relative to the repository root, with "/" separators
    kind: Kind
    title: str


# ---- The code -------------------------------------------------------------------------------


def _under(path: str, entries: tuple[str, ...]) -> bool:
    return any(path == e or (e.endswith("/") and path.startswith(e)) for e in entries)


def is_included(path: str) -> bool:
    """True when this repository-relative path (with "/") is on the index list."""
    if not _under(path, INCLUDE) or _under(path, EXCLUDE_PATHS):
        return False
    pure = PurePosixPath(path)
    if any(part in EXCLUDE_DIRS for part in pure.parts[:-1]):
        return False
    name = pure.name.lower()
    if any(fnmatch.fnmatchcase(name, pattern.lower()) for pattern in EXCLUDE_NAMES):
        return False
    if fnmatch.fnmatchcase(path, EXCLUDE_WEB_TEST_HELPERS):
        return False
    if path.startswith(ARB_FRAGMENTS) and path.endswith(".arb") and path != ARB_INDEXED:
        return False
    return pure.suffix.lower() in EXTENSIONS


def _title(path: str, root: Path) -> str:
    """The first Markdown heading for a document, else the file name."""
    pure = PurePosixPath(path)
    if pure.suffix.lower() == ".md":
        try:
            with (root / path).open(encoding="utf-8", errors="replace") as handle:
                for _ in range(40):
                    line = handle.readline()
                    if not line:
                        break
                    if line.startswith("#"):
                        return line.lstrip("#").strip()[:300] or pure.name
        except OSError:
            pass
    return pure.name


def _listed_files(root: Path) -> list[str]:
    try:
        out = subprocess.run(
            ["git", "-C", str(root), "ls-files", "-z", "--cached", "--others", "--exclude-standard"],
            capture_output=True, check=True, timeout=60)
    except (OSError, subprocess.SubprocessError):
        out = None
    # Only trust git when the root is itself the top of a repository.
    if out is not None and (root / ".git").exists():
        names = [n for n in out.stdout.decode("utf-8", errors="replace").split("\0") if n]
        return [n for n in names if (root / n).is_file()]
    found = []
    for item in root.rglob("*"):
        rel = item.relative_to(root)
        if any(part in EXCLUDE_DIRS for part in rel.parts[:-1]):
            continue
        if item.is_file():
            found.append(rel.as_posix())
    return found


def discover(root: Path) -> list[SourceFile]:
    """The files to index, sorted by path."""
    root = Path(root)
    paths = sorted({p for p in _listed_files(root) if is_included(p)})
    return [SourceFile(p, EXTENSIONS[PurePosixPath(p).suffix.lower()], _title(p, root)) for p in paths]
