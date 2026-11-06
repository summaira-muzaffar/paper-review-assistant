"""Tests for Step 4, per paragraph review prompts.

Run directly with python, or with pytest if it is installed:

    .venv/bin/python tests/test_prompts.py

The central claim under test is Professor Tao's second hard
requirement, at the level of the prompt module: every paragraph
has its own prompt, and changing one paragraph's prompt leaves
every other paragraph's prompt untouched.
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.prompts import (
    BASE_REVIEW_PROMPT,
    collect_prompts,
    get_default_prompt,
    paragraph_key,
    prompt_widget_key,
)

SECTIONS = [
    {"title": "Abstract", "paragraphs": ["Abstract paragraph one."]},
    {
        "title": "1 Introduction",
        "paragraphs": ["Intro paragraph one.", "Intro paragraph two."],
    },
    {"title": "References", "paragraphs": ["Reference paragraph one."]},
]


def test_default_prompt_is_complete_and_section_aware():
    abstract_prompt = get_default_prompt("Abstract")
    assert BASE_REVIEW_PROMPT in abstract_prompt
    assert "abstract" in abstract_prompt.lower()
    references_prompt = get_default_prompt("References")
    assert "citation" in references_prompt.lower()
    assert abstract_prompt != references_prompt


def test_every_paragraph_gets_a_prompt_by_default():
    prompts = collect_prompts(SECTIONS, state={})
    assert len(prompts) == 4
    for section_index, section in enumerate(SECTIONS):
        for paragraph_index in range(len(section["paragraphs"])):
            key = paragraph_key(section_index, paragraph_index)
            assert prompts[key] == get_default_prompt(section["title"])


def test_editing_one_prompt_changes_only_that_paragraph():
    custom = "Check only the statistics in this paragraph, nothing else."
    state = {prompt_widget_key(1, 0): custom}
    prompts = collect_prompts(SECTIONS, state=state)
    assert prompts[paragraph_key(1, 0)] == custom
    assert prompts[paragraph_key(1, 1)] == get_default_prompt("1 Introduction")
    assert prompts[paragraph_key(0, 0)] == get_default_prompt("Abstract")
    assert prompts[paragraph_key(2, 0)] == get_default_prompt("References")


if __name__ == "__main__":
    test_default_prompt_is_complete_and_section_aware()
    test_every_paragraph_gets_a_prompt_by_default()
    test_editing_one_prompt_changes_only_that_paragraph()
    print("TEST_PROMPTS_OK 3 tests passed")
