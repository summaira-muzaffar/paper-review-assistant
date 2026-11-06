# Know Your Project: Paper Review Assistant

Your defense notes. Everything here is true of the code in this repo and the tests that were actually run. If Professor Tao asks about this project, these are your answers in your own words.

## The 60 second story

"Professor Tao's task asked for an LLM based paper review tool with two specific requirements: a software interface, and user settable prompts for each paragraph. I built it as a web application. A user uploads a paper as a PDF. The system extracts the full text, splits it into sections and paragraphs, and then sends each paragraph to a large language model together with that paragraph's own review prompt. The model answers in a fixed structure: the issues it finds, a severity for each one, why it matters, a concrete fix, and the paragraph's strengths. At the end, everything is combined into one report with an overall summary, and the user can download it as a Word document. The interface works in English and Chinese, and the review itself can be generated in either language."

## How it works, stage by stage

1. Extraction, src/pdf_extract.py. PyMuPDF reads the PDF page by page and returns the full text. Corrupt files and PDFs with no text produce clear error messages in the interface, never a crash.
2. Splitting, src/segmentation.py. Rule based, no machine learning. Headings are recognised three ways: known academic headings like Abstract or References, numbered headings like 3.2 High-order Degradation Model, and short capital headings. Blank lines end paragraphs, wrapped lines are joined, hyphen split words are repaired, and blocks longer than 2,000 characters are split on sentence boundaries. Text before the first heading is called Front Matter.
3. Prompts, src/prompts.py. Every paragraph gets a prompt built from a shared reviewer base plus one focus line that depends on its section, for example checking claims against evidence for a Results section. Each prompt is stored under its own key, section index and paragraph index, which is exactly why editing one can never touch another.
4. Review, src/llm_client.py. For each paragraph, one model call is made through an OpenAI compatible API. The user's prompt for that paragraph goes first in the message, then the section name and the paragraph, then the output language instruction. A system prompt forces the model to answer with JSON only, in the fixed shape. Temperature is 0.2, low, because a review task wants consistent, focused answers, not creative ones.
5. Report, src/report.py. The results are counted and grouped: totals, severity counts, strengths, issues by section. Then a second model call reads a compact one line per finding digest of all results and writes the overall summary, so the summary is based on the findings, not on re-reading the whole paper. The report downloads as a formatted DOCX.

## His two requirements, and your proof

Requirement 1, a software interface: a Streamlit application with a custom theme, a settings sidebar, and a guided flow from upload to report.
Requirement 2, prompts per paragraph: every paragraph has an editable prompt box with a reset button. Three separate tests prove the isolation: a unit test at the prompt module level, an interface test where paragraph 1 was edited in the running app and paragraph 2 kept its exact default, and a model level test where a recording fake client proved the custom prompt appeared in that paragraph's model call and in no other.

## Concepts to be able to explain

- OpenAI compatible API: many model providers accept the same request format. By letting the user type the key, base URL, and model name, the same code works with DeepSeek or any similar service. Nothing about the project is locked to one vendor.
- Structured output: the model is not asked to write an essay. It must return JSON with fixed keys, so the interface can render each issue separately and count severities. If a model ignores the instruction and answers in free text, the parser keeps the raw text as one fallback issue, so no review is silently lost.
- Prompt engineering per paragraph: a whole paper reviewed in one call would produce shallow, general comments and would hit context limits. Paragraph by paragraph gives specific comments tied to exact text, and lets the user steer the focus per paragraph.
- Failure isolation: if one paragraph's API call fails, only that paragraph is marked as an error and the rest of the review completes. One bad call never throws away a whole paper's review.
- Session state: Streamlit reruns the script on every interaction, so uploaded text, structure, prompts, and results are cached in session state, keyed by the uploaded file, and cleared when a new paper is uploaded. Because session state dies with the session, results are also saved to disk after every paragraph, keyed by a fingerprint of the paper's text, and restored when the same paper is uploaded again. A sleeping laptop or a closed tab can no longer wipe a half done run.
- Batched reviewing: paragraphs are not sent one call each. They are grouped (up to 5 paragraphs and 8,000 characters per call), each paragraph keeps its own prompt and id inside the batch, batches run in parallel waves of 3, and any paragraph missing from a batch answer is reviewed again on its own. A 38 paragraph paper takes about 10 calls instead of 38.
- Rate limit policy: a run does not stall on long retry waits. A limited batch gets one short pause and one retry, then its paragraphs are saved for later and the run moves on; if three batches in a row hit the limit, the run stops calling the provider and saves the rest at once. Measured with a completely spent quota, a 38 paragraph pass finishes in about 24 seconds with only 6 provider calls, instead of crawling for hours.
- Rule based splitting: heading patterns in academic papers are regular enough that explicit rules are predictable, testable, and easy to explain, which matters for an assessment. A learned model would be harder to verify and to defend.

## Numbers card

- 45 automated tests across 6 test files, all passing.
- Real paper test: Real-ESRGAN, 13 pages, 47,980 characters, split into 16 sections and 38 paragraphs, full pipeline in under 0.3 seconds with a test client.
- First split attempt gave 41 sections because figure labels looked like headings. The fix and the rerun are both recorded in TEST_REPORT.md.
- Two column papers merge paragraphs badly at extraction, so blocks are capped at 2,000 characters. The longest review unit in the test paper is 1,981 characters.
- Interface labels: 53 keys, each present in English and Chinese.

## Likely questions, with answers

Q: Why Streamlit and not a full web stack?
A: The task required a software interface, and named no technology. Streamlit let the effort go into review quality, structure, and testing instead of a second front end stack, and the logic lives in separate modules, so the interface could be replaced later without touching the pipeline. I checked Flask, Gradio, and React with FastAPI before deciding; the comparison is written in INTERFACE_DECISION.md.

