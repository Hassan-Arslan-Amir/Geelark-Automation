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
    """Post immediately (current time)."""
    return int(time.time())

def get_schedule_at(dt_string: str) -> int:
    """Schedule at a specific date & time. Format: '2026-05-15 20:00:00'"""
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
# CORE: Post video on ONE device
# ─────────────────────────────────────────
def post_video_on_device(
    env_id:       str,
    video_url:    str,
    caption:      str  = "",
    schedule_at:  int  = None,
    plan_name:    str  = None,
    mark_ai:      bool = False,
    max_retries:  int  = 3,
    timeout_min:  int  = 80,
) -> dict | None:
    """
    Posts a TikTok video on a single device.

    env_id       : Cloud phone ID (envId in TikTok API)
    video_url    : Single video URL from GeeLark CDN
    caption      : TikTok caption (max 4000 chars)
    schedule_at  : Unix timestamp. None = post immediately.
    mark_ai      : Label as AI-generated content (default False)
    max_retries  : Auto-retry attempts 0-3 (default 3)
    timeout_min  : Task timeout in minutes 30-80 (default 80)
    """
    task_item = {
        "envId":       env_id,
        "video":       video_url,
        "scheduleAt":  schedule_at if schedule_at else get_schedule_now(),
    }

    if caption:
        task_item["videoDesc"] = caption
    if mark_ai:
        task_item["markAI"] = mark_ai
    if max_retries != 3:
        task_item["maxTryTimes"] = max_retries
    if timeout_min != 80:
        task_item["timeoutMin"] = timeout_min

    payload = {
        "taskType": 1,   # 1 = Publish Video
        "list":     [task_item],
    }
    if plan_name:
        payload["planName"] = plan_name

    res  = api_post(
        f"{BASE_URL}/task/add",
        headers=get_headers(),
        json_data=payload
    )
    data = res.json()

    if data.get("code") == 0:
        task_ids = data.get("data", {}).get("taskIds", [])
        return {"taskId": task_ids[0] if task_ids else None}
    else:
        print(f"   ❌ API Error: {data.get('msg', 'Unknown error')}")
        return None

# ─────────────────────────────────────────
# CORE: Post image set on ONE device
# ─────────────────────────────────────────
def post_image_on_device(
    env_id:       str,
    image_urls:   list,
    caption:      str  = "",
    schedule_at:  int  = None,
    plan_name:    str  = None,
    title:        str  = None,
    mark_ai:      bool = False,
    max_retries:  int  = 3,
    timeout_min:  int  = 80,
) -> dict | None:
    """
    Posts a TikTok image set on a single device.

    env_id      : Cloud phone ID (envId in TikTok API)
    image_urls  : List of image URLs from GeeLark CDN
    caption     : TikTok caption (max 4000 chars)
    schedule_at : Unix timestamp. None = post immediately.
    title       : Gallery title (max 90 chars)
    mark_ai     : Label as AI-generated content (default False)
    """
    task_item = {
        "envId":      env_id,
        "images":     image_urls,
        "scheduleAt": schedule_at if schedule_at else get_schedule_now(),
    }

    if caption:
        task_item["videoDesc"] = caption
    if title:
        task_item["videoTitle"] = title
    if mark_ai:
        task_item["markAI"] = mark_ai
    if max_retries != 3:
        task_item["maxTryTimes"] = max_retries
    if timeout_min != 80:
        task_item["timeoutMin"] = timeout_min

    payload = {
        "taskType": 3,   # 3 = Publish Image Set
        "list":     [task_item],
    }
    if plan_name:
        payload["planName"] = plan_name

    res  = api_post(
        f"{BASE_URL}/task/add",
        headers=get_headers(),
        json_data=payload
    )
    data = res.json()

    if data.get("code") == 0:
        task_ids = data.get("data", {}).get("taskIds", [])
        return {"taskId": task_ids[0] if task_ids else None}
    else:
        print(f"   ❌ API Error: {data.get('msg', 'Unknown error')}")
        return None

