"""Private photo upload and retrieval for the current account."""

from io import BytesIO

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from PIL import Image, ImageOps
from starlette.concurrency import run_in_threadpool

from vindex.accounts.middleware import MAX_PHOTO_BYTES
from vindex.accounts.models import Profile
from vindex.accounts.resumes import cipher, decrypt
from vindex.accounts.security import principal, rate_limit, require_origin
from vindex.db import Session

router = APIRouter(prefix="/api/v1/me/profile/photo", tags=["Private accounts"])
guard = [Depends(require_origin)]


def normalize_photo(data: bytes) -> bytes:
    try:
        with Image.open(BytesIO(data), formats=["JPEG", "PNG", "WEBP"]) as image:
            if image.width * image.height > 12_000_000 or getattr(image, "is_animated", False):
                raise ValueError("Image exceeds limits")
            photo = ImageOps.exif_transpose(image)
            photo.thumbnail((384, 384))
            clean = Image.new("RGB", photo.size, "white")
            converted = photo.convert("RGBA")
            clean.paste(converted, mask=converted.getchannel("A"))
            output = BytesIO()
            clean.save(output, "JPEG", quality=86)
            return output.getvalue()
    except (OSError, ValueError, Image.DecompressionBombError) as error:
        raise HTTPException(422, "Choose a readable JPEG, PNG, or WebP photo within 2 MB.") from error


@router.get("")
def photo(request: Request) -> Response:
    with Session() as session:
        account = principal(request, session)
        profile = session.get(Profile, account.id)
        if not profile or not profile.photo_ciphertext:
            raise HTTPException(404, "No profile photo")
        rate_limit(f"photo-read:{account.id}", 60)
        return Response(decrypt(profile.photo_ciphertext), media_type="image/jpeg")


@router.put("", status_code=204, dependencies=guard)
async def upload_photo(request: Request) -> None:
    with Session() as session:
        account_id = principal(request, session).id
    rate_limit(f"photo-write:{account_id}", 6)
    body = await request.body()
    if len(body) > MAX_PHOTO_BYTES:
        raise HTTPException(413, "Profile photo exceeds 2 MB")
    data = await run_in_threadpool(normalize_photo, body)
    with Session() as session:
        account = principal(request, session)
        if account.id != account_id:
            raise HTTPException(401, "Session changed during upload")
        profile = session.get(Profile, account_id)
        if profile is None:
            raise HTTPException(409, "Profile is unavailable")
        profile.photo_ciphertext = cipher().encrypt(data)
        session.commit()


@router.delete("", status_code=204, dependencies=guard)
def delete_photo(request: Request) -> None:
    with Session() as session:
        account = principal(request, session)
        rate_limit(f"photo-write:{account.id}", 6)
        profile = session.get(Profile, account.id)
        if profile:
            profile.photo_ciphertext = None
            session.commit()
