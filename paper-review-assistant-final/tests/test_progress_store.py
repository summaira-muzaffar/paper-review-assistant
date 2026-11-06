"""Tests for the progress store.

Run directly with python, or with pytest if it is installed:

    .venv/bin/python tests/test_progress_store.py

The store is what makes a half done review run survive a
closed tab, a sleeping laptop, or a restarted app: progress
is written to disk after every paragraph and restored when
the same paper is uploaded again. These tests prove the
round trip, the fingerprint stability, and that a missing or
corrupt save is treated as "no save" instead of a crash.
"""

import builtins
import os
import sys
import tempfile
from unittest import mock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.progress_store import (
    delete_progress,
    load_progress,
    paper_id_for_text,
    progress_path,
    save_progress,
)

PAYLOAD = {
    "paper_name": "paper.pdf",
    "paragraph_count": 3,
    "results": {
        "s0_p0": {"issues": [], "strengths": ["Clear."]},
        "s0_p1": {
            "error": "Saved for later: the provider rate limit was reached.",
            "rate_limited": True,
        },
    },
    "overall_summary": "",
    "run_info": "model @ host, 10:00",
    "prompts": {"prompt_s0_p0": "Check the statistics only."},
}


def test_paper_id_is_stable_and_text_specific():
    assert paper_id_for_text("same text") == paper_id_for_text("same text")
    assert paper_id_for_text("same text") != paper_id_for_text("other text")
    assert paper_id_for_text("") == paper_id_for_text(None)


def test_save_load_round_trip_and_delete():
    with tempfile.TemporaryDirectory() as base:
        paper_id = paper_id_for_text("the paper text")
        assert load_progress(base, paper_id) is None
        save_progress(base, paper_id, PAYLOAD)
        assert progress_path(base, paper_id).exists()
        loaded = load_progress(base, paper_id)
        assert loaded == PAYLOAD
        # A different paper never sees this save.
        assert load_progress(base, paper_id_for_text("another")) is None
        delete_progress(base, paper_id)
        assert load_progress(base, paper_id) is None
        # Deleting twice is harmless.
        delete_progress(base, paper_id)


def test_corrupt_or_wrong_shaped_save_counts_as_no_save():
    with tempfile.TemporaryDirectory() as base:
        paper_id = paper_id_for_text("the paper text")
        path = progress_path(base, paper_id)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("{not json", encoding="utf-8")
        assert load_progress(base, paper_id) is None
        path.write_text('{"unrelated": true}', encoding="utf-8")
        assert load_progress(base, paper_id) is None


def test_windows_style_locked_file_is_retried_until_it_opens():
    # Simulates the live Windows failure of 6 November 2026:
    # os.replace refused with PermissionError (WinError 5)
    # because the destination was momentarily locked. The
    # save must wait and retry, then land.
    with tempfile.TemporaryDirectory() as base:
        paper_id = paper_id_for_text("the paper text")
        real_replace = os.replace
        attempts = {"count": 0}

        def flaky_replace(source, destination):
            attempts["count"] += 1
            if attempts["count"] < 3:
                raise PermissionError(5, "Access is denied")
            return real_replace(source, destination)

        with mock.patch.object(os, "replace", flaky_replace):
            saved_ok = save_progress(
                base, paper_id, PAYLOAD, sleep=lambda seconds: None
            )
        assert saved_ok is True
        assert attempts["count"] == 3
        assert load_progress(base, paper_id) == PAYLOAD


def test_permanently_locked_replace_falls_back_to_a_direct_write():
    with tempfile.TemporaryDirectory() as base:
        paper_id = paper_id_for_text("the paper text")

        def always_locked(source, destination):
            raise PermissionError(5, "Access is denied")

        with mock.patch.object(os, "replace", always_locked):
            saved_ok = save_progress(
                base, paper_id, PAYLOAD, sleep=lambda seconds: None
            )
        assert saved_ok is True
        assert load_progress(base, paper_id) == PAYLOAD


def test_total_save_failure_returns_false_instead_of_raising():
    with tempfile.TemporaryDirectory() as base:
        paper_id = paper_id_for_text("the paper text")
        real_open = builtins.open

        def failing_open(file, *args, **kwargs):
            if ".review_progress" in str(file):
                raise OSError("simulated disk failure")
            return real_open(file, *args, **kwargs)

        with mock.patch.object(builtins, "open", failing_open):
            saved_ok = save_progress(
                base, paper_id, PAYLOAD, sleep=lambda seconds: None
            )
        # No exception escaped: a dead disk degrades saving,
        # it must never crash the review it exists to protect.
        assert saved_ok is False
        assert load_progress(base, paper_id) is None


if __name__ == "__main__":
    test_paper_id_is_stable_and_text_specific()
    test_save_load_round_trip_and_delete()
    test_corrupt_or_wrong_shaped_save_counts_as_no_save()
    test_windows_style_locked_file_is_retried_until_it_opens()
    test_permanently_locked_replace_falls_back_to_a_direct_write()
    test_total_save_failure_returns_false_instead_of_raising()
    print("TEST_PROGRESS_STORE_OK 6 tests passed")
