# Build Log, Paper Review Assistant

This log records every build step: the date, what was done, how it was done, any decision made and why, and the test result. It exists so the whole project can be explained later, step by step, from the record and not from memory.

## Project background

- Builder: Summaira Muzaffar, BS Computer Science 2026, Sir Syed CASE Institute of Technology, Pakistan, CGPA 3.30. Research Assistant at CARE, dotAI department, where she builds AI applications and handles testing and bug fixing.
- Relevant past work: LATEXIFY, an AI research paper formatting system and her final year project. ChartQA, a vision language benchmark with a fine tuned model. An image quality enhancer using Real ESRGAN.
- Why this project exists: Professor Tao Huanjie, School of Computer Science, Northwestern Polytechnical University, Xi'an, China, replied to Summaira's email about supervising her master's under the Chinese Government Scholarship. He sent assessment tasks and wrote, translated: "The assessment questions are attached. Choose any one, complete it, and contact me."
- Chosen task: task 3, the LLM based document and paper review auto generation tool.
- Task description, translated: academic paper review and annotation face low efficiency and uneven quality. This project uses the deep understanding ability of a large language model to automatically complete full text analysis of a paper, problem identification, and generation of revision suggestions, turning frontier AI technology into a practical academic assistance tool.
- Hard requirement 1: the tool must have a software interface.
- Hard requirement 2: the user must be able to set their own prompts for each paragraph.
- Contact rule: no further contact with Professor Tao until the finished work is ready. Summaira has already thanked him.
- Working method: strictly step by step, in a fixed order. Each step is explained before it is built, tested before the next step starts, and logged here after it is done. No extra features beyond the task requirements.

## Build steps

1. Project setup and folder structure
2. PDF upload and text extraction
3. Section and paragraph splitting
4. Prompt panel with editable per paragraph prompts
5. LLM integration
6. Final report view and export
7. Testing on real papers
8. GitHub repo with README and screenshots

---

## Step 1, Project setup and folder structure

Date: 5 November 2026

What was done:
- Created the project folder, paper-review-assistant, in the workspace.
- Created the folder structure listed below.
- Created app.py as the Streamlit entry point. In Step 1 it only shows the project title, a one line description, and the Step 1 status message. No upload or review feature was added.
- Created one placeholder module in src for each later step. Each file contains only a plain English note saying which step builds it and what its job will be. No feature code was written early.
- Created requirements.txt, README.md, and .gitignore.

How it was done:
- Folders were created first, then the files were written one by one into their correct places.
- The src modules were kept separate on purpose, one file per job, instead of putting everything in app.py.

Folder structure:

```
paper-review-assistant/
  app.py                  Streamlit entry point, the interface
  README.md               What the project is and how to run it
  BUILD_LOG.md            This file
  requirements.txt        Python libraries the project needs
  .gitignore              Files that must never go to GitHub
  src/
    __init__.py
    pdf_extract.py        Step 2, PDF text extraction with PyMuPDF
    segmentation.py       Step 3, section and paragraph splitting
    prompts.py            Step 4, default and per paragraph prompts
    llm_client.py         Step 5, LLM calls through an OpenAI compatible API
    report.py             Step 6, report building and export
  tests/
    __init__.py           Tests will be added as each step is built
  sample_papers/
    .gitkeep              Real papers for testing go here in Step 7
  screenshots/
    .gitkeep              Interface screenshots go here in Step 8
```

Decisions and why:
- Interface: Streamlit. Decision reason: it builds a clean browser interface in pure Python, fast, with no separate front end code. That directly meets hard requirement 1.
- PDF library: PyMuPDF. Decision reason: reliable text extraction from real academic PDFs, simple API.
- LLM access: an OpenAI compatible API, with the user entering their own API key and base URL in the interface. Decision reason: the same code then works with DeepSeek or a similar service, and no key is ever stored in the code.
- One module per job in src. Decision reason: Summaira must be able to explain this project herself. Small files with one clear job each are easier to explain and easier to test than one large file.
- Nothing beyond Step 1 was built. Decision reason: the working method for this project is one tested step at a time.

Test result:
- Folder check: all folders and files above exist in the correct places. Passed.
- Compile check: python compiled app.py and all files in src with no errors. Passed.
- Import check: all five src modules imported with no errors. Passed.
- Dependency check: a fresh virtual environment was created inside the project and requirements.txt was installed into it. Streamlit 1.66.1, PyMuPDF, openai 3.46.0, and python-docx all imported correctly. Passed.
- App run check: the Streamlit app was run with Streamlit AppTest. It ran with no exception, the title was "Paper Review Assistant", and the status message read "Step 1 complete: project setup. PDF upload comes in Step 2." Passed.
- What was not tested: PDF extraction, prompts, LLM calls, and export. None of them exist yet. They are tested in their own steps.

Step 1 status: complete and tested.
Next step: Step 2, PDF upload and text extraction.

---

## Addendum to Step 1, Interface decision confirmed and theme foundation added

Date: 5 November 2026

What was done:
- Summaira asked whether Streamlit was the right choice for impressing the professor. The options were checked in INTERFACE_DECISION.md (Streamlit polished, Flask with a custom front end, Gradio, React plus FastAPI).
- Summaira decided: keep Streamlit, polished properly.
- Added the polish foundation now, while it is still Step 1 setup: .streamlit/config.toml with the project theme (primary colour deep blue, white background, light grey secondary background, sans serif font, usage stats off), and a styled dark blue header band in app.py using a small block of custom CSS.

Decision and why:
- Professor Tao named no technology. His requirement is a software interface, nothing more specific, so the choice was ours to make well.
- Streamlit polished keeps the project in one language, Python, so Summaira can explain every line. It also keeps our time on review quality, which is the part being assessed, instead of on a second front end stack.
- The real logic stays in src, separate from app.py, so the interface choice does not lock the project in.

Test result:
- Compile check: app.py compiled with no errors after the change. Passed.
- App run check: Streamlit AppTest ran the updated app.py with no exception, and the Step 1 status message was still shown correctly. Passed.
- Dash check: no em dashes or en dashes in any project file. Passed.
- What was not tested: the theme colours were set in config, but a visual check of the real browser rendering happens with the Step 8 screenshots, when the finished interface exists.

Also recorded on this date: a language plan was prepared in LANGUAGE_PLAN.md after Summaira asked whether the tool should be in Chinese and English both. Recommendation there is English first, with a Chinese interface toggle, a selectable review output language, and one short Chinese summary in the README.

---

## Addendum to Step 1, Language decision confirmed and toggle foundation built

Date: 5 November 2026

