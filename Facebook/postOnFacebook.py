import time
import os
import sys
import uuid
import hashlib
import json
from datetime import datetime
from dotenv import load_dotenv

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils import api_post

load_dotenv()

APP_ID   = os.getenv("GEELARK_APP_ID")
API_KEY  = os.getenv("GEELARK_API_KEY")
BASE_URL = "https://openapi.geelark.com/open/v1"

from supabase_logger import get_all_devices as _get_all_devices
_device_data       = _get_all_devices()
PROFILE_IDS        = list(_device_data.values())
PROFILE_MOBILE_MAP = {v: k for k, v in _device_data.items()}

# ─────────────────────────────────────────
# SCHEDULE TIME HELPERS
# ─────────────────────────────────────────
def get_schedule_now() -> int:
    return int(time.time())

def get_schedule_at(dt_string: str) -> int:
    """Schedule at a specific date & time. Format: '2026-05-15 20:00:00'"""
    return int(datetime.strptime(dt_string, "%Y-%m-%d %H:%M:%S").timestamp())

def get_schedule_after_minutes(minutes: int) -> int:
    return int(time.time()) + (minutes * 60)

def get_schedule_after_hours(hours: int) -> int:
    return int(time.time()) + (hours * 60 * 60)

# ─────────────────────────────────────────
# AUTH HEADERS
# ─────────────────────────────────────────
def get_headers():
    trace_id = str(uuid.uuid4()).upper()
    ts       = str(int(time.time() * 1000))
    nonce    = trace_id[:6]
    raw_str  = f"{APP_ID}{trace_id}{ts}{nonce}{API_KEY}"
    sign     = hashlib.sha256(raw_str.encode("utf-8")).hexdigest().upper()
    return {
        "appId":        APP_ID,
        "traceId":      trace_id,
        "ts":           ts,
        "nonce":        nonce,
        "sign":         sign,
        "Content-Type": "application/json"
    }

# ─────────────────────────────────────────
# CORE: Post Reel on ONE device
#
# API endpoint : POST /rpa/task/faceBookPubReels
# Device field : "id"           (GeeLark profile ID)
# Caption field: "description"  (max 500 characters)
# Video field  : "video"        (single string URL, NOT a list)
# Response     : data.taskId    (single string)
# ─────────────────────────────────────────
def post_reel_on_device(
    profile_id:  str,
    video_url:   str,
    caption:     str = "",
    schedule_at: int = None,
    plan_name:   str = None,
) -> dict | None:
    """
    Posts a Facebook Reel on a single cloud phone device.

    profile_id  : GeeLark cloud phone profile ID
    video_url   : Single CDN URL string (not a list)
    caption     : Post description — truncated to 500 chars automatically
    schedule_at : Unix timestamp (seconds). Defaults to now + 60s.
    plan_name   : Optional task label visible in GeeLark dashboard
    """
    mobile = PROFILE_MOBILE_MAP.get(profile_id, profile_id)

    if schedule_at is None:
        schedule_at = int(time.time()) + 60

    payload = {
        "scheduleAt":  schedule_at,
        "id":          profile_id,
        "description": caption[:500],   # Facebook hard limit
        "video":       video_url,       # Single string, NOT a list
    }
    if plan_name:
        payload["name"] = plan_name

    res  = api_post(
        f"{BASE_URL}/rpa/task/faceBookPubReels",
        headers=get_headers(),
        json_data=payload
    )
    data = res.json()

    if data.get("code") == 0:
        task_id = data.get("data", {}).get("taskId")
        print(f"   ✅ Task created! Task ID: {task_id}")
        return {
            "profileId": profile_id,
            "mobile":    mobile,
            "taskId":    task_id,
            "status":    "created"
        }
    else:
        print(f"   ❌ API Error: {data.get('msg', 'Unknown error')}")
        return {
            "profileId": profile_id,
            "mobile":    mobile,
            "taskId":    None,
            "status":    "failed",
            "error":     data.get("msg"),
        }

