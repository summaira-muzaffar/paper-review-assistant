"""Paper Review Assistant.

The full tool: PDF upload, text extraction, section and
paragraph splitting, the per paragraph prompt panel, LLM
integration, and the final report with DOCX export are all in
place. The sidebar holds the language toggle, the API settings
(key, base URL, model), a Test API connection button, and the
review output language. Before a review run starts, the
settings are validated and the provider connection is checked,
so a wrong key or a mixed provider set fails once, in plain
language, instead of once per paragraph. The connection test
ends with one tiny real review call, so a key whose provider
quota is already spent fails here, once, instead of on every
paragraph. Batch runs use an adaptive rate limit policy: a
limited batch is retried, then split into smaller batches,
and only a paragraph that is still refused is saved for
later while the run moves on. Progress is saved to disk after every
paragraph, so a closed tab, a sleeping laptop, or a restarted
app can never wipe a half done run: uploading the same paper
again restores its finished paragraphs. After a run, the
report area shows the key numbers, an optional model written
overall summary, the strengths, the issues grouped by section,
and a download button for the DOCX report.
"""

import datetime
from pathlib import Path
from urllib.parse import urlparse

import streamlit as st

from src.i18n import get_text
from src.llm_client import (
    DEFAULT_BASE_URL,
    DEFAULT_MODEL,
    LlmError,
    preflight_check,
    review_all,
    validate_settings,
)
from src.progress_store import (
    delete_progress,
    load_progress,
    paper_id_for_text,
    save_progress,
)
from src.report import aggregate_results, build_docx, generate_overall_summary
from src.pdf_extract import PdfExtractionError, extract_text_from_bytes
from src.prompts import (
    collect_prompts,
    get_default_prompt,
    paragraph_key,
    prompt_widget_key,
)
from src.segmentation import count_paragraphs, split_into_sections

BASE_DIR = Path(__file__).parent

APP_CSS = """
<style>
.block-container { max-width: 1100px; padding-top: 2rem; }
.app-header {
    background-color: #1F4E79;
    color: #FFFFFF;
    padding: 1.4rem 1.6rem;
    border-radius: 10px;
    margin-bottom: 1.2rem;
}
.app-header h1 { color: #FFFFFF; font-size: 1.9rem; margin: 0 0 0.4rem 0; }
.app-header p { color: #D9E6F2; margin: 0; font-size: 1.0rem; }
</style>
"""


def language_name(code):
    return "English" if code == "en" else "中文"


def prompt_snapshot():
    """The user's current paragraph prompts, for progress saving."""
    return {
        key: st.session_state[key]
        for key in list(st.session_state)
        if key.startswith("prompt_")
    }


def save_snapshot():
    """Save the current paper's progress to disk.

    Called after every reviewed paragraph, after a run, and
    after the overall summary is generated, so the saved file
    is never more than one paragraph behind the screen. The
    API key is never part of the snapshot. A save failure is
    recorded in a flag and never raised: saving protects the
    review, it must never be able to crash it.
    """
    paper_id = st.session_state.get("paper_id")
    results = st.session_state.get("review_results")
    if not paper_id or not results:
        return
    sections = st.session_state.get("sections", [])
    try:
        saved_ok = save_progress(
            BASE_DIR,
            paper_id,
            {
                "paper_name": st.session_state.get("paper_name", "paper.pdf"),
                "paragraph_count": count_paragraphs(sections),
                "saved_at": datetime.datetime.now().isoformat(
                    timespec="seconds"
                ),
                "results": results,
                "overall_summary": st.session_state.get(
                    "overall_summary", ""
                ),
                "run_info": st.session_state.get("run_info", ""),
                "prompts": prompt_snapshot(),
            },
        )
    except Exception:
        saved_ok = False
    if not saved_ok:
        st.session_state["progress_save_failed"] = True


