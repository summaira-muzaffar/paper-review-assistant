"""Tests for Step 5, LLM integration.

Run directly with python, or with pytest if it is installed:

    .venv/bin/python tests/test_llm_client.py

No real API call is made and no key is needed. A fake client
with the same shape as the OpenAI client records every message
it receives and returns a fixed answer, so the tests can prove
exactly what would be sent to a real model: each paragraph is
sent with its own prompt, and a custom prompt for one paragraph
reaches the model for that paragraph only.
"""

import json
import os
import re
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from types import SimpleNamespace

from src.llm_client import (
    RATE_LIMIT_CIRCUIT_LIMIT,
    RATE_LIMIT_WAIT_SECONDS,
    SERVER_ERROR_WAIT_SECONDS,
    LlmError,
    build_review_messages,
    friendly_error,
    parse_review_response,
    preflight_check,
    review_all,
    review_paragraph,
    validate_settings,
)

CANNED_ANSWER = json.dumps(
    {
        "issues": [
            {
                "issue": "The claim has no supporting evidence.",
                "severity": "HIGH",
                "explanation": "No number or citation is given.",
                "suggested_fix": "Add the measured result or a citation.",
            }
        ],
        "strengths": ["The topic sentence is clear."],
    }
)


class FakeMessage:
    def __init__(self, content):
        self.content = content


class FakeChoice:
    def __init__(self, content):
        self.message = FakeMessage(content)


class FakeResponse:
    def __init__(self, content):
        self.choices = [FakeChoice(content)]


BATCH_PHRASE = "Review each item below independently"


def batch_answer_for(user_text):
    """A well behaved batch answer: one canned review per id."""
    ids = re.findall(r"ID: (s\d+_p\d+)", user_text)
    return json.dumps(
        {item_id: json.loads(CANNED_ANSWER) for item_id in ids}
    )


class FakeCompletions:
    def __init__(self, client):
        self._client = client

    def create(self, model, messages, temperature):
        self._client.calls.append(
            {"model": model, "messages": messages, "temperature": temperature}
        )
        if self._client.fail_on_call == len(self._client.calls):
            raise RuntimeError("simulated API failure")
        user_text = messages[1]["content"]
        if BATCH_PHRASE in user_text:
            return FakeResponse(batch_answer_for(user_text))
        return FakeResponse(self._client.answer)


class FakeChat:
    def __init__(self, client):
        self.completions = FakeCompletions(client)


class FakeClient:
    def __init__(self, answer=CANNED_ANSWER, fail_on_call=None):
        self.answer = answer
        self.fail_on_call = fail_on_call
        self.calls = []
        self.chat = FakeChat(self)


class FakeApiError(Exception):
    """An API error carrying a provider status code, like the
    real OpenAI client raises."""

    def __init__(self, status_code):
        super().__init__(f"Error code: {status_code}")
        self.status_code = status_code


class StatusFakeCompletions:
    """Fails with a chosen status code for the first N calls,
    or for every call whose user text contains a marker."""

    def __init__(self, client):
        self._client = client

    def create(self, model, messages, temperature):
        self._client.calls.append(
            {"model": model, "messages": messages, "temperature": temperature}
        )
        user_text = messages[1]["content"]
        marker = self._client.fail_marker
        if marker and marker in user_text:
            raise FakeApiError(self._client.status_code)
        if len(self._client.calls) <= self._client.fail_first:
            raise FakeApiError(self._client.status_code)
        if BATCH_PHRASE in user_text:
            return FakeResponse(batch_answer_for(user_text))
        return FakeResponse(CANNED_ANSWER)


class StatusFakeClient:
    def __init__(self, status_code=429, fail_first=0, fail_marker=None):
        self.status_code = status_code
        self.fail_first = fail_first
        self.fail_marker = fail_marker
        self.calls = []
        self.chat = SimpleNamespace(completions=StatusFakeCompletions(self))