What was done:
- Summaira decided: English main, with a Chinese toggle (Option 3 in LANGUAGE_PLAN.md).
- Created src/i18n.py. It holds every fixed interface label in one dictionary, in English and in Chinese side by side: 36 labels, covering the header, the tabs, the sidebar settings, upload, review, and report wording that later steps will need. Its get_text function returns the label in the chosen language, falls back to English if anything is missing, and can never crash the interface over a missing label.
- Wired the toggle into app.py. A language switch in the sidebar (English or Chinese) now controls the header title, the tagline, and the status message. Later steps will read all of their labels from the same dictionary.

Decision and why:
- English stays the main language because Summaira must be able to read, check, and explain everything in her own project, and English is the working language of the international master's she is applying for.
- Chinese is included as a toggle for fixed labels only, because Professor Tao's task document was in Chinese and the tool is meant for use in a Chinese university. No documents are duplicated in Chinese.

Test result:
- Dictionary check: English and Chinese hold exactly the same 36 keys, and no label is empty. Passed.
- Function check: get_text returned the correct English title, the correct Chinese title, fell back to English for an unknown language, and returned the key itself for a missing label. Passed.
- App run check in English: Streamlit AppTest ran with no exception and showed the English status message. Passed.
- Toggle check in Chinese: the test set the sidebar switch to Chinese and ran the app again. No exception, and the status message appeared in Chinese. Passed. This is a real working toggle, not a picture of one.
- What was not tested: review output in Chinese. That belongs to Step 5, where the review language selector is built.

---

## Step 2, PDF upload and text extraction

Date: 5 November 2026

What was done:
- Implemented src/pdf_extract.py for real. It takes the raw bytes of an uploaded PDF, opens them with PyMuPDF, extracts the text page by page, and returns the page count, the list of page texts, and one combined text with a page marker line before each page.
- Added the upload section to app.py. The user chooses a PDF, the app extracts its text, and then shows a success message with the file name, three numbers (pages, characters, words), and the full extracted text in a large reading box.
- Added three new labels to src/i18n.py in both languages (characters, words, full extracted text), bringing the dictionary to 39 keys. The upload section reads all of its wording from the dictionary, so the whole step works in Chinese as well as English.
- Wrote tests/test_pdf_extract.py for this step.

How it was done:
- The extraction logic lives in its own module, not in app.py, following the Step 1 structure. The interface only calls one function, extract_text_from_bytes, and displays what it returns.
- The result is stored in Streamlit session state, keyed by the uploaded file identity, so switching the language toggle does not extract the same file again.
- Character and word counts are calculated from the plain page texts, without the page marker lines, so the numbers describe the paper itself.

Decisions and why:
- Bad files are handled in the module. Empty bytes or bytes that are not a readable PDF raise one clean error type, PdfExtractionError, and the interface turns it into an error message instead of a crash. Decision reason: a professor testing the tool with a wrong file should see a controlled message, not a traceback.
- A PDF with no extractable text, for example a scanned paper, produces a clear warning that no text could be extracted. Decision reason: honest behaviour for a known PDF limitation, recorded here instead of hidden.
- The combined text uses a simple page marker, --- Page 1 ---, before each page. Decision reason: the reader can see where pages begin, and the marker format stays fixed in English in both interface languages so later steps can rely on it.

Test result:
- Unit tests: tests/test_pdf_extract.py passed all 3 tests. A small real PDF was built in memory with known text on two pages; extraction returned page count 2, the exact page texts, and the page markers. Invalid bytes and empty bytes each raised the clean error.
- Real file test: extraction was run on a real two page PDF from Summaira's own files, her CV. It returned 2 pages and 6,012 characters, and the expected name and project text were found in the output. Passed.
- App run test with no upload: Streamlit AppTest ran the app with no exception. Passed.
- App upload test: the test uploaded the generated two page PDF through the real file uploader. The app showed the success message with the file name, metrics of 2 pages, 88 characters, and 13 words, and the reading box contained the known first page title. Passed.
- Chinese mode test: the test switched the sidebar to Chinese and ran again. No exception, and the upload heading and uploader label appeared in Chinese. Passed.
- What was not tested: a scanned, image only PDF. The empty text warning path exists, but no scanned sample was run in this step. Scanned papers are recorded as a known limitation, not a solved problem.

Step 2 status: complete and tested.
Next step: Step 3, section and paragraph splitting.

---

## Step 3, Section and paragraph splitting

Date: 5 November 2026

What was done:
- Implemented src/segmentation.py for real. It takes the page texts from Step 2 and returns a list of sections in document order. Each section has a title and its paragraphs in order.
- The app now shows a Paper structure area after the extracted text: two numbers (sections, paragraphs), then one expandable block per section with its paragraphs numbered in order.
- Added three new labels to src/i18n.py in both languages (paper structure, sections, paragraphs), bringing the dictionary to 42 keys.
- Wrote tests/test_segmentation.py for this step.

How it works, in plain words:
- The splitter reads the paper line by line. A line is treated as a heading in three cases: it names a known academic section (Abstract, Introduction, Related Work, Methodology, Results, References, and similar, with or without a number), it is a short numbered heading, or it is a short line in all capital letters with no digits in it.
- Inside a section, a blank line ends one paragraph and starts the next. Lines wrapped by the PDF layout are joined with a space, and a word split across lines by a hyphen is joined back together.
- Lines that are only a page number are dropped.
- Text that appears before the first heading is kept in a section called Front Matter, so the title and author lines of a paper are not lost.

Decisions and why:
- Rule based splitting, no machine learning. Decision reason: the rules can be listed, tested one by one, and explained to the professor in a minute. A learned model for heading detection would be impossible to justify at this scope.
- Heading rules were tightened after the first real document test, see below. Two guards were added: a numbered heading must start with a small number, because papers do not have section 2024, and an all capitals heading may not contain digits, because a grade line is data, not a heading.

Test result:
- Unit tests: tests/test_segmentation.py passed all 5 tests. On a written out sample paper, the splitter found the sections Abstract, 1 Introduction, 2 Methodology, and References, with paragraph counts 1, 2, 2, and 1. Sentences were not mistaken for headings, text before the first heading became Front Matter, page number lines were dropped, and empty input returned no sections.
- Earlier tests still pass: tests/test_pdf_extract.py passed all 3 tests again in this step.
- Real document test, first run: on Summaira's CV the splitter found the real headings, but it also treated date range lines and a grade line as headings. This failure was found by testing, not hidden.
- Real document test, after the fix: the same document now splits into 8 sections and 9 paragraphs, and every major heading is a real one (Professional Summary, Education, Skills, Experience, Projects, Leadership and Activities, Achievements and Certifications). One known behaviour remains: the name line at the top, written in all capitals, is treated as a heading. On a real paper that position holds the paper title, where the same behaviour is harmless.
- App test: the generated two page PDF was uploaded through the real interface. The app showed 1 section and 2 paragraphs, with a Front Matter block holding both paragraphs, which is the correct result for a document with no headings. Passed.
- What was not tested: a full length journal paper with two column layout. Two column PDFs can interleave text across columns during extraction, which can disturb paragraph order. This is a recorded limitation of the extraction plus splitting path, to be checked again in Step 7 testing on real papers.