def clear_saved_progress():
    """Button callback: forget this paper's saved progress."""
    paper_id = st.session_state.get("paper_id")
    if paper_id:
        delete_progress(BASE_DIR, paper_id)
    st.session_state.pop("review_results", None)
    st.session_state.pop("overall_summary", None)
    st.session_state.pop("run_info", None)
    st.session_state.pop("restored_reviewed", None)
    st.session_state.pop("progress_save_failed", None)


def show_review_section(language, sections, settings):
    """Run the review for every paragraph and show the results."""
    st.subheader(get_text("review_results_heading", language))
    if st.button(get_text("run_review", language), key="run_review_button"):
        api_key = settings["api_key"].strip()
        base_url = settings["base_url"].strip()
        model = settings["model"].strip() or DEFAULT_MODEL
        problems = validate_settings(api_key, base_url, model)
        if problems:
            for problem in problems:
                st.error(problem)
        else:
            with st.spinner(get_text("checking_connection", language)):
                ok, message = preflight_check(api_key, base_url, model)
            if not ok:
                st.error(message)
            else:
                st.session_state.pop("overall_summary", None)
                total_paragraphs = sum(
                    len(section["paragraphs"]) for section in sections
                )
                progress_bar = st.progress(
                    0.0,
                    text=(
                        f"{get_text('reviewing', language)} "
                        f"0 of {total_paragraphs} (0%)"
                    ),
                )
                status_box = st.empty()

                def update_progress(done, total):
                    percent = round(done / total * 100) if total else 0
                    progress_bar.progress(
                        done / total,
                        text=(
                            f"{get_text('reviewing', language)} "
                            f"{done} of {total} ({percent}%)"
                        ),
                    )

                def show_status(message):
                    status_box.info(message)

                prompts = collect_prompts(sections, st.session_state)
                working_results = dict(
                    st.session_state.get("review_results") or {}
                )

                def save_paragraph(key, result):
                    working_results[key] = result
                    st.session_state["review_results"] = working_results
                    save_snapshot()

                results = review_all(
                    sections,
                    prompts,
                    api_key=api_key,
                    base_url=base_url,
                    model=model,
                    output_language=settings["review_language"],
                    progress_callback=update_progress,
                    result_callback=save_paragraph,
                    existing_results=st.session_state.get("review_results"),
                    status_callback=show_status,
                )
                status_box.empty()
                st.session_state["review_results"] = results
                st.session_state.pop("restored_reviewed", None)
                host = urlparse(base_url).netloc or base_url
                run_time = datetime.datetime.now().strftime("%H:%M")
                st.session_state["run_info"] = (
                    f"{model} @ {host}, {run_time}"
                )
                save_snapshot()
                failed_count = sum(
                    1 for result in results.values() if "error" in result
                )
                saved_later_count = sum(
                    1 for result in results.values() if result.get("rate_limited")
                )
                other_failed = failed_count - saved_later_count
                reviewed_count = len(results) - failed_count
                progress_bar.progress(
                    1.0,
                    text=(
                        f"{get_text('review_done', language)}: "
                        f"{reviewed_count} of {len(results)} "
                        "paragraphs reviewed"
                    ),
                )
                if not failed_count:
                    st.success(
                        "All "
                        f"{reviewed_count} paragraphs reviewed successfully."
                    )
                else:
                    parts = [
                        f"{reviewed_count} of {len(results)} paragraphs "
                        "reviewed."
                    ]
                    if saved_later_count:
                        parts.append(
                            f"{saved_later_count} are saved for later "
                            "and will finish when you press Run review "
                            "again."
                        )
                    if other_failed:
                        parts.append(
                            f"{other_failed} could not be reviewed; "
                            "the reason is shown under each one below."
                        )
                    if other_failed:
                        st.warning(" ".join(parts))
                    else:
                        st.info(" ".join(parts))

    results = st.session_state.get("review_results")
    if not results:
        st.caption(get_text("no_results", language))
        return
    run_info = st.session_state.get("run_info")
    if run_info:
        st.caption(f"{get_text('results_from', language)}: {run_info}")
    if st.session_state.get("progress_save_failed"):
        st.warning(
            "Progress could not be saved to disk on this "
            "computer, so keep this tab open until the run "
            "finishes. The review itself is not affected."
        )
    else:
        st.caption(
            "Progress is saved automatically on this computer. If "
            "the page reloads or the laptop sleeps, upload the same "
            "paper and the finished paragraphs come back."
        )
    st.button(
        "Start fresh for this paper",
        key="start_fresh_button",
        on_click=clear_saved_progress,
    )

    for section_index, section in enumerate(sections):
        st.markdown(f"### {section['title']}")
        for paragraph_index, paragraph in enumerate(section["paragraphs"]):
            key = paragraph_key(section_index, paragraph_index)
            result = results.get(key)
            if result is None:
                continue
            st.markdown(
                f"**{get_text('paragraph', language)} {paragraph_index + 1}**"
            )
            if "error" in result:
                if result.get("rate_limited"):
                    st.warning(result["error"])
                else:
                    st.error(
                        f"{get_text('error', language)}: {result['error']}"
                    )
                continue
            if result["strengths"]:
                st.markdown(f"*{get_text('strengths', language)}*")
                for strength in result["strengths"]:
                    st.markdown(f"- {strength}")
            if not result["issues"]:
                st.success(get_text("no_issues", language))
            for item in result["issues"]:
                st.markdown(
                    f"**{get_text('issue', language)}: {item['issue']}** "
                    f"({get_text('severity', language)}: {item['severity']})"
                )
                if item["explanation"]:
                    st.write(
                        f"{get_text('explanation', language)}: "
                        f"{item['explanation']}"
                    )
                if item["suggested_fix"]:
                    st.write(
                        f"{get_text('suggested_fix', language)}: "
                        f"{item['suggested_fix']}"
                    )