class PartialBatchCompletions:
    """Answers a batch with one id missing, so the missing
    paragraph has to be reviewed again on its own. The single
    paragraph call can be made to fail with a marker."""

    def __init__(self, client):
        self._client = client

    def create(self, model, messages, temperature):
        self._client.calls.append(
            {"model": model, "messages": messages, "temperature": temperature}
        )
        user_text = messages[1]["content"]
        if BATCH_PHRASE in user_text:
            ids = re.findall(r"ID: (s\d+_p\d+)", user_text)
            kept = {
                item_id: json.loads(CANNED_ANSWER)
                for item_id in ids
                if item_id != self._client.omit_key
            }
            return FakeResponse(json.dumps(kept))
        marker = self._client.fail_marker
        if marker and marker in user_text:
            raise RuntimeError("simulated API failure")
        return FakeResponse(CANNED_ANSWER)


class PartialBatchClient:
    def __init__(self, omit_key="s1_p0", fail_marker=None):
        self.omit_key = omit_key
        self.fail_marker = fail_marker
        self.calls = []
        self.chat = SimpleNamespace(completions=PartialBatchCompletions(self))


class ModelsFakeClient:
    """A client whose model list can be inspected, for the
    preflight check. Records how often the network was touched."""

    def __init__(self, model_ids, error=None):
        self.list_calls = 0
        self.fail_on_call = None
        self.answer = CANNED_ANSWER
        self._error = error

        def list_models():
            self.list_calls += 1
            if self._error is not None:
                raise self._error
            return SimpleNamespace(
                data=[SimpleNamespace(id=model_id) for model_id in model_ids]
            )

        self.models = SimpleNamespace(list=list_models)
        self.chat = FakeChat(self)
        self.calls = []


class NoListCompletions:
    def __init__(self, client):
        self._client = client

    def create(self, model, messages, temperature):
        self._client.calls.append(
            {"model": model, "messages": messages, "temperature": temperature}
        )
        if self._client.chat_error is not None:
            raise self._client.chat_error
        return FakeResponse(CANNED_ANSWER)


class NoListClient:
    """A provider endpoint with no model list (its list call
    answers 404), where preflight must fall back to a test chat
    call instead of blocking a working setup."""

    def __init__(self, chat_error=None):
        self.chat_error = chat_error
        self.calls = []

        def list_models():
            raise FakeApiError(404)

        self.models = SimpleNamespace(list=list_models)
        self.chat = SimpleNamespace(completions=NoListCompletions(self))


class ProbeRefusedClient:
    """The model list answers fine, but every generation call
    is refused with 429: a spent project quota. A list-only
    connection check would call this setup healthy, and the
    run would then fail on every paragraph."""

    def __init__(self):
        self.models = SimpleNamespace(
            list=lambda: SimpleNamespace(
                data=[SimpleNamespace(id="openai/gpt-oss-120b")]
            )
        )

        def refuse(model, messages, temperature):
            raise FakeApiError(429)

        self.chat = SimpleNamespace(
            completions=SimpleNamespace(create=refuse)
        )


class MultiItemBatchCompletions:
    """Refuses any batch carrying more than one paragraph
    (a per minute token ration), but reviews single paragraph
    batches normally."""

    def __init__(self, client):
        self._client = client

    def create(self, model, messages, temperature):
        self._client.calls.append(
            {"model": model, "messages": messages, "temperature": temperature}
        )
        user_text = messages[1]["content"]
        ids = re.findall(r"ID: (s\d+_p\d+)", user_text)
        if len(ids) > 1:
            raise FakeApiError(429)
        if BATCH_PHRASE in user_text:
            return FakeResponse(batch_answer_for(user_text))
        return FakeResponse(CANNED_ANSWER)


class MultiItemBatchClient:
    def __init__(self):
        self.calls = []
        self.chat = SimpleNamespace(
            completions=MultiItemBatchCompletions(self)
        )


SECTIONS = [
    {"title": "Abstract", "paragraphs": ["Abstract paragraph text."]},
    {
        "title": "1 Introduction",
        "paragraphs": ["Intro paragraph one.", "Intro paragraph two."],
    },
]

PROMPTS = {
    "s0_p0": "Default prompt for the abstract.",
    "s1_p0": "CUSTOM PROMPT: check only the statistics.",
    "s1_p1": "Default prompt for intro paragraph two.",
}


