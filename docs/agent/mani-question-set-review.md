# Mani Bond: golden question set (v2, for review)

Date: 31-Oct-2026. Status: **Reviewed 31-Oct-2026: all 50 questions marked Keep.** This replaces the first set of 50 questions (30-Oct-2026), which is removed from the repository; git history keeps it. The new set tests one thing: whether Mani finds and states facts from the indexed sources.

This file is the evaluation answer key. It stays out of the search index (`services/api/app/mani/sources.py`, `EXCLUDE_PATHS`). Do not remove that exclusion, or Mani will find its own answers.

## The set

| Group | Questions | Source of the golden answers |
|---|---|---|
| A. Code implementation | 1 to 20 | The source code in `priveo/apps/mobile/android/app/src`,`priveo/apps/web/src`,`priveo/services/api/app`, Wiki has a english explaination and documentation of the core implementation `priveo/wiki` |
| B. Tech stack and architecture | 21 to 30 | `docs/architecture.md`, `docs/tech-stack.md`, `docs/security-backlog.md`, `docs/system-component-diagram.md` |
| C. Business requirements | 31 to 40 | The files in `docs/reqs/` |
| D. How to run Priveo | 41 to 50 | `CLAUDE.md` and the scripts in `apps/mobile/tool/` |

## The five files

The questions and golden answers are in five files, so each part can be run and cleared on its own. All five are answer keys and are excluded from the search index.

| Part | Questions | File |
|---|---|---|
| A1 | 1 to 10 | [`mani-question-set-review-A1.md`](mani-question-set-review-A1.md) |
| A2 | 11 to 20 | [`mani-question-set-review-A2.md`](mani-question-set-review-A2.md) |
| B | 21 to 30 | [`mani-question-set-review-B.md`](mani-question-set-review-B.md) |
| C | 31 to 40 | [`mani-question-set-review-C.md`](mani-question-set-review-C.md) |
| D | 41 to 50 | [`mani-question-set-review-D.md`](mani-question-set-review-D.md) |

## How to review

For each row, fill in the **Decision** column: Keep, Change or Drop. If Change, say what in the Notes column. A golden answer is what a correct reply must say. Mani is scored on the facts, not the wording. Every row names its source, so a reviewer can check it in under a minute.

Targets stay as in section 10 of `agent-architecure.md`: 95% factual correctness, and the correct source named for each claim.

## Points to settle before this becomes the test

1. **`docs/system-component-diagram.md` was refreshed on 31-Oct-2026** to match the code (PostgreSQL on Supabase, the portal, Mani, cron jobs, Vercel hosting). Question 30 uses the new version.
2. **`docs/architecture.md` is a v0.3 draft of 11-Oct-2026.** Its hosting target (AWS) is still the later goal. Section 7.1 records the interim Vercel and Supabase setup. Questions 21 to 29 use what it says, and say so where it differs from today's setup.
3. **`CLAUDE.md` gives Windows paths** (`.venv/Scripts/python`). The owner confirmed (31-Oct-2026) that Windows and macOS are both fine and the only difference is the OS. Questions 41 and 42 therefore accept either interpreter: `.venv/Scripts/python` on Windows, `.venv/bin/python` on macOS and Linux. `CLAUDE.md` stays as it is.
4. **Add-on payment timing is settled.** `ADM-PAY-06` was changed on 31-Oct-2026 (Admin file v0.37): an add-on payment becomes Over due immediately after its service is completed, as `ADM-PAY-13`, `ADD-18` and the code (`add_on_service_completed`) already say. Question 18 is consistent with all of them.
5. **The old question set is gone.** `tests/mani_eval/questions.py` and Appendix A of `agent-architecure.md` now hold this set (31-Oct-2026).