def show_report_section(language, sections, settings):
    """Show the aggregated final report and the DOCX download."""
    results = st.session_state.get("review_results")
    if not results:
        return
    report = aggregate_results(sections, results)
    st.subheader(get_text("report_heading", language))
    if report["reviewed_paragraphs"] == 0 and report["error_paragraphs"]:
        st.warning(
            "Nothing has been reviewed yet, so this report is "
            "empty. Every paragraph hit the provider limit on "
            "the last run. Wait for the limit to reset, or "
            "switch the sidebar to a different provider set, "
            "then press Run review again. The saved paragraphs "
            "finish automatically."
        )
    elif report["error_paragraphs"]:
        st.warning(
            f"{report['reviewed_paragraphs']} of "
            f"{report['total_paragraphs']} paragraphs reviewed. "
            f"{report['error_paragraphs']} are saved for later "
            "and will finish on the next Run review, after the "
            "provider limit resets."
        )
    col_issues, col_sections, col_paragraphs = st.columns(3)
    col_issues.metric(get_text("total_issues", language), report["issue_count"])
    col_sections.metric(get_text("section_count", language), len(sections))
    col_paragraphs.metric(
        get_text("paragraph_count", language), report["total_paragraphs"]
    )
    counts = report["severity_counts"]
    st.write(
        f"{get_text('severity', language)}: "
        f"high {counts['high']}, medium {counts['medium']}, "
        f"low {counts['low']}"
    )

    st.markdown(f"### {get_text('overall_summary', language)}")
    summary_text = st.session_state.get("overall_summary", "")
    if summary_text:
        st.write(summary_text)
    if st.button(
        get_text("generate_summary", language), key="generate_summary_button"
    ):
        if not settings["api_key"].strip():
            st.warning(get_text("missing_api_key", language))
        else:
            try:
                summary_text = generate_overall_summary(
                    report,
                    api_key=settings["api_key"].strip(),
                    base_url=settings["base_url"].strip(),
                    model=settings["model"].strip() or DEFAULT_MODEL,
                    output_language=settings["review_language"],
                )
                st.session_state["overall_summary"] = summary_text
                save_snapshot()
                st.write(summary_text)
            except LlmError as error:
                st.error(f"{get_text('error', language)}: {error}")

    if report["strengths"]:
        st.markdown(f"### {get_text('strengths', language)}")
        for item in report["strengths"]:
            st.markdown(f"- [{item['section']}] {item['text']}")

    st.markdown(f"### {get_text('issues', language)}")
    for section in report["sections"]:
        section_issues = [
            paragraph
            for paragraph in section["paragraphs"]
            if paragraph["result"]
            and "error" not in paragraph["result"]
            and paragraph["result"].get("issues")
        ]
        if not section_issues:
            continue
        with st.expander(section["title"]):
            for paragraph in section_issues:
                st.markdown(
                    f"**{get_text('paragraph', language)} "
                    f"{paragraph['number']}**"
                )
                for item in paragraph["result"]["issues"]:
                    st.markdown(
                        f"- **{item['issue']}** "
                        f"({item['severity']}): {item['explanation']} "
                        f"{item['suggested_fix']}"
                    )

    paper_name = st.session_state.get("paper_name", "paper.pdf")
    base_name = paper_name.rsplit(".", 1)[0]
    docx_bytes = build_docx(report, summary_text, paper_name)
    st.download_button(
        get_text("download_docx", language),
        data=docx_bytes,
        file_name=f"{base_name}_review.docx",
        mime=(
            "application/vnd.openxmlformats-officedocument."
            "wordprocessingml.document"
        ),
        key="download_docx_button",
    )