def test_messages_carry_prompt_section_paragraph_and_language():
    messages = build_review_messages(
        "1 Introduction",
        "The paragraph body.",
        "My custom instruction.",
        output_language="zh",
    )
    user_text = messages[1]["content"]
    assert "My custom instruction." in user_text
    assert "Section: 1 Introduction" in user_text
    assert "The paragraph body." in user_text
    assert "Simplified Chinese" in user_text
    assert messages[0]["role"] == "system"
    assert "JSON" in messages[0]["content"]


def test_parse_structured_and_fenced_and_free_text():
    result = parse_review_response(CANNED_ANSWER)
    assert result["issues"][0]["issue"].startswith("The claim")
    assert result["issues"][0]["severity"] == "high"
    assert result["strengths"] == ["The topic sentence is clear."]
    fenced = parse_review_response(f"```json\n{CANNED_ANSWER}\n```")
    assert fenced == result
    free = parse_review_response("This paragraph is too vague overall.")
    assert len(free["issues"]) == 1
    assert "too vague" in free["issues"][0]["explanation"]


def test_review_all_sends_each_paragraph_with_its_own_prompt():
    client = FakeClient()
    progress = []
    results = review_all(
        SECTIONS,
        PROMPTS,
        api_key="test-key",
        client=client,
        progress_callback=lambda done, total: progress.append((done, total)),
    )
    # All three paragraphs travel in ONE batch call, each with
    # its own prompt and its own id, instead of three calls.
    assert len(client.calls) == 1
    sent_user = client.calls[0]["messages"][1]["content"]
    assert "CUSTOM PROMPT" in sent_user
    assert "Default prompt for the abstract." in sent_user
    assert "Intro paragraph one." in sent_user
    assert "Intro paragraph two." in sent_user
    assert "ID: s1_p0" in sent_user
    assert set(results) == {"s0_p0", "s1_p0", "s1_p1"}
    assert results["s1_p0"]["issues"][0]["severity"] == "high"
    assert progress == [(1, 3), (2, 3), (3, 3)]


def test_one_failure_is_recorded_and_the_rest_continue():
    client = PartialBatchClient(fail_marker="Intro paragraph one.")
    results = review_all(SECTIONS, PROMPTS, api_key="test-key", client=client)
    assert "error" in results["s1_p0"]
    assert "issues" in results["s0_p0"]
    assert "issues" in results["s1_p1"]
    assert len(client.calls) == 2


def test_partial_batch_response_falls_back_for_the_missing_paragraph():
    client = PartialBatchClient()
    results = review_all(SECTIONS, PROMPTS, api_key="test-key", client=client)
    # The batch answered two paragraphs; the missing one was
    # reviewed on its own, so nothing was dropped.
    assert all("issues" in result for result in results.values())
    assert len(client.calls) == 2


def test_missing_key_and_single_call_error_raise_llm_error():
    try:
        review_paragraph("Abstract", "Text.", "Prompt.", api_key="")
    except LlmError:
        pass
    else:
        raise AssertionError("Empty key should raise LlmError")
    failing = FakeClient(fail_on_call=1)
    try:
        review_paragraph(
            "Abstract", "Text.", "Prompt.", api_key="k", client=failing
        )
    except LlmError:
        pass
    else:
        raise AssertionError("API failure should raise LlmError")


def test_validate_settings_catches_provider_mixups():
    groq_url = "https://api.groq.com/openai/v1"
    google_url = "https://generativelanguage.googleapis.com/v1beta/openai/"
    assert validate_settings("gsk_abc", groq_url, "openai/gpt-oss-120b") == []
    assert validate_settings("AIza_abc", google_url, "gemini-2.5-flash") == []
    # Newer AI Studio keys start with AQ. and are equally valid.
    assert validate_settings("AQ.abc_def", google_url, "gemini-2.5-flash") == []
    aq_key_on_groq = validate_settings("AQ.abc_def", groq_url, "openai/gpt-oss-120b")
    assert aq_key_on_groq and "Google" in aq_key_on_groq[0]
    assert validate_settings("sk-abc", "https://api.deepseek.com", "deepseek-chat") == []
    google_key_on_groq = validate_settings("AIza_abc", groq_url, "openai/gpt-oss-120b")
    assert google_key_on_groq and "Google" in google_key_on_groq[0]
    groq_key_on_google = validate_settings("gsk_abc", google_url, "gemini-2.5-flash")
    assert groq_key_on_google and "Groq" in groq_key_on_google[0]
    gemini_model_on_groq = validate_settings("gsk_abc", groq_url, "gemini-2.5-flash")
    assert gemini_model_on_groq
    assert validate_settings("", groq_url, "openai/gpt-oss-120b")


