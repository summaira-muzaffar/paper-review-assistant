"""Review prompts.

Built in Step 4.

Job: hold the default review prompt and manage one editable
prompt per paragraph. This module is the heart of Professor
Tao's second hard requirement: the user must be able to set
their own prompts for each paragraph.

How prompt identity works: every paragraph in the paper has a
stable key built from its position, for example s0_p1 means
section 0, paragraph 1 (counting from 0, as code does). The
interface stores the prompt text for each paragraph under a
widget key built from that same identity, so an edit to one
paragraph can never leak into another paragraph.

The default prompt is not identical for every section. A short
focus line is added for known section types, because a good
reviewer reads an abstract differently from a reference list.
The user can edit or fully replace any of it, per paragraph.
"""

BASE_REVIEW_PROMPT = (
    "You are an experienced academic reviewer. Review the paragraph "
    "below from a research paper. Identify the most important problems "
    "with clarity, logic, evidence, and academic writing. For each "
    "problem, state the issue, explain why it matters, and give a "
    "concrete suggested fix. Point at exact phrases where you can. "
    "If the paragraph is strong, say briefly what makes it strong. "
    "Do not rewrite the whole paragraph."
)

SECTION_FOCUS = {
    "abstract": "Focus extra attention on whether the abstract states the problem, the method, the main result, and the conclusion, in that order.",
    "introduction": "Focus extra attention on whether the research problem, the gap, and the aim of the work are stated clearly.",
    "related work": "Focus extra attention on whether earlier work is compared and criticised, not only listed.",
    "literature review": "Focus extra attention on whether earlier work is compared and criticised, not only listed.",
    "method": "Focus extra attention on whether another researcher could repeat the work from this description alone.",
    "experiment": "Focus extra attention on whether the setup, the data, and the evaluation measures are described completely.",
    "result": "Focus extra attention on whether each claim is supported by a number, a table, or a figure reference.",
    "discussion": "Focus extra attention on whether the findings are interpreted and compared with earlier work, not only repeated.",
    "conclusion": "Focus extra attention on whether the conclusion matches what the paper actually showed, without new claims.",
    "reference": "Focus extra attention on citation completeness and consistent reference formatting.",
    "limitation": "Focus extra attention on whether the limitations are stated honestly and specifically.",
}

GENERIC_FOCUS = "Focus extra attention on structure and on whether each sentence follows from the one before it."


def _focus_for_section(section_title):
    """Pick the focus line that matches a section title."""
    title = section_title.lower()
    for keyword, focus in SECTION_FOCUS.items():
        if keyword in title:
            return focus
    return GENERIC_FOCUS


def get_default_prompt(section_title):
    """Return the full default review prompt for a section."""
    return f"{BASE_REVIEW_PROMPT} {_focus_for_section(section_title)}"


def paragraph_key(section_index, paragraph_index):
    """Return the stable identity of one paragraph."""
    return f"s{section_index}_p{paragraph_index}"


def prompt_widget_key(section_index, paragraph_index):
    """Return the interface state key holding one prompt text."""
    return f"prompt_{paragraph_key(section_index, paragraph_index)}"


def collect_prompts(sections, state):
    """Collect the current prompt for every paragraph.

    Args:
        sections: the section structure from Step 3.
        state: a mapping of interface state, for example Streamlit
            session state. When a paragraph has no stored prompt,
            its section default is used.

    Returns:
        A dictionary mapping each paragraph key to its prompt.
    """
    prompts = {}
    for section_index, section in enumerate(sections):
        for paragraph_index in range(len(section["paragraphs"])):
            key = paragraph_key(section_index, paragraph_index)
            widget_key = prompt_widget_key(section_index, paragraph_index)
            prompts[key] = state.get(widget_key) or get_default_prompt(
                section["title"]
            )
    return prompts
