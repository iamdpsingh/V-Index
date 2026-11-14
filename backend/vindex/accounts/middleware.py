"""Bound private request bodies before JSON parsing or upload buffering."""

from fastapi import HTTPException
from starlette.responses import JSONResponse

MAX_RESUME_BYTES = 5 * 1024 * 1024
MAX_PHOTO_BYTES = 2 * 1024 * 1024
PRIVATE_PREFIXES = ("/api/v1/auth/", "/api/v1/me")


class PrivateRequestMiddleware:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http" or not scope["path"].startswith(PRIVATE_PREFIXES):
            return await self.app(scope, receive, send)
        maximum = MAX_RESUME_BYTES if scope["path"] == "/api/v1/me/resume" else 64 * 1024
        if scope["path"] == "/api/v1/me/profile/photo":
            maximum = MAX_PHOTO_BYTES
        headers = dict(scope.get("headers", []))
        try:
            length = int(headers.get(b"content-length", b"0"))
            if length < 0:
                raise ValueError
        except ValueError:
            return await JSONResponse({"detail": "Invalid content length"}, status_code=400)(
                scope, receive, send
            )
        if length > maximum:
            return await JSONResponse(
                {"detail": "Request exceeds size limit"},
                status_code=413,
                headers={"Cache-Control": "no-store"},
            )(scope, receive, send)
        consumed = 0

        async def bounded_receive():
            nonlocal consumed
            message = await receive()
            if message["type"] == "http.request":
                consumed += len(message.get("body", b""))
                if consumed > maximum:
                    raise HTTPException(413, "Request exceeds size limit")
            return message

        async def private_send(message):
            if message["type"] == "http.response.start":
                headers = [
                    (k, v) for k, v in message.get("headers", []) if k.lower() != b"cache-control"
                ]
                headers.extend(
                    [
                        (b"cache-control", b"no-store"),
                        (b"x-content-type-options", b"nosniff"),
                        (b"vary", b"Cookie"),
                    ]
                )
                message = {**message, "headers": headers}
            await send(message)

        await self.app(scope, bounded_receive, private_send)
