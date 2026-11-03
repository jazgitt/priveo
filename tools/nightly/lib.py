"""Shared pieces of the nightly pipeline: the run log (evidence trace), command runner, settings.

Every command goes through RunLog.run(), which records start time, end time, exit code and where
the full output was written. Nothing here puts a secret on a command line.
"""
from __future__ import annotations

import json
import os
import subprocess
import time
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path

REPO_SLUG = "jazgitt/priveo"
DEFAULT_HOME = Path(os.environ.get("NIGHTLY_HOME", str(Path.home() / "priveo-nightly")))
TEST_API_URL = os.environ.get("NIGHTLY_TEST_URL", "https://priveo-api-test.vercel.app")


class StageFailed(Exception):
    """A hard gate: the run stops here and later stages do not start."""


class Skipped(Exception):
    """A normal reason to do nothing tonight (quiet night, recent deploy). Not an error."""


def now_iso() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def load_env_file(path: Path) -> dict[str, str]:
    """KEY=VALUE lines. Read as data, never executed."""
    out: dict[str, str] = {}
    if path.is_file():
        for line in path.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                out[k.strip()] = v.strip().strip('"').strip("'")
    return out


def is_enabled(home: Path, environ: dict | None = None) -> bool:
    environ = os.environ if environ is None else environ
    value = environ.get("NIGHTLY_ENABLED")
    if value is None:
        value = load_env_file(home / "nightly.env").get("NIGHTLY_ENABLED", "false")
    return value.strip().lower() == "true"


def kill_reason(home: Path, environ: dict | None = None, ignore_enabled: bool = False) -> str | None:
    """Why the run must not go on, or None. A dry run ignores NIGHTLY_ENABLED but never the KILL file."""
    if (home / "KILL").exists():
        return "the KILL file exists"
    if not ignore_enabled and not is_enabled(home, environ):
        return "NIGHTLY_ENABLED is not true"
    return None


class CmdResult:
    def __init__(self, rc: int, log_path: Path, seconds: float):
        self.rc, self.log_path, self.seconds = rc, log_path, seconds

    @property
    def ok(self) -> bool:
        return self.rc == 0

    def text(self) -> str:
        return self.log_path.read_text(errors="replace") if self.log_path.exists() else ""


def unique_folder(root: Path, name: str) -> Path:
    path, n = root / name, 1
    while path.exists():
        n += 1
        path = root / f"{name}-{n}"
    return path


class RunLog:
    def __init__(self, logs_root: Path, dry_run: bool, when: datetime | None = None):
        when = when or datetime.now().astimezone()
        name = when.strftime("%Y-%m-%d")
        if dry_run:
            name += "-dryrun-" + when.strftime("%H%M")
        self.dir = unique_folder(logs_root, name)
        (self.dir / "commands").mkdir(parents=True)
        self.dry_run = dry_run
        self.n = 0
        self.manifest: dict = {
            "mode": "dry-run" if dry_run else "real", "started": now_iso(), "finished": None,
            "result": "running", "stages": [], "selected": [], "dropped": [], "merged_prs": [],
            "local_checks": [], "fix_attempts": [], "ci_checks": [], "merge_commit": None,
            "nightly_pr": None, "deploy": None, "rollback": None, "notes": [],
            "production": "untouched (manual)",
        }
        self.event("run_start", mode=self.manifest["mode"], folder=str(self.dir))

    # -- events ------------------------------------------------------------------
    def event(self, kind: str, **fields) -> None:
        with (self.dir / "events.jsonl").open("a") as f:
            f.write(json.dumps({"ts": now_iso(), "event": kind, **fields}) + "\n")

    def note(self, text: str) -> None:
        self.manifest["notes"].append(text)
        self.event("note", text=text)

    def save(self) -> None:
        (self.dir / "manifest.json").write_text(json.dumps(self.manifest, indent=2) + "\n")

    # -- commands ----------------------------------------------------------------
    def run(self, name: str, argv: list[str], cwd: str | Path | None = None, env: dict | None = None,
            timeout: int = 1800) -> CmdResult:
        self.n += 1
        safe = "".join(c if c.isalnum() or c in "-_" else "-" for c in name)[:50]
        log_path = self.dir / "commands" / f"{self.n:02d}-{safe}.log"
        start = time.time()
        started = now_iso()
        full_env = {**os.environ, **(env or {})}
        try:
            with log_path.open("w") as out:
                proc = subprocess.run(argv, cwd=cwd, env=full_env, stdout=out, stderr=subprocess.STDOUT,
                                      stdin=subprocess.DEVNULL, timeout=timeout)
            rc = proc.returncode
        except subprocess.TimeoutExpired:
            rc = 124
            with log_path.open("a") as out:
                out.write(f"\n[nightly] timed out after {timeout}s\n")
        except FileNotFoundError as e:
            rc = 127
            log_path.write_text(f"[nightly] {e}\n")
        seconds = round(time.time() - start, 1)
        self.event("command", name=name, argv=argv, cwd=str(cwd) if cwd else None, started=started,
                   ended=now_iso(), seconds=seconds, exit=rc, passed=rc == 0,
                   output=str(log_path.relative_to(self.dir)))
        return CmdResult(rc, log_path, seconds)

    # -- stages ------------------------------------------------------------------
    @contextmanager
    def stage(self, num: int, name: str):
        rec = {"num": num, "name": name, "started": now_iso(), "ended": None, "status": "running", "detail": ""}
        self.manifest["stages"].append(rec)
        self.event("stage_start", stage=num, name=name)
        self.save()
        t0 = time.time()
        try:
            yield rec
            if rec["status"] == "running":
                rec["status"] = "passed"
        except Skipped as e:
            rec["status"], rec["detail"] = "skipped", str(e)
            raise
        except StageFailed as e:
            rec["status"], rec["detail"] = "failed", str(e)
            raise
        except Exception as e:  # a bug in the pipeline is a failed stage too
            rec["status"], rec["detail"] = "error", f"{type(e).__name__}: {e}"
            raise StageFailed(rec["detail"]) from e
        finally:
            rec["ended"] = now_iso()
            rec["seconds"] = round(time.time() - t0, 1)
            self.event("stage_end", stage=num, name=name, status=rec["status"], detail=rec["detail"])
            self.save()


def gh_json(log: RunLog, name: str, argv: list[str], cwd=None):
    """Run a gh command, return parsed JSON (or None on failure)."""
    res = log.run(name, argv, cwd=cwd, timeout=120)
    if not res.ok:
        return None
    try:
        return json.loads(res.text())
    except json.JSONDecodeError:
        return None
