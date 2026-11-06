# Test Report, Step 7: Testing on Real Papers

Date: 5 November 2026
Tester: the build assistant, in the project virtual environment.
Companion record: BUILD_LOG.md, Step 7 entry.

## Method

Three real PDF documents were run through the complete pipeline with the runner at tests/run_real_paper_tests.py: extraction (Step 2), splitting (Step 3), prompt collection (Step 4), review (Step 5), aggregation, summary, and DOCX export (Step 6). The review and summary stages used a recording fake model client that returns one fixed structured answer, so every stage except the live network call was exercised end to end on real documents. The live call check is reported separately at the end of this report, with its exact status.

The three documents:

1. A real research paper: "Real-ESRGAN: Training Real-World Blind Super-Resolution with Pure Synthetic Data" (arXiv 2107.10833), 13 pages, two column layout. Chosen because it is a genuine paper of the kind this tool is built for, and because it is the paper behind Summaira's own Real-ESRGAN project. Kept as a local test file only; it is excluded from the GitHub repo by .gitignore, because it is the authors' work, not ours.
2. Summaira's CV, 2 pages, a real single column document.
3. Summaira's BS transcript, 1 page, a real structured document with tables of grades.

## Results after fixes

| Document | Pages | Characters | Sections | Paragraphs | Pipeline time | All checks |
|---|---|---|---|---|---|---|
| Real-ESRGAN paper | 13 | 47,980 | 16 | 38 | 0.29 s | Passed |
| CV | 2 | 6,012 | 7 | 8 | 0.07 s | Passed |
| Transcript | 1 | 3,319 | 1 | 2 | 0.06 s | Passed |

The checks for each document were: text extracted, sections found, one prompt collected per paragraph, one review result per paragraph, no result errors, issues aggregated to exactly the paragraph count (with the fixed fake answer), summary returned, one model call per paragraph plus one summary call, and the exported DOCX reopening with the report title inside.

## What real testing found, and what was fixed

Finding 1: figure and table labels became fake sections.
First run on the Real-ESRGAN paper produced 41 sections. The real headings were all found, but short all capital tokens from figures and tables (JPEG, RRDB, CDC, BSRGAN, the model name ESRGAN) were also treated as headings.
Fix: a one word all capital heading must now be a known section name or a long word (8 letters or more). Short capital tokens are acronyms far more often than headings.
Result after fix: 16 sections, and the list is the paper's real structure (Abstract, 1. Introduction, 2. Related Work, 3.1 to 3.4, 4.1 to 4.4, 5. Conclusion, References, Appendix). One residual false section remains, a bullet label "• JPEG" from a figure, recorded here as a known imperfection.

Finding 2: two column text merged true paragraphs into giant blocks.
Blank lines are rare in the extracted text of a two column paper, so blocks of up to 5,332 characters arrived as single paragraphs. A block that size makes a slow, unfocused review unit.
Fix: blocks longer than 2,000 characters are now split into chunks on sentence boundaries inside the splitter (MAX_PARAGRAPH_CHARS in src/segmentation.py).
Result after fix: the longest paragraph unit in the paper is 1,981 characters, and no unit is above the cap.
Reading order note: within paragraphs, the extracted sentences were coherent and in the right order on the pages spot checked. The two column layout did not scramble sentence order in this paper.

