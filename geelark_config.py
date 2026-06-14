"""
GeeLark API credentials — Dashboard bot_settings first, .env fallback.
"""
import hashlib
import os
import time
import uuid

from dotenv import load_dotenv

load_dotenv()


def get_geelark_credentials() -> dict:
    """Return app_id, api_key, and bearer_token from Supabase or environment."""
    settings: dict = {}
    try:
        from supabase_logger import get_bot_settings

        settings = get_bot_settings() or {}
    except Exception:
        settings = {}

    app_id = (settings.get("geelark_app_id") or "").strip()
    api_key = (settings.get("geelark_api_key") or "").strip()
    bearer_token = (
        settings.get("geelark_bearer_token") or ""
    ).strip()

    return {
        "app_id": app_id,
        "api_key": api_key,
        "bearer_token": bearer_token,
    }


def require_geelark_credentials() -> dict:
    creds = get_geelark_credentials()
    if not creds["app_id"] or not creds["api_key"]:
        raise ValueError(
            "Missing GeeLark App ID or API Key. Add them in Dashboard Settings "
            "or set GEELARK_APP_ID and GEELARK_API_KEY in .env."
        )
    return creds


def build_geelark_headers(multipart: bool = False) -> dict:
    """Build signed GeeLark Open API headers."""
    creds = require_geelark_credentials()

    trace_id = str(uuid.uuid4()).upper()
    ts = str(int(time.time() * 1000))
    nonce = trace_id[:6]
    raw_str = f"{creds['app_id']}{trace_id}{ts}{nonce}{creds['api_key']}"
    sign = hashlib.sha256(raw_str.encode("utf-8")).hexdigest().upper()

    headers = {
        "appId": creds["app_id"],
        "traceId": trace_id,
        "ts": ts,
        "nonce": nonce,
        "sign": sign,
    }

    if not multipart:
        headers["Content-Type"] = "application/json"

    return headers
