# Interface decision, Paper Review Assistant

Date: 5 November 2026
Status: DECIDED by Summaira on 5 November 2026. Keep Streamlit, polished properly (Option A below). The theme foundation was added the same day: .streamlit/config.toml with the project colours and font, and a styled header in app.py. Both were tested with Streamlit AppTest, see the addendum in BUILD_LOG.md.

## The key fact

Professor Tao did not name any technology. His translated requirement is only that the tool must have a software interface, and that the user must be able to set their own prompts for each paragraph. Streamlit was our choice in the build plan, not his instruction. We are free to choose, and we should choose on purpose.

## What will actually impress him

He is a computer science professor assessing a future master's student in AI. The impressive parts of this project are not the web framework name. They are:

1. The review logic works. Each paragraph is reviewed with its own prompt, and changing a prompt changes that paragraph's review. We will prove this with a test.
2. The output is structured and useful: issue, severity, explanation, and a concrete suggested fix, not one vague paragraph of feedback.
3. Long papers are handled properly, with progress shown and failures handled cleanly.
4. A second pass combines the paragraph reviews into an overall summary with strengths and issues grouped by section.
5. The exported report looks professional.
6. The code is clean, separated into modules, tested step by step, and Summaira can explain every part of it herself.
7. The GitHub repo has a clear README, an architecture description, screenshots, and a sample report from a real paper.

A fancy interface with weak review logic would fail on all seven points. A polished simple interface with strong logic passes all seven.

## Options checked

### Option A, Streamlit, polished properly (recommended)

What it is: a Python only web interface. Upload, paragraph cards, prompt editors, results, and report view all in Streamlit, with a custom theme and layout so it does not look like a default tutorial app.

Strengths:
- One language, Python. Summaira can explain every line.
- File upload, text areas for per paragraph prompts, session state, progress bars, and download buttons are all built in and reliable.
- Fastest route to a fully working tool, so most of our time goes into review quality, which is the part he is grading.
- Runs locally and can also be shared as a live link.

Weakness and the fix:
- A default Streamlit app looks basic. That is a styling problem, not a capability problem. Fix: custom theme colours, a proper header, a sidebar for API settings, three clear tabs (Upload, Review, Report), one styled card per paragraph, and severity labels in the results. None of this is extra feature scope, it is presentation of the required features.

Risk: low.

### Option B, Flask or FastAPI with a custom HTML front end

What it is: a Python back end with hand written HTML, CSS, and JavaScript pages.

Strengths:
- Looks the most like a custom software product, with full control over every pixel.

Weaknesses:
- Two stacks to build and explain, Python plus JavaScript. More moving parts, more places for bugs.
- Two to three times the interface work, and that time comes directly out of review quality, testing, and the report.
- Summaira's application is for an AI master's. Spending the assessment on web development sends the wrong signal about where her strength is.

Risk: medium to high, mainly time and reliability.

### Option C, Gradio

What it is: another Python demo interface tool, common for machine learning demos.

Weaknesses:
- Built for single input and output demos. A long list of paragraphs, each with its own editable prompt and its own result, fights against its design.
- Less control over layout and report export than Streamlit.

Risk: low to build, high that the per paragraph workflow feels cramped. Not recommended.

### Option D, React plus FastAPI

Weaknesses:
- The heaviest option by far. A separate front end project, a separate back end, and a build pipeline, for a tool whose value is its LLM logic.
- Hardest for Summaira to explain in full if he asks questions.

Risk: high. Not recommended.

## Safety built into our current structure

Step 1 already separates the real logic (src/pdf_extract.py, src/segmentation.py, src/prompts.py, src/llm_client.py, src/report.py) from the interface (app.py). The logic does not depend on Streamlit. If we ever wanted a different interface later, only app.py would change. That separation is itself a good design point to show the professor.

## Recommendation

Keep Streamlit, but hold it to a product standard, not a tutorial standard:

- Custom theme and clean header, no default Streamlit look.
- Sidebar for API key, base URL, and model name, with a clear note that the key is never stored.
- Three tabs: Upload, Review, Report.
- One card per paragraph, showing the paragraph text, its editable prompt, and later its review result.
- Progress bar during review, clear error messages, and a formatted DOCX report export.
- Screenshots taken only after this polish, so the GitHub repo shows the finished standard.

This keeps the scope exactly on his two requirements, protects the timeline, and puts our effort where he will actually judge it: the quality and correctness of the review engine.
