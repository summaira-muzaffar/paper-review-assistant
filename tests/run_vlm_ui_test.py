"""End to end UI test of the Paper Review Assistant on VLM.pdf.

Runs the real Streamlit app through AppTest: sidebar settings filled
with Summaira's Groq configuration values, the real VLM.pdf uploaded
through the uploader, Run review clicked, summary generated, report
checked. Only the network transport is faked (a stand-in OpenAI
client), because no real API key exists in this environment.
"""

import json
import os
import re
import sys
from types import SimpleNamespace

sys.path.insert(0, os.path.expanduser("~/workspace/paper-review-assistant"))
os.chdir(os.path.expanduser("~/workspace/paper-review-assistant"))

# Start clean: a saved progress file from an earlier run would
# be restored on upload (that is its job), which would make
# this test's call counts meaningless.
import glob
import shutil

shutil.rmtree(
    os.path.expanduser(
        "~/workspace/paper-review-assistant/.review_progress"
    ),
    ignore_errors=True,
)

CALLS = {"review": 0, "summary": 0}

CANNED_REVIEW = json.dumps(
    {
        "issues": [
            {
                "issue": "The paragraph states a claim without citing supporting evidence.",
                "severity": "medium",
                "explanation": "Readers cannot verify the claim from the text given.",
                "suggested_fix": "Add the citation or the measured result that supports it.",
            }
        ],
        "strengths": ["The paragraph is clearly written and easy to follow."],
    }
)
CANNED_SUMMARY = (
    "Overall, the paper is clearly structured and the method is described "
    "in a logical order. The most common issue is claims that need direct "
    "support from citations or reported numbers. Addressing those points "
    "and tightening a few long paragraphs would strengthen the paper."
)


class FakeCompletions:
    def create(self, model=None, messages=None, temperature=None):
        joined = " ".join(m.get("content", "") for m in (messages or []))
        if "Review results:" in joined:
            CALLS["summary"] += 1
            content = CANNED_SUMMARY
        elif "Review each item below independently" in joined:
            CALLS["review"] += 1
            ids = re.findall(r"ID: (s\d+_p\d+)", joined)
            content = json.dumps(
                {
                    item_id: json.loads(CANNED_REVIEW)
                    for item_id in ids
                }
            )
        else:
            CALLS["review"] += 1
            content = CANNED_REVIEW
        return SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content=content))]
        )


class FakeOpenAI:
    def __init__(self, api_key=None, base_url=None):
        self.chat = SimpleNamespace(completions=FakeCompletions())
        self.models = SimpleNamespace(
            list=lambda: SimpleNamespace(
                data=[SimpleNamespace(id="openai/gpt-oss-120b")]
            )
        )


import openai

openai.OpenAI = FakeOpenAI

from streamlit.testing.v1 import AppTest

PDF_PATH = (
    sys.argv[1]
    if len(sys.argv) > 1
    else os.path.expanduser("~/workspace/user/files/VLM.pdf")
)
with open(PDF_PATH, "rb") as handle:
    pdf_bytes = handle.read()

APP_PATH = os.path.expanduser("~/workspace/paper-review-assistant/app.py")
at = AppTest.from_file(APP_PATH).run(timeout=60)
assert not at.exception, list(at.exception)

# Sidebar settings: her Groq configuration, typed into the real fields.
at.text_input[0].set_value("gsk_test_key_not_real")
at.text_input[1].set_value("https://api.groq.com/openai/v1")
at.text_input[2].set_value("openai/gpt-oss-120b")
at.run(timeout=60)
assert not at.exception, list(at.exception)
print("SETTINGS_OK base:", at.text_input[1].value, "| model:", at.text_input[2].value)

# Upload the real paper through the real uploader.
at.file_uploader[0].set_value(("VLM.pdf", pdf_bytes, "application/pdf"))
at.run(timeout=60)
assert not at.exception, list(at.exception)

metric_values = [m.value for m in at.metric]
print("UPLOAD_METRICS:", metric_values)
assert "13" in metric_values, metric_values

expander_labels = [e.label for e in at.expander]
print("SECTIONS_IN_UI:", len(expander_labels), expander_labels)
assert len(expander_labels) == 11, expander_labels
prompt_boxes = [
    ta for ta in at.text_area if str(getattr(ta, "key", "")).startswith("prompt_")
]
print("TEXT_AREAS:", len(at.text_area), "| PROMPT_BOXES:", len(prompt_boxes))
assert len(prompt_boxes) == 38, len(prompt_boxes)


def click_button_by_key(app_test, key):
    for button in app_test.button:
        if getattr(button, "key", None) == key:
            return button.click().run(timeout=600)
    raise AssertionError(f"button with key {key} not found")


# The Test API connection button proves the settings before any run.
at = click_button_by_key(at, "test_connection_button")
assert not at.exception, list(at.exception)
connection_texts = [s.value for s in at.success]
print("CONNECTION_TEST:", connection_texts)
assert any("Connection OK" in s for s in connection_texts), connection_texts


at = click_button_by_key(at, "run_review_button")
assert not at.exception, list(at.exception)
success_texts = [s.value for s in at.success]
print("SUCCESS_BANNERS:", success_texts)
assert any(
    "reviewed successfully" in s.lower() for s in success_texts
), success_texts

results = at.session_state["review_results"]
total = len(results)
errors = [k for k, v in results.items() if "error" in v]
print("RESULTS:", total, "| errors:", len(errors), "| model calls:", CALLS)
assert total == 38, total
assert not errors, errors
# Paragraphs now travel in batches: far fewer calls than 38,
# one per batch, with no paragraph reviewed twice.
assert 1 <= CALLS["review"] <= 12, CALLS

# Report metrics rendered: total issues, sections, paragraphs.
report_metrics = [m.value for m in at.metric]
print("REPORT_METRICS:", report_metrics)
assert "38" in report_metrics and "11" in report_metrics, report_metrics

# DOCX download button present.
assert len(at.download_button) >= 1, "no download button"
print("DOWNLOAD_BUTTON_OK label:", at.download_button[0].label)

# Generate the overall summary through the real button.
at = click_button_by_key(at, "generate_summary_button")
assert not at.exception, list(at.exception)
summary = at.session_state.get("overall_summary", "")
print("SUMMARY_CALLS:", CALLS["summary"], "| SUMMARY_LEN:", len(summary))
assert CALLS["summary"] == 1, CALLS
assert summary.startswith("Overall,"), summary[:80]

# Progress was saved to disk during the run: exactly one paper
# file, holding all 38 results and the generated summary. This
# is what brings a half done run back after a reload or sleep.
save_files = glob.glob(
    os.path.expanduser(
        "~/workspace/paper-review-assistant/.review_progress/*.json"
    )
)
assert len(save_files) == 1, save_files
with open(save_files[0], encoding="utf-8") as handle:
    saved = json.load(handle)
assert len(saved["results"]) == 38, len(saved["results"])
assert saved["overall_summary"].startswith("Overall,")
print("PROGRESS_SAVE_OK file:", os.path.basename(save_files[0]))

print("VLM_E2E_UI_TEST_PASSED")
