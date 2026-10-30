"""The scrubber: removes secrets and PII before text is indexed and from every tool result
(decisions D8, D14, D20), so nothing sensitive reaches a model.

It redacts secrets (passwords, tokens, database credentials, the dev sign-in code), customer
and admin PII (emails, mobiles, address fields, the admin login ID). It keeps customer names,
society names, crew names and crew mobiles, requirement IDs, ordinary numbers and the helpline
numbers. A replacement looks like `[redacted:email]`.

Every pattern is written to run in linear time: runs are bounded or anchored by a lookbehind,
so a 1 MB input scrubs in well under a second. Scrubbing twice gives the same text as once,
because no pattern matches a replacement marker."""
import re
from collections import Counter
from typing import Any

from app.mani.contracts import ScrubResult

DEFAULT_ADMIN_LOGIN = "priveopapa"
# Not PII (owner decision D20). Compared on the last 10 digits.
HELPLINE_NUMBERS = frozenset({"0000000000", "1234567890"})
_MAX_DEPTH = 40
_MARK = "[redacted:{}]"

# ---- Patterns -----------------------------------------------------------------------------

_PEM = re.compile(r"-----BEGIN [A-Z ]{0,30}PRIVATE KEY-----[\s\S]*?(?:-----END [A-Z ]{0,30}PRIVATE KEY-----|\Z)")
_TOKENS = re.compile(
    r"(?<![A-Za-z0-9_-])(?:"
    r"vercel_blob_rw_[A-Za-z0-9_]{8,}"
    r"|re_(?=[A-Za-z0-9_]*\d)[A-Za-z0-9_]{16,}"
    r"|sk-or-[A-Za-z0-9_-]{8,}"
    r"|AKIA[0-9A-Z]{16}"
    r"|gh[pousr]_[A-Za-z0-9]{20,}"
    r"|eyJ[A-Za-z0-9_-]{5,}\.[A-Za-z0-9_-]{5,}(?:\.[A-Za-z0-9_-]*)?"
    r")")
_BEARER = re.compile(r"\b(Bearer[ \t]+)[A-Za-z0-9._~+/=-]{16,}", re.I)
# Only what follows `://` and precedes `@`, so the scheme and host stay.
_DB_CREDS = re.compile(r"(?<=://)(?!\[redacted:)[^\s/@'\"<>]{1,200}(?=@)")

_SECRET_KW = (r"(?:password|passwd|pwd|(?<![a-z])pw(?![a-z])|secret|token(?!s)|api[_-]?key|private[_-]?key"
              r"|access[_-]?key|credentials?|email[_-]?code)")
_QUOTED = r"\"(?:[^\"\\\n]|\\.){0,2000}\"|'(?:[^'\\\n]|\\.){0,2000}'"
_SECRET_KV = re.compile(
    _SECRET_KW + r"[\w-]{0,40}(?P<q>[\"']?)(?P<sep>[ \t]{0,20}[:=][ \t]{0,20})"
    r"(?P<val>" + _QUOTED + r"|[^\s,;&\"'<>)}\]]+)", re.I)
_NOT_SECRET = frozenset({"", "none", "null", "true", "false", "str", "string", "required", "optional"})
# A crew password is the name plus four digits and a dollar sign (`Raj1111$`).
_CREW_PASSWORD = re.compile(r"(?<![A-Za-z0-9])[A-Z][a-z]{1,15}\d{4}\$")

_EMAIL = re.compile(r"(?<![A-Za-z0-9._%+-])[A-Za-z0-9._%+-]+@[A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)+")

_ADDR_KV = re.compile(
    r"(?<![A-Za-z])(?:address(?:[_ ]?line[_ ]?\d)?|flat(?:[_ ]?(?:no|number))?|tower|parking[_ ]?basement)"
    r"(?P<q>[\"']?)(?P<sep>[ \t]{0,20}[:=][ \t]{0,20})"
    r"(?P<val>" + _QUOTED + r"|(?!(?:null|none|true|false)\b)[^\n\"'{}\[\]]+)", re.I)
_NOT_ADDRESS = frozenset({"", "none", "null", "true", "false"})

_MOBILE = re.compile(
    r"(?<![\w+])(?:(?:\+91|91|0)[ \t-]?)?(?:[6-9]\d{4}[ \t-]?\d{5}|[6-9]\d{2}[ \t-]\d{3}[ \t-]\d{4})(?![\d]|\.\d)")
# The words before a number that say it is an id, an order or a time, not a mobile.
_ID_CONTEXT = re.compile(
    r"(?<![A-Za-z])(?:order|invoice|txn|transaction|utr|receipt|ticket|timestamp|epoch|ref|reference|id)"
    r"\w{0,10}[\"']?[ \t]{0,3}[:=#]?[ \t]{0,3}[\"']?$", re.I)

# ---- Key names for scrub_data -------------------------------------------------------------

_SECRET_KEY = re.compile(_SECRET_KW, re.I)
_ADDRESS_KEY = re.compile(r"(?:^|_)(?:address|flat|tower|parking_?basement)", re.I)
_PHONE_KEY = re.compile(r"mobile|phone|whatsapp|contact_?(?:no|number)", re.I)
_ID_KEY = re.compile(r"(?:^|_)(?:id|order|invoice|txn|utr|ref|timestamp|ts|amount|total)", re.I)
_ADMIN_KEY = re.compile(r"^(?:login_id|admin_login(?:_id)?)$", re.I)


def _last10(text: str) -> str:
    return re.sub(r"\D", "", text)[-10:]


