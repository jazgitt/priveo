from app.mani.tidy import tidy_answer

NAMES = ["subscriptions_summary", "payments_summary", "search_sources"]


def test_a_source_aside_is_removed():
    assert tidy_answer("There are 2 active subscriptions as of 01-Nov-26 13:55 (from `subscriptions_summary` tool).",
                       NAMES) == "There are 2 active subscriptions as of 01-Nov-26 13:55."


def test_a_tool_name_in_a_sentence_becomes_plain_words():
    out = tidy_answer("The subscriptions_summary tool only shows counts. I used `payments_summary` too.", NAMES)
    assert out == "The live summary only shows counts. I used the live summary too."


def test_other_text_and_backticked_commands_are_left_alone():
    text = "Run `npm run lint`, then `npm test`.\n\n- first\n- second"
    assert tidy_answer(text, NAMES) == text
    assert tidy_answer("Nothing to change here.", []) == "Nothing to change here."


def test_the_prompt_label_tool_data_is_not_repeated():
    assert tidy_answer("The tool data shows 5. These come from tool data.", NAMES) == \
        "The data shows 5. These come from data."


def test_code_files_are_dropped_unless_the_question_was_about_code():
    text = ("I cannot see renewal dates. They are worked out in the code (e.g., via `renewal_date` in cycle.py). "
            "Shall I give you the counts?\n- See cycle.py for details\n- Counts by status")
    out = tidy_answer(text, NAMES, about_code=False)
    assert "cycle.py" not in out and "`" not in out
    assert "Shall I give you the counts?" in out and "- Counts by status" in out
    assert "cycle.py" in tidy_answer(text, NAMES, about_code=True)
    assert tidy_answer("Only cycle.py matters.", NAMES, about_code=False) == "Only cycle.py matters."
