"""Trust client IP metadata only when signed by our server-side web proxy."""

import hashlib
import hmac
import os
import re
import time
from ipaddress import ip_address

from fastapi import Request


def verified_proxy_ip(request: Request) -> str | None:
    secret = os.getenv("PROXY_SHARED_SECRET", "")
    if len(secret) < 32:
        return None
    address = request.headers.get("x-rolewisp-client-ip", "")
    stamp = request.headers.get("x-rolewisp-proxy-time", "")
    signature = request.headers.get("x-rolewisp-proxy-signature", "")
    if not re.fullmatch(r"[0-9a-f]{64}", signature):
        return None
    try:
        ip_address(address)
        if len(stamp) > 12 or abs(time.time() - int(stamp)) > 60:
            return None
    except ValueError:
        return None
    message = f"{stamp}\n{request.method}\n{request.url.path}\n{address}"
    expected = hmac.new(secret.encode(), message.encode(), hashlib.sha256).hexdigest()
    return address if hmac.compare_digest(expected, signature) else None


def client_ip(request: Request) -> str:
    return verified_proxy_ip(request) or (request.client.host if request.client else "unknown")
