"""LLM integration.

Built in Step 5.

Job: send one paragraph, together with that paragraph's own
review prompt from Step 4, to a large language model, and return
the answer as structured data: a list of issues, where each issue
has a severity, an explanation, and a suggested fix, plus a list
of strengths.

The model is reached through an OpenAI compatible API. The user
supplies their own API key, base URL, and model name in the
interface, so the same code works with DeepSeek or any similar
service. No key is stored anywhere in this project.

Reliability rules:
- The model is instructed to answer with JSON only, in a fixed
  shape, so the interface can display issues one by one instead
  of showing one block of free text.
- If a model still answers in free text, the raw answer is kept
  as a single fallback issue. A review is never silently lost.
- A failure on one paragraph is recorded as an error entry for
  that paragraph. The remaining paragraphs are still reviewed.
- Settings are validated before any call: an API key, base URL,
  and model from different providers (a mix that can never work)
  is stopped with one plain message instead of failing on every
  paragraph. A preflight check then verifies the key and model
  against the provider before a full run starts.
- Paragraphs are reviewed in small batches, not one call per
  paragraph: each batch call carries several paragraphs, each
  with its own prompt, and must answer with one result per
  paragraph id. Batching cuts the request count roughly five
  fold, which is what a per minute and per day rationed free
  tier actually charges for, and batches run a few at a time
  in parallel waves. Correctness does not depend on the model
  behaving: every returned id is checked, and any paragraph
  missing from a batch answer is reviewed again on its own.
- Temporary provider failures are retried, with a policy that
  matches the call. A single call on its own (and the overall
  summary) retries patiently with growing waits. A batch run
  uses an adaptive policy, tuned on live free tier use: a rate
  limited batch gets one short wait and one retry, then it is
  split into smaller batches and retried, because per minute
  token rations refuse large requests that smaller ones fit
  under. Only when even a single paragraph is refused is it
  saved for later, and if several batches in a row end that
  way the run stops calling the provider for the rest of that
  pass and saves the remaining paragraphs for later at once.
  A spent quota becomes a short run with a clear result, never
  an hours long crawl of long waits.
- The connection check ends with one tiny real generation
  call, not just the provider's model list. A list answer
  costs the provider nothing and proves nothing about review
  calls: a key whose project quota is already spent passes a
  list-only check and then fails on every paragraph. The probe
  makes "Connection OK" mean a review call actually works,
  and a refused probe fails once, here, with the quota
  explanation, instead of once per paragraph.
- Runs are resumable: pressing run again with earlier results
  present reviews only the paragraphs that are missing or
  failed, so a rate limited run is finished by waiting and
  rerunning, never by starting over.
- Every error the user sees is translated into plain language
  with the action to take, with the raw code kept for reference.
"""

import json
import re
import threading
import time
from concurrent.futures import ThreadPoolExecutor

from src.prompts import paragraph_key

DEFAULT_BASE_URL = "https://api.deepseek.com"
DEFAULT_MODEL = "deepseek-chat"

LANGUAGE_INSTRUCTIONS = {
    "en": "Write your answer in English.",
    "zh": "Write your answer in Simplified Chinese.",
}

SYSTEM_PROMPT = (
    "You are an academic paper review engine. You always answer "
    "with valid JSON only, with no text before or after it. The "
    "JSON must have exactly these keys: "
    '"issues": a list of objects, each with "issue", "severity" '
    '(one of "high", "medium", "low"), "explanation", and '
    '"suggested_fix"; and "strengths": a list of short strings. '
    "If the paragraph has no real problems, return an empty "
    "issues list and describe its strengths."
)


class LlmError(Exception):
    """Raised when a model call fails.

    Carries the provider status code when one is known, so the
    interface can act on it (for example, retry a rate limit).
    """

    def __init__(self, message, status_code=None):
        super().__init__(message)
        self.status_code = status_code