class FakeClock:
    def __init__(self):
        self.t = 0.0
        self.sleeps = []

    def now(self):
        return self.t

    def sleep(self, seconds):
        self.sleeps.append(seconds)
        self.t += seconds


def test_review_all_paces_batch_calls():
    clock = FakeClock()
    six = [
        {
            "title": "Paper",
            "paragraphs": [f"Paragraph {i}." for i in range(6)],
        }
    ]
    prompts = {f"s0_p{i}": "Review it." for i in range(6)}
    client = StatusFakeClient()
    results = review_all(
        six,
        prompts,
        api_key="<redacted>",
        client=client,
        sleep=clock.sleep,
        clock=clock.now,
        pace_seconds=5.0,
        max_workers=1,
    )
    assert all("issues" in result for result in results.values())
    # Six paragraphs make two batches, and the starts of the
    # two calls were spaced by the pacing gap.
    assert len(client.calls) == 2
    assert clock.sleeps.count(5.0) >= 1


def test_rate_limit_wait_is_brief_and_calm():
    clock = FakeClock()
    statuses = []
    client = StatusFakeClient(status_code=429, fail_first=1)
    results = review_all(
        SECTIONS,
        PROMPTS,
        api_key="<redacted>",
        client=client,
        sleep=clock.sleep,
        clock=clock.now,
        max_workers=1,
        status_callback=statuses.append,
    )
    assert all("issues" in result for result in results.values())
    # The throttled batch got ONE short wait and one retry, not
    # the old 30/60/120 second stall ladder.
    assert clock.sleeps == [RATE_LIMIT_WAIT_SECONDS]
    # The pause is announced calmly, with no countdown in it:
    # no status message ever mentions seconds.
    assert any(text.startswith("Pausing briefly") for text in statuses)
    assert not any("seconds" in text for text in statuses)
    # Progress is reported with counts as results land.
    assert any("paragraphs processed" in text for text in statuses)


def test_result_callback_reports_every_paragraph_as_it_finishes():
    client = FakeClient()
    seen = []
    results = review_all(
        SECTIONS,
        PROMPTS,
        api_key="k",
        client=client,
        result_callback=lambda key, result: seen.append((key, result)),
    )
    assert [key for key, _ in seen] == ["s0_p0", "s1_p0", "s1_p1"]
    assert all(
        seen_result is results[key] for key, seen_result in seen
    )


def test_server_error_gets_one_short_retry_then_succeeds():
    sleeps = []
    client = StatusFakeClient(status_code=503, fail_first=1)
    results = review_all(
        SECTIONS,
        PROMPTS,
        api_key="k",
        client=client,
        sleep=sleeps.append,
        max_workers=1,
    )
    assert all("issues" in result for result in results.values())
    assert sleeps.count(SERVER_ERROR_WAIT_SECONDS) == 1


def test_other_providers_and_google_gemma_pass():
    google_url = "https://generativelanguage.googleapis.com/v1beta/openai/"
    # Google serves Gemma models on the same endpoint.
    assert validate_settings("AQ.abc_def", google_url, "gemma-4-26b-a4b-it") == []
    # Providers the checker has never heard of must not be
    # blocked: their own matching sets pass validation, and the
    # preflight check then verifies them against the live list.
    assert validate_settings(
        "sk-or-abc", "https://openrouter.ai/api/v1", "google/gemini-2.5-flash"
    ) == []
    assert validate_settings(
        "a1b2c3", "https://api.together.xyz/v1", "meta-llama/Llama-3.3-70B"
    ) == []
    client = ModelsFakeClient(["google/gemini-2.5-flash"])
    ok, message = preflight_check(
        "sk-or-abc",
        "https://openrouter.ai/api/v1",
        "google/gemini-2.5-flash",
        client=client,
    )
    assert ok and "Connection OK" in message


