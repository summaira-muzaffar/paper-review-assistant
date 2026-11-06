"""Final report building and export.

Built in Step 6.

Job: turn the per paragraph review results from Step 5 into one
report. The report has an overall summary (written by the model
in a second pass over a digest of all results), the key numbers,
the strengths collected across the paper, and the issues grouped
by section with their explanations and suggested fixes. The
report can be downloaded as a DOCX file.

The aggregation in this module is pure counting and grouping,
with no model involved, so it can be tested exactly. Only the
overall summary uses the model, through the same OpenAI
compatible client pattern as Step 5.
"""

from io import BytesIO

from docx import Document

from src.llm_client import (
    DEFAULT_BASE_URL,
    DEFAULT_MODEL,
    DEFAULT_RETRY_DELAYS,
    LlmError,
    call_with_retry,
    friendly_error,
    status_code_of,
)
from src.prompts import paragraph_key

SUMMARY_SYSTEM_PROMPT = (
    "You write the overall summary for an academic paper review "
    "report. You are given the structured review results for every "
    "paragraph of a paper. Write a clear summary of five to eight "
    "sentences: what the paper does well, the most important "
    "problems in order of severity, and what the author should "
    "fix first. Write in plain prose, with no lists and no JSON."
)


def aggregate_results(sections, results):
    """Aggregate per paragraph results into report data.

    Returns a dictionary with totals, severity counts, the flat
    list of strengths with their section titles, and the section
    structure paired with each paragraph's result.
    """
    severity_counts = {"high": 0, "medium": 0, "low": 0}
    strengths = []
    issue_count = 0
    reviewed = 0
    errors = 0
    grouped_sections = []

    for section_index, section in enumerate(sections):
        grouped_paragraphs = []
        for paragraph_index, paragraph_text in enumerate(section["paragraphs"]):
            key = paragraph_key(section_index, paragraph_index)
            result = results.get(key)
            grouped_paragraphs.append(
                {
                    "number": paragraph_index + 1,
                    "text": paragraph_text,
                    "result": result,
                }
            )
            if result is None:
                continue
            if "error" in result:
                errors += 1
                continue
            reviewed += 1
            for item in result.get("issues", []):
                issue_count += 1
                severity = item.get("severity", "medium")
                if severity in severity_counts:
                    severity_counts[severity] += 1
            for strength in result.get("strengths", []):
                strengths.append(
                    {"section": section["title"], "text": strength}
                )
        grouped_sections.append(
            {"title": section["title"], "paragraphs": grouped_paragraphs}
        )

    total = sum(len(section["paragraphs"]) for section in sections)
    return {
        "total_paragraphs": total,
        "reviewed_paragraphs": reviewed,
        "error_paragraphs": errors,
        "issue_count": issue_count,
        "severity_counts": severity_counts,
        "strengths": strengths,
        "sections": grouped_sections,
    }


# The digest goes out in one single model call, so its size must
# stay bounded even when a review produces hundreds of findings.
# Live use on 5 November 2026 proved the need: a digest of 233
# findings was about 19,500 tokens, and Groq's free tier rejected
# the summary call with error 413 (tokens per minute limit 8,000
# on openai/gpt-oss-120b). The budget below keeps the whole
# request safely under that class of limit, and the severity
# ordering means what is left out is the least important first.
MAX_DIGEST_CHARS = 16000
SEVERITY_ORDER = {"high": 0, "medium": 1, "low": 2}


def build_summary_digest(report):
    """Build the compact text digest sent to the model for the
    overall summary.

    One line per finding, most important first: a totals header,
    then issues in severity order (high, medium, low), then
    strengths. Lines are included until the character budget is
    reached. Anything left out is counted in a closing note, so
    the model knows the digest was trimmed, and the totals header
    still carries the exact full counts either way.
    """
    counts = report["severity_counts"]
    header = (
        f"TOTALS: {report['reviewed_paragraphs']} of "
        f"{report['total_paragraphs']} paragraphs reviewed, "
        f"{report['issue_count']} issues (high {counts['high']}, "
        f"medium {counts['medium']}, low {counts['low']}), "
        f"{len(report['strengths'])} strengths."
    )
    issue_lines = []
    strength_lines = []
    for section in report["sections"]:
        for paragraph in section["paragraphs"]:
            result = paragraph["result"]
            if not result or "error" in result:
                continue
            for item in result.get("issues", []):
                severity = item.get("severity", "medium")
                issue_lines.append(
                    (
                        SEVERITY_ORDER.get(severity, 1),
                        f"ISSUE ({severity}) [{section['title']}] "
                        f"{item.get('issue', '')}: "
                        f"{item.get('explanation', '')[:220]}",
                    )
                )
            for strength in result.get("strengths", []):
                strength_lines.append(
                    f"STRENGTH [{section['title']}] {strength}"
                )
    issue_lines.sort(key=lambda pair: pair[0])
    ordered = [line for _, line in issue_lines] + strength_lines

    lines = [header]
    used = len(header)
    included = 0
    for line in ordered:
        if used + len(line) + 1 > MAX_DIGEST_CHARS:
            continue
        lines.append(line)
        used += len(line) + 1
        included += 1
    omitted = len(ordered) - included
    if omitted:
        lines.append(
            f"NOTE: {omitted} of {len(ordered)} finding lines were "
            "left out of this digest to fit the model request size "
            "limit. The totals above are exact and complete, and "
            "the lines included are the highest severity first."
        )
    return "\n".join(lines)


