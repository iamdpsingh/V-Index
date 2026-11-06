import json
import os
import subprocess
import sys
from pathlib import Path

from cryptography.fernet import Fernet, InvalidToken
from fastapi import HTTPException

MEDIA = {
    "pdf": "application/pdf",
    "txt": "text/plain",
    "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
}


def cipher() -> Fernet:
    try:
        key = os.environ["RESUME_ENCRYPTION_KEY"]
        return Fernet(key.encode("ascii"))
    except (KeyError, ValueError, UnicodeError) as error:
        raise HTTPException(
            503, "Private resume storage requires a valid encryption key"
        ) from error


def decrypt(value: bytes) -> bytes:
    try:
        return cipher().decrypt(value)
    except InvalidToken as error:
        raise HTTPException(
            503, "Resume data cannot be read with the configured encryption key"
        ) from error


def filename(value: str | None) -> tuple[str, str]:
    if not value or len(value) > 120 or any(c in value for c in ("/", "\\", "\r", "\n", "\x00")):
        raise HTTPException(422, "Use a plain filename ending in .pdf, .docx or .txt")
    kind = value.rsplit(".", 1)[-1].lower()
    if kind not in MEDIA or value.startswith("."):
        raise HTTPException(415, "Supported resume types are readable PDF, DOCX and UTF-8 TXT")
    return value, kind


def extract_text(data: bytes, kind: str) -> str:
    try:
        result = subprocess.run(
            [sys.executable, "-m", "vindex.accounts.parse_worker", kind],
            input=data,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            timeout=10,
            env={"PYTHONPATH": str(Path(__file__).resolve().parents[2])},
            check=False,
        )
        parsed = json.loads(result.stdout)
        if result.returncode or not isinstance(parsed.get("text"), str):
            raise ValueError("Unreadable resume")
        return parsed["text"]
    except (subprocess.TimeoutExpired, ValueError, KeyError, OSError) as error:
        raise HTTPException(
            422,
            "Resume could not be read within limits; use a readable PDF, DOCX or UTF-8 TXT file",
        ) from error