Q: Why review paragraph by paragraph?
A: Specificity and control. A paragraph sized unit gets comments about that exact text, the user can set a different instruction per paragraph, which the task explicitly required, and no single call has to hold a whole paper.

Q: Why DeepSeek?
A: Only as the default. The user enters their own key, base URL, and model, so any OpenAI compatible provider works. The code never stores a key.

Q: How do you know the splitting works?
A: Unit tests on known structures, plus full pipeline runs on three real documents: a two column research paper, a CV, and a transcript. The failures found, figure labels as headings and merged paragraphs, were fixed and rerun, and are documented in TEST_REPORT.md.

Q: Is it built for one specific paper?
A: No. Nothing in the application code names any paper, author, topic, or file. That was checked directly by searching src and app.py for the test papers used during development, and nothing was found. The code only knows generic academic structure: a list of standard section names used across all fields, numbered headings, and capital headings, with a generic prompt for any section it does not recognise. The VLM and Real-ESRGAN papers were only test documents. As a final check, the full pipeline was run on two papers the tool had never seen, in different areas and layouts: the LIGO gravitational waves paper from physics (16 pages, 80 paragraphs, all checks passed, its Roman numeral headings recognised by the capital heading rule) and the BERT paper (16 pages, 53 paragraphs, all checks passed). Journal running headers and table labels can occasionally appear as extra sections in unusual layouts; no content is lost and the review still completes, and that is stated as a known limitation, not hidden.

Q: What happens when a paper produces hundreds of findings?
A: The full report and the DOCX always carry everything. Only the overall summary works from a digest, and that digest is size bounded on purpose: totals first, then issues in severity order, then strengths, up to a fixed character budget, with a note telling the model that lower severity lines were trimmed. Live use found this the hard way, when a 233 finding digest of about 19,500 tokens was rejected by a free tier limit of 8,000 tokens per minute. The fix is in src/report.py, with a regression test, and after it the same size of report produces a digest of roughly 4,600 tokens.

Q: What happens if the API fails halfway?
A: Temporary failures, rate limits and provider server errors, are retried automatically with growing waits, because waiting is the correct fix for them. If a paragraph still fails, it is recorded as an error inside its own result, the remaining paragraphs finish, and the report lists the error paragraphs separately instead of mixing them into the findings. And the run is resumable: pressing Run review again keeps every paragraph that already succeeded and reviews only the missing and failed ones, so a rate limited free tier run is finished by waiting a few minutes and rerunning, never by starting over. That combination, retry plus resume plus per paragraph isolation, is what makes the tool usable on free tiers with strict per minute limits, like Google Gemini, not only on generous ones.

Q: What stops a user from mixing up API keys and providers?
A: Three layers, all added after live use exposed this as the most common real world failure. First, the sidebar settings are validated before any call: key prefixes and provider addresses are checked against each other, so a Google key next to a Groq address is stopped with one plain message instead of failing on all 38 paragraphs. Second, a Test API connection button, and the same preflight check inside Run review, ask the provider for its model list, which proves the key is accepted and the model exists, for the cost of one small request. Third, every provider error is translated into plain language with the action that fixes it, with the raw code kept for reference. There is also a line under the results naming the model, provider, and time of the run they came from, so old results are never mistaken for new ones.

Q: Does it work for Chinese papers and users?
A: The interface has a Chinese toggle for all labels, and the review output language is selectable, with the instruction passed to the model in the message. The code and README stay in English, with a short Chinese summary in the README.

Q: What are the limitations?
A: Scanned PDFs have no extractable text and the tool says so instead of inventing a review; OCR is out of scope. Splitting is rule based and tuned for research papers, so an occasional figure label can still be mistaken for a heading, and documents that are not papers split less precisely. And review quality depends on the model and prompts chosen; the tool structures the feedback, a human still judges it.

Q: What would you improve next?
A: OCR for scanned papers, table and figure caption awareness in the splitter, and a small human rated evaluation set to measure how often the model's issues are judged correct and useful. That is the honest next research step.

## Lines never to cross

- The live model run is done and verified: you ran it yourself on your laptop (Groq free tier, model openai/gpt-oss-120b) on the VLM paper, 38 of 38 paragraphs reviewed, 233 issues with severities, explanations, and fixes, and the downloaded DOCX was read back and checked. You may claim that. The one piece not yet exercised live is the Generate overall summary button; click it once in the app before claiming the summary specifically.
- Do not claim the tool checks facts or guarantees a correct review. It structures model feedback; it does not certify it.
- Do not present the Real-ESRGAN sample paper as your own work. It is a published paper used as a test document, and it is deliberately excluded from the repo.
- Do not claim OCR or handwriting support. There is none.

## A three minute demo order

1. Open the app, point at the sidebar: key, model, review language, interface language toggle. Switch the labels to Chinese and back.
2. Upload the Real-ESRGAN paper. Show the counts and the structure: 16 sections, 38 paragraphs.
3. Open one paragraph and edit its prompt, for example "Check only the statistics in this paragraph." Point out the Custom prompt caption and the reset button.
4. Run the review, show the progress bar, then one paragraph's structured result.
5. Generate the overall summary and download the DOCX. Open it.

## Where everything lives

- BUILD_LOG.md: every step, decision, and test result, in order.
- TEST_REPORT.md: the real paper testing, the two fixes, and the live run checklist.
- INTERFACE_DECISION.md and LANGUAGE_PLAN.md: the two design decisions and their reasoning.
- SUBMISSION_EMAIL_DRAFT.md: the email to send when the repo is live. Draft only, you send it.
