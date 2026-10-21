"""Validate the repository wiki without third-party dependencies or network access."""

from __future__ import annotations

import re
import sys
from collections import Counter
from pathlib import Path
from urllib.parse import unquote, urlsplit


WIKI = Path(__file__).resolve().parent
LINK = re.compile(r"(?<!!)\[[^\]\n]+\]\((<[^>]+>|[^\s)]+)\)")
FOOTNOTE = re.compile(r"\[\^([^\]]+)\]")
DEFINITION = re.compile(r"^\[\^([^\]]+)\]:", re.MULTILINE)


def anchors(source: str) -> set[str]:
    """GitHub-style heading anchors for the simple headings used by this wiki."""
    result: set[str] = set()
    seen: Counter[str] = Counter()
    for title in re.findall(r"^#{1,6}\s+(.+?)\s*#*\s*$", source, re.MULTILINE):
        slug = re.sub(r"[^\w\- ]", "", title.lower()).replace(" ", "-")
        count = seen[slug]
        seen[slug] += 1
        result.add(f"{slug}-{count}" if count else slug)
    return result


def main() -> int:
    files = sorted(WIKI.glob("*.md"))
    errors: list[str] = []
    graph: dict[Path, set[Path]] = {}
    counts: list[tuple[int, str]] = []
    home = WIKI / "README.md"
    for path in files:
        source = path.read_text(encoding="utf-8")
        words = len(source.split())
        counts.append((words, path.name))
        graph[path] = set()
        if words > 2000:
            errors.append(f"{path.name}: {words} words exceeds 2,000")
        if len(re.findall(r"^# ", source, re.MULTILINE)) != 1:
            errors.append(f"{path.name}: expected one level-one title")
        if "## References\n" not in source:
            errors.append(f"{path.name}: missing References section")
        if path != home and "## See also\n" not in source:
            errors.append(f"{path.name}: missing See also section")
        if not re.search(r"Evidence reviewed: \d{1,2} [A-Za-z]+ \d{4}\.", source):
            errors.append(f"{path.name}: missing review-date footer")
        previous = 1
        for heading in re.finditer(r"^(#{1,6}) ", source, re.MULTILINE):
            level = len(heading.group(1))
            if level > previous + 1:
                errors.append(f"{path.name}: skipped heading level")
            previous = level
        definitions = DEFINITION.findall(source)
        body = DEFINITION.sub("", source)
        used = set(FOOTNOTE.findall(body))
        defined = set(definitions)
        if not used:
            errors.append(f"{path.name}: no inline references")
        for label in sorted(used - defined):
            errors.append(f"{path.name}: undefined footnote {label}")
        for label in sorted(defined - used):
            errors.append(f"{path.name}: unused footnote {label}")
        if len(definitions) != len(defined):
            errors.append(f"{path.name}: duplicate footnote definitions")
        for match in LINK.finditer(source):
            target = match.group(1).strip("<>")
            parsed = urlsplit(target)
            if parsed.scheme or parsed.netloc:
                continue
            destination = (path.parent / unquote(parsed.path)).resolve() if parsed.path else path
            if not destination.exists():
                errors.append(f"{path.name}: missing target {target}")
                continue
            if destination.parent == WIKI and destination.suffix == ".md":
                graph[path].add(destination)
            if parsed.fragment and destination.suffix == ".md":
                if unquote(parsed.fragment) not in anchors(destination.read_text(encoding="utf-8")):
                    errors.append(f"{path.name}: missing anchor {target}")
        if path != home and home not in graph[path]:
            errors.append(f"{path.name}: no main-page link")
    if home not in graph:
        errors.append("Missing README.md main page")
    else:
        for path in files:
            if path != home and path not in graph[home]:
                errors.append(f"README.md: article not indexed: {path.name}")
        visited: set[Path] = set()
        pending = [home]
        while pending:
            current = pending.pop()
            if current not in visited:
                visited.add(current)
                pending.extend(graph.get(current, set()) - visited)
        for path in set(files) - visited:
            errors.append(f"Unreachable article: {path.name}")
    for words, name in sorted(counts, reverse=True):
        print(f"{words:4} words  {name}")
    if errors:
        print("\nVALIDATION FAILED")
        for error in errors:
            print(f"- {error}")
        return 1
    print(f"\nPASS: {len(files)} articles; all at most 2,000 words; links, references and index valid.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