def generate_overall_summary(
    report,
    api_key,
    base_url=DEFAULT_BASE_URL,
    model=DEFAULT_MODEL,
    output_language="en",
    client=None,
    retry_delays=DEFAULT_RETRY_DELAYS,
    sleep=None,
):
    """Generate the overall summary with one model call.

    The digest of all paragraph results is sent once. Returns the
    summary as plain text. Raises LlmError when the call fails.
    """
    if client is None:
        if not api_key:
            raise LlmError("No API key was provided.")
        from openai import OpenAI

        client = OpenAI(api_key=api_key, base_url=base_url or None)
    digest = build_summary_digest(report)
    language_line = (
        "Write the summary in Simplified Chinese."
        if output_language == "zh"
        else "Write the summary in English."
    )
    messages = [
        {"role": "system", "content": SUMMARY_SYSTEM_PROMPT},
        {
            "role": "user",
            "content": f"Review results:\n{digest}\n\n{language_line}",
        },
    ]
    def call():
        return client.chat.completions.create(
            model=model, messages=messages, temperature=0.2
        )

    try:
        response = call_with_retry(call, retry_delays=retry_delays, sleep=sleep)
    except Exception as error:
        raise LlmError(
            friendly_error(error), status_code=status_code_of(error)
        ) from error
    return (response.choices[0].message.content or "").strip()


def build_docx(report, summary_text, paper_name):
    """Build the downloadable DOCX report and return its bytes."""
    document = Document()
    document.add_heading("Paper Review Report", level=0)
    document.add_paragraph(f"Paper: {paper_name}")
    counts = report["severity_counts"]
    document.add_paragraph(
        f"Paragraphs reviewed: {report['reviewed_paragraphs']} of "
        f"{report['total_paragraphs']}. Total issues: "
        f"{report['issue_count']} (high: {counts['high']}, medium: "
        f"{counts['medium']}, low: {counts['low']})."
    )
    if report["error_paragraphs"]:
        document.add_paragraph(
            f"Paragraphs that could not be reviewed: "
            f"{report['error_paragraphs']}."
        )

    document.add_heading("Overall Summary", level=1)
    document.add_paragraph(
        summary_text or "The overall summary was not generated."
    )

    document.add_heading("Strengths", level=1)
    if report["strengths"]:
        for item in report["strengths"]:
            document.add_paragraph(
                f"[{item['section']}] {item['text']}", style="List Bullet"
            )
    else:
        document.add_paragraph("No strengths were recorded.")

    document.add_heading("Issues by Section", level=1)
    for section in report["sections"]:
        document.add_heading(section["title"], level=2)
        for paragraph in section["paragraphs"]:
            result = paragraph["result"]
            document.add_heading(
                f"Paragraph {paragraph['number']}", level=3
            )
            if result is None:
                document.add_paragraph("Not reviewed.")
                continue
            if "error" in result:
                document.add_paragraph(f"Error: {result['error']}")
                continue
            if not result.get("issues"):
                document.add_paragraph("No issues found.")
            for item in result.get("issues", []):
                line = document.add_paragraph()
                run = line.add_run(f"Issue: {item.get('issue', '')} ")
                run.bold = True
                line.add_run(
                    f"(severity: {item.get('severity', 'medium')})"
                )
                if item.get("explanation"):
                    document.add_paragraph(
                        f"Explanation: {item['explanation']}"
                    )
                if item.get("suggested_fix"):
                    document.add_paragraph(
                        f"Suggested fix: {item['suggested_fix']}"
                    )

    buffer = BytesIO()
    document.save(buffer)
    return buffer.getvalue()