Finding 3: documents that are not papers behave roughly, and that is acceptable.
The transcript's repeated "GPA:" lines were treated as headings in the first run. After Finding 1's fix they no longer are: the transcript now returns 1 section and 2 paragraphs (the second is a chunk of the first, from Finding 2's cap). The CV lost its one word SKILLS heading to the same acronym guard, returning 7 sections instead of 8. Both documents still flow through the whole pipeline without errors. This tool is built and tuned for research papers, and the report records the trade off honestly instead of hiding it.

## Robustness checks

- Blank PDF (a PDF with one empty page): the app showed the warning "No text could be extracted from this PDF." No crash, no fake results. Passed.
- Corrupt file with a .pdf name: the app showed "Text extraction failed: This file could not be opened as a PDF." No crash, no traceback shown to the user. Passed.
- Regression: all 20 unit tests across the 5 test files still pass after the Step 7 fixes.

## Live model run: exact status

COMPLETED on 5 November 2026 by Summaira on her own laptop, after the main body of this report was written. See Addendum 2 at the end of this report for the verified result. The original status text below is kept for the record.

Original status at the time of writing: not done yet, and not claimed here. This environment holds no API key (checked: no OpenAI or DeepSeek key variables are present), and keys are never requested or handled in chat. Every stage around the call is verified: message building, per paragraph prompt delivery, JSON parsing, failure isolation, aggregation, summary generation, export, and the full pipeline above.

The remaining check is a five minute manual one, done by Summaira in the running app with her own key:

1. Start the app, enter a DeepSeek API key, base URL, and model in the sidebar.
2. Upload the Real-ESRGAN paper from sample_papers, or any real paper.
3. Press Run review, then read the first three paragraph results and judge: does each comment point at a real, specific problem in that paragraph?
4. Edit one paragraph's prompt (for example, "Check only the statistics."), run again, and confirm that paragraph's review changes focus while the others keep the same style.
5. Generate the overall summary, download the DOCX, and open it.

Step 8 screenshots should be taken during this live run, so the GitHub repo shows real model output, not test doubles. The Step 7 entry in BUILD_LOG.md will be updated with the live run result when it happens.

## Addendum, 5 November 2026: full application test on VLM.pdf

At Summaira's request the whole application was tested on the same paper she used locally (VLM, ACL-IJCNLP 2021, supplied by her). Pipeline level: all 10 checks passed, 13 pages, 11 sections, 38 paragraphs, counts identical to her local app. Interface level: a new AppTest driver (tests/run_vlm_ui_test.py) filled her Groq settings into the real sidebar, uploaded the paper through the real uploader, and completed a full run: 38 results, 0 errors, 38 model calls, correct report metrics, DOCX button present, summary generated in 1 call. The transport was a recording test double, as in the rest of this report; the live Groq response to her key remains the one unverified link, by the same key rule stated above. Full record in BUILD_LOG.md, addendum after Step 8.

## Addendum 2, 5 November 2026: live run completed and verified

This addendum supersedes the "live Groq response remains unverified" line in Addendum 1 and the original status section above. Summaira completed the live run on her laptop (Groq free tier, model openai/gpt-oss-120b, her own key) on the VLM paper and returned the downloaded DOCX, which was opened and verified in this chat: 38 of 38 paragraphs reviewed, 233 issues (high 75, medium 86, low 72), 233 explanations, 231 suggested fixes, zero failure markers, and content specific to the paper throughout. One gap: the summary section of that download was not generated, because the summary button was not clicked before download; the summary feature is verified separately (Step 6 and the VLM interface test). Full record in BUILD_LOG.md, live run completion entry.


## Addendum 3, 5 November 2026: Gemini run attempted, partial, discarded

A live run against the Gemini free tier (Google AI Studio, model gemini-2.5-flash, her own key, VLM paper) was attempted on 5 November 2026 and its downloaded DOCX (VLM_review_next.docx) was opened and verified in this chat. Result: 12 of 38 paragraphs reviewed, 26 not reviewed, 60 issues (high 34, medium 20, low 6), 60 explanations, 60 suggested fixes, summary not generated. The failed calls returned error 429 (rate limit), with error 503 on the three Introduction paragraphs, and the summary call also returned 429. Cause: the free tier throttled 38 rapid calls. The partial report still exported correctly, which confirms per paragraph failure isolation in real use. This run is discarded as submission evidence and does not replace Addendum 2. The provider path for the final run is Groq with the bounded summary digest fix.


## Addendum 4, 5 November 2026: generality check on unseen papers

At Summaira's instruction that the tool must work on every paper, not only the ones used during development, the application code was audited and the pipeline was run on two unseen papers. Audit: searching src and app.py for the development test papers' names, topics, authors, and file names found nothing; the code holds only generic academic section vocabulary, generic heading rules, and a generic prompt with a generic fallback for unrecognised sections. Pipeline results on unseen papers, all 10 checks passed for both: LIGO gravitational waves paper (physics, arXiv 1602.03837), 16 pages, 74,349 characters, 42 sections, 80 paragraphs, with journal running headers appearing as extra small sections; BERT (arXiv 1810.04805), 16 pages, 64,101 characters, 21 sections, 53 paragraphs, with a few table rows appearing as extra sections. Both imperfections are the already recorded cosmetic heading behaviour; no content was lost and no run failed. The transport in this check was the Step 7 recording test double, as before; live model behaviour is covered by Addendum 2.

## Addendum 5, 5 November 2026: reliability upgrade

Requested by Summaira after a repeated live 401. Changes: settings validation and a preflight connection check in src/llm_client.py, a Test API connection button and a run information line in app.py, automatic retry of 429 and 5xx responses in reviews and in the summary call, and plain language translation of provider errors. Verification, all run after the change: 27 automated tests across 5 files, all passing (11 in test_llm_client.py, including the 6 new ones for validation, preflight, and retry); the VLM end to end interface test passed with its new step, clicking Test API connection returned "Connection OK. The key was accepted and the model openai/gpt-oss-120b is available.", then 38 of 38 paragraphs reviewed with 0 errors and the summary generated in exactly 1 call; a negative interface test with her exact mixed settings (Google AI Studio key, Groq base URL, Groq model) was blocked by validation on both buttons with zero model calls and no stored results; pipeline runs on VLM, Real-ESRGAN, LIGO, and BERT each passed all 10 checks. As in the earlier addenda, the network transport in these tests is a recording double, because no real key exists in this environment; the live behaviour of a correct Groq key remains the verified run in Addendum 2, and the mixup blocking was verified against the same validation logic her screenshot failed.

## Addendum 6, 5 November 2026: resumable runs, preflight fallback

Added after Summaira confirmed she is using her Google AI Studio key: review runs are resumable (an earlier run's successful paragraphs are kept, only missing and failed paragraphs are called again), and the preflight check falls back to one tiny test chat call when a provider endpoint has no model list. Verification: 29 automated tests, all passing, including new tests that resume kept the exact earlier result for one paragraph and made only 2 calls for the remaining failed and unreviewed paragraphs, and that preflight passed through the fallback probe and failed plainly on a probe rejected with 401. The VLM interface test passed (Connection OK, 38 of 38, summary in 1 call) and the mixed settings negative test still blocks with zero model calls. Live Gemini behaviour with the resumable build is hers to confirm in the app; the earlier discarded Gemini run predates both retry and resume.

## Addendum 7: any provider, any paper checks (5 November 2026)

Provider generality: validation and preflight tests now cover an OpenRouter style set (sk-or key, openrouter.ai address, google/gemini model id) and a Together style set, both passing; Google Gemma model names are accepted on the Google endpoint after a false block was found and fixed. Paper generality: Attention Is All You Need (arXiv 1706.03762): 15 pages, 39,483 characters, 39 paragraphs, all 10 pipeline checks passed. Bahdanau et al. (arXiv 1409.0473): 15 pages, 50,136 characters, 34 sections, 58 paragraphs, all 10 checks passed. Project total is now 31 automated tests, all passing.

## Addendum 8: pacing and live progress (5 November 2026)

Free tier pacing: batch calls are spaced at least 5 seconds apart, rate limit retries wait 30, 60, then 120 seconds, and long waits are announced on screen. A fake clock test proves the pacing gaps, the patient first wait, and the status messages. The v6 package passed a full end to end interface run from a clean extraction with real pacing active (3 minutes 57 seconds wall clock): Connection OK, 38 of 38 paragraphs, 0 errors, summary in 1 call. Live progress (v7): the progress bar label carries the paragraph count and percentage, a status line reports the running tally after every paragraph, and a finished run states the exact reviewed count, with a warning and the retry instruction when some paragraphs hit the limit. The v7 package passed the same end to end run from a clean extraction (pacing disabled inside that test only, since pacing itself is proven by the unit test and the v6 run): 38 of 38, the completion message "All 38 paragraphs reviewed successfully.", progress at 100 percent.

## Addendum 9: fast calm runs and saved progress (6 November 2026, build v8)

Changes: batch rate limit policy rebuilt in src/llm_client.py (one 20 second pause and one retry per limited paragraph, then a saved for later entry; circuit breaker after 3 in a row; 5 second single retry for server errors; pacing 2 seconds), calmer progress and completion wording in app.py, and progress saved to disk after every paragraph via the new src/progress_store.py with restore on re-upload of the same paper. Verification: 38 automated tests across 6 files, all passing (19 in test_llm_client.py including the new policy tests, 3 in the new test_progress_store.py). The VLM end to end interface test passed from the repo: Connection OK, 38 of 38 paragraphs, 0 errors, summary in exactly 1 call, and the on disk progress file verified to hold all 38 results plus the summary. Two extra session checks: a brand new app session restored 38 of 38 results from the saved file on upload alone (no run click, no model calls), and a real time pass against a double that answers 429 to everything finished 38 paragraphs in 64.0 seconds using only 6 provider calls, every paragraph marked saved for later. As before, network transport in the interface test is a recording double; live provider behaviour with her own key remains hers to run, now with the fixed policy.

## Addendum 10: batched reviewing (6 November 2026, build v9)

Change: review_all in src/llm_client.py now groups pending paragraphs into batches (plan_batches: at most 5 paragraphs, at most 8,000 characters per call), sends one call per batch with per paragraph ids and prompts (build_batch_messages, BATCH_SYSTEM_PROMPT), parses per id answers (parse_batch_response), reviews any missing paragraph individually, and runs batches in parallel waves of 3 under one shared call limiter. Rate limiting is handled per batch with the same brief policy and circuit breaker as Addendum 9. Verification: 40 automated tests across 6 files, all passing. The pipeline runner passed all 10 checks on the VLM paper (38 paragraphs, 10 review calls plus summary), Attention Is All You Need (39 paragraphs), and Bahdanau et al. (58 paragraphs). The VLM end to end interface test passed in about 22 seconds: Connection OK, 38 of 38 paragraphs, 0 errors, exactly 10 review calls and 1 summary call, DOCX button present, and the on disk progress file verified. The dead quota timing check improved to 24.0 seconds for a full 38 paragraph pass with 6 provider calls. Network transport in these tests is a recording double, as before; live timings will depend on the provider's per call latency, which batching reduces in count but cannot control.

## Addendum 11: Windows save crash fix (6 November 2026, build v10)

The bug: on the user's Windows laptop, the first live v9 run crashed with PermissionError (WinError 5) at os.replace inside src/progress_store.py. Windows locks a just written file against replacement in a way Linux does not, and every test in this project runs on Linux, so the battery passed over a Windows only fault. The fix: replace retries with short delays, a direct write fallback, and save failures reported as a False return plus one calm in app warning, never as an exception. Verification: 43 automated tests across 6 files, all passing, including three new simulations of the Windows failure in test_progress_store.py (transient lock retried to success on the third attempt, permanent lock falling back to a direct write with the payload intact, and total failure returning False without raising). The VLM end to end interface test passed normally (10 review calls, 1 summary call, progress file verified), and a variant of it with the Windows lock forced on every save also passed end to end: the run completed with 38 of 38 results and the progress file landed through the fallback. That variant is the honest limit of what can be proven from a Linux environment, and it is recorded as such.

## Addendum 12: empty report notice (6 November 2026, build v11)

Change: app.py report section shows an explicit notice when reviewed_paragraphs is 0 and error_paragraphs is nonzero, explaining that the report is empty because every paragraph hit the provider limit, with the two ways forward. Verification: the 43 automated tests still pass; the normal VLM interface test still passes; and a dedicated interface check with a provider double that answers 429 to every call passed: the run completed in about 29 seconds, all 38 paragraphs were marked saved for later, no exception was raised, and the new notice was present in the rendered warnings. Context: the live run that prompted this had a genuinely exhausted Gemini free allowance, so the zero issue report was accurate; the fault fixed here is presentation, not counting.

## Addendum 13: Final build verification (2026-11-06)
Requested after a live run where a fresh Google key in the same (already spent) project passed the old list-only connection test and the run then saved all 38 paragraphs for later. Changes: (1) the connection test now ends with one tiny real generation call, so a spent quota fails once, before a run, with the explanation that a new key in the same account or project does not reset the limit; (2) refused batches are retried, then split into smaller batches down to single paragraphs, with splitting latched off after the first fully refused branch and the circuit breaker unchanged, so a dead quota stays bounded (14 calls on a 20 paragraph paper in unit tests); (3) the report always states reviewed vs saved-for-later counts; (4) the sidebar carries no version label. Gate, all run on the extracted final package: 45 unit tests across 6 files pass; full VLM interface test passes (38 of 38, 0 errors, progress saved, summary in 1 call); a fresh session restores 38 of 38 from disk on upload alone; the Google settings shape passes end to end with the new probe message; a refused-everything provider now stops the run at the connection check with the quota message and creates no results, and after the provider recovers, the same session completes 38 of 38; a probe-passes-but-reviews-refused pass (per minute token ration) splits down, saves all 38 for later without crashing, and the report explains the empty result; pipeline checks pass on VLM, Attention, and Bahdanau; the server from the extracted folder returns HTTP 200. Package: paper-review-assistant-final.zip. Still not testable from the build environment: a live run with the user's real key (none exists here, by design) and genuine Windows behaviour (covered by simulation).
