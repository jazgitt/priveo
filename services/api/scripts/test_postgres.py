"""Run pytest on a disposable local PostgreSQL cluster, never the app database.

Set POSTGRES_BIN to the installed PostgreSQL bin directory. On Windows the
default is C:/Program Files/PostgreSQL/17/bin. Requires initdb and pg_ctl.
"""
import os
import socket
import subprocess
import sys
import tempfile
from pathlib import Path

API = Path(__file__).resolve().parents[1]
ROOT = API.parents[1]


def main() -> int:
    bin_dir = Path(os.environ.get("POSTGRES_BIN", "C:/Program Files/PostgreSQL/17/bin"))
    suffix = ".exe" if os.name == "nt" else ""
    with socket.socket() as listener:
        listener.bind(("127.0.0.1", 0))
        port = listener.getsockname()[1]
    with tempfile.TemporaryDirectory(prefix="postgres-check-", dir=ROOT) as temporary:
        work = Path(temporary).resolve()
        # Verify the target before the context recursively removes test files.
        if ROOT.resolve() not in work.parents:
            raise RuntimeError("Test cluster must stay inside the workspace")
        data = work / "data"

        def run(program: str, *args: str) -> None:
            # On Windows a server started by pg_ctl can inherit pipe handles,
            # preventing communicate() from seeing EOF. Use a file instead.
            output = work / f"{program}.log"
            with output.open("w", encoding="utf-8") as log:
                result = subprocess.run(
                    [str(bin_dir / f"{program}{suffix}"), *args],
                    stdout=log, stderr=log, check=False,
                )
            if result.returncode:
                raise RuntimeError(f"{program} failed: {output.read_text(encoding='utf-8')}")

        run("initdb", "-D", str(data), "-A", "trust", "-U", "priveo_test",
            "--encoding=UTF8", "--locale=C")
        started = False
        try:
            run("pg_ctl", "-D", str(data), "-l", str(work / "server.log"),
                "-o", f"-h 127.0.0.1 -p {port}", "-w", "start")
            started = True
            run("createdb", "-h", "127.0.0.1", "-p", str(port), "-U", "priveo_test",
                "priveo_test")
            env = {**os.environ,
                   "TEST_DATABASE_URL": f"postgresql://priveo_test@127.0.0.1:{port}/priveo_test"}
            print("Testing on a disposable PostgreSQL cluster", flush=True)
            return subprocess.call(
                [sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider", *sys.argv[1:]],
                cwd=API, env=env,
            )
        finally:
            if started:
                run("pg_ctl", "-D", str(data), "-m", "fast", "-w", "stop")


if __name__ == "__main__":
    raise SystemExit(main())
