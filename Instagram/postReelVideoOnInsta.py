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
from geelark_config import build_geelark_headers

BASE_URL = "https://openapi.geelark.com/open/v1"

from supabase_logger import get_all_devices as _get_all_devices
_device_data       = _get_all_devices()
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
    return build_geelark_headers()

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
        "description": caption.strip() if (caption or "").strip() else " ",
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
    caption:            str  = "",
    profile_ids:        dict = None,    # {mobile: profile_id} — if None, uses all devices
    schedule_at:        int  = None,    # Fixed time for all devices
    stagger_minutes:    int  = 0,       # Gap between each device (0 = same time)
    stagger_seconds:    int  = 0,       # Overrides stagger_minutes when > 0
):
    # Use provided devices or fall back to full list
    devices = profile_ids if profile_ids else {v: k for k, v in PROFILE_MOBILE_MAP.items()}
    device_list = [(v, k) for k, v in devices.items()]  # [(profile_id, mobile)]

    print(f"\n{'='*55}")
    print(f"🎬 Posting Instagram Reels on devices...")
    print(f"   Devices         : {len(device_list)}")
    stagger = stagger_seconds if stagger_seconds else stagger_minutes * 60
    stagger_label = f"{stagger_seconds}s" if stagger_seconds else f"{stagger_minutes} min(s)"
    print(f"   Stagger interval: {stagger_label} between devices")
    print(f"{'='*55}")

    results = []

    for i, (profile_id, mobile) in enumerate(device_list, 0):

        # Use fixed time if provided, otherwise use current time + 1 min buffer
        # This ensures the schedule is always in the future when the API call is sent
        if schedule_at:
            device_schedule = schedule_at + (i * stagger)
        else:
            device_schedule = int(time.time()) + 60 + (i * stagger)
        readable_time = datetime.fromtimestamp(device_schedule).strftime("%Y-%m-%d %H:%M:%S")

        print(f"\n[{i+1}/{len(device_list)}] Mobile: {mobile} | Profile: {profile_id}")
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