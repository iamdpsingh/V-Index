from urllib.parse import quote, unquote

from fastapi import APIRouter, Depends, Header, HTTPException, Request, Response
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from starlette.concurrency import run_in_threadpool

from vindex.accounts.matching import detected_skills
from vindex.accounts.middleware import MAX_RESUME_BYTES
from vindex.accounts.models import Account, Resume
from vindex.accounts.resumes import MEDIA, cipher, decrypt, extract_text, filename
from vindex.accounts.schemas import ResumeOut
from vindex.accounts.security import parser_slot, principal, rate_limit, require_origin
from vindex.db import Session, now

router = APIRouter(prefix="/api/v1/me", tags=["Private resumes"])


def metadata(saved: Resume) -> dict:
    return {
        "filename": saved.filename,
        "media_type": saved.media_type,
        "size_bytes": saved.size_bytes,
        "text_characters": saved.text_characters,
        "updated_at": saved.updated_at,
        "detected_skills": detected_skills(decrypt(saved.text_ciphertext).decode()),
    }


@router.get("/resume", response_model=ResumeOut)
def get_resume(request: Request):
    with Session() as session:
        account = principal(request, session)
        saved = session.get(Resume, account.id)
        if saved is None:
            raise HTTPException(404, "No resume saved")
        return metadata(saved)


@router.put(
    "/resume",
    response_model=ResumeOut,
    dependencies=[Depends(require_origin)],
    openapi_extra={
        "requestBody": {
            "required": True,
            "description": "Raw readable PDF, DOCX or UTF-8 TXT bytes; maximum 5 MiB. X-Filename is percent-encoded UTF-8.",
            "content": {
                "application/octet-stream": {"schema": {"type": "string", "format": "binary"}}
            },
        }
    },
)
async def upload_resume(request: Request, x_filename: str = Header()):
    if x_filename and len(x_filename) > 1500:
        raise HTTPException(422, "Filename too long")
    try:
        name, kind = filename(unquote(x_filename, errors="strict") if x_filename else None)
    except UnicodeError as error:
        raise HTTPException(422, "Invalid filename encoding") from error
    encryption = cipher()
    with Session() as session:
        account = principal(request, session)
        account_id = account.id
    rate_limit(f"resume-upload:{account_id}", 3)
    body = bytearray()
    async for chunk in request.stream():
        body.extend(chunk)
        if len(body) > MAX_RESUME_BYTES:
            raise HTTPException(413, "Resume exceeds 5 MB")
    data = bytes(body)

    def parse():
        with parser_slot():
            return extract_text(data, kind)

    text = await run_in_threadpool(parse)
    with Session() as session:
        # Recheck identity/session after parsing; a concurrent logout/delete must take effect.
        account = principal(request, session)
        if account.id != account_id:
            raise HTTPException(401, "Session changed during upload")
        session.scalar(select(Account).where(Account.id == account_id).with_for_update())
        saved = session.get(Resume, account_id)
        if saved is None:
            saved = Resume(account_id=account_id)
            session.add(saved)
        saved.filename = name
        saved.media_type = MEDIA[kind]
        saved.file_ciphertext = encryption.encrypt(data)
        saved.text_ciphertext = encryption.encrypt(text.encode())
        saved.size_bytes = len(data)
        saved.text_characters = len(text)
        saved.updated_at = now()
        try:
            session.commit()
        except IntegrityError as error:
            session.rollback()
            raise HTTPException(
                409, "Account changed while saving resume; sign in again"
            ) from error
        return metadata(saved)


@router.get(
    "/resume/download",
    response_class=Response,
    responses={
        200: {
            "content": {
                "application/octet-stream": {"schema": {"type": "string", "format": "binary"}}
            }
        }
    },
)
def download_resume(request: Request):
    with Session() as session:
        account = principal(request, session)
        saved = session.get(Resume, account.id)
        if saved is None:
            raise HTTPException(404, "No resume saved")
        rate_limit(f"resume-download:{account.id}", 30)
        return Response(
            content=decrypt(saved.file_ciphertext),
            media_type="application/octet-stream",
            headers={
                "Content-Disposition": f"attachment; filename*=UTF-8''{quote(saved.filename, safe='')}"
            },
        )


@router.delete("/resume", status_code=204, dependencies=[Depends(require_origin)])
def delete_resume(request: Request):
    with Session() as session:
        account = principal(request, session)
        saved = session.get(Resume, account.id)
        if saved is not None:
            session.delete(saved)
            session.commit()