class PatternScrubber:
    def __init__(self, extra_literals: tuple[str, ...] | list[str] = ()) -> None:
        try:
            from app.mani.config import get_mani_settings
            admin = get_mani_settings().founder_login_id
        except Exception:  # settings must never stop the scrubber from working
            admin = DEFAULT_ADMIN_LOGIN
        literals = sorted({s for s in (admin, *extra_literals) if s}, key=len, reverse=True)
        self.literals = tuple(literals)
        # An existing marker is matched first and left alone, so a literal such as "login"
        # is not found inside `[redacted:admin-login]`.
        self._literal_re = re.compile(
            r"\[redacted:[\w-]+\]|(?<!\w)(?:" + "|".join(re.escape(s) for s in literals) + r")(?!\w)", re.I)

    # ---- Text ----------------------------------------------------------------------------

    def scrub(self, text: str, *, source_path: str | None = None) -> ScrubResult:
        try:
            return self._scrub(text if isinstance(text, str) else str(text), crew=False, id_value=False)
        except Exception:  # fail closed: never hand back text that was not scrubbed
            return ScrubResult(_MARK.format("unscrubbable"), {"unscrubbable": 1})

    def _scrub(self, text: str, *, crew: bool, id_value: bool) -> ScrubResult:
        counts: Counter[str] = Counter()

        def fixed(kind: str):
            def repl(_m: re.Match) -> str:
                counts[kind] += 1
                return _MARK.format(kind)
            return repl

        text = _PEM.sub(fixed("private-key"), text)
        text = _TOKENS.sub(fixed("token"), text)

        def bearer(m: re.Match) -> str:
            counts["token"] += 1
            return m.group(1) + _MARK.format("token")
        text = _BEARER.sub(bearer, text)
        text = _DB_CREDS.sub(fixed("db-credentials"), text)

        def keyed(kind: str, skip: frozenset[str]):
            def repl(m: re.Match) -> str:
                val = m.group("val")
                inner = val.strip("\"'").strip().lower()
                if "[redacted:" in val or inner in skip:
                    return m.group(0)
                counts[kind] += 1
                quote = val[0] if val[0] in "\"'" else ""
                head = m.group(0)[: m.start("val") - m.start()]
                tail = "" if quote else val[len(val.rstrip()):]
                return f"{head}{quote}{_MARK.format(kind)}{quote}{tail}"
            return repl
        text = _SECRET_KV.sub(keyed("secret", _NOT_SECRET), text)
        text = _CREW_PASSWORD.sub(fixed("secret"), text)
        text = _EMAIL.sub(fixed("email"), text)

        def literal(m: re.Match) -> str:
            if m.group(0).startswith("["):
                return m.group(0)
            counts["admin-login"] += 1
            return _MARK.format("admin-login")
        text = self._literal_re.sub(literal, text)
        text = _ADDR_KV.sub(keyed("address", _NOT_ADDRESS), text)

        if not id_value:
            text = self._mobiles(text, crew, counts)
        return ScrubResult(text, dict(counts))

    @staticmethod
    def _mobiles(text: str, crew: bool, counts: Counter[str]) -> str:
        """Mobiles are redacted line by line: a line about crew keeps its numbers."""

        def repl(m: re.Match) -> str:
            if _last10(m.group(0)) in HELPLINE_NUMBERS:
                return m.group(0)
            line = m.string
            if _ID_CONTEXT.search(line[max(0, m.start() - 40): m.start()]):
                return m.group(0)
            counts["mobile"] += 1
            return _MARK.format("mobile")

        out = []
        for line in text.split("\n"):
            if crew or "crew" in line.lower() or not any(c.isdigit() for c in line):
                out.append(line)
            else:
                out.append(_MOBILE.sub(repl, line))
        return "\n".join(out)

    # ---- Structures ----------------------------------------------------------------------

    def scrub_data(self, value: Any) -> Any:
        try:
            return self._walk(value, crew=False, admin=False, id_value=False, depth=0)
        except Exception:
            return _MARK.format("unscrubbable")

    def _walk(self, value: Any, *, crew: bool, admin: bool, id_value: bool, depth: int) -> Any:
        if depth > _MAX_DEPTH:
            return _MARK.format("too-deep")
        if isinstance(value, str):
            return self._scrub(value, crew=crew, id_value=id_value).text
        if isinstance(value, dict):
            role = str(value.get("role", "")).lower()
            crew_here = crew or role == "crew"
            admin_here = admin or role == "admin"
            return {k: self._walk_item(str(k), v, crew_here, admin_here, depth) for k, v in value.items()}
        if isinstance(value, (list, tuple)):
            items = [self._walk(v, crew=crew, admin=admin, id_value=id_value, depth=depth + 1) for v in value]
            return tuple(items) if isinstance(value, tuple) else items
        return value

    def _walk_item(self, key: str, value: Any, crew: bool, admin: bool, depth: int) -> Any:
        if value is None or isinstance(value, bool):
            return value
        kind = None
        if _SECRET_KEY.search(key):
            kind = "secret"
        elif "email" in key.lower():
            kind = "email"
        elif _ADDRESS_KEY.search(key):
            kind = "address"
        elif _ADMIN_KEY.match(key):
            kind = "admin-login"
        elif _PHONE_KEY.search(key):
            if (crew and not admin) or "crew" in key.lower():
                # A crew mobile stays; a helpline is not PII either way.
                return value
            if isinstance(value, str) and _last10(value) in HELPLINE_NUMBERS:
                return value
            kind = "mobile"
        if kind:
            return _MARK.format(kind)
        key_crew = crew or "crew" in key.lower()
        return self._walk(value, crew=key_crew, admin=admin, id_value=bool(_ID_KEY.search(key)), depth=depth + 1)
