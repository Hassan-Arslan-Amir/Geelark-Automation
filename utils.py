import time
import requests

MAX_RETRIES  = 5
BACKOFF_BASE = 3   # seconds — waits 3s, 6s, 9s, 12s, 15s between attempts


def api_post(url: str, headers: dict, json_data: dict) -> requests.Response:
    """
    Wrapper around requests.post with retry + backoff on connection errors.
    Retries up to MAX_RETRIES times before raising.
    """
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            return requests.post(url, headers=headers, json=json_data)
        except requests.exceptions.ConnectionError as e:
            if attempt < MAX_RETRIES:
                wait = BACKOFF_BASE * attempt
                print(f"   ⚠️  Connection error (attempt {attempt}/{MAX_RETRIES}). Retrying in {wait}s...")
                time.sleep(wait)
            else:
                print(f"   ❌ Connection failed after {MAX_RETRIES} attempts: {e}")
                raise


def api_put(url: str, data) -> requests.Response:
    """
    Wrapper around requests.put with retry + backoff on connection errors.
    Used for binary file uploads.
    """
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            return requests.put(url, data=data)
        except requests.exceptions.ConnectionError as e:
            if attempt < MAX_RETRIES:
                wait = BACKOFF_BASE * attempt
                print(f"   ⚠️  Upload connection error (attempt {attempt}/{MAX_RETRIES}). Retrying in {wait}s...")
                time.sleep(wait)
            else:
                print(f"   ❌ Upload failed after {MAX_RETRIES} attempts: {e}")
                raise
