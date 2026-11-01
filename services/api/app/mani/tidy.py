"""The last pass over an answer before it is saved. The persona asks the model not to name its tools, and a
small model still does it now and then ("from the `subscriptions_summary` tool"). The portal already lists the
tools and files under every answer, so the name is taken out here, in code, where it cannot be forgotten."""
import re
from collections.abc import Iterable

PLAIN = "the live summary"
FILE = r"\b[\w-]+\.(?:py|dart|tsx?|json|md|sh|ya?ml)\b"
SENTENCE_END = re.compile(r"(?<=[.!?])\s+")


def drop_code_references(text: str) -> str:
    """Take out what names a code file, when the question was not about code. A brackets aside goes whole; a
    sentence or list line that names a file goes; a back-ticked single word loses its ticks. If nothing would
    be left, the text is kept as it was."""
    text = re.sub(rf"\s*\([^()]*{FILE}[^()]*\)", "", text)
    kept: list[str] = []
    for line in text.split("\n"):
        if re.search(FILE, line) and re.match(r"\s*(?:[-*]|\d+[.)])\s", line):
            continue
        sentences = SENTENCE_END.split(line)
        kept.append(" ".join(x for x in sentences if not re.search(FILE, x)))
    result = "\n".join(kept)
    result = re.sub(r"`([\w.]+)`", r"\1", result)
    result = re.sub(r"\n{3,}", "\n\n", result).strip()
    return result if result else text


def tidy_answer(text: str, tool_names: Iterable[str], *, about_code: bool = True, about_tools: bool = False) -> str:
    # The prompt labels what it sends "TOOL DATA", and a small model repeats the label.
    text = re.sub(r"\b(the\s+)?tool data\b", lambda m: ("T" if m.group(1)[0] == "T" else "t") + "he data"
                  if m.group(1) else "data", text, flags=re.I)
    if not about_code:
        text = drop_code_references(text)
    names = "|".join(re.escape(n) for n in sorted(set(tool_names), key=len, reverse=True))
    if not names or about_tools:  # asked which tools there are: the names are the answer
        return re.sub(r"[ \t]{2,}", " ", text).strip()
    name = rf"`?(?:{names})`?"
    # "(from the `x` tool)", "(via x)": the whole aside goes.
    text = re.sub(rf"\s*\((?:from|via|using|per|source:?)\s[^)]*?{name}[^)]*\)", "", text, flags=re.I)

    def plain(match: re.Match) -> str:
        start = match.start()
        before = text[:start].rstrip()
        sentence_start = start == 0 or before.endswith((".", "!", "?", ":", "\n"))
        return PLAIN.capitalize() if sentence_start else PLAIN

    # "the x tool", "x tool" and a bare "x" all become one plain phrase.
    text = re.sub(rf"(?:\bthe\s+)?{name}(?:\s+tool)?", plain, text, flags=re.I)
    return re.sub(r"[ \t]{2,}", " ", text).strip()