def test_preflight_blocks_a_mixup_without_any_network_call():
    client = ModelsFakeClient(["openai/gpt-oss-120b"])
    ok, message = preflight_check(
        "AIza_abc",
        "https://api.groq.com/openai/v1",
        "openai/gpt-oss-120b",
        client=client,
    )
    assert ok is False
    assert "Google" in message
    assert client.list_calls == 0


def test_preflight_checks_the_model_list():
    client = ModelsFakeClient(["openai/gpt-oss-120b", "openai/gpt-oss-20b"])
    ok, message = preflight_check(
        "gsk_abc",
        "https://api.groq.com/openai/v1",
        "openai/gpt-oss-120b",
        client=client,
    )
    assert ok is True and "Connection OK" in message
    ok, message = preflight_check(
        "gsk_abc",
        "https://api.groq.com/openai/v1",
        "llama-3.3-70b-versatile",
        client=client,
    )
    assert ok is False and "not found" in message
    rejected = ModelsFakeClient([], error=FakeApiError(401))
    ok, message = preflight_check(
        "gsk_abc",
        "https://api.groq.com/openai/v1",
        "openai/gpt-oss-120b",
        client=rejected,
    )
    assert ok is False and "Invalid API key" in message


def test_retry_recovers_from_temporary_rate_limits():
    client = StatusFakeClient(status_code=429, fail_first=2)
    result = review_paragraph(
        "Abstract",
        "Text.",
        "Prompt.",
        api_key="k",
        client=client,
        sleep=lambda seconds: None,
    )
    assert result["issues"][0]["severity"] == "high"
    assert len(client.calls) == 3


def test_batch_rate_limit_saves_the_whole_group_for_later():
    client = StatusFakeClient(status_code=429, fail_first=999)
    results = review_all(
        SECTIONS,
        PROMPTS,
        api_key="k",
        client=client,
        sleep=lambda seconds: None,
        max_workers=1,
    )
    # The batch of three was tried twice (one wait, one
    # retry), then split into smaller batches, which were
    # also refused, down to single paragraphs: ten calls in
    # all. Every paragraph was then saved for later, not
    # stalled on.
    assert len(client.calls) == 10
    assert all(
        result.get("rate_limited") for result in results.values()
    )
    assert "Saved for later" in results["s0_p0"]["error"]


def test_split_batches_recover_when_only_large_requests_are_refused():
    client = MultiItemBatchClient()
    results = review_all(
        SECTIONS,
        PROMPTS,
        api_key="k",
        client=client,
        sleep=lambda seconds: None,
        max_workers=1,
    )
    # The provider refuses any call carrying more than one
    # paragraph. The run splits the refused batch down to
    # single paragraphs and reviews everything instead of
    # saving the whole group for later.
    assert len(results) == 3
    assert all("issues" in result for result in results.values())
    assert not any(
        result.get("rate_limited") for result in results.values()
    )
    assert len(client.calls) == 7


def test_rate_limit_circuit_breaker_saves_the_rest_for_later():
    many = [
        {
            "title": "Paper",
            "paragraphs": [f"Paragraph {i}." for i in range(20)],
        }
    ]
    prompts = {f"s0_p{i}": "Review it." for i in range(20)}
    client = StatusFakeClient(status_code=429, fail_first=999)
    seen = []
    progress = []
    results = review_all(
        many,
        prompts,
        api_key="k",
        client=client,
        sleep=lambda seconds: None,
        max_workers=1,
        result_callback=lambda key, result: seen.append(key),
        progress_callback=lambda done, total: progress.append((done, total)),
    )
    assert len(results) == 20
    assert all(
        result.get("rate_limited") for result in results.values()
    )
    # Twenty paragraphs make four batches. The first batch
    # probes smaller sizes before giving up (ten calls: the
    # batch, its halves, and singles), which turns splitting
    # off for the rest of the run. The next two batches cost
    # two calls each, and once RATE_LIMIT_CIRCUIT_LIMIT
    # batches in a row have ended limited, the last batch is
    # saved for later without burning more of the spent
    # quota, which is what keeps a dead quota run bounded
    # instead of endless.
    assert len(client.calls) == 14
    assert len(seen) == 20
    assert progress[-1] == (20, 20)


