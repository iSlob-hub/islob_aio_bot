from __future__ import annotations

import os
from pathlib import Path
from typing import Optional
from urllib.parse import urlparse

from dotenv import load_dotenv
from itsdangerous import BadSignature, URLSafeSerializer

load_dotenv()

TRAINING_FILE_TOKEN_SALT = "training-file"
SECRET = os.environ.get("WEB_APP_SESSION_SECRET", "your_session_secret")
_serializer = URLSafeSerializer(SECRET)


def extract_training_filename(file_url: Optional[str]) -> Optional[str]:
    if not file_url:
        return None
    parsed = urlparse(file_url)
    filename = Path(parsed.path).name
    return filename or None


def build_training_file_token(telegram_id: str, filename: str) -> str:
    safe_filename = Path(filename).name
    return _serializer.dumps(
        {"telegram_id": str(telegram_id), "filename": safe_filename},
        salt=TRAINING_FILE_TOKEN_SALT,
    )


def parse_training_file_token(token: str) -> dict:
    return _serializer.loads(token, salt=TRAINING_FILE_TOKEN_SALT)


def build_training_view_path(token: str) -> str:
    return f"/training-file/{token}"


def build_training_view_url(base_host: Optional[str], token: str) -> Optional[str]:
    if not base_host:
        return None
    return f"{base_host.rstrip('/')}{build_training_view_path(token)}"


__all__ = [
    "BadSignature",
    "TRAINING_FILE_TOKEN_SALT",
    "build_training_file_token",
    "build_training_view_path",
    "build_training_view_url",
    "extract_training_filename",
    "parse_training_file_token",
]