RETRYABLE_STATUS_CODES = {429, 500, 502, 503, 504}
# Used by single calls (one paragraph on its own, and the
# overall summary): a patient retry is right there, because
# there is only one call to wait for.
DEFAULT_RETRY_DELAYS = (30, 60, 120)
# The batch run policy (see the module docstring): one short
# wait and one retry for a rate limited paragraph, one short
# wait and one retry for a server error, then the paragraph is
# recorded and the run moves on. After this many paragraphs in
# a row end rate limited, the run stops calling the provider
# for the rest of the pass.
RATE_LIMIT_WAIT_SECONDS = 20
SERVER_ERROR_WAIT_SECONDS = 5
RATE_LIMIT_CIRCUIT_LIMIT = 3
RATE_LIMIT_MESSAGE = (
    "Saved for later: the provider rate limit was reached, so "
    "this paragraph will be finished on the next Run review. "
    "Everything already reviewed is kept."
)
DEFAULT_PACE_SECONDS = 2.0
# Batching: at most this many paragraphs per model call, and
# at most this many characters of paragraph plus prompt text
# per call, so answers stay complete and requests stay well
# inside per minute token rations. Batches run in parallel
# waves of at most DEFAULT_MAX_WORKERS at a time.
MAX_BATCH_ITEMS = 5
MAX_BATCH_CHARS = 8000
DEFAULT_MAX_WORKERS = 3

BATCH_SYSTEM_PROMPT = (
    "You are an academic paper review engine. You always answer "
    "with valid JSON only, with no text before or after it. The "
    "JSON must be a single object whose keys are the item ids "
    "given in the request, one entry per item, and every item id "
    "must be present exactly once. Each entry must have exactly "
    'these keys: "issues": a list of objects, each with "issue", '
    '"severity" (one of "high", "medium", "low"), "explanation", '
    'and "suggested_fix"; and "strengths": a list of short '
    "strings. If an item has no real problems, return an empty "
    "issues list for it and describe its strengths."
)


def status_code_of(error):
    """Return the HTTP status code carried by an API error."""
    code = getattr(error, "status_code", None)
    if isinstance(code, int):
        return code
    match = re.search(r"[Ee]rror code: (\d{3})", str(error))
    if match:
        return int(match.group(1))
    return None


def friendly_error(error):
    """Translate an API error into plain language with the fix.

    Live use produced every one of these codes, and the raw
    provider message alone left the user guessing. Each branch
    names the cause and the one action that resolves it. The raw
    code is kept at the end for reference.
    """
    code = status_code_of(error)
    if code == 401:
        return (
            "Invalid API key for this provider (error 401). The key, "
            "the API base URL, and the model must all come from the "
            "same provider. Check that the three sidebar fields are "
            "one matching set, then use Test API connection."
        )
    if code == 402:
        return (
            "The provider account has no API balance (error 402). "
            "Top up the account that owns this key, or switch to a "
            "provider and key with balance or a free tier."
        )
    if code == 404:
        return (
            "The model name was not found at this provider "
            "(error 404). Check the model name in the sidebar for a "
            "typo or a model the provider no longer offers."
        )
    if code == 413:
        return (
            "The request was too large for this provider "
            "(error 413). Shorten the input, or use a model or tier "
            "with a higher per minute token limit."
        )
    if code == 429:
        return (
            "The provider rate limit was reached (error 429). "
            "Paragraphs that hit it are saved for later and "
            "finished on the next Run review; everything already "
            "reviewed is kept."
        )
    if code in (500, 502, 503, 504):
        return (
            f"The provider's server was unavailable (error {code}). "
            "The app retries automatically; if it still fails, wait "
            "a few minutes and try again."
        )
    return f"The model call failed: {error}"


