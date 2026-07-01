"""ASGI entry point.

Run with::

    poetry run uvicorn apps.web.backend.main:app --reload --host 127.0.0.1 --port 8000
"""

from __future__ import annotations

from .app_factory import create_app

app = create_app()