# ─────────────────────────────────────────
# MAIN: Post video on ALL / selected devices
# ─────────────────────────────────────────
def post_videos_on_devices(
    video_urls:      list,
    caption:         str  = "",
    profile_ids:     dict = None,   # {mobile: profile_id} — if None, uses all devices
    schedule_at:     int  = None,
    stagger_minutes: int  = 0,
    mark_ai:         bool = False,
) -> list:
    """
    Posts a TikTok video on all selected devices.

    video_urls  : List of video URLs — only the first URL is used (TikTok = 1 video per post)
    profile_ids : dict {mobile: profile_id}. If None, uses all devices from database
    """
    if not video_urls:
        print("❌ No video URL provided.")
        return []

    video_url = video_urls[0]   # TikTok supports one video per post

    devices     = profile_ids if profile_ids else {PROFILE_MOBILE_MAP.get(pid, "?"): pid for pid in PROFILE_IDS if pid}
    device_list = list(devices.items())   # [(mobile, profile_id)]

    print(f"\n{'='*55}")
    print(f"🎵 Posting TikTok Video on devices...")
    print(f"   Devices         : {len(device_list)}")
    print(f"   Video           : {video_url}")
    print(f"   Caption         : {'(none)' if not caption.strip() else caption[:50] + '...'}")
    print(f"   Stagger interval: {stagger_minutes} min(s) between devices")
    print(f"{'='*55}")

    results = []

    for i, (mobile, profile_id) in enumerate(device_list, 0):
        if schedule_at:
            device_schedule = schedule_at + (i * stagger_minutes * 60)
        else:
            device_schedule = int(time.time()) + 60 + (i * stagger_minutes * 60)
        readable_time = datetime.fromtimestamp(device_schedule).strftime("%Y-%m-%d %H:%M:%S")

        print(f"\n[{i+1}/{len(device_list)}] Mobile: {mobile} | Profile: {profile_id}")
        print(f"   📅 Scheduled at: {readable_time}")

        result = post_video_on_device(
            env_id      = profile_id,
            video_url   = video_url,
            caption     = caption,
            schedule_at = device_schedule,
            mark_ai     = mark_ai,
        )

        if result:
            task_id = result.get("taskId")
            print(f"   ✅ Task created! Task ID: {task_id}")
            results.append({
                "profileId":   profile_id,
                "mobile":      mobile,
                "taskId":      task_id,
                "scheduledAt": readable_time,
                "status":      "created",
            })
        else:
            print(f"   ❌ Failed to create task.")
            results.append({
                "profileId":   profile_id,
                "mobile":      mobile,
                "taskId":      None,
                "scheduledAt": readable_time,
                "status":      "failed",
            })

        time.sleep(5)

    # ── Final Summary ──────────────────────
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
# MAIN: Post image set on ALL / selected devices
# ─────────────────────────────────────────
def post_images_on_devices(
    image_urls:      list,
    caption:         str  = "",
    profile_ids:     dict = None,   # {mobile: profile_id} — if None, uses all devices
    schedule_at:     int  = None,
    stagger_minutes: int  = 0,
    title:           str  = None,
    mark_ai:         bool = False,
) -> list:
    """
    Posts a TikTok image set on all selected devices.

    image_urls  : List of image URLs from GeeLark CDN
    profile_ids : dict {mobile: profile_id}. If None, uses all devices from deviceIDs.json
    """
    if not image_urls:
        print("❌ No image URLs provided.")
        return []

    devices     = profile_ids if profile_ids else {PROFILE_MOBILE_MAP.get(pid, "?"): pid for pid in PROFILE_IDS if pid}
    device_list = list(devices.items())   # [(mobile, profile_id)]

    print(f"\n{'='*55}")
    print(f"🎵 Posting TikTok Image Set on devices...")
    print(f"   Devices         : {len(device_list)}")
    print(f"   Images          : {len(image_urls)}")
    print(f"   Caption         : {'(none)' if not caption.strip() else caption[:50] + '...'}")
    print(f"   Stagger interval: {stagger_minutes} min(s) between devices")
    print(f"{'='*55}")

    results = []

    for i, (mobile, profile_id) in enumerate(device_list, 0):
        if schedule_at:
            device_schedule = schedule_at + (i * stagger_minutes * 60)
        else:
            device_schedule = int(time.time()) + 60 + (i * stagger_minutes * 60)
        readable_time = datetime.fromtimestamp(device_schedule).strftime("%Y-%m-%d %H:%M:%S")

        print(f"\n[{i+1}/{len(device_list)}] Mobile: {mobile} | Profile: {profile_id}")
        print(f"   📅 Scheduled at: {readable_time}")

        result = post_image_on_device(
            env_id      = profile_id,
            image_urls  = image_urls,
            caption     = caption,
            schedule_at = device_schedule,
            title       = title,
            mark_ai     = mark_ai,
        )

        if result:
            task_id = result.get("taskId")
            print(f"   ✅ Task created! Task ID: {task_id}")
            results.append({
                "profileId":   profile_id,
                "mobile":      mobile,
                "taskId":      task_id,
                "scheduledAt": readable_time,
                "status":      "created",
            })
        else:
            print(f"   ❌ Failed to create task.")
            results.append({
                "profileId":   profile_id,
                "mobile":      mobile,
                "taskId":      None,
                "scheduledAt": readable_time,
                "status":      "failed",
            })

        time.sleep(5)

    # ── Final Summary ──────────────────────
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
# RUN — Set your test values below
# ─────────────────────────────────────────
if __name__ == "__main__":

    # ── Fill in your test values ──────────
    VIDEO_URL  = "https://singapore-upgrade.geelark.com/open-upload/611903133815210283/20260516/PXjdlqOX.mp4"
    IMAGE_URLS = ["https://your-cdn-url/image.jpg"]
    CAPTION    = """Sunny days are made for backyard adventures! ☀️ While the little one dives into a world of toy dinosaurs and trucks, I’m soaking in some fresh air and moments of peace. It's amazing how the simplest activities can bring the biggest smiles and memories. Let's cherish these everyday wonders. ❤️

                    How do you enjoy your outdoor time?

                    #MomLife #BackyardFun #FamilyTime #MakingMemories #OutdoorAdventures #SimpleJoys #PlaytimeMagic #CherishTheMoment"""

    # ── Test with specific devices (optional) ─
    # Leave as None to use ALL devices from deviceIDs.json
    TEST_DEVICES = {
        "102": "613444917972173207",
        "101": "613444913962418583",
        "99":  "613444889417351587",
    }

    # ── Option 1: Post video ──────────────
    post_videos_on_devices(
        video_urls = [VIDEO_URL],
        caption    = CAPTION,
        profile_ids = TEST_DEVICES,
    )

    # ── Option 2: Post image set ──────────
    # post_images_on_devices(
    #     image_urls  = IMAGE_URLS,
    #     caption     = CAPTION,
    #     profile_ids = TEST_DEVICES,
    # )

    # ── Option 3: Staggered video post ───
    # post_videos_on_devices(
    #     video_urls      = [VIDEO_URL],
    #     caption         = CAPTION,
    #     profile_ids     = TEST_DEVICES,
    #     stagger_minutes = 5,
    # )

