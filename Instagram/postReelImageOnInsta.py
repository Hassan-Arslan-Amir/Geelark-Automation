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

from supabase_logger import get_all_devices as _get_all_devices
_device_data       = _get_all_devices()
PROFILE_IDS        = list(_device_data.values())
PROFILE_MOBILE_MAP = {v: k for k, v in _device_data.items()}

# ─────────────────────────────────────────
# SCHEDULE TIME HELPERS
# ─────────────────────────────────────────

def get_schedule_now() -> int:
    """Post immediately."""
    return int(time.time())

def get_schedule_at(dt_string: str) -> int:
    """
    Schedule at a specific date & time.
    Format: "2026-05-08 20:00:00"
    """
    return int(datetime.strptime(dt_string, "%Y-%m-%d %H:%M:%S").timestamp())

def get_schedule_after_minutes(minutes: int) -> int:
    """Post after X minutes from now."""
    return int(time.time()) + (minutes * 60)

def get_schedule_after_hours(hours: int) -> int:
    """Post after X hours from now."""
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
# CORE: Post Reels Image on ONE device
# ─────────────────────────────────────────
def post_image_on_device(
    profile_id:      str,
    image_urls:      list,
    caption:         str  = "",
    schedule_at:     int  = None,
    task_name:       str  = None,
    remark:          str  = None,
    ai_tag:          bool = False,
    publish_post:    bool = False,
    need_share_link: bool = False,
    same_style_url:  str  = None,
) -> dict | None:
    """
    Posts a Reels image on Instagram for a single device.

    profile_id      : Cloud phone Profile ID
    image_urls      : List of image URLs from GeeLark storage (max 10)
    caption         : Instagram caption (max 2200 chars). Pass "" for no caption.
    schedule_at     : Unix timestamp (seconds). None = post immediately.
    task_name       : Optional label for the task (max 128 chars)
    remark          : Optional notes (max 200 chars)
    ai_tag          : Add AI label tag (default False)
    publish_post    : True = publish as regular POST, False = publish as Reel
    need_share_link : Return sharing link after post (default False)
    same_style_url  : Optional same style URL
    """
    payload = {
        "id":          profile_id,
        "image":       image_urls,
        "description": caption,
        "scheduleAt":  schedule_at if schedule_at else get_schedule_now(),
    }

    # Add optional fields only if provided
    if task_name:
        payload["name"]          = task_name
    if remark:
        payload["remark"]        = remark
    if ai_tag:
        payload["aiTag"]         = ai_tag
    if publish_post:
        payload["publishPost"]   = publish_post
    if need_share_link:
        payload["needShareLink"] = need_share_link
    if same_style_url:
        payload["sameStyleUrl"]  = same_style_url

    res  = api_post(
        f"{BASE_URL}/rpa/task/instagramPubReelsImages",
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
# MAIN: Post Reels Image on ALL devices
# ─────────────────────────────────────────
def post_images_on_all_devices(
    image_urls:      list,
    caption:         str  = "",
    profile_ids:     dict = None,    # {mobile: profile_id} — if None, uses all devices
    schedule_at:     int  = None,
    stagger_minutes: int  = 0,
    task_name:       str  = None,
    remark:          str  = None,
    ai_tag:          bool = False,
    publish_post:    bool = False,
    need_share_link: bool = False,
    same_style_url:  str  = None,
) -> list:
    # Use provided devices or fall back to full list
    devices     = profile_ids if profile_ids else {v: k for k, v in PROFILE_MOBILE_MAP.items()}
    device_list = [(v, k) for k, v in devices.items()]  # [(profile_id, mobile)]

    print(f"\n{'='*55}")
    print(f"🖼️  Posting Instagram Reels Image on devices...")
    print(f"   Devices         : {len(device_list)}")
    print(f"   Images          : {len(image_urls)}")
    print(f"   Publish as      : {'Regular POST' if publish_post else 'Reel'}")
    print(f"   Caption         : {'(none)' if not caption.strip() else caption[:50] + '...'}")
    print(f"   Stagger interval: {stagger_minutes} min(s) between devices")
    print(f"{'='*55}")

    results = []

    for i, (profile_id, mobile) in enumerate(device_list, 0):

        # Use fixed time if provided, otherwise use current time + 1 min buffer
        # This ensures the schedule is always in the future when the API call is sent
        if schedule_at:
            device_schedule = schedule_at + (i * stagger_minutes * 60)
        else:
            device_schedule = int(time.time()) + 60 + (i * stagger_minutes * 60)
        readable_time = datetime.fromtimestamp(device_schedule).strftime("%Y-%m-%d %H:%M:%S")

        print(f"\n[{i+1}/{len(device_list)}] Mobile: {mobile} | Profile: {profile_id}")
        print(f"   📅 Scheduled at : {readable_time}")

        result = post_image_on_device(
            profile_id      = profile_id,
            image_urls      = image_urls,
            caption         = caption,
            schedule_at     = device_schedule,
            task_name       = task_name,
            remark          = remark,
            ai_tag          = ai_tag,
            publish_post    = publish_post,
            need_share_link = need_share_link,
            same_style_url  = same_style_url,
        )

        if result:
            task_id = result.get("taskId")
            print(f"   ✅ Task created! Task ID: {task_id}")
            results.append({
                "profileId":   profile_id,
                "mobile":      mobile,
                "taskId":      task_id,
                "scheduledAt": readable_time,
                "status":      "created"
            })
        else:
            print(f"   ❌ Failed to create task.")
            results.append({
                "profileId":   profile_id,
                "mobile":      mobile,
                "taskId":      None,
                "scheduledAt": readable_time,
                "status":      "failed"
            })

        time.sleep(5)

    # ── Final Summary ─────────────────────
    print(f"\n{'='*55}")
    print(f"📋 FINAL SUMMARY")
    print(f"{'='*55}")
    success = [r for r in results if r["status"] == "created"]
    failed  = [r for r in results if r["status"] == "failed"]

    for r in results:
        icon = "✅" if r["status"] == "created" else "❌"
        print(f"   {icon} Mobile: {r['mobile']:<15} | "
              f"Scheduled: {r['scheduledAt']} | "
              f"Task ID: {r.get('taskId', '--')}")

    print(f"\n   ✅ Successfully queued : {len(success)} device(s)")
    print(f"   ❌ Failed              : {len(failed)} device(s)")

    return results


# ─────────────────────────────────────────
# RUN — Choose your options below
# ─────────────────────────────────────────
if __name__ == "__main__":

    # ── Image URLs from upload_file() ───── #

    IMAGE_URLS = [
        "https://material.geelark.com/your-image.jpg",
        # Add up to 10 image URLs here
        # "https://material.geelark.com/your-image-2.jpg",
    ]

    CAPTION = " "

    # Option 1: Post immediately on all devices at the same time
    post_images_on_all_devices(
        image_urls   = IMAGE_URLS,
        caption      = CAPTION,
        publish_post = False,    # False = Reel | True = Regular POST
    )

    # Option 2: Post at a specific date & time
    # post_images_on_all_devices(
    #     image_urls   = IMAGE_URLS,
    #     caption      = CAPTION,
    #     schedule_at  = get_schedule_at("2026-05-08 20:00:00"),
    #     publish_post = False,
    # )

    # Option 3: Post after 2 hours from now
    # post_images_on_all_devices(
    #     image_urls   = IMAGE_URLS,
    #     caption      = CAPTION,
    #     schedule_at  = get_schedule_after_hours(2),
    #     publish_post = False,
    # )

    # Option 4: Staggered — 10 min gap between each device
    # post_images_on_all_devices(
    #     image_urls      = IMAGE_URLS,
    #     caption         = CAPTION,
    #     stagger_minutes = 10,
    #     publish_post    = False,
    # )

    # Option 5: Specific time + staggered per device
    # post_images_on_all_devices(
    #     image_urls      = IMAGE_URLS,
    #     caption         = CAPTION,
    #     schedule_at     = get_schedule_at("2026-05-08 20:00:00"),
    #     stagger_minutes = 10,
    #     publish_post    = False,
    # )