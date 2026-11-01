"""Which tools a question needs. Every tool definition is sent on every model call, so sending
all fourteen costs about 2,000 tokens a call, and a turn may make several calls. A live tool is
kept when the question (or one of the last two questions, for a follow-up like "and last month?")
holds one of its words. A tool with no entry here, such as search_sources, is always kept.
When no live tool matches, a question about documents or code gets none, a greeting gets none,
and any other question gets all of them, so a question worded in an unexpected way is not left
without its data."""
from collections.abc import Sequence

from app.mani.contracts import ToolSpec

# Lower-case fragments, matched anywhere in the question. A fragment that is too wide only costs a few
# tokens; one that is missing is covered by the fallback above.
KEYWORDS: dict[str, tuple[str, ...]] = {
    "subscriptions_summary": ("subscri", "plans", "by plan", "societ", "inactive", "churn", "cancel", "active",
                              "customer", "member", "ग्राहक", "grahak"),
    "pauses_and_skips_summary": ("pause", "skip", "schedule change", "paus"),
    "complaints_summary": ("customer", "complain", "issue", "ticket", "unresolved", "shikayat", "शिकायत"),
    "ratings_summary": ("customer", "rating", "star", "review", "feedback", "satisf", "tag"),
    "operations_summary": ("job", "today", "visit", "schedule", "at risk", "missed", "absent", "complet",
                           "in progress", "operation", "societ", "aaj", "आज"),
    "on_time_completion_rate": ("on time", "on-time", "ontime", "cut-off", "cutoff", "cut off", "late",
                                "punctual"),
    "crew_capacity_outlook": ("capacity", "outlook", "demand", "overbook", "tight", "forecast", "upcoming",
                              "next week", "next 7", "utilis", "utiliz", "crew minutes"),
    "addons_summary": ("add-on", "addon", "add on", "spa"),
    "payments_summary": ("customer", "payment", "paid", "revenue", "money", "owed", "owe", "over due", "overdue", "due",
                         "collect", "rupee", "receiv", "gst", "invoice", "₹", "paisa", "पैसे"),
    "crew_summary": ("crew", "trainee", "blocked", "staff", "team", "absent", "locked", "member"),
    "remember_fact": ("remember", "memory", "memories", "note", "told you", "yaad", "याद"),
    "list_memory": ("remember", "memory", "memories", "know about", "told you", "yaad", "याद"),
    "forget_fact": ("forget", "remove", "delete", "bhool", "bhul", "भूल"),
}
# A follow-up that asks for more facts, with no topic of its own: every live tool is offered.
OPEN_WORDS = ("what else", "tell me more", "anything else", "more about", "what about", "anything more")
OVERVIEW_WORDS = ("overview", "business pulse", "how is the business", "how are we doing", "status update",
                  "give me a summary", "the big picture")
LIVE = {n for n in KEYWORDS if n not in ("remember_fact", "list_memory", "forget_fact")}
# Words that mark a question about documents or code. With one of these and no live-tool word, no live tool is sent.
DOCUMENT_WORDS = ("requirement", "rule", "code", "file", "migration", "release", "security", "constant", "limit",
                  "setting", "document", "spec", "adr", "how does", "how do", "where is", "which file",
                  "endpoint", "table", "doc")


def choose_tools(specs: Sequence[ToolSpec], question: str, earlier_questions: Sequence[str] = (),
                 *, small_talk: bool = False) -> list[ToolSpec]:
    """The specs this turn sends, in their original order."""
    text = " ".join([question, *earlier_questions[-2:]]).lower()
    matched = {name for name, words in KEYWORDS.items() if any(w in text for w in words)}
    own_text = question.lower()
    if any(w in own_text for w in OPEN_WORDS):
        matched = set(KEYWORDS) - {"remember_fact", "list_memory", "forget_fact"} | (matched & set(KEYWORDS))
    if not matched:
        if small_talk or any(w in own_text for w in DOCUMENT_WORDS):
            matched = set()
        else:
            matched = set(KEYWORDS)
    return [s for s in specs if s.name not in KEYWORDS or s.name in matched]


# Words so general that they do not name a topic: "what else about my customers" is still an open question.
GENERIC = {"customer", "member", "societ", "active", "today", "team", "staff", "plans", "by plan"}


def is_open_question(question: str) -> bool:
    """A request for more facts with no topic of its own ("what else about my customers?", "give me an
    overview"). The agent reads the main live summaries for it in code, so a small model cannot answer with a
    menu of what it could look up, or with figures it made up."""
    text = question.lower()
    if not any(w in text for w in OPEN_WORDS + OVERVIEW_WORDS):
        return False
    topics = {w for name, words in KEYWORDS.items() if name in LIVE for w in words if w not in GENERIC}
    return not any(w in text for w in topics)