def test_non_retryable_errors_fail_at_once_in_plain_language():
    client = StatusFakeClient(status_code=401, fail_first=99)
    try:
        review_paragraph(
            "Abstract",
            "Text.",
            "Prompt.",
            api_key="k",
            client=client,
            sleep=lambda seconds: None,
        )
    except LlmError as error:
        assert error.status_code == 401
        assert "Invalid API key" in str(error)
    else:
        raise AssertionError("A 401 should raise LlmError")
    assert len(client.calls) == 1
    assert "no API balance" in friendly_error(FakeApiError(402))
    assert "not found" in friendly_error(FakeApiError(404))


def test_resume_keeps_successes_and_redoes_only_failures():
    kept = {
        "issues": [
            {
                "issue": "KEPT ORIGINAL RESULT",
                "severity": "low",
                "explanation": "From the earlier run.",
                "suggested_fix": "",
            }
        ],
        "strengths": [],
    }
    existing = {"s0_p0": kept, "s1_p0": {"error": "rate limit reached"}}
    client = FakeClient()
    results = review_all(
        SECTIONS, PROMPTS, api_key="k", client=client, existing_results=existing
    )
    assert results["s0_p0"] is kept
    assert "issues" in results["s1_p0"]
    assert "issues" in results["s1_p1"]
    # The two paragraphs still to review travel in one batch.
    assert len(client.calls) == 1


def test_preflight_accepts_google_prefixed_model_ids():
    google_client = ModelsFakeClient(["models/gemini-2.5-flash"])
    ok, message = preflight_check(
        "AQ.abc_def",
        "https://generativelanguage.googleapis.com/v1beta/openai/",
        "gemini-2.5-flash",
        client=google_client,
    )
    assert ok and "Connection OK" in message


def test_preflight_probe_catches_a_spent_quota_behind_a_healthy_list():
    ok, message = preflight_check(
        "gsk_abc",
        "https://api.groq.com/openai/v1",
        "openai/gpt-oss-120b",
        client=ProbeRefusedClient(),
    )
    # The model list said the setup was fine, but the test
    # generation call was refused: the check must fail here,
    # once, instead of letting a run fail on every paragraph.
    assert ok is False
    assert "quota" in message
    assert "429" in message


def test_preflight_falls_back_to_a_test_call_when_there_is_no_model_list():
    google = (
        "AIza_abc",
        "https://generativelanguage.googleapis.com/v1beta/openai/",
        "gemini-2.5-flash",
    )
    ok, message = preflight_check(*google, client=NoListClient())
    assert ok is True and "test call" in message
    rejected = NoListClient(chat_error=FakeApiError(401))
    ok, message = preflight_check(*google, client=rejected)
    assert ok is False and "Invalid API key" in message


if __name__ == "__main__":
    test_messages_carry_prompt_section_paragraph_and_language()
    test_parse_structured_and_fenced_and_free_text()
    test_review_all_sends_each_paragraph_with_its_own_prompt()
    test_one_failure_is_recorded_and_the_rest_continue()
    test_missing_key_and_single_call_error_raise_llm_error()
    test_validate_settings_catches_provider_mixups()
    test_review_all_paces_batch_calls()
    test_rate_limit_wait_is_brief_and_calm()
    test_result_callback_reports_every_paragraph_as_it_finishes()
    test_server_error_gets_one_short_retry_then_succeeds()
    test_other_providers_and_google_gemma_pass()
    test_preflight_blocks_a_mixup_without_any_network_call()
    test_preflight_checks_the_model_list()
    test_retry_recovers_from_temporary_rate_limits()
    test_partial_batch_response_falls_back_for_the_missing_paragraph()
    test_batch_rate_limit_saves_the_whole_group_for_later()
    test_split_batches_recover_when_only_large_requests_are_refused()
    test_rate_limit_circuit_breaker_saves_the_rest_for_later()
    test_non_retryable_errors_fail_at_once_in_plain_language()
    test_resume_keeps_successes_and_redoes_only_failures()
    test_preflight_falls_back_to_a_test_call_when_there_is_no_model_list()
    test_preflight_accepts_google_prefixed_model_ids()
    test_preflight_probe_catches_a_spent_quota_behind_a_healthy_list()
    print("TEST_LLM_CLIENT_OK 23 tests passed")