Step 3 status: complete and tested.
Next step: Step 4, prompt panel with editable per paragraph prompts.

---

## Step 4, Prompt panel with editable per paragraph prompts

Date: 5 November 2026

What was done:
- Implemented src/prompts.py for real. It holds the default review prompt, adds a section specific focus line to it, and manages one prompt per paragraph.
- The structure view in app.py now shows, under every paragraph, a prompt editor prefilled with that paragraph's default prompt, a marker when the prompt has been customised, and a reset button that restores the default for that paragraph only.
- Added three new labels to src/i18n.py in both languages (the editing note, reset to default, custom prompt), bringing the dictionary to 45 keys.
- Wrote tests/test_prompts.py for this step.

How it works, in plain words:
- Every paragraph has a stable identity built from its position, for example s0_p1 means section 0, paragraph 1. The prompt text for a paragraph is stored under a key built from that identity. Because the storage keys are different for every paragraph, an edit to one paragraph cannot leak into another. That isolation is the whole design of this step.
- The default prompt asks the model to act as an experienced academic reviewer: find problems with clarity, logic, evidence, and writing, state each issue, explain why it matters, and give a concrete fix, pointing at exact phrases.
- On top of the shared base, one focus line is added per section type. An abstract is checked for problem, method, result, and conclusion in order. A methods section is checked for repeatability. A results section is checked for claims backed by numbers. A reference section is checked for citation completeness and formatting. Unknown sections get a generic focus on structure and flow.
- When a new paper is uploaded, all stored prompts from the previous paper are cleared before the new defaults are created.

Decisions and why:
- Defaults are section aware rather than one identical text everywhere. Decision reason: it shows the prompt design was thought through like a reviewer thinks, and the user still controls every word per paragraph, which is the requirement.
- Prompts live in the module, not in the interface code. Decision reason: Step 5 will collect the current prompt for every paragraph from one function, collect_prompts, without knowing anything about widgets.
- The custom marker appears only after an edit. Decision reason: in a long paper the user needs to see at a glance which prompts they have changed.

Test result:
- Unit tests: tests/test_prompts.py passed all 3 tests. The default prompt contains the full base text plus the correct focus line per section, and the Abstract and References defaults differ. Every paragraph of a sample structure received a prompt. Editing the stored prompt of one paragraph changed only that paragraph in the collected result; the paragraph before it, the paragraph after it, and the other sections kept their defaults.
- Regression tests: the Step 2 and Step 3 test files passed again, 3 and 5 tests.
- App test: the generated PDF was uploaded through the real interface. Two prompt editors appeared, both prefilled with the Front Matter default. The test then typed a custom prompt into the first editor only: the first paragraph stored the custom text, the second paragraph kept the default, and the Custom prompt marker appeared. The test then clicked the first reset button: the first prompt returned to the default exactly. Passed on all points. This is the requirement level proof for this step, done in the real interface, not only in the module.
- What was not tested: no LLM has seen these prompts yet. Sending them is Step 5.

Step 4 status: complete and tested. His second hard requirement now works in the interface, and in Step 5 the edited prompts are what actually get sent to the model.
Next step: Step 5, LLM integration.

---

## Step 5, LLM integration

Date: 5 November 2026

What was done:
- Implemented src/llm_client.py for real. It sends one paragraph with that paragraph's own prompt to a large language model through an OpenAI compatible API, and returns structured results.
- Added the settings area to the sidebar: API key (password field, never stored), API base URL (prefilled with the DeepSeek address), model name (prefilled with deepseek-chat), and the review language selector (English or Chinese) that was promised in the language plan.
- Added the review area to the app: a Run review button, a progress bar that advances per paragraph, and a results view that shows, for every paragraph, its strengths and its issues with severity, explanation, and suggested fix.
- Added four new labels to src/i18n.py in both languages, bringing the dictionary to 49 keys.
- Wrote tests/test_llm_client.py for this step.

How it works, in plain words:
- For each paragraph, the app collects the current prompt for that paragraph from Step 4, builds a user message containing the prompt first, then the section name, then the paragraph, then the output language instruction, and sends it with a system message that orders the model to answer in one fixed JSON shape: issues with issue, severity, explanation, and suggested fix, plus strengths.
- Answers are parsed into that shape. Answers wrapped in code fences are unwrapped first. Severity is normalised to lower case.
- Temperature is set to 0.2, so reviews stay focused and repeatable rather than creative.
- Results are stored in session state, so they stay on screen while the user reads them.

Decisions and why:
- Structured JSON output instead of free text. Decision reason: the interface can then show issues one by one with severity, and Step 6 can build a real report from the parts. Free text could only be displayed, not used.
- Free text fallback. If a model ignores the JSON instruction, its answer is kept as a single fallback issue holding the full raw text. Decision reason: a review is never silently lost because of a formatting failure.
- Per paragraph failure isolation. If one paragraph's call fails, that paragraph gets an error entry and the rest still complete, with the progress bar reaching the end. Decision reason: one bad call in a 60 paragraph paper must not waste the other 59 paid calls.
- No key in code, ever. The key lives only in the password field for the session. Decision reason: the GitHub repo in Step 8 must be safe to make public.

Test result:
- Unit tests: tests/test_llm_client.py passed all 5 tests, using a fake client with the same interface as the real OpenAI client, which recorded every message it was given. The message test confirmed the prompt, the section name, the paragraph, and the Simplified Chinese instruction all reach the model together. The parsing tests confirmed structured JSON, code fenced JSON, and the free text fallback. The review all test confirmed exactly 3 calls for 3 paragraphs, in order, with progress reported as (1, 3), (2, 3), (3, 3).
- Requirement proof at the API level: in the review all test, a custom prompt was set for the middle paragraph only. The recorded messages show the custom prompt in that paragraph's call and in no other call. This is Step 4's requirement verified at the point where it matters, the actual model request.
- Failure tests: a simulated failure on the second call was recorded as an error entry for that paragraph while the first and third paragraphs still returned reviews. A missing API key and a failing single call each raised the clean LlmError type.
- Regression tests: all earlier test files passed again. The project total is now 16 passing tests across 4 test files.
- App tests: the sidebar showed 3 settings inputs and 2 language selectors. Uploading the test PDF showed the Run review button. Clicking it with no API key produced the warning asking for a key in the sidebar, with no exception and no fake success. A stored results set was then displayed through the real results view: the issue text, its explanation, and the no issues state for a clean paragraph all rendered correctly.
- What was not tested: a live call to a real model. No API key was available in this environment, and keys are never requested in chat. The transport, message building, parsing, error handling, and display are all verified with the fake client and the app tests above. One live run with Summaira's own key, entered by her in the running app, is part of Step 7 testing on real papers, and the result will be recorded there before anything is submitted.

