# Mani Bond: golden question set, part A1

Part A1: code implementation, questions 1 to 10. Run and clear on its own with `--set A1` (`services/api/tests/mani_eval`). The overview, the review rules and the points to settle are in [`mani-question-set-review.md`](mani-question-set-review.md).

This file is part of the evaluation answer key. It stays out of the search index (`services/api/app/mani/sources.py`, `EXCLUDE_PATHS`). Do not remove that exclusion, or Mani will find its own answers.

## A. Code implementation (sources: `services/api`, `wiki/`) - part 1 (questions 1 to 10)

| # | Question | Golden answer | Source | Decision | Notes |
|---|---|---|---|---|---|
| 1 | How does Mani rank search results, and what constants control it? | Vector search (pgvector cosine distance) and full-text search each give a ranked list, merged by reciprocal rank fusion with `RRF_K = 60`. A requirement ID named in the question adds `ID_BOOST = 1.0`. A passage scoring under half of the best one (`MIN_RELATIVE = 0.5`) is dropped, and one source supplies at most two passages (`PER_SOURCE = 2`). | `app/mani/retrieval.py`, `wiki/Mani_Bond.md` (plan only) | Keep | |
| 2 | How are documents split into chunks for Mani's index? | Chunks are cut at about 1,200 characters (`CHUNK_CHARS`), on a paragraph or line where possible, and the last 150 characters (`OVERLAP_CHARS`) repeat at the start of the next chunk in the same section. | `app/mani/ingest.py` | Keep | |
| 3 | Which models and vector size does Mani use by default? | Backend `local` (Ollama). Chat model `qwen3-14b-16k` (`qwen3:14b` built with a 16,384-token context), embedding model `qwen3-embedding:8b`, and every index is `vector(1024)` (`EMBEDDING_DIMENSIONS = 1024`). | `app/mani/config.py` | Keep | |
| 4 | What spending and loop limits does Mani have? | A budget of 1.0 US dollar (`budget_usd`), no per-request limit by default (`per_request_budget_usd = 0`), at most 6 tool rounds per turn (`max_tool_rounds`), and conversations are kept 90 days (`conversation_retention_days`). | `app/mani/config.py`, `wiki/Mani_Bond.md` (plan only) | Keep | |
| 5 | Which live data tools can Mani call? | Ten read tools: `subscriptions_summary`, `pauses_and_skips_summary`, `complaints_summary`, `ratings_summary`, `operations_summary`, `on_time_completion_rate`, `crew_capacity_outlook`, `addons_summary`, `payments_summary` and `crew_summary`. | `app/mani/tools/__init__.py` and the tool modules | Keep | |
| 6 | How many passages does Mani fetch for a question, and how do the documents reach the model? | Before the model runs, `_prefetch` looks the question up and adds the passages as a system message wrapped in data markers. The model can also call its own `search_sources` tool. | `app/mani/agent.py` | Keep | |
| 7 | Why is the question-set review file not searchable by Mani? | It is the evaluation answer key, listed in `EXCLUDE_PATHS` in `sources.py` (owner decision 31-Oct-2026), so Mani cannot find the answers. | `app/mani/sources.py` | Drop | |
| 8 | How many wrong passwords block a customer, and for how long? | `MAX_WRONG_ATTEMPTS = 5`, then `CUSTOMER_BLOCK`, 15 minutes. | `app/identity/service.py`, `wiki/Identity_and_access.md` | Keep | |
| 9 | How do blocks work for crew and admin logins? | After 5 wrong attempts: 15 minutes, then 1 hour, then 24 hours for each further round within 24 hours (`STAFF_BLOCKS`, `STAFF_BLOCK_MEMORY = 24h`). A block ends by itself, so nobody is locked out for good. | `app/identity/service.py`, `wiki/Identity_and_access.md` | Keep | |
| 10 | How long does an web access token last? | 12 hours or (12 * 60) minutes . The refresh token is a separate value, hashed for storage. | `app/platform/config.py`, `app/identity/tokens.py` | Keep | |
