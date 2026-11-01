"""The 50 golden questions as data (docs/agent/mani-question-set-review-*.md, Appendix A of
the architecture). The text matches the review files; a test checks that.

`type` is the group: code, architecture, business or run. Every question is scored by
`check = "phrases"`: `params["phrases_all"]` lists the facts the answer must state (case-insensitive
regular expressions; a `{migration_head}` style token is filled in from the repository), and the
answer must carry a citation. `gold` lists regexes over the indexed chunks that hold those facts, so
a failure can be placed in the pipeline (`stage.py`). The golden answers are in the review files.
`SETS` splits the questions as the review files do: A1 (1-10), A2 (11-20), B, C, D."""
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

TYPES = ("code", "architecture", "business", "run")

# Wording that signals a refusal, an honest "I do not have that" and a confirmed action.
REFUSAL = (r"can(?:no|')?t|cannot|won't|will not|unable|not able|not allowed|not permitted|"
           r"decline|refuse|sorry|read-only|read only|don't share|do not share|not something i|"
           r"नहीं|मना")
# "The documents do not explicitly state the dates" says the data is missing as plainly as "I don't have".
NOT_STATED = (r"(?:does|do|did|is|are) not (?:explicitly |specifically |clearly )?(?:state|say|give|list|show|"
              r"record|contain|mention|provide|specify|document)|not (?:explicitly |specifically )?"
              r"(?:stated|recorded|listed|given|mentioned|provided|documented)")
MISSING = (r"don't have|do not have|doesn't have|does not have|cannot|can't|no (?:data|record|"
           r"such|payment|job)|missing|not (?:available|recorded|found|indexed|in the)|unable|"
           r"couldn't find|could not find|doesn't exist|does not exist|none|zero|\b0\b|nahi|नहीं|"
           + NOT_STATED)

WRITE_TOOL = (r"^(?:create|update|delete|set|write|send|approve|assign|reassign|change|mark|cancel|"
              r"add|remove|insert|execute|apply|pay|refund)(?:_|$)")


@dataclass(frozen=True)
class Question:
    id: int
    area: str
    text: str  # as written in the review file
    type: str
    check: str
    expected_key: str | None = None
    ask: str | None = None  # what is sent to the agent, when it differs from `text`
    lang: str = "en"  # en, hi or mixed
    needs_seed: bool = False  # cannot be scored until the owner approves a seed addition
    needs_citation: bool = False
    setup: tuple[str, ...] = ()  # earlier user messages in the same conversation
    precondition: str = ""  # for example "budget_exhausted"
    params: dict[str, Any] = field(default_factory=dict)
    # Facts the answer rests on, as regexes (case-insensitive) over a chunk's heading and text.
    # A chunk that matches one is a gold chunk for it. Used to place a failure in the pipeline.
    gold: tuple[str, ...] = ()
    dropped: bool = False  # marked Drop in the review file: keeps its number, is not run or scored

    @property
    def prompt(self) -> str:
        return self.ask or self.text


def _q(id: int, area: str, text: str, type: str, check: str, **kwargs: Any) -> Question:
    assert type in TYPES, type
    return Question(id, area, text, type, check, **kwargs)


CODE, ARCH, BIZ, RUN = ("Code implementation", "Tech stack and architecture",
                        "Business requirements", "How to run Priveo")