Step 5 status: complete and tested, with the one live call check honestly deferred to Step 7.
Next step: Step 6, final report view and export.

---

## Step 6, Final report view and export

Date: 5 November 2026

What was done:
- Implemented src/report.py for real. It aggregates the Step 5 results, builds the digest for the overall summary, generates that summary with one model call, and builds the downloadable DOCX report.
- Added the Final report area to the app. It appears after a review run and shows the total issues, the section and paragraph counts, the severity breakdown, the overall summary area with its generate button, the collected strengths, the issues grouped by section, and the DOCX download button.
- Added four new labels to src/i18n.py in both languages, bringing the dictionary to 53 keys.
- Wrote tests/test_report.py for this step.

How it works, in plain words:
- Aggregation is pure counting and grouping, no model involved. It walks every section and paragraph once and produces the totals, the severity counts (high, medium, low), the flat list of strengths with their section names, and the grouped structure. Paragraphs whose review failed are counted separately as errors and are never mixed into the findings.
- The overall summary is a second model pass, by design. A compact digest is built first, one line per finding, so even a long paper stays small. That digest goes to the model once, with an instruction to write five to eight sentences of plain prose: what the paper does well, the most important problems in severity order, and what to fix first. The summary language follows the review language selector.
- The DOCX is built with python-docx: title, paper name, the key numbers line, the overall summary, the strengths as bullets, and then issues by section, each with its paragraph number, the issue in bold with its severity, the explanation, and the suggested fix. Error paragraphs are named as errors in the document, not hidden.

Decisions and why:
- The summary is generated from the findings digest, not from the raw paper. Decision reason: the summary then reflects what the review actually found, it costs one small call instead of re sending the whole paper, and it works for papers of any length.
- The report view and the DOCX carry the same content. Decision reason: what the user sees on screen is exactly what they hand over, no surprises in the downloaded file.
- DOCX as the export format. The original task allowed DOCX or PDF. Decision reason: a DOCX can be edited by the author before use, which is how a review report is actually used, and python-docx output was verified by reading the file back.

Test result:
- Unit tests: tests/test_report.py passed all 4 tests. Aggregation on a known sample returned exact totals (3 paragraphs, 2 reviewed, 1 error, 1 issue, severity counts high 1, medium 0, low 0, and 2 strengths). The digest contained the findings and excluded the error entry. The summary generator, run against a fake client, returned the summary text and had sent the digest content to the model; a failing client raised the clean LlmError.
- DOCX verification: the exported file was opened again with python-docx and its text read back. It contained the report title, the paper name, the summary text, the line "Total issues: 1", the issue text, and the suggested fix. The file starts with the correct DOCX signature. Passed.
- Regression tests: all earlier test files passed again. The project total is now 20 passing tests across 5 test files.
- App test: before any review, no report and no download button appear. After stored results were provided, the Final report area appeared with a Total issues metric of 1 and a Download DOCX report button. Clicking Generate overall summary with no API key produced the key warning, with no exception. Passed.
- What was not tested: the live summary call against a real model, for the same reason as Step 5. It is verified with the fake client and joins the live run scheduled in Step 7.

Step 6 status: complete and tested. The tool is now functionally complete: upload, extract, split, prompt per paragraph, review, report, export.
Next step: Step 7, testing on real papers.

---

## Step 7, Testing on real papers

Date: 5 November 2026

Full detail: TEST_REPORT.md in this folder. This entry is the summary.

What was done:
- Downloaded one real research paper for testing, Real-ESRGAN (arXiv 2107.10833, 13 pages, two column), the paper behind Summaira's own image enhancer project. It is a local test file only and is excluded from the GitHub repo by .gitignore.
- Wrote tests/run_real_paper_tests.py, which runs the complete pipeline on any PDF: extraction, splitting, prompt collection, review, aggregation, summary, and DOCX export, with a recording fake model client, and checks every stage's output.
- Ran the pipeline on three real documents: the Real-ESRGAN paper, Summaira's CV, and Summaira's transcript.
- Fixed the two real problems the testing exposed, in src/segmentation.py, then reran everything.

Findings and fixes:
- Finding 1: figure and table labels became fake sections. The paper first produced 41 sections because short all capital tokens (JPEG, RRDB, CDC, BSRGAN) passed the heading rule. Fix: a one word all capital heading must now be a known section name or at least 8 letters long. After the fix the paper produces 16 sections matching its real structure, with one residual false section, a bullet label from a figure, recorded in TEST_REPORT.md.
- Finding 2: two column extraction merged true paragraphs into blocks of up to 5,332 characters. Fix: blocks over 2,000 characters are split on sentence boundaries in the splitter. After the fix, the longest review unit in the paper is 1,981 characters. Sentence order inside paragraphs was spot checked and is correct in this paper.
- Finding 3, trade off recorded, not fixed: the same acronym guard costs the CV its one word SKILLS heading (7 sections instead of 8), and the transcript now returns 1 section and 2 paragraphs. Both still complete the pipeline without errors. The tool is tuned for research papers, which is its stated purpose.

Test result:
- Pipeline checks passed on all three documents: prompts and results matched the paragraph count exactly, aggregation was exact, the summary call was made once, and every DOCX reopened with the report inside. Final numbers: paper 13 pages, 47,980 characters, 16 sections, 38 paragraphs; CV 2 pages, 6,012 characters, 7 sections, 8 paragraphs; transcript 1 page, 3,319 characters, 1 section, 2 paragraphs. Pipeline time under 0.3 seconds per document with the fake client.
- Robustness: a blank PDF produced the empty text warning in the real interface, and a corrupt file produced the clean extraction error. No crashes in either case. Passed.
- Regression: all 20 unit tests across the 5 test files still pass after the fixes.
- Live model run: NOT done. This environment holds no API key (checked directly), and keys are never handled in chat. TEST_REPORT.md lists the exact five minute manual check for Summaira to run with her own key in the app, including the prompt edit check from the original evaluation plan. Step 8 screenshots are to be taken during that live run so the repo shows real model output.

