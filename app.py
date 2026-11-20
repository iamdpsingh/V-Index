"""Vercel ASGI entry point; the existing backend package stays in backend/."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "backend"))

from vindex.api import app as app  # noqa: E402
