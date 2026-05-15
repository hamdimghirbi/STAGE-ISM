"""File upload edge cases.

`save_upload` has defensive checks (empty filename) that the HTTP layer
already filters out — we exercise them by calling the function directly.
"""
from __future__ import annotations

import io

import pytest
from fastapi import HTTPException, UploadFile

from app.files import save_upload


def test_save_upload_rejects_empty_filename() -> None:
    """Defensive check: 400 when filename is missing."""
    upload = UploadFile(file=io.BytesIO(b"data"), filename="")
    with pytest.raises(HTTPException) as exc_info:
        save_upload(upload, user_id=1, subdir="signatures")
    assert exc_info.value.status_code == 400


def test_save_upload_rejects_none_filename() -> None:
    upload = UploadFile(file=io.BytesIO(b"data"), filename=None)
    with pytest.raises(HTTPException) as exc_info:
        save_upload(upload, user_id=1, subdir="signatures")
    assert exc_info.value.status_code == 400