# ─────────────────────────────────────────
# MAIN: Post Reels on ALL selected devices
# ─────────────────────────────────────────
def post_videos_on_devices(
    video_urls:      list,
    caption:         str  = "",
    profile_ids:     dict = None,   # {mobile: profile_id}
    schedule_at:     int  = None,   # Fixed time for all (None = now+60s per device)
    stagger_minutes: int  = 0,      # Gap between each device
) -> list:
    """
    Post a Facebook Reel on each selected device.

    video_urls      : List of URLs — only the first URL is used (Facebook takes one video)
    caption         : Post description (auto-truncated to 500 chars)
    profile_ids     : Dict {mobile: profile_id} — if None, uses all devices
    stagger_minutes : Stagger posting time between devices (0 = post at same time)
    """
    video_url = video_urls[0] if video_urls else None
    if not video_url:
        print("❌ No video URL provided.")
        return []

    devices     = profile_ids if profile_ids else {PROFILE_MOBILE_MAP.get(pid, pid): pid for pid in PROFILE_IDS}
    device_list = [(v, k) for k, v in devices.items()]  # [(profile_id, mobile)]

    print(f"\n{'='*55}")
    print(f"📘 Facebook — Posting Reel on {len(device_list)} device(s)")
    print(f"   Video           : {video_url}")
    print(f"   Caption         : {caption[:80]}{'...' if len(caption) > 80 else ''}")
    print(f"   Stagger interval: {stagger_minutes} min(s) between devices")
    print(f"{'='*55}")

    results = []

    for i, (profile_id, mobile) in enumerate(device_list):
        # Timestamp computed fresh each iteration — avoids stale schedule on long loops
        device_schedule = (
            schedule_at + (i * stagger_minutes * 60)
            if schedule_at
            else int(time.time()) + 60 + (i * stagger_minutes * 60)
        )
        readable_time = datetime.fromtimestamp(device_schedule).strftime("%Y-%m-%d %H:%M:%S")

        print(f"\n[{i+1}/{len(device_list)}] Mobile: {mobile} | Profile: {profile_id}")
        print(f"   📅 Scheduled at: {readable_time}")

        result = post_reel_on_device(
            profile_id  = profile_id,
            video_url   = video_url,
            caption     = caption,
            schedule_at = device_schedule,
        )

        if result:
            result["scheduledAt"] = readable_time
            results.append(result)

    successful = sum(1 for r in results if r.get("status") == "created")
    print(f"\n{'='*55}")
    print(f"✅ Done — {successful}/{len(device_list)} tasks created successfully.")
    print(f"{'='*55}")
    return results

# ─────────────────────────────────────────
# IMAGE POSTING — No API endpoint documented
# ─────────────────────────────────────────
def post_images_on_devices(
    image_urls:      list,
    caption:         str  = "",
    profile_ids:     dict = None,
    schedule_at:     int  = None,
    stagger_minutes: int  = 0,
) -> list:
    """
    🚧 NOT YET IMPLEMENTED — No GeeLark API endpoint documented
    for Facebook image posts. Implement when endpoint is available.
    """
    print(f"\n{'='*55}")
    print(f"📘 Facebook image posting — 🚧 NOT YET IMPLEMENTED")
    print(f"   No GeeLark API endpoint documented for Facebook image posts.")
    print(f"{'='*55}")

    results = []
    if profile_ids:
        for mobile, profile_id in profile_ids.items():
            results.append({
                "profileId": profile_id,
                "mobile":    mobile,
                "taskId":    None,
                "status":    "not_implemented",
            })
    return results

# ─────────────────────────────────────────
# STANDALONE TEST
# Run: python Facebook/postOnFacebook.py
# ─────────────────────────────────────────
if __name__ == "__main__":

    VIDEO_URL = "https://singapore-upgrade.geelark.com/open-upload/611903133815210283/20260516/DyoT1fuY.mp4"

    CAPTION = (
        "Snap into nostalgia with this slap band! 🎉 Perfect for camping & backyard fun. "
        "Who else loved these? Drop your favorite throwback accessories below! 👇✨ "
        "#SlapBand #Nostalgia"
    )

    # Device IDs provided for testing
    TEST_DEVICES = {
        "test_device_1": "613444913962418583",
        "test_device_2": "613444889417351587",
    }

    results = post_videos_on_devices(
        video_urls  = [VIDEO_URL],
        caption     = CAPTION,
        profile_ids = TEST_DEVICES,
    )

    print(f"\n{'─'*55}")
    print("📋 Results Summary:")
    for r in results:
        icon = "✅" if r["status"] == "created" else "❌"
        print(f"   {icon} Device {r['mobile']} → taskId: {r.get('taskId', 'N/A')} [{r['status']}]")
    print(f"{'─'*55}")
