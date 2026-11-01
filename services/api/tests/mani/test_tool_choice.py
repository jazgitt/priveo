"""Which tools a question sends to the model (app/mani/tools/choice.py)."""
from app.mani.agent import EXTRA_SPECS
from app.mani.scrub import PatternScrubber
from app.mani.tools import build_registry
from app.mani.tools.choice import KEYWORDS, choose_tools

SPECS = build_registry(PatternScrubber()).specs() + EXTRA_SPECS


def names(question, earlier=(), small_talk=False):
    return [s.name for s in choose_tools(SPECS, question, earlier, small_talk=small_talk)]


def test_every_keyword_entry_names_a_real_tool():
    assert set(KEYWORDS) <= {s.name for s in SPECS}


def test_a_payment_question_sends_the_payment_tool_and_search_only():
    assert names("How much is Over due this month?") == ["payments_summary", "search_sources"]


def test_a_follow_up_uses_the_earlier_questions():
    assert len(names("and last month?")) == len(SPECS)  # nothing to go on: every tool
    assert "payments_summary" in names("and last month?", ["What is the revenue?", "ok"])


def test_a_document_question_sends_no_live_tool():
    assert names("What does the migration for the planner change?") == ["search_sources"]


def test_a_greeting_sends_no_live_tool():
    assert names("Hello Sir", small_talk=True) == ["search_sources"]


def test_an_unrecognised_business_question_gets_every_tool():
    assert len(names("Give me a quick business pulse")) == len(SPECS)


def test_memory_tools_follow_their_words():
    assert {"remember_fact", "list_memory"} <= set(names("What do you remember?"))
    assert "forget_fact" in names("Please forget that note")


def test_a_request_for_more_facts_offers_every_live_tool_but_not_memory():
    got = names("Ok what else can you tell me about my customers?")
    assert {"subscriptions_summary", "payments_summary", "complaints_summary", "ratings_summary"} <= set(got)
    assert "remember_fact" not in got


def test_open_questions_are_those_that_ask_for_more_with_no_topic():
    from app.mani.tools.choice import is_open_question
    assert is_open_question("Ok what else can you tell me about my customers?")
    assert is_open_question("Give me an overview")
    assert not is_open_question("What about payments over due?")
    assert not is_open_question("How many active subscriptions do we have?")
