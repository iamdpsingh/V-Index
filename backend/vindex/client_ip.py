"""Trust client IP metadata only when signed by our server-side web proxy."""

import hashlib
import hmac
import os
import re
import time
from ipaddress import ip_address

from fastapi import Request


def client_ip(request: Request) -> str:
    peer = request.client.host if request.client else "unknown"
    secret = os.getenv("PROXY_SHARED_SECRET", "")
    if len(secret) < 32:
        return peer
    address = request.headers.get("x-rolewisp-client-ip", "")
    stamp = request.headers.get("x-rolewisp-proxy-time", "")
    signature = request.headers.get("x-rolewisp-proxy-signature", "")
    if not re.fullmatch(r"[0-9a-f]{64}", signature):
        return peer
    try:
        ip_address(address)
        if len(stamp) > 12 or abs(time.time() - int(stamp)) > 60:
            return peer
    except ValueError:
        return peer
    message = f"{stamp}\n{request.method}\n{request.url.path}\n{address}"
    expected = hmac.new(secret.encode(), message.encode(), hashlib.sha256).hexdigest()
    return address if hmac.compare_digest(expected, signature) else peer
