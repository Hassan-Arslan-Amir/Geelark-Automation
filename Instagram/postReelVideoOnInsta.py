import requests
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

_json_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "deviceIDs.json")
with open(_json_path, "r") as _f:
    _device_data = json.load(_f)
PROFILE_IDS        = list(_device_data.values())
PROFILE_MOBILE_MAP = {v: k for k, v in _device_data.items()}

# ─────────────────────────────────────────
# SCHEDULE TIME OPTIONS
# Uncomment the one you want to use
# ─────────────────────────────────────────

# Option 1: Post immediately
def get_schedule_now() -> int:
    return int(time.time())

# Option 2: Post at a specific date & time
def get_schedule_at(dt_string: str) -> int:
    """
    Pass a date string like "2026-05-08 20:00:00"
    Returns Unix timestamp in seconds
    """
    return int(datetime.strptime(dt_string, "%Y-%m-%d %H:%M:%S").timestamp())

# Option 3: Post after X minutes from now
def get_schedule_after_minutes(minutes: int) -> int:
    return int(time.time()) + (minutes * 60)

# Option 4: Post after X hours from now
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
# CORE: Post Reels on ONE device
# ─────────────────────────────────────────
def post_reel_on_device(
    profile_id:    str,
    video_urls:    list,
    caption:       str = "",
    schedule_at:   int = None,
) -> dict | None:

    payload = {
        "id":          profile_id,
        "video":       video_urls,
        "description": caption,
        "scheduleAt":  schedule_at if schedule_at else get_schedule_now()
    }

    res  = api_post(
        f"{BASE_URL}/rpa/task/instagramPubReels",
        headers=get_headers(),
        json_data=payload
    )
    data = res.json()

    if data.get("code") == 0:
        return data.get("data")
    else:
        print(f"   ❌ API Error: {data.get('msg', 'Unknown error')}")
        return None

# ─────────────────────────────────────────
# MAIN: Post Reels on ALL devices
# With staggered timing per device
# ─────────────────────────────────────────
def post_reels_on_all_devices(
    video_urls:         list,
    caption:            str = "",
    schedule_at:        int = None,     # Fixed time for all devices
    stagger_minutes:    int = 0,        # Gap between each device (0 = same time)
):
    print(f"\n{'='*55}")
    print(f"🎬 Posting Instagram Reels on all devices...")
    print(f"   Devices         : {len(PROFILE_IDS)}")
    print(f"   Stagger interval: {stagger_minutes} min(s) between devices")
    print(f"{'='*55}")

    results = []

    for i, profile_id in enumerate(PROFILE_IDS, 0):
        if not profile_id:
            continue

        mobile = PROFILE_MOBILE_MAP.get(profile_id, "?")

        # Use fixed time if provided, otherwise use current time + 1 min buffer
        # This ensures the schedule is always in the future when the API call is sent
        if schedule_at:
            device_schedule = schedule_at + (i * stagger_minutes * 60)
        else:
            device_schedule = int(time.time()) + 60 + (i * stagger_minutes * 60)
        readable_time = datetime.fromtimestamp(device_schedule).strftime("%Y-%m-%d %H:%M:%S")

        print(f"\n[{i+1}/{len(PROFILE_IDS)}] Mobile: {mobile} | Profile: {profile_id}")
        print(f"   📅 Scheduled at: {readable_time}")

        result = post_reel_on_device(
            profile_id  = profile_id,
            video_urls  = video_urls,
            caption     = caption,
            schedule_at = device_schedule
        )

        if result:
            print(f"   ✅ Task created! Task ID: {result.get('taskId')}")
            results.append({
                "profileId":   profile_id,
                "mobile":      mobile,
                "taskId":      result.get("taskId"),
                "scheduledAt": readable_time,
                "status":      "created"
            })
        else:
            print(f"   ❌ Failed to create task.")
            results.append({
                "profileId": profile_id,
                "mobile":    mobile,
                "taskId":    None,
                "status":    "failed"
            })

        time.sleep(5)

    # ── Summary ───────────────────────────
    print(f"\n{'='*55}")
    print(f"📋 FINAL SUMMARY")
    print(f"{'='*55}")
    for r in results:
        icon = "✅" if r["status"] == "created" else "❌"
        print(f"   {icon} Mobile: {r['mobile']:<15} | "
              f"Scheduled: {r.get('scheduledAt','--')} | "
              f"Task ID: {r.get('taskId','--')}")

    return results


# ─────────────────────────────────────────
# RUN — Choose your scheduling option
# ─────────────────────────────────────────
if __name__ == "__main__":

    VIDEO_URLS = ["https://material.geelark.com/your-video.mp4"]
    CAPTION    = " "
    
    # Option 1: Post immediately on all devices
    post_reels_on_all_devices(
        video_urls = VIDEO_URLS,
        caption    = CAPTION,
    )

    # Option 2: Post at a specific date & time
    # post_reels_on_all_devices(
    #     video_urls  = VIDEO_URLS,
    #     caption     = CAPTION,
    #     schedule_at = get_schedule_at("2026-05-08 20:00:00")
    # )

    # Option 3: Post 2 hours from now
    # post_reels_on_all_devices(
    #     video_urls  = VIDEO_URLS,
    #     caption     = CAPTION,
    #     schedule_at = get_schedule_after_hours(2)
    # )

    # Option 4: Stagger — 10 min gap between each device
    # post_reels_on_all_devices(
    #     video_urls      = VIDEO_URLS,
    #     caption         = CAPTION,
    #     stagger_minutes = 10
    # )

    # Option 5: Specific time + staggered per device
    # post_reels_on_all_devices(
    #     video_urls      = VIDEO_URLS,
    #     caption         = CAPTION,
    #     schedule_at     = get_schedule_at("2026-05-08 20:00:00"),
    #     stagger_minutes = 10   # Device 1 at 8PM, Device 2 at 8:10PM, etc.
    # )