Step 7 status: complete for everything that can be tested without a live key. The live run is a named, owned, five minute check, not a silent gap.
Next step: Step 8, GitHub repo with README and screenshots.

---

## Step 8, GitHub repo with README and screenshots

Date: 5 November 2026

What was done:
- Rewrote README.md as the public repo document: what the tool does, a short Chinese summary paragraph directly under the English summary (translated from it, per LANGUAGE_PLAN.md), how the design answers the task's two hard requirements, features, an architecture diagram in text, how to run, how to use, project structure, testing, and known limitations stated plainly.
- Added an MIT LICENSE file in Summaira's name.
- Initialised a local git repository on the main branch and committed the complete project. First commit: 12125c4, 28 files. Verified before committing that the virtual environment and the Real-ESRGAN sample paper are excluded by .gitignore, as they must be: one is machine local, the other is another author's copyrighted paper used only as a local test file.
- Prepared SUBMISSION_EMAIL_DRAFT.md: the draft email to Professor Tao for when the work is finished, marked do not send yet, with the two preconditions named inside it.
- Built the final delivery zip, paper-review-assistant-final.zip, 28 files, matching the committed file list exactly.
- Wrote screenshots/SCREENSHOTS.md: the exact three screenshots to capture during the live run, with their file names and what each must show.

What could not be done from this environment, stated plainly:
- Pushing to GitHub. The GitHub CLI is installed here but is not logged into Summaira's account, and a direct SSH connection to github.com is reset by this environment's network. Creating the repo and pushing are therefore her actions, with the prepared zip: create an empty public repo named paper-review-assistant under github.com/summaira-muzaffar, then upload the extracted contents of the final zip, exactly as she did for her earlier AI Smell repo. The local git history is one clean commit, so a later clone and push keeps it intact.
- Screenshots. A headless screenshot of the running app was attempted on a local Streamlit server (the server itself ran and answered with HTTP 200). The local browser binary is blocked by an environment policy error, so no screenshot could be captured here, and none has been faked. The three real screenshots are captured during her live run, following screenshots/SCREENSHOTS.md, so they show genuine model output.

Test result:
- Full regression on the final committed state: all 20 tests across the 5 test files passed.
- Delivery check: the final zip contains exactly the 28 committed files, no virtual environment, no caches, no sample paper PDF.
- Git check: working tree clean after commit.

Step 8 status: everything that can be prepared without Summaira's GitHub login and API key is complete. Two actions remain, both hers and both small: the five minute live run with her key (TEST_REPORT.md), with screenshots, and creating the GitHub repo and uploading the final zip. After those, the submission email draft is ready for her review, and the target remains the first week of December 2026, well ahead of schedule.

---

## Addendum, Full application test on the user's own paper (VLM.pdf)

Date: 5 November 2026, after Step 8, at Summaira's request: "use this and test the whole application for me."

The document is the same paper Summaira used in her own local runs (VLM: Task-agnostic Video-Language Model Pre-training, ACL-IJCNLP 2021), supplied by her as VLM.pdf.

Two test levels were run:

1. Pipeline level, tests/run_real_paper_tests.py on VLM.pdf. All 10 checks passed: 13 pages, 49,117 characters extracted, 11 sections, 38 paragraphs, one prompt and one result per paragraph, no result errors, exact aggregation, summary returned, DOCX reopened with the report inside, 0.21 seconds. The section and paragraph counts match exactly what her own local app showed for this paper (11 and 38), which cross verifies her local copy against this one.