def validate_settings(api_key, base_url, model):
    """Check that key, base URL, and model belong together.

    Returns a list of plain language problems. An empty list
    means the three fields are a consistent set. This catches
    the most expensive beginner mistake in this tool, pasting
    one provider's key next to another provider's address, before
    a single call is made: that mix can never work, and without
    this check it fails identically on every paragraph.
    """
    problems = []
    key = (api_key or "").strip()
    url = (base_url or "").strip().lower()
    model_name = (model or "").strip()
    if not key:
        problems.append("Enter your API key in the sidebar first.")
        return problems
    key_is_groq = key.startswith("gsk_")
    key_is_google = key.startswith(("AIza", "AQ."))
    url_is_groq = "api.groq.com" in url
    url_is_google = "generativelanguage.googleapis.com" in url
    url_is_deepseek = "api.deepseek.com" in url
    if key_is_groq and not url_is_groq:
        problems.append(
            "This looks like a Groq key (it starts with gsk_) but "
            "the API base URL is not Groq's. Groq keys only work "
            "with https://api.groq.com/openai/v1."
        )
    if key_is_google and not url_is_google:
        problems.append(
            "This looks like a Google AI Studio key (it starts "
            "with AIza or AQ.) but the API base URL is not "
            "Google's. That key only works with the Google base "
            "URL and a Gemini model."
        )
    if url_is_groq and not key_is_groq:
        problems.append(
            "The API base URL is Groq's, but the key does not look "
            "like a Groq key (Groq keys start with gsk_). Paste "
            "the key from console.groq.com."
        )
    if url_is_google and not key_is_google:
        problems.append(
            "The API base URL is Google's, but the key does not "
            "look like a Google AI Studio key (those start with "
            "AIza or AQ.)."
        )
    if url_is_deepseek and (key_is_groq or key_is_google):
        problems.append(
            "The API base URL is DeepSeek's, but the key comes "
            "from another provider. DeepSeek needs its own key "
            "from platform.deepseek.com."
        )
    if url_is_groq and model_name.startswith("gemini"):
        problems.append(
            "The model name is a Gemini model but the API base "
            "URL is Groq's. Use one provider's key, address, and "
            "model together."
        )
    if (
        url_is_google
        and model_name
        and not model_name.startswith(("gemini", "gemma", "models/"))
    ):
        problems.append(
            "The API base URL is Google's but the model name is "
            "not a Google model. Use a model name that starts "
            "with gemini or gemma."
        )
    if url_is_deepseek and (
        model_name.startswith("gemini") or model_name.startswith("openai/")
    ):
        problems.append(
            "The API base URL is DeepSeek's but the model name "
            "belongs to another provider."
        )
    return problems


def call_with_retry(operation, retry_delays=DEFAULT_RETRY_DELAYS, sleep=None):
    """Run one API call, retrying temporary provider failures.

    Rate limits (429) and server errors (5xx) usually clear
    within seconds or a minute, so waiting and retrying is the
    correct response. Any other failure (a wrong key, a missing
    model, no balance) is raised at once, because retrying it
    would only waste time. sleep is injectable so tests can run
    instantly.
    """
    if sleep is None:
        sleep = time.sleep
    attempts = 0
    while True:
        try:
            return operation()
        except Exception as error:
            code = status_code_of(error)
            if code in RETRYABLE_STATUS_CODES and attempts < len(retry_delays):
                sleep(retry_delays[attempts])
                attempts += 1
                continue
            raise


def preflight_check(api_key, base_url, model, client=None):
    """Verify the settings against the provider before a run.

    Returns (ok, message). First the offline pairing validation
    runs, so a mixed provider set fails with no network use at
    all. Then the provider's model list is checked: it proves
    the key is accepted and confirms the model exists. Last,
    one tiny real generation call is made, because the list
    check alone cannot see a spent quota: the list costs the
    provider nothing, so a key whose project quota is already
    exhausted passes it and then fails on every paragraph.
    A provider whose compatible endpoint offers no model list
    (a 404, 405, or 501 from that one call) skips straight to
    the test call, so a working setup is never blocked by a
    missing list.
    """
    problems = validate_settings(api_key, base_url, model)
    if problems:
        return False, problems[0]
    if client is None:
        client = _create_client(api_key, (base_url or "").strip())
    model_name = (model or "").strip()

    def probe():
        client.chat.completions.create(
            model=model_name,
            messages=[
                {"role": "system", "content": "You are a connection test."},
                {"role": "user", "content": "Reply with OK."},
            ],
            temperature=0,
        )

    try:
        listing = client.models.list()
        model_ids = [
            str(getattr(item, "id", "")) for item in getattr(listing, "data", [])
        ]
    except Exception as error:
        if status_code_of(error) not in (404, 405, 501):
            return False, friendly_error(error)
        try:
            probe()
        except Exception as probe_error:
            return False, friendly_error(probe_error)
        return True, (
            "Connection OK. The key was accepted in a test call "
            f"and the model {model_name} answered."
        )
    accepted = set(model_ids)
    for model_id in model_ids:
        # Google's model list returns ids like
        # "models/gemini-2.5-flash" while chat calls use the
        # short name, so the short form counts as a match too.
        if "/" in model_id:
            accepted.add(model_id.split("/", 1)[1])
    if model_ids and model_name and model_name not in accepted:
        examples = ", ".join(sorted(accepted)[:5])
        return False, (
            f"Model not found at this provider: {model_name}. "
            f"Models this key can use include: {examples}. Fix the "
            "model name in the sidebar."
        )
    try:
        probe()
    except Exception as probe_error:
        if status_code_of(probe_error) == 429:
            return False, (
                "The key and the model are correct, but the "
                "provider refused a test review call: its rate "
                "limit or quota is already reached (error 429). "
                "A new key in the same account or project does "
                "not reset that limit. Wait for the limit to "
                "reset, or switch the sidebar to a different "
                "provider set, then test again."
            )
        return False, friendly_error(probe_error)
    return True, (
        "Connection OK. The key was accepted, the model "
        f"{model_name} is available, and a test review call "
        "succeeded."
    )


