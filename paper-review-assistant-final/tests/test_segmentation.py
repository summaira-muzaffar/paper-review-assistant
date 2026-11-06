"""Tests for Step 3, section and paragraph splitting.

Run directly with python, or with pytest if it is installed:

    .venv/bin/python tests/test_segmentation.py

The tests use small page texts written out in full, so the
expected sections and paragraphs are known exactly.
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.segmentation import count_paragraphs, is_section_heading, split_into_sections

SAMPLE_PAGES = [
    (
        "Abstract\n"
        "This paper studies automated review of academic papers. "
        "It proposes a practical tool.\n"
        "\n"
        "1 Introduction\n"
        "Reviewing papers is slow work. Feedback is often vague.\n"
        "\n"
        "This second paragraph explains the aim of the work in detail.\n"
    ),
    (
        "2 Methodology\n"
        "The system extracts text from PDF files first.\n"
        "\n"
        "It then splits the text into sections and paragraphs.\n"
        "\n"
        "References\n"
        "[1] A reference entry for an earlier paper.\n"
    ),
]


def test_known_and_numbered_headings_are_detected():
    assert is_section_heading("Abstract")
    assert is_section_heading("1 Introduction")
    assert is_section_heading("RELATED WORK")
    assert is_section_heading("References")


def test_sentences_are_not_headings():
    assert is_section_heading("Reviewing papers is slow work.") is False
    assert is_section_heading("This second paragraph explains the aim.") is False
    assert is_section_heading("A very long line that simply keeps going and going on") is False


def test_split_into_sections_and_paragraphs():
    sections = split_into_sections(SAMPLE_PAGES)
    titles = [section["title"] for section in sections]
    assert titles == ["Abstract", "1 Introduction", "2 Methodology", "References"]
    counts = [len(section["paragraphs"]) for section in sections]
    assert counts == [1, 2, 2, 1]
    assert count_paragraphs(sections) == 6
    assert "Reviewing papers is slow work." in sections[1]["paragraphs"][0]


def test_text_before_first_heading_becomes_front_matter():
    pages = ["A Study of Automated Review\nBy A. Researcher\n\nIntroduction\nFirst body paragraph of the paper."]
    sections = split_into_sections(pages)
    assert sections[0]["title"] == "Front Matter"
    assert sections[1]["title"] == "Introduction"
    assert count_paragraphs(sections) == 2


def test_page_numbers_and_empty_input():
    assert split_into_sections([]) == []
    assert split_into_sections(["", "  "]) == []
    pages = ["Introduction\nBody text of the section.\n\n12"]
    sections = split_into_sections(pages)
    assert count_paragraphs(sections) == 1
    assert "12" not in sections[0]["paragraphs"][0]


if __name__ == "__main__":
    test_known_and_numbered_headings_are_detected()
    test_sentences_are_not_headings()
    test_split_into_sections_and_paragraphs()
    test_text_before_first_heading_becomes_front_matter()
    test_page_numbers_and_empty_input()
    print("TEST_SEGMENTATION_OK 5 tests passed")
