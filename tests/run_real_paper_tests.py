"""Step 7 real document evaluation runner.

Not a unit test. This script runs the complete pipeline (extract,
split, prompt, review, aggregate, summarise, export) on real PDF
files, using a recording fake model client, and prints a JSON
summary of what happened for the Step 7 test report. The only
stage not exercised against a live service is the network call
itself, which needs a real API key.

Usage:
    .venv/bin/python tests/run_real_paper_tests.py <pdf> [<pdf> ...]
"""

import json
import os
import re
import sys
import time
from io import BytesIO

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from docx import Document

from src.llm_client import plan_batches, review_all
from src.pdf_extract import extract_text_from_bytes
from src.prompts import collect_prompts, paragraph_key
from src.report import aggregate_results, build_docx, generate_overall_summary
from src.segmentation import count_paragraphs, split_into_sections

CANNED = json.dumps(
    {
        "issues": [
            {
                "issue": "Evaluation placeholder issue.",
                "severity": "medium",
                "explanation": "Returned by the fake client for pipeline testing.",
                "suggested_fix": "No fix, this is a test double.",
            }
        ],
        "strengths": ["Evaluation placeholder strength."],
    }
)


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
        if "overall summary" in messages[0]["content"].lower():
            return FakeResponse("Fake overall summary for pipeline testing.")
        user_text = messages[1]["content"]
        if "Review each item below independently" in user_text:
            ids = re.findall(r"ID: (s\d+_p\d+)", user_text)
            return FakeResponse(
                json.dumps(
                    {item_id: json.loads(CANNED) for item_id in ids}
                )
            )
        return FakeResponse(CANNED)


class FakeChat:
    def __init__(self, client):
        self.completions = FakeCompletions(client)


class FakeClient:
    def __init__(self):
        self.calls = []
        self.chat = FakeChat(self)


def run_one(path):
    started = time.time()
    with open(path, "rb") as handle:
        data = handle.read()
    extracted = extract_text_from_bytes(data)
    sections = split_into_sections(extracted["pages"])
    prompts = collect_prompts(sections, state={})
    total_paragraphs = count_paragraphs(sections)

    custom_key = paragraph_key(0, 0) if total_paragraphs else None

    pending_items = [
        {
            "key": paragraph_key(section_index, paragraph_index),
            "paragraph_text": paragraph_text,
            "user_prompt": prompts[
                paragraph_key(section_index, paragraph_index)
            ],
        }
        for section_index, section in enumerate(sections)
        for paragraph_index, paragraph_text in enumerate(
            section["paragraphs"]
        )
    ]
    expected_calls = len(plan_batches(pending_items)) + 1

    client = FakeClient()
    results = review_all(
        sections, prompts, api_key="test", client=client
    )
    report = aggregate_results(sections, results)
    summary = generate_overall_summary(report, api_key="test", client=client)
    docx_bytes = build_docx(report, summary, os.path.basename(path))
    document = Document(BytesIO(docx_bytes))
    docx_text = "\n".join(p.text for p in document.paragraphs)

    checks = {
        "pages_match": extracted["page_count"] > 0,
        "text_extracted": sum(len(p) for p in extracted["pages"]) > 500,
        "sections_found": len(sections) >= 1,
        "prompt_per_paragraph": len(prompts) == total_paragraphs,
        "result_per_paragraph": len(results) == total_paragraphs,
        "no_result_errors": report["error_paragraphs"] == 0,
        "issues_aggregated": report["issue_count"] == total_paragraphs,
        "summary_returned": summary.startswith("Fake overall summary"),
        "docx_reopens": "Paper Review Report" in docx_text,
        "model_calls": len(client.calls) == expected_calls,
    }
    return {
        "file": os.path.basename(path),
        "pages": extracted["page_count"],
        "characters": sum(len(p) for p in extracted["pages"]),
        "sections": len(sections),
        "section_titles": [s["title"] for s in sections][:20],
        "paragraphs": total_paragraphs,
        "seconds": round(time.time() - started, 2),
        "checks": checks,
        "all_checks_passed": all(checks.values()),
        "first_section_first_paragraph": (
            sections[0]["paragraphs"][0][:300] if sections else ""
        ),
    }


if __name__ == "__main__":
    summaries = [run_one(path) for path in sys.argv[1:]]
    print(json.dumps(summaries, indent=2, ensure_ascii=False))