def build_review_messages(section_title, paragraph_text, user_prompt, output_language="en"):
    """Build the chat messages for reviewing one paragraph.

    The user's own prompt for this paragraph comes first, then
    the section name and the paragraph itself, then the output
    language instruction. This is the exact point where the
    per paragraph prompt from Step 4 reaches the model.
    """
    language_instruction = LANGUAGE_INSTRUCTIONS.get(
        output_language, LANGUAGE_INSTRUCTIONS["en"]
    )
    user_message = (
        f"{user_prompt}\n\n"
        f"Section: {section_title}\n\n"
        f"Paragraph:\n{paragraph_text}\n\n"
        f"{language_instruction}"
    )
    return [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user_message},
    ]


def parse_review_response(raw_text):
    """Parse a model answer into the structured review shape.

    Accepts plain JSON or JSON wrapped in code fences. Free text
    answers fall back to one issue holding the raw text, so the
    content is preserved instead of dropped.
    """
    text = (raw_text or "").strip()
    cleaned = text
    if cleaned.startswith("```"):
        lines = cleaned.splitlines()
        cleaned = "\n".join(
            line for line in lines if not line.strip().startswith("```")
        ).strip()
    try:
        data = json.loads(cleaned)
        issues = []
        for item in data.get("issues", []):
            issues.append(
                {
                    "issue": str(item.get("issue", "")).strip(),
                    "severity": str(item.get("severity", "medium")).strip().lower(),
                    "explanation": str(item.get("explanation", "")).strip(),
                    "suggested_fix": str(item.get("suggested_fix", "")).strip(),
                }
            )
        strengths = [str(item).strip() for item in data.get("strengths", [])]
        return {"issues": issues, "strengths": [s for s in strengths if s]}
    except (ValueError, AttributeError, TypeError):
        return {
            "issues": [
                {
                    "issue": "The model answered in free text instead of the requested structure.",
                    "severity": "low",
                    "explanation": text,
                    "suggested_fix": "",
                }
            ],
            "strengths": [],
        }


def _create_client(api_key, base_url):
    from openai import OpenAI

    return OpenAI(api_key=api_key, base_url=base_url or None)


def review_paragraph(
    section_title,
    paragraph_text,
    user_prompt,
    api_key,
    base_url=DEFAULT_BASE_URL,
    model=DEFAULT_MODEL,
    output_language="en",
    client=None,
    retry_delays=DEFAULT_RETRY_DELAYS,
    sleep=None,
):
    """Review one paragraph with the model.

    Args:
        client: an optional pre built client with the OpenAI chat
            interface. Tests pass a fake client here, so no real
            API call is needed to verify this module.
        retry_delays: the waits, in seconds, between automatic
            retries of temporary provider failures.
        sleep: the wait function, injectable for tests.

    Returns:
        The structured review dictionary from parse_review_response.

    Raises:
        LlmError: if the API call itself fails, with a plain
            language message and the provider status code.
    """
    if client is None:
        if not api_key:
            raise LlmError("No API key was provided.")
        client = _create_client(api_key, base_url)
    messages = build_review_messages(
        section_title, paragraph_text, user_prompt, output_language
    )

    def call():
        return client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=0.2,
        )

    try:
        response = call_with_retry(call, retry_delays=retry_delays, sleep=sleep)
    except Exception as error:
        raise LlmError(
            friendly_error(error), status_code=status_code_of(error)
        ) from error
    raw_text = response.choices[0].message.content or ""
    return parse_review_response(raw_text)


