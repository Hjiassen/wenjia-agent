"""API-only FastAPI backend for the wenjia-agent web app.

The HTTP/SSE transport layer only. All conversation logic is delegated to the
agent core in :mod:`app.runtime` and reused unchanged.
"""