QUESTIONS: tuple[Question, ...] = (
    _q(1, CODE,
       "How does Mani rank search results, and what constants control it?",
       "code", "phrases", needs_citation=True,
       params={"phrases_all": [r"RRF|reciprocal rank", r"\b60\b", r"PER_SOURCE", r"0\.5"]},
       gold=(r"RRF_K = 60",)),
    _q(2, CODE,
       "How are documents split into chunks for Mani's index?",
       "code", "phrases", needs_citation=True,
       params={"phrases_all": [r"1,?200", r"\b150\b"]},
       gold=(r"CHUNK_CHARS = 1200", r"OVERLAP_CHARS = 150",)),
    _q(3, CODE,
       "Which models and vector size does Mani use by default?",
       "code", "phrases", needs_citation=True,
       params={"phrases_all": [r"qwen3(?::14b|-14b-16k)", r"qwen3-embedding:8b", r"1,?024"]},
       gold=(r"EMBEDDING_DIMENSIONS = 1024", r"qwen3-embedding:8b",)),
    _q(4, CODE,
       "What spending and loop limits does Mani have?",
       "code", "phrases", needs_citation=True,
       params={"phrases_all": [r"\b6\b", r"budget"]},
       gold=(r"max_tool_rounds: int = 6", r"conversation_retention_days: int = 90",)),
    _q(5, CODE,
       "Which live data tools can Mani call?",
       "code", "phrases", needs_citation=True,
       params={"phrases_all": [r"subscriptions[_ ]?summary", r"payments[_ ]?summary", r"capacity[_ ]?outlook",
                                   r"ratings[_ ]?summary"]},
       gold=(r"SubscriptionsSummary\(\), ScheduleChangesSummary\(\)",)),
    _q(6, CODE,
       (
    "How many passages does Mani fetch for a question, and how do the documents reach the "
        "model?"),
       "code", "phrases", needs_citation=True,
       params={"phrases_all": [r"prefetch|search_sources"]},
       gold=(r"def _prefetch",)),
    _q(7, CODE,
       "Why is the question-set review file not searchable by Mani?",
       "code", "phrases", needs_citation=True,
       params={"phrases_all": [r"answer key", r"EXCLUDE_PATHS|exclu"]},
       gold=(r"the evaluation answer key",),
       dropped=True),
    _q(8, CODE,
       "How many wrong passwords block a customer, and for how long?",
       "code", "phrases", needs_citation=True,
       params={"phrases_all": [r"\b5\b", r"15 minutes"]},
       gold=(r"MAX_WRONG_ATTEMPTS = 5", r"CUSTOMER_BLOCK = timedelta\(minutes=15\)",)),
    _q(9, CODE,
       "How do blocks work for crew and admin logins?",
       "code", "phrases", needs_citation=True,
       params={"phrases_all": [r"15 minutes", r"1 hour", r"24 hours"]},
       gold=(r"STAFF_BLOCKS = ",)),
    _q(10, CODE,
       "How long does an web access token last?",
       "code", "phrases", needs_citation=True,
       params={"phrases_all": [r"12 ?hours|12 ?\* ?60|\b720\b"]},
       gold=(r"WEB_SESSION_MINUTES = 12 \* 60",)),
    _q(11, CODE,
       "How is a crew member's first password generated?",
       "code", "phrases", needs_citation=True,
       params={"phrases_all": [r"(?:3|three) letters", r"(?:4|four) (?:random )?digits", r"\$"]},
       gold=(r"def generate_password",)),
    _q(12, CODE,
       "Where are the 8 PM freeze and the 9 PM customer cutoff set?",
       "code", "phrases", needs_citation=True,
       params={"phrases_all": [r"8 ?PM", r"9 ?PM", r"skip|pause", r"schedul"]},
       gold=(r"FREEZE_HOUR = 20", r"CUTOFF_HOUR = 21",),
       dropped=True),
    _q(13, CODE,
       "What are the upload size limits for media?",
       "code", "phrases", needs_citation=True,
       params={"phrases_all": [r"10 ?MB", r"25 ?MB", r"5 ?MB"]},
       gold=(r"MAX_BYTES = \{",)),
    _q(14, CODE,
       "What does the server check at startup, and what stops it from starting?",
       "code", "phrases", needs_citation=True,
       params={"phrases_all": [r"TOKEN_SECRET", r"ENVIRONMENT", r"CRON_SECRET"]},
       gold=(r"TOKEN_SECRET is not set",)),
    _q(15, CODE,
       "Which scheduled jobs does the API expose, and where do they run?",
       "code", "phrases", needs_citation=True,
       params={"phrases_all": [r"payments-overdue", r"freeze-due", r"bom1"]},
       gold=(r"crew-society-moves",)),
    _q(16, CODE,
       "What does the overdue job do?",
       "code", "phrases", needs_citation=True,
       params={"phrases_all": [r"7 days", r"Inactive", r"Over due"]},
       gold=(r"def mark_overdue_and_inactive",)),
    _q(17, CODE,
       "When does the backend create the next plan payment?",
       "code", "phrases", needs_citation=True,
       params={"phrases_all": [r"7 days", r"renewal"]},
       gold=(r"def generate_due_payments",)),
    _q(18, CODE,
       "What happens to an add-on payment when its service is completed?",
       "code", "phrases", needs_citation=True,
       params={"phrases_all": [r"Over[ _]?due", r"add_on_service_completed|service completed|ADM-PAY-13"]},
       gold=(r"def add_on_service_completed",)),
    _q(19, CODE,
       "What shape does an API error have?",
       "code", "phrases", needs_citation=True,
       params={"phrases_all": [r"code", r"message", r"fields", r"request[_ ]?id"]},
       gold=(r"class ErrorBody",)),
    _q(20, CODE,
       "What does `/v1/public/config` return, and what is the latest migration?",
       "code", "phrases", needs_citation=True,
       params={"phrases_all": [r"min_app_version", r"0042|mani[_ ]foundation"]},
       gold=(r"min_app_version", r"Revision ID: 0042",),
       dropped=True),
    _q(21, ARCH,
       "What is the app built with, and how does it handle state and navigation?",
       "architecture", "phrases", needs_citation=True,
       params={"phrases_all": [r"Flutter", r"Riverpod", r"go_router"]},
       gold=(r"Riverpod, go_router, feature folders",)),
    _q(22, ARCH,
       "What are the rules between backend modules?",
       "architecture", "phrases", needs_citation=True,
       params={"phrases_all": [r"service interface|through.{0,40}service", r"scheduling"]},
       gold=(r"A module reads another module only through",)),
    _q(23, ARCH,
       "How do the mobile app and the web portal authenticate?",
       "architecture", "phrases", needs_citation=True,
       params={"phrases_all": [r"cookie", r"CSRF", r"60[- ]minutes?", r"refresh"]},
       gold=(r"HttpOnly secure cookie, CSRF token",)),
    _q(24, ARCH,
       "How does the scheduler work?",
       "architecture", "phrases", needs_citation=True,
       params={"phrases_all": [r"OR-?Tools", r"CP-SAT", r"Draft", r"pure function|no database"]},
       gold=(r"pure function: `solve\(inputs\)",)),
    _q(25, ARCH,
       "How do crew uploads survive a poor connection?",
       "architecture", "phrases", needs_citation=True,
       params={"phrases_all": [r"queue", r"signed|confirm", r"every required upload|until|CRW-SVC-10"]},
       gold=(r"Upload queue",)),
    _q(26, ARCH,
       "Which security findings are open, and which is High?",
       "architecture", "phrases", needs_citation=True,
       params={"phrases_all": [r"media", r"public", r"CRON_SECRET"]},
       gold=(r"Media files are public and permanent",)),
    _q(27, ARCH,
       "What conventions apply to time, money and API errors?",
       "architecture", "phrases", needs_citation=True,
       params={"phrases_all": [r"paise", r"IST|India Standard Time", r"request_id"]},
       gold=(r"integer paise",)),
    _q(28, ARCH,
       "What is the hosting target, and what runs today?",
       "architecture", "phrases", needs_citation=True,
       params={"phrases_all": [r"Vercel", r"Supabase", r"AWS", r"RDS"]},
       gold=(r"Supabase first, then AWS Mumbai",)),
    _q(29, ARCH,
       "What is the admin web portal built with?",
       "architecture", "phrases", needs_citation=True,
       params={"phrases_all": [r"React", r"TanStack", r"shadcn", r"dnd-kit"]},
       gold=(r"dnd-kit",)),
    _q(30, ARCH,
       "What does the system component diagram show?",
       "architecture", "phrases", needs_citation=True,
       params={"phrases_all": [r"Flutter", r"FastAPI", r"Supabase", r"Resend"]},
       gold=(r"flowchart LR",)),
    _q(31, BIZ,
       "By when must a customer change a date's schedule, and what happens after?",
       "business", "phrases", needs_citation=True,
       params={"phrases_all": [r"9 ?PM", r"previous day|day before", r"helpline|call support"]},
       gold=(r"SCHED-01 \|",)),
    _q(32, BIZ,
       "What happens after 5 wrong customer passwords?",
       "business", "phrases", needs_citation=True,
       params={"phrases_all": [r"blocked", r"15 minutes", r"forgot password"]},
       gold=(r"AUTH-13 \|",)),
    _q(33, BIZ,
       "How are crew passwords created, handed over and protected from guessing?",
       "business", "phrases", needs_citation=True,
       params={"phrases_all": [r"(?:3|three) letters", r"\$", r"once", r"1 hour"]},
       gold=(r"CRW-ACC-07 \|",)),
    _q(34, BIZ,
       "When does a subscription become Inactive for non-payment?",
       "business", "phrases", needs_citation=True,
       params={"phrases_all": [r"7 days", r"Over due", r"add-on"]},
       gold=(r"ADM-SUB-03 \|",)),
    _q(35, BIZ,
       "When does the backend create the plan payment for the next cycle?",
       "business", "phrases", needs_citation=True,
       params={"phrases_all": [r"7 days", r"renewal"]},
       gold=(r"ADM-PAY-06 \|",)),
    _q(36, BIZ,
       "When is a schedule frozen, and how does that relate to the customer deadline?",
       "business", "phrases", needs_citation=True,
       params={"phrases_all": [r"8 ?PM", r"9 ?PM"]},
       gold=(r"ADM-SCH-25 \|",)),
    _q(37, BIZ,
       "What happens to crew photos and videos on a poor connection?",
       "business", "phrases", needs_citation=True,
       params={"phrases_all": [r"upload", r"not (?:considered )?complete"]},
       gold=(r"CRW-SVC-10 \|",)),
    _q(38, BIZ,
       "How does the admin portal keep an admin signed in?",
       "business", "phrases", needs_citation=True,
       params={"phrases_all": [r"cookie", r"CSRF", r"60 minutes"]},
       gold=(r"ADM-ACC-12 \|",)),
    _q(39, BIZ,
       "Does skipping a visit extend the plan or change the month's cost, and who can skip?",
       "business", "phrases", needs_citation=True,
       params={"phrases_all": [r"crew\.manager_skip", r"only (?:the )?admin"]},
       gold=(r"A skipped day does not extend the plan",)),
    _q(40, BIZ,
       "How does a customer pay in the MVP?",
       "business", "phrases", needs_citation=True,
       params={"phrases_all": [r"UPI", r"QR", r"coming soon|disabled|not available"]},
       gold=(r"PAY-05 \|",)),
    _q(41, RUN,
       "How do I lint and test the API?",
       "run", "phrases", needs_citation=True,
       params={"phrases_all": [r"ruff", r"pytest"]},
       gold=(r"python -m ruff check",)),
    _q(42, RUN,
       "How do I run the PostgreSQL checks, and what must I never do?",
       "run", "phrases", needs_citation=True,
       params={"phrases_all": [r"test_postgres", r"TEST_DATABASE_URL"]},
       gold=(r"test_postgres\.py",)),
    _q(43, RUN,
       "How do I run all the checks at once?",
       "run", "phrases", needs_citation=True,
       params={"phrases_all": [r"check-local\.sh", r"--changed"]},
       gold=(r"tools/dev/check-local\.sh",)),
    _q(44, RUN,
       "How do I check the web portal?",
       "run", "phrases", needs_citation=True,
       params={"phrases_all": [r"npm run lint", r"npm test", r"npm run build"]},
       gold=(r"npm run lint",)),
    _q(45, RUN,
       "How do I check the Flutter app, and when must I regenerate files?",
       "run", "phrases", needs_citation=True,
       params={"phrases_all": [r"flutter analyze", r"gen_theme", r"gen-l10n", r"gen_api"]},
       gold=(r"dart run tool/gen_theme\.dart",)),
    _q(46, RUN,
       "How do I build and run the app on a simulator or emulator?",
       "run", "phrases", needs_citation=True,
       params={"phrases_all": [r"build_local\.sh", r"android", r"ios"]},
       gold=(r"build_local\.sh android",)),
    _q(47, RUN,
       "How do I point the app at the API running on my Mac?",
       "run", "phrases", needs_citation=True,
       params={"phrases_all": [r"--local", r"10\.0\.2\.2", r"debug"]},
       gold=(r"10\.0\.2\.2",)),
    _q(48, RUN,
       "How do I build an installable app for the test or production API?",
       "run", "phrases", needs_citation=True,
       params={"phrases_all": [r"build_release\.sh", r"envtest", r"in\.priveo\.app"]},
       gold=(r"flavor envtest|--flavor envtest",)),
    _q(49, RUN,
       "How is the app version raised, and how do I put a build on a phone?",
       "run", "phrases", needs_citation=True,
       params={"phrases_all": [r"bump_version", r"\b100\b", r"push_apk"]},
       gold=(r"fewer than 100 lines",)),
    _q(50, RUN,
       "How do changes reach the test and production servers?",
       "run", "phrases", needs_citation=True,
       params={"phrases_all": [r"main", r"test", r"tag|v\*", r"approv"]},
       gold=(r"v\*` tag",)),
)

# The parts the review files are split into, each run and cleared on its own (`--set A1`).
ACTIVE: tuple[Question, ...] = tuple(q for q in QUESTIONS if not q.dropped)  # what the runs use
SETS: dict[str, tuple[Question, ...]] = {
    name: tuple(q for q in ACTIVE if first <= q.id <= last)
    for name, (first, last) in {"A1": (1, 10), "A2": (11, 20), "B": (21, 30), "C": (31, 40), "D": (41, 50)}.items()
}

BY_ID = {q.id: q for q in QUESTIONS}


def migration_head(root: Path | None = None) -> tuple[str, str]:
    """The repository's Alembic head from the migration file names, for example
    ("0042", "mani_foundation"). Read from files, so it follows the repo."""
    folder = (root or Path(__file__).resolve().parents[2]) / "migrations" / "versions"
    names = sorted(p.stem for p in folder.glob("2*_*.py"))
    _date, number, *rest = names[-1].split("_")
    return number, "_".join(rest)


def phrase_context() -> dict[str, str]:
    number, name = migration_head()
    return {"migration_head": number, "migration_head_name": name.replace("_", "[ _]")}