def build_batch_messages(items, output_language="en"):
    """Build the chat messages for reviewing a batch of items.

    Each item keeps its own paragraph prompt, section, and text,
    under its own id. The model is asked for one result per id,
    so a batch never blurs paragraphs together: the answer is a
    map from id to that paragraph's own structured review.
    """
    language_instruction = LANGUAGE_INSTRUCTIONS.get(
        output_language, LANGUAGE_INSTRUCTIONS["en"]
    )
    parts = [
        "Review each item below independently, using only that "
        "item's own prompt for that item. Return one result per "
        "item id, and include every item id."
    ]
    for position, item in enumerate(items, start=1):
        parts.append(
            f"ITEM {position}\n"
            f"ID: {item['key']}\n"
            f"Section: {item['section_title']}\n"
            f"Prompt: {item['user_prompt']}\n"
            f"Paragraph:\n{item['paragraph_text']}"
        )
    parts.append(language_instruction)
    return [
        {"role": "system", "content": BATCH_SYSTEM_PROMPT},
        {"role": "user", "content": "\n\n".join(parts)},
    ]


def parse_batch_response(raw_text, expected_keys):
    """Parse a batch answer into per paragraph reviews.

    Accepts a JSON object keyed by item id, the same object
    under a "results" key, or a list of objects carrying an
    "id". Returns only the expected keys that came back with a
    usable entry; the caller reviews any missing paragraph on
    its own, so a partial answer can never lose a paragraph.
    """
    text = (raw_text or "").strip()
    cleaned = text
    if cleaned.startswith("```"):
        lines = cleaned.splitlines()
        cleaned = "\n".join(
            line for line in lines if not line.strip().startswith("```")
        ).strip()
    try:
        data = json.loads(cleaned)
    except ValueError:
        return {}
    container = data
    if isinstance(data, dict) and isinstance(data.get("results"), dict):
        container = data["results"]
    if isinstance(data, list):
        container = {}
        for entry in data:
            if isinstance(entry, dict):
                entry_id = entry.get("id") or entry.get("key")
                if entry_id:
                    container[entry_id] = entry
    if not isinstance(container, dict):
        return {}
    parsed = {}
    for key in expected_keys:
        value = container.get(key)
        if isinstance(value, dict):
            parsed[key] = parse_review_response(json.dumps(value))
        elif isinstance(value, str) and value.strip():
            parsed[key] = parse_review_response(value)
    return parsed


def plan_batches(items):
    """Group pending paragraphs into review batches, in order.

    A batch holds at most MAX_BATCH_ITEMS paragraphs and at
    most MAX_BATCH_CHARS of paragraph plus prompt text, so a
    38 paragraph paper needs about 8 calls instead of 38.
    """
    groups = []
    current = []
    current_chars = 0
    for item in items:
        size = len(item["paragraph_text"]) + len(item["user_prompt"])
        if current and (
            len(current) >= MAX_BATCH_ITEMS
            or current_chars + size > MAX_BATCH_CHARS
        ):
            groups.append(current)
            current = []
            current_chars = 0
        current.append(item)
        current_chars += size
    if current:
        groups.append(current)
    return groups


class _CallLimiter:
    """Spaces out the starts of model calls across threads.

    One limiter is shared by every worker in a run, so parallel
    batches still respect the run's pacing instead of each
    thread pacing only itself.
    """

    def __init__(self, pace_seconds, sleep, clock):
        self._pace = pace_seconds
        self._sleep = sleep
        self._clock = clock
        self._lock = threading.Lock()
        self._last_started = None

    def wait_turn(self):
        with self._lock:
            if self._last_started is not None:
                elapsed = self._clock() - self._last_started
                if elapsed < self._pace:
                    self._sleep(self._pace - elapsed)
            self._last_started = self._clock()


