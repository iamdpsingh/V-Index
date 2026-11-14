import io
import os
import zipfile

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
        raise HTTPException(503, "Resume storage is temporarily unavailable") from error


def decrypt(value: bytes) -> bytes:
    try:
        return cipher().decrypt(value)
    except InvalidToken as error:
        raise HTTPException(503, "Resume storage is temporarily unavailable") from error


def filename(value: str | None) -> tuple[str, str]:
    if not value or len(value) > 120 or any(c in value for c in ("/", "\\", "\r", "\n", "\x00")):
        raise HTTPException(422, "Use a plain filename ending in .pdf, .docx or .txt")
    kind = value.rsplit(".", 1)[-1].lower()
    if kind not in MEDIA or value.startswith("."):
        raise HTTPException(415, "Supported resume types are readable PDF, DOCX and UTF-8 TXT")
    return value, kind


def validate_file(data: bytes, kind: str) -> None:
    # Files are stored as opaque attachments. Check the format without extracting content.
    valid = False
    if kind == "pdf":
        valid = data.startswith(b"%PDF-") and data.rstrip().endswith(b"%%EOF")
    elif kind == "docx":
        if zipfile.is_zipfile(io.BytesIO(data)):
            try:
                with zipfile.ZipFile(io.BytesIO(data)) as archive:
                    names = archive.namelist()
                    valid = "[Content_Types].xml" in names and "word/document.xml" in names
                    valid = valid and not any(name.lower().endswith(".bin") for name in names)
            except (ValueError, zipfile.BadZipFile):
                pass
    else:
        try:
            valid = b"\x00" not in data and bool(data.decode("utf-8-sig").strip())
        except UnicodeError:
            pass
    if not valid:
        raise HTTPException(422, "Choose a valid PDF, DOCX, or UTF-8 TXT file")