def show_upload_section(language, settings):
    """Upload one PDF, extract its text, and show the result."""
    st.subheader(get_text("upload_heading", language))
    uploaded = st.file_uploader(
        get_text("upload_prompt", language),
        type=["pdf"],
        key="paper_upload",
    )
    if uploaded is None:
        return

    if st.session_state.get("paper_file_id") != uploaded.file_id:
        for key in [k for k in st.session_state if k.startswith("prompt_")]:
            del st.session_state[key]
        st.session_state.pop("review_results", None)
        st.session_state.pop("overall_summary", None)
        st.session_state.pop("run_info", None)
        st.session_state.pop("restored_reviewed", None)
        st.session_state.pop("progress_save_failed", None)
        st.session_state.pop("paper_id", None)
        try:
            result = extract_text_from_bytes(uploaded.getvalue())
        except PdfExtractionError as error:
            st.session_state.pop("paper", None)
            st.session_state.pop("sections", None)
            st.session_state.pop("paper_file_id", None)
            st.error(f"{get_text('extraction_failed', language)}: {error}")
            return
        st.session_state["paper"] = result
        st.session_state["sections"] = split_into_sections(result["pages"])
        st.session_state["paper_file_id"] = uploaded.file_id
        st.session_state["paper_name"] = uploaded.name
        paper_id = paper_id_for_text(result["text"])
        st.session_state["paper_id"] = paper_id
        saved = load_progress(BASE_DIR, paper_id)
        if saved and saved.get("paragraph_count") == count_paragraphs(
            st.session_state["sections"]
        ):
            restored = saved["results"]
            st.session_state["review_results"] = restored
            if saved.get("overall_summary"):
                st.session_state["overall_summary"] = saved["overall_summary"]
            if saved.get("run_info"):
                st.session_state["run_info"] = saved["run_info"]
            for widget_key, text in (saved.get("prompts") or {}).items():
                if widget_key.startswith("prompt_"):
                    st.session_state[widget_key] = text
            st.session_state["restored_reviewed"] = sum(
                1 for item in restored.values() if "error" not in item
            )

    paper = st.session_state["paper"]
    plain_text = "\n".join(paper["pages"])
    if not plain_text.strip():
        st.warning(get_text("extraction_empty", language))
        return

    st.success(
        f"{get_text('file_uploaded', language)}: "
        f"{st.session_state['paper_name']}"
    )
    col_pages, col_chars, col_words = st.columns(3)
    col_pages.metric(get_text("page_count", language), paper["page_count"])
    col_chars.metric(get_text("character_count", language), len(plain_text))
    col_words.metric(
        get_text("word_count", language), len(plain_text.split())
    )
    st.text_area(
        get_text("full_text", language),
        value=paper["text"],
        height=450,
        disabled=True,
    )
    sections = st.session_state.get("sections", [])
    restored_reviewed = st.session_state.get("restored_reviewed")
    if restored_reviewed:
        st.info(
            f"Saved progress restored: {restored_reviewed} of "
            f"{count_paragraphs(sections)} paragraphs were already "
            "reviewed for this paper. Press Run review to finish "
            "the rest. Nothing was lost."
        )
    show_structure_section(language, sections)
    if sections:
        show_review_section(language, sections, settings)
        show_report_section(language, sections, settings)


