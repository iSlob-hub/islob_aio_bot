from __future__ import annotations

import os
from pathlib import Path
from typing import Optional
from urllib.parse import urlparse

from dotenv import load_dotenv
from itsdangerous import (
    BadSignature,
    SignatureExpired,
    URLSafeSerializer,
    URLSafeTimedSerializer,
)

load_dotenv()

TRAINING_FILE_TOKEN_SALT = "training-file"
DEFAULT_TRAINING_FILE_TOKEN_TTL_SECONDS = 86400
SECRET = os.environ.get("WEB_APP_SESSION_SECRET", "your_session_secret")
_stable_serializer = URLSafeSerializer(SECRET)
_timed_serializer = URLSafeTimedSerializer(SECRET)


def _get_training_file_token_ttl_seconds() -> int:
    raw_ttl = os.environ.get("TRAINING_FILE_TOKEN_TTL_SECONDS")
    if not raw_ttl:
        return DEFAULT_TRAINING_FILE_TOKEN_TTL_SECONDS
    try:
        return max(60, int(raw_ttl))
    except ValueError:
        return DEFAULT_TRAINING_FILE_TOKEN_TTL_SECONDS


def extract_training_filename(file_url: Optional[str]) -> Optional[str]:
    if not file_url:
        return None
    parsed = urlparse(file_url)
    filename = Path(parsed.path).name
    return filename or None


def build_training_file_token(telegram_id: str, filename: str) -> str:
    safe_filename = Path(filename).name
    return _stable_serializer.dumps(
        {"telegram_id": str(telegram_id), "filename": safe_filename},
        salt=TRAINING_FILE_TOKEN_SALT,
    )


def parse_training_file_token(token: str, max_age: Optional[int] = None) -> dict:
    try:
        return _stable_serializer.loads(token, salt=TRAINING_FILE_TOKEN_SALT)
    except BadSignature:
        if max_age is None:
            max_age = _get_training_file_token_ttl_seconds()
        return _timed_serializer.loads(token, salt=TRAINING_FILE_TOKEN_SALT, max_age=max_age)


def build_training_view_path(token: str) -> str:
    return f"/training-file/{token}"


def build_training_view_url(base_host: Optional[str], token: str) -> Optional[str]:
    if not base_host:
        return None
    return f"{base_host.rstrip('/')}{build_training_view_path(token)}"


__all__ = [
    "BadSignature",
    "TRAINING_FILE_TOKEN_SALT",
    "DEFAULT_TRAINING_FILE_TOKEN_TTL_SECONDS",
    "SignatureExpired",
    "build_training_file_token",
    "build_training_view_path",
    "build_training_view_url",
    "extract_training_filename",
    "parse_training_file_token",
]
