"""Vercel entrypoint for the FastAPI backend service."""

from app.main import app

__all__ = ["app"]
