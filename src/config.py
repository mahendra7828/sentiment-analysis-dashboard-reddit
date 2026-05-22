from __future__ import annotations

import os
from dataclasses import dataclass

from dotenv import load_dotenv


@dataclass(frozen=True)
class RedditSettings:
    client_id: str
    client_secret: str
    user_agent: str


def load_reddit_settings(secrets: object | None = None) -> RedditSettings | None:
    """Load credentials from .env, environment variables, or Streamlit secrets."""
    load_dotenv()

    client_id = _read_value("REDDIT_CLIENT_ID", secrets)
    client_secret = _read_value("REDDIT_CLIENT_SECRET", secrets)
    user_agent = _read_value("REDDIT_USER_AGENT", secrets)

    if not client_id or not client_secret or not user_agent:
        return None

    return RedditSettings(
        client_id=client_id,
        client_secret=client_secret,
        user_agent=user_agent,
    )


def _read_value(name: str, secrets: object | None) -> str:
    value = os.getenv(name, "").strip()
    if value:
        return value

    if secrets is None:
        return ""

    try:
        secret_value = secrets.get(name, "")
    except Exception:
        secret_value = ""

    return str(secret_value).strip()
