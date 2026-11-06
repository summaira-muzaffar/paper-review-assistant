"""Section and paragraph splitting.

Built in Step 3.

Job: take the page texts produced by Step 2 and split them into
sections, each holding its paragraphs in order. Later steps work
on this structure: Step 4 attaches one review prompt to each
paragraph, and Step 5 sends each paragraph to the LLM.

The method is rule based and explainable, with no machine
learning:
1. A line is treated as a section heading when it matches a known
   academic heading (Abstract, Introduction, Methodology, and so
   on, with or without a number), when it is a short numbered
   heading, or when it is a short line in all capital letters.
2. Inside a section, a blank line in the extracted text ends one
   paragraph and starts the next. Wrapped lines inside a
   paragraph are joined with a space, and a word split across
   lines by a hyphen is joined back together.
3. Lines that are only a page number are dropped.
4. Text before the first heading is kept in a section called
   Front Matter, so nothing from the paper is lost.
5. Very long blocks are split into paragraph sized chunks on
   sentence boundaries, because two column papers often extract
   with few blank lines (added in Step 7, after real paper
   testing showed merged blocks of several thousand characters).
"""

import re

FRONT_MATTER_TITLE = "Front Matter"

KNOWN_HEADINGS = {
    "abstract",
    "introduction",
    "background",
    "related work",
    "literature review",
    "methodology",
    "methods",
    "proposed method",
    "approach",
    "system design",
    "implementation",
    "experiments",
    "experimental setup",
    "evaluation",
    "results",
    "results and discussion",
    "discussion",
    "analysis",
    "conclusion",
    "conclusions",
    "conclusion and future work",
    "future work",
    "limitations",
    "acknowledgements",
    "acknowledgments",
    "references",
    "bibliography",
    "appendix",
}

NUMBER_PREFIX = re.compile(r"^\d+(\.\d+)*\.?\s+")
NUMBERED_HEADING = re.compile(r"^\d+(\.\d+)*\.?\s+\S.*$")


def _normalise_heading(line):
    """Remove a leading section number from a heading line."""
    return NUMBER_PREFIX.sub("", line).strip()


def is_section_heading(line):
    """Return True when a single text line looks like a heading.

    A heading is a short line, never a sentence, that either names
    a known academic section, carries a section number, or is
    written in all capital letters.
    """
    text = line.strip()
    if not text or len(text) > 80:
        return False
    if text.endswith(".") or text.endswith(","):
        return False
    if len(text.split()) > 8:
        return False

    if _normalise_heading(text).lower() in KNOWN_HEADINGS:
        return True
    if NUMBERED_HEADING.match(text) and text[0].isdigit():
        # Real section numbers in a paper are small. A line that
        # starts with a year, such as a date range in a document,
        # is not a heading.
        first_number = int(re.match(r"^\d+", text).group())
        if first_number <= 30:
            return True
    letters = [char for char in text if char.isalpha()]
    # All capital headings are phrases or single section words,
    # and they never contain digits. A line with digits in it,
    # such as a grade line, is data, not a heading.
    if (
        not any(char.isdigit() for char in text)
        and len(letters) >= 3
        and all(char.isupper() for char in letters)
    ):
        words = text.split()
        # Short all capital tokens in a paper are usually acronyms
        # or model names in figures and tables, not headings. A
        # one word heading must either be a known section name or
        # a long word, like EDUCATION.
        if len(words) >= 2:
            return True
        word = words[0].strip(":")
        if word.lower() in KNOWN_HEADINGS or len(word) >= 8:
            return True
    return False


MAX_PARAGRAPH_CHARS = 2000


def _chunk_long_text(text):
    """Split one very long block of text into paragraph sized
    chunks on sentence boundaries.

    Two column papers often extract with few blank lines, so
    several true paragraphs arrive as one large block. Reviewing
    such a block in one model call would be slow and unfocused.
    Blocks up to MAX_PARAGRAPH_CHARS pass through unchanged.
    """
    if len(text) <= MAX_PARAGRAPH_CHARS:
        return [text]
    sentences = re.split(r"(?<=[.!?])\s+", text)
    chunks = []
    current = ""
    for sentence in sentences:
        if current and len(current) + len(sentence) + 1 > MAX_PARAGRAPH_CHARS:
            chunks.append(current)
            current = sentence
        else:
            current = f"{current} {sentence}".strip()
    if current:
        chunks.append(current)
    return chunks


def _lines_from_pages(pages):
    """Flatten page texts into lines, marking page breaks as blank."""
    lines = []
    for page in pages:
        lines.extend(page.splitlines())
        lines.append("")
    return lines


def split_into_sections(pages):
    """Split page texts into sections with their paragraphs.

    Args:
        pages: list of page text strings from Step 2 extraction.

    Returns:
        A list of sections in document order. Each section is a
        dictionary with a title (str) and paragraphs (list of
        str). Sections with no paragraphs are not returned.
    """
    sections = []
    current_title = FRONT_MATTER_TITLE
    current_paragraphs = []
    paragraph_lines = []

    def flush_paragraph():
        if paragraph_lines:
            text = " ".join(paragraph_lines).strip()
            if text:
                current_paragraphs.extend(_chunk_long_text(text))
            paragraph_lines.clear()

    def flush_section():
        flush_paragraph()
        if current_paragraphs:
            sections.append(
                {"title": current_title, "paragraphs": list(current_paragraphs)}
            )
            current_paragraphs.clear()

    for raw_line in _lines_from_pages(pages):
        line = raw_line.strip()
        if line.isdigit():
            continue
        if is_section_heading(line):
            flush_section()
            current_title = line
            continue
        if not line:
            flush_paragraph()
            continue
        if paragraph_lines and paragraph_lines[-1].endswith("-"):
            paragraph_lines[-1] = paragraph_lines[-1][:-1] + line
        else:
            paragraph_lines.append(line)

    flush_section()
    return sections


def count_paragraphs(sections):
    """Return the total number of paragraphs across all sections."""
    return sum(len(section["paragraphs"]) for section in sections)