def reset_prompt(widget_key, default_text):
    """Button callback: restore one paragraph prompt to default."""
    st.session_state[widget_key] = default_text


def show_structure_section(language, sections):
    """Show sections with numbered paragraphs and prompt editors."""
    st.subheader(get_text("structure_heading", language))
    st.caption(get_text("prompts_note", language))
    col_sections, col_paragraphs = st.columns(2)
    col_sections.metric(get_text("section_count", language), len(sections))
    col_paragraphs.metric(
        get_text("paragraph_count", language), count_paragraphs(sections)
    )
    for section_index, section in enumerate(sections):
        title = section["title"]
        count = len(section["paragraphs"])
        default_prompt = get_default_prompt(title)
        with st.expander(f"{title} ({count})"):
            for paragraph_index, paragraph in enumerate(section["paragraphs"]):
                number = paragraph_index + 1
                widget_key = prompt_widget_key(section_index, paragraph_index)
                if widget_key not in st.session_state:
                    st.session_state[widget_key] = default_prompt
                st.markdown(f"**{get_text('paragraph', language)} {number}**")
                st.write(paragraph)
                st.text_area(
                    get_text("review_prompt", language),
                    key=widget_key,
                    height=140,
                )
                if st.session_state[widget_key] != default_prompt:
                    st.caption(get_text("custom_prompt", language))
                st.button(
                    get_text("reset_prompt", language),
                    key=f"reset_{widget_key}",
                    on_click=reset_prompt,
                    args=(widget_key, default_prompt),
                )


def main():
    st.set_page_config(
        page_title="Paper Review Assistant",
        layout="wide",
        initial_sidebar_state="expanded",
    )
    st.markdown(APP_CSS, unsafe_allow_html=True)

    with st.sidebar:
        language = st.selectbox(
            get_text("language_label"),
            options=["en", "zh"],
            format_func=language_name,
            key="ui_language",
        )
        st.subheader(get_text("settings", language))
        settings = {
            "api_key": st.text_input(
                get_text("api_key", language),
                type="password",
                help=get_text("api_key_help", language),
                key="api_key_input",
            ),
            "base_url": st.text_input(
                get_text("api_base_url", language),
                value=DEFAULT_BASE_URL,
                key="base_url_input",
            ),
            "model": st.text_input(
                get_text("model_name", language),
                value=DEFAULT_MODEL,
                key="model_input",
            ),
            "review_language": st.selectbox(
                get_text("review_language", language),
                options=["en", "zh"],
                format_func=language_name,
                key="review_language_select",
            ),
        }
        st.caption(
            "Final build: the connection test verifies a real "
            "review call, rate limits are handled adaptively, "
            "and progress is saved automatically."
        )
        if st.button(
            get_text("test_connection", language), key="test_connection_button"
        ):
            with st.spinner(get_text("checking_connection", language)):
                ok, message = preflight_check(
                    settings["api_key"].strip(),
                    settings["base_url"].strip(),
                    settings["model"].strip() or DEFAULT_MODEL,
                )
            if ok:
                st.success(message)
            else:
                st.error(message)

    st.markdown(
        '<div class="app-header">'
        f"<h1>{get_text('app_title', language)}</h1>"
        f"<p>{get_text('app_tagline', language)}</p>"
        "</div>",
        unsafe_allow_html=True,
    )
    show_upload_section(language, settings)


if __name__ == "__main__":
    main()
