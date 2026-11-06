"""Tests for Step 6, final report building and export.

Run directly with python, or with pytest if it is installed:

    .venv/bin/python tests/test_report.py

Aggregation and the digest are exact, so they are checked
against known inputs and outputs. The summary generator is
checked with a fake client. The DOCX export is checked by
opening the produced file again and reading its text back.
"""

import os
import sys
from io import BytesIO

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from docx import Document

from src.llm_client import LlmError
from src.report import (
    MAX_DIGEST_CHARS,
    aggregate_results,
    build_docx,
    build_summary_digest,
    generate_overall_summary,
)

SECTIONS = [
    {"title": "Abstract", "paragraphs": ["Abstract paragraph."]},
    {
        "title": "1 Introduction",
        "paragraphs": ["Intro paragraph one.", "Intro paragraph two."],
    },
]

RESULTS = {
    "s0_p0": {
        "issues": [
            {
                "issue": "The main result is not stated.",
                "severity": "high",
                "explanation": "The abstract ends before the result.",
                "suggested_fix": "Add one sentence with the main result.",
            }
        ],
        "strengths": ["The problem is stated clearly."],
    },
    "s1_p0": {"issues": [], "strengths": ["Good topic sentence."]},
    "s1_p1": {"error": "The model call failed: simulated."},
}


class FakeMessage:
    def __init__(self, content):
        self.content = content


class FakeChoice:
    def __init__(self, content):
        self.message = FakeMessage(content)


class FakeResponse:
    def __init__(self, content):
        self.choices = [FakeChoice(content)]


class FakeCompletions:
    def __init__(self, client):
        self._client = client

    def create(self, model, messages, temperature):
        self._client.calls.append(messages)
        if self._client.fail:
            raise RuntimeError("simulated failure")
        return FakeResponse(self._client.answer)


class FakeChat:
    def __init__(self, client):
        self.completions = FakeCompletions(client)


class FakeClient:
    def __init__(self, answer="Overall summary text.", fail=False):
        self.answer = answer
        self.fail = fail
        self.calls = []
        self.chat = FakeChat(self)


def test_aggregation_counts_are_exact():
    report = aggregate_results(SECTIONS, RESULTS)
    assert report["total_paragraphs"] == 3
    assert report["reviewed_paragraphs"] == 2
    assert report["error_paragraphs"] == 1
    assert report["issue_count"] == 1
    assert report["severity_counts"] == {"high": 1, "medium": 0, "low": 0}
    assert len(report["strengths"]) == 2
    assert report["strengths"][0]["section"] == "Abstract"


def test_digest_contains_findings_and_skips_errors():
    digest = build_summary_digest(aggregate_results(SECTIONS, RESULTS))
    assert "The main result is not stated." in digest
    assert "STRENGTH [Abstract]" in digest
    assert "simulated" not in digest


def test_digest_is_bounded_for_large_reports():
    big_sections = [
        {
            "title": "Methods",
            "paragraphs": [f"Paragraph {i}." for i in range(40)],
        }
    ]
    big_results = {}
    for i in range(40):
        big_results[f"s0_p{i}"] = {
            "issues": [
                {
                    "issue": f"Issue {j} in paragraph {i}.",
                    "severity": ["high", "medium", "low"][j % 3],
                    "explanation": "A long explanation. " * 20,
                    "suggested_fix": "Fix it.",
                }
                for j in range(6)
            ],
            "strengths": ["A strength worth noting. " * 5],
        }
    digest = build_summary_digest(
        aggregate_results(big_sections, big_results)
    )
    assert digest.startswith("TOTALS:")
    assert "240 issues (high 80, medium 80, low 80)" in digest
    note_allowance = 300
    assert len(digest) <= MAX_DIGEST_CHARS + note_allowance, len(digest)
    assert "NOTE:" in digest and "left out of this digest" in digest
    first_issue = digest.index("ISSUE (high)")
    first_low = digest.index("ISSUE (low)")
    assert first_issue < first_low


def test_summary_generation_with_fake_client():
    report = aggregate_results(SECTIONS, RESULTS)
    client = FakeClient()
    summary = generate_overall_summary(report, api_key="k", client=client)
    assert summary == "Overall summary text."
    sent = client.calls[0][1]["content"]
    assert "The main result is not stated." in sent
    failing = FakeClient(fail=True)
    try:
        generate_overall_summary(report, api_key="k", client=failing)
    except LlmError:
        pass
    else:
        raise AssertionError("Failing summary call should raise LlmError")


def test_docx_opens_and_contains_the_report():
    report = aggregate_results(SECTIONS, RESULTS)
    data = build_docx(report, "Overall summary text.", "sample_paper.pdf")
    assert data[:2] == b"PK"
    document = Document(BytesIO(data))
    text = "\n".join(paragraph.text for paragraph in document.paragraphs)
    assert "Paper Review Report" in text
    assert "sample_paper.pdf" in text
    assert "Overall summary text." in text
    assert "Total issues: 1" in text
    assert "The main result is not stated." in text
    assert "Add one sentence with the main result." in text


if __name__ == "__main__":
    test_aggregation_counts_are_exact()
    test_digest_contains_findings_and_skips_errors()
    test_digest_is_bounded_for_large_reports()
    test_summary_generation_with_fake_client()
    test_docx_opens_and_contains_the_report()
    print("TEST_REPORT_OK 5 tests passed")