2. Interface level, tests/run_vlm_ui_test.py (new file, kept in the repo). The real app was driven through Streamlit AppTest with her intended Groq settings typed into the real sidebar fields (base URL https://api.groq.com/openai/v1, model openai/gpt-oss-120b, a dummy key), and VLM.pdf uploaded through the real uploader. Verified in the running interface: upload metrics (13 pages, 11 sections, 38 paragraphs), all 11 sections rendered, exactly 38 per paragraph prompt boxes, Run review clicked and completed with 38 results and 0 errors from exactly 38 recorded model calls, final report metrics (38 total issues from the test double's one issue per paragraph, 11 sections, 38 paragraphs), the Download DOCX report button present, and Generate overall summary producing the summary through exactly 1 additional model call.

Honest boundary, unchanged: the network transport in both tests is a recording test double, because no real API key exists in this environment and keys are never handled in chat. Everything in the application itself, interface included, is now verified end to end on her own document. The single remaining unverified link is the live response of Groq's servers to her key with the corrected model name, which is one Run review click in her app.

This test also closes her "no review results" report from the same day: that caption is shown when no completed run is stored in the session, which happens after an app restart or a fresh upload, by design.

---

## Live run completion, 5 November 2026

The one remaining unverified link is now closed. Summaira ran the application on her own laptop with her own Groq free tier key and the corrected model name openai/gpt-oss-120b, on the same VLM paper, and sent the downloaded report (VLM_review_NEW.docx) back to this chat, where it was opened and verified directly:

- Report header: "Paragraphs reviewed: 38 of 38. Total issues: 233 (high: 75, medium: 86, low: 72)."
- 233 issue entries, each with issue, severity, explanation, and a suggested fix (231 fix lines, 2 issues without one).
- Zero failure markers anywhere in the document. Every paragraph was reviewed by the live model.
- The content is specific to this paper, not generic: strengths cite the task agnostic framework, the MMM masking scheme, the S3D encoder and HowTo100M; issues cite exact phrases, Table 1, and reported gains, each with a concrete rewrite.
- One gap, recorded plainly: the Overall Summary section of this download reads "The overall summary was not generated", because the Generate overall summary button was not clicked before downloading. The feature itself is verified (Step 6 tests and the VLM interface test, exactly 1 summary call). One click in her still open app session, then a fresh download, completes it; if the session has closed, a rerun of the review is needed first.

With this entry, every stage of the tool, including the live model call, has been verified working at least once. Remaining actions are only the screenshots, the GitHub upload, and the submission email, all Summaira's.

---

## Fix, Summary digest size bound (found by live use at scale)

Date: 5 November 2026

What happened: with the live review complete (233 findings), Summaira clicked Generate overall summary and Groq returned error 413: the summary request was 19,513 tokens against the free tier tokens per minute limit of 8,000 for openai/gpt-oss-120b. The original digest sent one full line per finding with no size bound, a flaw the Step 6 tests could not expose because their reports held a handful of findings. Waiting and retrying cannot fix a request that is itself too large, so the code was fixed instead.

The fix, in src/report.py: build_summary_digest now opens with an exact totals header, orders finding lines by severity (high, medium, low) and then strengths, shortens each explanation, and includes lines only up to MAX_DIGEST_CHARS (16,000 characters). Anything left out is counted in a closing note that tells the model the digest was trimmed and that the totals are exact. The full findings remain untouched in the report view and the DOCX; only the summary's input is bounded.

Test result: a new regression test (tests/test_report.py, now 5 tests) builds a 240 issue report and asserts the digest stays within budget, keeps the exact totals, carries the trimming note, and orders high severity before low. All 21 project tests pass, and the VLM interface test passes unchanged. A scale check at exactly her numbers (233 issues with long explanations) produces a 16,164 character digest, roughly 4,600 tokens, safely under the 8,000 limit that rejected the live call.

Note for her current app session: the fix ships in the updated project zip. Her already completed review results live in her running app's session, so for today's summary she can either switch the sidebar to a provider without that small per minute cap and click the button again (her results are not affected by sidebar changes), or restart with the updated code and run the review once more.


---

## Addendum, Gemini run attempted and discarded (5 November 2026)

Summaira tried the no rerun summary path, but pressed Run review with the Gemini free tier settings in the sidebar (Google AI Studio, model gemini-2.5-flash), so the app re-ran all 38 paragraphs against Gemini instead of only generating the summary.

Verified result, from her screenshots and from the downloaded report VLM_review_next.docx opened and checked in this chat:

- Only 12 of 38 paragraphs were reviewed. 26 paragraphs could not be reviewed.
- Total issues: 60 (high 34, medium 20, low 6), with 60 explanations and 60 suggested fixes.
- The overall summary was not generated. The summary call returned error 429.
- The failed paragraph calls returned error 429 (rate limit) in most sections, and error 503 in the three Introduction paragraphs.

Interpretation: Gemini's free tier throttled the app's 38 rapid back to back calls. This is a provider limit, not an application failure. The application's failure isolation worked exactly as designed in Step 5: the 12 successful reviews were kept, the 26 failures were marked per paragraph, and a partial report was still generated and exported.

Decision: this Gemini run is discarded and is not submission evidence. The verified live success remains the Groq run (38 of 38 paragraphs, 233 issues). The Gemini provider path is closed. The remaining path is a rerun on Groq using the updated code with the bounded summary digest, then Generate overall summary, then a fresh DOCX download for verification.


---

## Generality audit and unseen paper test (5 November 2026)

At Summaira's instruction: the tool must be global, coded for every paper, never for one specific research paper.

Audit of the application code (src and app.py only, test files excluded because tests must name their test documents):

- Searched for every development test paper's fingerprints: paper names, topic terms, author names, file names, arXiv references. Result: none found. No paper, topic, or file is named anywhere in the application code.
- What the code actually contains is generic academic structure only. Segmentation recognises a standard section vocabulary shared by all fields (abstract, introduction, related work, methods, results, discussion, conclusion, references, and similar), short numbered headings, and short capital headings. Anything before the first heading is Front Matter for any document.
- Prompts are one generic reviewer prompt plus a focus line matched by section type. A section the code does not recognise gets the generic focus line, so an unusual paper structure still reviews.
- The model, provider, and language are sidebar settings, not coded to any paper or provider. The report uses the uploaded file's own name, taken from the upload at run time.

Unseen paper test, using the Step 7 pipeline runner (tests/run_real_paper_tests.py) on two papers never used in development, chosen for different fields and layouts:

- LIGO gravitational waves paper, physics, journal letter layout, arXiv 1602.03837: 16 pages, 74,349 characters, 42 sections, 80 paragraphs, all 10 pipeline checks passed. Its Roman numeral headings (I. INTRODUCTION and similar) were recognised by the generic capital heading rule. Honest imperfection: the journal running headers became extra small sections. No content lost, no failure.
- BERT paper, arXiv 1810.04805: 16 pages, 64,101 characters, 21 sections, 53 paragraphs, all 10 pipeline checks passed. A few table rows appear as extra sections, the same known cosmetic behaviour already recorded for figure labels.

Conclusion: the tool is generic by construction and by test. The test papers from development (Real-ESRGAN, VLM) appear only in tests and records, never in application logic. These two extra test papers were downloaded to a temporary folder for this check only and are not part of the repo.

## Reliability upgrade after live use (5 November 2026)

Summaira asked for an improved version after the live session produced the same 401 error again, and the causes of every live failure were addressed in code rather than only in instructions:

- Settings validation (src/llm_client.py, validate_settings): the key, base URL, and model are checked against each other before any call. Key prefixes (Groq keys start with gsk_, Google AI Studio keys start with AIza) are matched against the provider in the base URL, and model families are matched against the provider. A mixed set, the exact failure in her screenshot (a Google key with Groq's address and model), is stopped with one plain message.
- Preflight check (preflight_check): after validation, the provider's model list is requested once. It proves the key is accepted and confirms the model name exists, so a retired model name is caught before a run instead of on paragraph one.
- Test API connection button in the sidebar runs the same validation and preflight, so settings can be proven in seconds without a full run.
- Automatic retry (call_with_retry): rate limits (429) and provider server errors (5xx) are retried with waits of 2, 5, and 12 seconds, in both paragraph reviews and the overall summary call. Other failures (wrong key, no balance, missing model) are not retried, because waiting cannot fix them.
- Plain language errors (friendly_error): every provider error code seen in live use (401, 402, 404, 413, 429, 5xx) is translated into the cause and the fixing action, with the raw code kept for reference.
- Run information line: the results area now names the model, provider host, and time of the run the results came from, so results from an earlier run are never mistaken for a new one. A blocked run no longer starts at all, and starting a new run clears the previous overall summary.

Tests: 6 new tests in tests/test_llm_client.py (27 project tests in total, all passing) cover provider mixup detection, preflight blocking a mixup with zero network calls, preflight model list checks including a rejected key, retry recovery after two 429 responses, retry exhaustion recording a plain error while the remaining paragraphs continue, and non retryable errors failing at once. The VLM interface test gained a Test API connection step and passes in full. A separate interface check reproduced her exact mixup (Google key, Groq address, Groq model): both the Test button and Run review showed the clear validation message, no results were stored, and zero model calls were made. Full pipeline regression on four papers (VLM, Real-ESRGAN, LIGO, BERT) passed all 10 checks each. No claim is made that a provider can never fail; what changed is that configuration mistakes are caught before the run, temporary failures recover on their own, and any remaining failure arrives as one explained message.

## Resumable runs and preflight fallback (5 November 2026)

Summaira confirmed she is using her Google AI Studio key, so the tool was adapted to the provider she actually has in hand instead of only steering her back to Groq:

- Resumable review runs: review_all now accepts the results of an earlier run of the same paper. Paragraphs with a successful review are kept untouched and are not called again; only missing and failed paragraphs are reviewed. The app passes the stored session results into every Run review click. Combined with the automatic retry, this makes a strictly rate limited free tier (Gemini) finishable: run once, wait for the limit window to reset, press Run review again, and repeat until no error paragraphs remain.
- Preflight fallback probe: a provider whose OpenAI compatible endpoint offers no model list (the list call answering 404, 405, or 501) is now verified with one tiny test chat call instead of being blocked, so a working Gemini style setup cannot be stopped by a missing list endpoint. A rejected key still fails the probe and is reported in plain language.

Tests: 2 new tests (29 project tests in total, all passing) cover resume keeping the original result object while redoing only the failure, and the preflight fallback succeeding through a test call and failing plainly on a rejected key. The VLM interface test and the mixed settings negative interface test both pass unchanged after the change.

## Visible build marker (5 November 2026)

After several rounds where the old local copy kept being served instead of the new code, the sidebar gained a permanent caption under the settings: "Improved build: settings check, Test API connection, automatic retry, resumable runs." Together with the Test API connection button it makes the running version identifiable at a glance. The delivery zip was also renamed and restructured so it extracts to a brand new top folder, paper-review-assistant-v2, which cannot be confused with any earlier folder on the user's machine. The extracted v2 package was itself started and verified end to end before handover (server response, button presence, full VLM interface run, and the automated tests, all from the extracted copy).

## Google AQ. key format fix (5 November 2026)

The user's real AI Studio key starts with "AQ.", not "AIza". Google's AI Studio list confirmed it: the key shown there ends with the same last four characters as the key she holds, created the same day under her Default Gemini Project. The settings check only knew the older AIza format, so it wrongly blocked her genuine key before any call. The check now accepts both Google formats (AIza and AQ.), the messages say so, and the marker caption reads "Improved build v3" so the running version is again provable at a glance. Tests cover an AQ. key validating cleanly on the Google set and still being flagged on Groq's address. Separately, the full key was pasted into the chat during this troubleshooting, so she was advised to delete that key in AI Studio and create a fresh one; the value itself was never stored in this project or its records.

## Preflight model list prefix fix (5 November 2026)

The connection check compared the typed model name against the provider's model list exactly as returned. Google's list returns ids with a "models/" prefix (models/gemini-2.5-flash) while chat calls use the short name (gemini-2.5-flash), so the check claimed the model was missing when it was present, even listing it in its own message. The matcher now also accepts the short form of any returned id, and the not found message shows readable names. A regression test feeds the prefixed Google id and expects a clean pass. Marker caption now reads "Improved build v4".

## Any key, any paper verification (5 November 2026)

At the user's demand that the tool work for any API key and on any paper, both claims were audited and tested rather than asserted. Provider side: the only provider specific code is the sidebar defaults (changeable) and the mismatch guards between known providers. One real false block was found and fixed: Google's endpoint also serves Gemma models, and the Google model check only allowed names starting with gemini, so it now accepts gemini, gemma, and models/ prefixed names. A new test proves that matching sets from providers the checker has never heard of (an OpenRouter style set and a Together style set) pass validation, and that an unknown provider passes the preflight check against its model list. Paper side: two more unseen papers passed all 10 pipeline checks, Attention Is All You Need (NeurIPS format, 15 pages, 39 paragraphs) and Bahdanau et al. on neural machine translation (ICLR 2015 format, 15 pages, 58 paragraphs), bringing the unseen paper evidence to six papers across six venues plus a CV. The honest boundaries are unchanged: the provider must offer an OpenAI compatible endpoint, the account must hold balance or free quota, and the paper must contain extractable text (scanned image PDFs need OCR, which the tool does not do).

## Free tier pacing fix (5 November 2026)

The first live Gemini run on the improved build still returned mostly 429 errors, with occasional successes slipping through. The cause was in this app, not only in the provider: the retry waits (2, 5, 12 seconds) were tuned for a paid API, so a throttled paragraph could fire four requests inside half a minute into a bucket that refills per minute, and the whole run kept the bucket empty. The batch run now paces itself: at least 5 seconds between the starts of two calls, retry waits of 30, 60, and 120 seconds, and a visible on screen status whenever a long wait begins ("The provider asked us to slow down. Waiting N seconds, then continuing."), so waiting reads as waiting, not as a hang. A fake clock test proves the pacing gaps, the patient 30 second first wait, and the status message. The honest limit is unchanged: if a provider's daily free allowance is fully spent, pacing cannot create quota, and the run must finish on a later pass.

## Live progress display (5 November 2026)

At the user's demand for an app that keeps the user informed instead of frustrated, the run view was upgraded. The progress bar now carries the count and percentage in its label (for example "Reviewing... 12 of 38 (32%)"). A status line under it updates after every paragraph with the running tally (paragraphs processed, how many reviewed, how many hit the provider limit and will be retried on the next run), alongside the waiting messages from the pacing build. When a run ends, the app no longer shows a bare "Review complete": it states the exact reviewed count, and when some paragraphs hit the limit it shows a warning with that count and the one next step, press Run review again after a wait so only those are retried. Marker caption now reads "Improved build v7".

## Test expectation corrected (5 November 2026)

The critical check of the delivered v7 package ran the repo's own interface test against the extracted app. The run itself completed perfectly (upload, Connection OK, 38 results), but the test stopped on its success banner assertion: it still expected the old wording containing "complete", while build v7 deliberately replaced that banner with the exact count message "All 38 paragraphs reviewed successfully." The app was right and the test was stale. The assertion now checks for the current message, and the delivery zip was rebuilt so the shipped test suite matches the shipped app.

## Fast, calm runs and saved progress (6 November 2026, build v8)

Live use of v7 on the Gemini free tier exposed two design faults, both in this app. First, speed: the patient retry ladder (30, 60, 120 seconds per paragraph) turned a low quota into a crawl; after more than an hour and a half the run had barely started. Second, fragility: results lived only in session memory and were written only when a whole run finished, so when the user's laptop slept for a second and the session dropped, all progress vanished.

The batch run policy is rebuilt. A rate limited paragraph now gets one short pause (20 seconds) and one retry, then it is recorded as saved for later (a "rate_limited" entry) and the run moves on. A server error gets one 5 second pause and one retry. If three paragraphs in a row end rate limited, a circuit breaker stops calling the provider for the rest of the pass and saves the remaining paragraphs at once, so a spent quota stops burning itself. Pacing between calls is 2 seconds. The on screen wording is calmer throughout: no countdown messages, progress lines report reviewed and saved for later counts, and a finished partial run reads as saved work with one next step, not as a failure. Single calls (review_paragraph used directly, and the overall summary) keep the patient retry ladder, because there is only one call to wait for.

Progress is now saved to disk after every paragraph by the new src/progress_store.py: an atomic JSON write per paper, keyed by a SHA-256 fingerprint of the extracted text, holding results, the summary, the run label, and the user's prompts, never the API key. Uploading the same paper in a fresh session restores its finished paragraphs and prompts, and a Start fresh button clears one paper's save. The .review_progress folder is gitignored.

Verification: 38 automated tests (6 files), all passing, including new tests for the brief wait policy with a fake clock, saved for later marking after exactly two attempts, the circuit breaker (8 paragraphs, all 429, only 6 provider calls), the per paragraph result callback, and the progress store round trip. The VLM interface test passes and now also asserts the on disk save holds all 38 results and the summary. Two session checks beyond the suite: a fresh session restored 38 of 38 results from disk on upload alone, and a real time run against an always 429 double finished a 38 paragraph pass in 64.0 seconds with 6 provider calls and every paragraph saved for later. Marker caption now reads "Improved build v8".

## Batched reviewing (6 November 2026, build v9)

The user's verdict on v8 was "flawless but not this much slow", with a demand for the best, optimal solution rather than another patch. The remaining cost driver was structural: one model call per paragraph means 38 requests for a 38 paragraph paper, and a free tier charges per request (per minute and per day rations), so request count, not only waiting, was the bottleneck.

The run engine now batches. Pending paragraphs are grouped by plan_batches (at most 5 paragraphs and at most 8,000 characters of text plus prompts per call). Each batch call carries every paragraph under its own id, with that paragraph's own prompt and section, and the batch system prompt requires a JSON object with one entry per id. Batches run in parallel waves of 3 workers sharing one call limiter, so pacing is global across threads. Flawlessness is guarded, not assumed: parse_batch_response returns only ids that came back usable, and any paragraph missing from a batch answer is reviewed again on its own with the brief v8 policy; a batch that fails with a non limit error also falls back to individual calls. The rate limit policy now applies per batch (one 20 second pause, one retry, then the batch's paragraphs are saved for later), and the circuit breaker counts consecutive limited batches. A 38 paragraph paper now takes about 10 calls instead of 38.

Measured after the change: all 40 automated tests pass (21 in test_llm_client.py, including batch prompt carriage in a single call, partial batch fallback, whole group saved for later, and the circuit breaker over 20 paragraphs with only 6 calls). The pipeline runner passes all 10 checks on VLM, Attention, and Bahdanau, with its call count check now expecting batches plus the summary call. The full VLM interface test passes in about 22 seconds wall clock (10 review calls, down from 38; the same test took about 77 seconds on v8 and about 3 minutes 57 seconds in the v6 pacing run), including the on disk progress save assertion. A real time pass against an always 429 double now finishes 38 paragraphs in 24.0 seconds with 6 provider calls (v8: 64.0 seconds; v7 policy could crawl for hours). Marker caption now reads "Improved build v9".

## Windows progress save crash fix (6 November 2026, build v10)

The first live v9 run on the user's Windows laptop crashed inside the progress saver: PermissionError, WinError 5, access denied, on os.replace of the progress file, three paragraphs into the run. Root cause: Windows refuses to replace a file that another process is holding open at that moment, which happens when saves land in quick succession and a scanner or indexer holds the just written file. Linux, where every test in this project runs, allows the replace unconditionally, so the full test battery passed while the code was broken on the only machine that matters. That verification gap is recorded here plainly: the tests ran, but not under the operating system semantics the user actually has.

The fix has three layers, in src/progress_store.py and app.py. The replace is retried with short delays (0.1, 0.25, 0.5, 1.0 seconds), which clears a transient lock. If the replace stays locked, the save falls back to writing the destination file directly. And save_progress now returns True or False instead of raising, while the app's save_snapshot records a failure flag and shows one calm warning ("keep this tab open until the run finishes; the review itself is not affected") instead of the false "saved automatically" caption. A protective feature must never be able to crash the work it protects.

Coverage for a platform the development environment cannot run is by simulation: three new tests force os.replace to fail the Windows way (transiently, permanently, and with the disk write itself failing) and prove the retry lands, the fallback lands, and total failure returns False without raising. A full interface test variant with the lock forced on every save also passes end to end: 38 of 38 results, and the progress file still lands through the fallback. Project total is now 43 automated tests, all passing. Marker caption now reads "Improved build v10".

## Empty report notice (6 November 2026, build v11)

The user's first completed v10 run was against a Gemini key whose free allowance was already spent (largely by the morning's long v7 run), so every batch was refused, all 38 paragraphs were saved for later, and the final report correctly showed zero issues, which read as a broken app. The behaviour was right and the presentation was not: an empty report must explain itself. The report section now opens with a clear notice whenever zero paragraphs were reviewed and some are outstanding: nothing has been reviewed yet, every paragraph hit the provider limit, wait for the reset or switch provider set, then press Run review again and the saved paragraphs finish automatically. Verified with a dedicated interface check in which the provider refuses every call: the pass completes without crashing, all 38 paragraphs are marked saved for later, and the notice appears in the report. The full interface test still passes. Marker caption now reads "Improved build v11".

## Final build (2026-11-06)
- The connection test now ends with one tiny real generation call after the model list check. Reason: a spent project quota passes a list-only check (the list costs the provider nothing) and then fails on every paragraph; her new Google key in the same project tested OK and the run still saved all 38 paragraphs for later. A refused probe now fails once, before a run, with the quota explanation, including the fact that a new key in the same account or project does not reset the limit.
- Rate limit handling is adaptive: a refused batch is retried once, then split into smaller batches down to single paragraphs, because per minute token rations refuse large requests that smaller ones fit under. The first split branch that comes back entirely refused turns splitting off for the rest of the run, and the circuit breaker still stops calls after 3 limited batches, so a spent quota stays bounded (verified: a dead quota costs 14 calls on a 20 paragraph paper, not a tree of retries).
- The final report now always states how many paragraphs were reviewed and how many are saved for later, not only when nothing was reviewed.
- The sidebar no longer carries a version label.
- Tests: 45 automated tests across 6 files (2 new: the probe catching a spent quota behind a healthy model list, and split recovery when only multi paragraph batches are refused; 2 updated call counts for the splitting policy).
