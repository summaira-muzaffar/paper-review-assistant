"""Saving review progress to disk.

Why this module exists: review results used to live only in
the running app's session memory. If the browser tab closed,
the laptop slept and the session dropped, or the app was
restarted halfway through a run, every finished paragraph was
lost and the run started over. Live use proved how frustrating
that is.

Now the interface saves progress to a small JSON file after
every single paragraph. The file is keyed by a fingerprint of
the paper's extracted text, so uploading the same paper again
in a new session restores exactly its own progress, and a
different paper never sees it. The API key is never written
to the file: only results, the overall summary, the run label,
and the user's own paragraph prompts are stored.

Files live in a .review_progress folder inside the project
(gitignored, one file per paper). Writes are atomic where the
operating system allows it: the new content goes to a
temporary file first and is then moved over the old one, so a
crash mid write can never corrupt the last good save.

Windows lesson, learned live on 6 November 2026: os.replace
raises PermissionError (WinError 5, access denied) when the
destination file is momentarily held open by another process,
which happens on Windows when saves follow each other quickly
and a scanner or indexer is holding the just written file.
Linux allows the same replace unconditionally, so Linux tests
never showed it, and the first version crashed the user's run
on her Windows laptop. The save below therefore retries the
replace briefly, falls back to writing the destination
directly, and reports failure by returning False instead of
raising: progress saving exists to protect the review, so it
must never be able to crash it.
"""

import hashlib
import json
import os
import time
from pathlib import Path

PROGRESS_DIR_NAME = ".review_progress"
REPLACE_RETRY_DELAYS = (0.1, 0.25, 0.5, 1.0)


def paper_id_for_text(text):
    """A stable fingerprint for one paper's extracted text.

    The same PDF extracts to the same text, so the same paper
    always maps to the same progress file, in any session.
    """
    return hashlib.sha256((text or "").encode("utf-8")).hexdigest()[:16]


def progress_path(base_dir, paper_id):
    return Path(base_dir) / PROGRESS_DIR_NAME / f"{paper_id}.json"


def save_progress(base_dir, paper_id, payload, sleep=None):
    """Write one paper's progress file. Returns True on success.

    Never raises for an operating system level failure: a
    False return lets the caller note that saving is
    unavailable and carry on with the review itself.
    """
    if sleep is None:
        sleep = time.sleep
    path = progress_path(base_dir, paper_id)
    tmp_path = path.with_name(f"{path.stem}.{os.getpid()}.tmp")
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(tmp_path, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, ensure_ascii=False)
    except OSError:
        return False
    replaced = False
    for attempt in range(len(REPLACE_RETRY_DELAYS) + 1):
        try:
            os.replace(tmp_path, path)
            replaced = True
            break
        except PermissionError:
            if attempt < len(REPLACE_RETRY_DELAYS):
                sleep(REPLACE_RETRY_DELAYS[attempt])
        except OSError:
            break
    if replaced:
        return True
    try:
        with open(path, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, ensure_ascii=False)
        return True
    except OSError:
        return False
    finally:
        try:
            tmp_path.unlink()
        except OSError:
            pass


def load_progress(base_dir, paper_id):
    """Read one paper's progress file.

    Returns the saved payload, or None when there is no usable
    save: no file yet, an unreadable file, or content that is
    not a progress payload. A bad save must never crash the
    app or block a fresh run.
    """
    path = progress_path(base_dir, paper_id)
    try:
        with open(path, encoding="utf-8") as handle:
            data = json.load(handle)
    except (OSError, ValueError):
        return None
    if not isinstance(data, dict) or not isinstance(
        data.get("results"), dict
    ):
        return None
    return data


def delete_progress(base_dir, paper_id):
    """Remove one paper's progress file, if it exists."""
    try:
        progress_path(base_dir, paper_id).unlink()
    except OSError:
        pass