def review_all(
    sections,
    prompts,
    api_key,
    base_url=DEFAULT_BASE_URL,
    model=DEFAULT_MODEL,
    output_language="en",
    client=None,
    progress_callback=None,
    result_callback=None,
    sleep=None,
    existing_results=None,
    pace_seconds=DEFAULT_PACE_SECONDS,
    clock=None,
    status_callback=None,
    max_workers=DEFAULT_MAX_WORKERS,
):
    """Review every paragraph of the paper, in order.

    Args:
        sections: the section structure from Step 3.
        prompts: the per paragraph prompts from Step 4, keyed by
            paragraph key.
        progress_callback: optional function called after each
            paragraph with (done, total), for a progress bar.
        result_callback: optional function called with (key,
            result) the moment each paragraph is final. The
            interface uses it to save progress to disk paragraph
            by paragraph, so a closed page, a sleeping laptop,
            or a restarted app can never wipe a half done run.
        existing_results: optional results from an earlier run
            of the same paper. Paragraphs that already have a
            successful review are kept and not called again;
            only missing and failed paragraphs are reviewed.
            This makes runs resumable, which is what a rate
            limited free tier needs: wait for the limit to reset,
            press run again, and only the failed paragraphs are
            retried instead of starting over.
        pace_seconds: the minimum spacing between the starts of
            two model calls. Free tiers ration requests per
            minute, so a batch run stays under the ration by
            pacing itself instead of firing as fast as possible
            and bouncing off the limit.
        clock: the time source for pacing, injectable for tests.
        status_callback: optional function called with a calm
            progress line as results land, and with one short
            notice when the run pauses briefly to stay within
            the provider limit. It never reports a long
            countdown: the run is designed so there is none.
        max_workers: how many batches may be in flight at
            once. Batches run in parallel waves of this size;
            all callbacks still fire from the calling thread, in
            paper order, as each wave lands.

    Batching: pending paragraphs are grouped by plan_batches
    and each group is reviewed with one call that must return
    one result per paragraph id. Any paragraph missing from a
    batch answer is reviewed again on its own, so batching can
    never silently drop a paragraph.

    Rate limit policy: a batch that hits the provider limit
    gets one short wait and one retry; if it still hits the
    limit, the batch is split into two smaller batches and
    each half is retried the same way, down to single
    paragraphs, because per minute token rations refuse large
    requests that smaller ones fit under. If a whole split
    branch comes back refused, splitting stops for the rest
    of the run: the provider is out of quota, not asking for
    smaller requests, and more calls would only burn what is
    left. Paragraphs that are still refused are recorded as
    saved for later (entries with "rate_limited": True). If
    RATE_LIMIT_CIRCUIT_LIMIT batches in a row end that way,
    the run stops calling the provider and records every
    remaining paragraph as saved for later at once. Server
    errors get one short wait and one retry, then the batch's
    paragraphs fall back to individual calls. Any other batch
    failure also falls back to individual calls, where the
    same brief policy applies per paragraph.

    Returns:
        A dictionary mapping each paragraph key to its structured
        review, or to an entry with an "error" message when that
        paragraph's call failed. One failure never stops the rest.
    """
    total = sum(len(section["paragraphs"]) for section in sections)
    results = {}
    done = 0
    wait = sleep if sleep is not None else time.sleep
    now = clock if clock is not None else time.monotonic
    if client is None and api_key:
        client = _create_client(api_key, base_url)
    limiter = _CallLimiter(pace_seconds, wait, now)
    pause_notice = (
        "Pausing briefly to stay within the free plan limit. "
        "Finished paragraphs are saved automatically."
    )

    def note_result(key, result):
        results[key] = result
        if result_callback is not None:
            result_callback(key, result)

    def report_progress():
        if progress_callback is not None:
            progress_callback(done, total)
        if status_callback is not None:
            reviewed = sum(
                1 for result in results.values() if "error" not in result
            )
            saved_later = sum(
                1 for result in results.values() if result.get("rate_limited")
            )
            other_errors = sum(
                1
                for result in results.values()
                if "error" in result and not result.get("rate_limited")
            )
            if saved_later:
                message = (
                    f"Progress: {done} of {total} paragraphs "
                    f"processed. {reviewed} reviewed, {saved_later} "
                    "saved for later."
                )
            elif other_errors:
                message = (
                    f"Progress: {done} of {total} paragraphs "
                    f"processed. {reviewed} reviewed, {other_errors} "
                    "could not be reviewed."
                )
            else:
                message = (
                    f"Progress: {done} of {total} paragraphs "
                    f"processed. {reviewed} reviewed."
                )
            status_callback(message)

    def saved_for_later():
        return {"error": RATE_LIMIT_MESSAGE, "rate_limited": True}

    def call_model(messages):
        limiter.wait_turn()
        if client is None:
            raise LlmError("No API key was provided.")
        return client.chat.completions.create(
            model=model, messages=messages, temperature=0.2
        )

    def review_one(item, notices):
        """Review a single paragraph with the brief policy."""
        attempts = 0
        while True:
            attempts += 1
            try:
                limiter.wait_turn()
                return review_paragraph(
                    item["section_title"],
                    item["paragraph_text"],
                    item["user_prompt"],
                    api_key=api_key,
                    base_url=base_url,
                    model=model,
                    output_language=output_language,
                    client=client,
                    retry_delays=(),
                    sleep=wait,
                )
            except LlmError as error:
                code = error.status_code
                if code == 429 and attempts == 1:
                    notices.append(pause_notice)
                    wait(RATE_LIMIT_WAIT_SECONDS)
                    continue
                if code == 429:
                    return saved_for_later()
                if code in RETRYABLE_STATUS_CODES and attempts == 1:
                    wait(SERVER_ERROR_WAIT_SECONDS)
                    continue
                return {"error": str(error)}

    # Splitting a refused batch only helps while smaller
    # requests actually get through. The first split branch
    # that comes back entirely refused turns splitting off for
    # the rest of the run, so a spent quota costs a bounded
    # number of extra calls instead of a tree of them.
    split_state = {"enabled": True}

    def review_subset(items_subset, notices):
        """Review a subset with one batch call, splitting on limits.

        Returns a result for every item in the subset. Runs in
        a worker thread when waves are parallel, so it touches
        no callbacks: it only returns what it found.
        """
        keys = [item["key"] for item in items_subset]
        messages = build_batch_messages(items_subset, output_language)
        parsed = None
        limited = False
        attempts = 0
        while True:
            attempts += 1
            try:
                response = call_model(messages)
                raw_text = response.choices[0].message.content or ""
                parsed = parse_batch_response(raw_text, keys)
                break
            except Exception as error:
                code = status_code_of(error)
                if code == 429 and attempts == 1:
                    notices.append(pause_notice)
                    wait(RATE_LIMIT_WAIT_SECONDS)
                    continue
                if code == 429:
                    limited = True
                    break
                if code in RETRYABLE_STATUS_CODES and attempts == 1:
                    wait(SERVER_ERROR_WAIT_SECONDS)
                    continue
                break
        if limited:
            if len(items_subset) > 1 and split_state["enabled"]:
                middle = len(items_subset) // 2
                merged = {}
                merged.update(review_subset(items_subset[:middle], notices))
                merged.update(review_subset(items_subset[middle:], notices))
                if not any(
                    "error" not in result for result in merged.values()
                ):
                    split_state["enabled"] = False
                return merged
            return {key: saved_for_later() for key in keys}
        subset_results = {}
        if parsed:
            subset_results.update(parsed)
        for item in items_subset:
            if item["key"] not in subset_results:
                subset_results[item["key"]] = review_one(item, notices)
        return subset_results

    def review_group(group):
        """Review one batch. Returns (results, notices)."""
        notices = []
        return review_subset(group, notices), notices

    pending = []
    for section_index, section in enumerate(sections):
        for paragraph_index, paragraph_text in enumerate(section["paragraphs"]):
            key = paragraph_key(section_index, paragraph_index)
            prior = (existing_results or {}).get(key)
            if prior is not None and "error" not in prior:
                note_result(key, prior)
                done += 1
                report_progress()
            else:
                pending.append(
                    {
                        "key": key,
                        "section_title": section["title"],
                        "paragraph_text": paragraph_text,
                        "user_prompt": prompts[key],
                    }
                )

    groups = plan_batches(pending)
    consecutive_limited_groups = 0
    group_index = 0
    while group_index < len(groups):
        if consecutive_limited_groups >= RATE_LIMIT_CIRCUIT_LIMIT:
            for group in groups[group_index:]:
                for item in group:
                    note_result(item["key"], saved_for_later())
                    done += 1
                    report_progress()
            break
        wave = groups[group_index:group_index + max(1, max_workers)]
        group_index += len(wave)
        if len(wave) == 1:
            outcomes = [review_group(wave[0])]
        else:
            with ThreadPoolExecutor(max_workers=len(wave)) as pool:
                futures = [pool.submit(review_group, group) for group in wave]
                outcomes = [future.result() for future in futures]
        for group, (group_results, notices) in zip(wave, outcomes):
            if status_callback is not None:
                for notice in dict.fromkeys(notices):
                    status_callback(notice)
            group_limited = False
            group_succeeded = False
            for item in group:
                result = group_results[item["key"]]
                note_result(item["key"], result)
                if result.get("rate_limited"):
                    group_limited = True
                elif "error" not in result:
                    group_succeeded = True
                done += 1
                report_progress()
            if group_limited and not group_succeeded:
                consecutive_limited_groups += 1
            else:
                consecutive_limited_groups = 0
    return results
