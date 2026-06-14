import requests
import time
import os
import sys
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils import api_post
from geelark_config import build_geelark_headers

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
def get_headers() -> dict:
    return build_geelark_headers()


# ─────────────────────────────────────────
# CORE: Post YouTube Short on ONE device
# ─────────────────────────────────────────
def post_short_on_device(
    profile_id:             str,
    video_url:              str,
    title:                  str,
    schedule_at:            int  = None,
    same_style_url:         str  = None,
    same_style_voice:       int  = 0,
    original_voice:         int  = 100,
    is_disclosure_mandatory: bool = False,
    task_name:              str  = None,
    remark:                 str  = None,
) -> dict | None:
    """
    Posts a YouTube Short on a single cloud phone.

    profile_id              : GeeLark cloud phone ID (field: 'id' in this API)
    video_url               : Video URL from GeeLark CDN
    title                   : Short title — max 100 chars (required by YouTube API)
    schedule_at             : Unix timestamp. None = post immediately.
    same_style_url          : Reference video URL for same-style duplication (optional)
    same_style_voice        : Same-style audio volume 0-100. Use 0 if no same_style_url.
    original_voice          : Original audio volume 0-100 (default 100 = full volume)
    is_disclosure_mandatory : Force AI-content disclosure (default False)
    task_name               : Optional task label in GeeLark UI (max 128 chars)
    remark                  : Optional task notes (max 200 chars)
    """
    # YouTube title is capped at 100 characters
    if len(title) > 100:
        title = title[:97] + "..."

    payload = {
        "id":          profile_id,
        "video":       video_url,
        "title":       title,
        "scheduleAt":  schedule_at if schedule_at else get_schedule_now(),
        "sameStyleVoice": same_style_voice,
        "originalVoice":  original_voice,
    }

    if same_style_url:
        payload["sameStyleUrl"] = same_style_url
    if is_disclosure_mandatory:
        payload["isDisclosureMandatory"] = is_disclosure_mandatory
    if task_name:
        payload["name"] = task_name
    if remark:
        payload["remark"] = remark

    res  = api_post(
        f"{BASE_URL}/rpa/task/youtubePubShort",
        headers=get_headers(),
        json_data=payload,
    )
    data = res.json()

    if data.get("code") == 0:
        task_id = data.get("data", {}).get("taskId")
        return {"taskId": task_id}
    else:
        print(f"   ❌ API Error [{data.get('code')}]: {data.get('msg', 'Unknown error')}")
        return None


# ─────────────────────────────────────────
# MAIN: Post YouTube Short on ALL / selected devices
# ─────────────────────────────────────────
def post_shorts_on_devices(
    video_url:              str,
    title:                  str,
    profile_ids:            dict = None,   # {mobile: profile_id} — None = all devices
    schedule_at:            int  = None,
    stagger_minutes:        int  = 0,
    stagger_seconds:        int  = 0,
    same_style_url:         str  = None,
    same_style_voice:       int  = 0,
    original_voice:         int  = 100,
    is_disclosure_mandatory: bool = False,
) -> list:
    """
    Posts a YouTube Short on all selected cloud phone devices.

    video_url    : Single video URL from GeeLark CDN
    title        : Short title — max 100 chars. Longer strings are auto-truncated.
    profile_ids  : dict {mobile: profile_id}. If None, uses all devices from database.
    stagger_minutes : Minutes to add between each device's schedule time (default 0 = all at once).
    """
    if not video_url:
        print("❌ No video URL provided.")
        return []

    devices     = profile_ids if profile_ids else {PROFILE_MOBILE_MAP.get(pid, "?"): pid for pid in PROFILE_IDS if pid}
    device_list = list(devices.items())   # [(mobile, profile_id)]

    print(f"\n{'='*55}")
    print(f"▶️  Posting YouTube Shorts on devices...")
    print(f"   Devices         : {len(device_list)}")
    print(f"   Video           : {video_url}")
    print(f"   Title           : {title[:60]}{'...' if len(title) > 60 else ''}")
    stagger = stagger_seconds if stagger_seconds else stagger_minutes * 60
    stagger_label = f"{stagger_seconds}s" if stagger_seconds else f"{stagger_minutes} min(s)"
    print(f"   Stagger interval: {stagger_label} between devices")
    print(f"{'='*55}")

    results = []

    for i, (mobile, profile_id) in enumerate(device_list):
        if schedule_at:
            device_schedule = schedule_at + (i * stagger)
        else:
            device_schedule = int(time.time()) + 60 + (i * stagger)
        readable_time = datetime.fromtimestamp(device_schedule).strftime("%Y-%m-%d %H:%M:%S")

        print(f"\n[{i+1}/{len(device_list)}] Mobile: {mobile} | Profile: {profile_id}")
        print(f"   📅 Scheduled at : {readable_time}")

        result = post_short_on_device(
            profile_id              = profile_id,
            video_url               = video_url,
            title                   = title,
            schedule_at             = device_schedule,
            same_style_url          = same_style_url,
            same_style_voice        = same_style_voice,
            original_voice          = original_voice,
            is_disclosure_mandatory = is_disclosure_mandatory,
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

        time.sleep(5)   # Rate limit protection between devices

    # ── Final Summary ──────────────────────
    success = [r for r in results if r["status"] == "created"]
    failed  = [r for r in results if r["status"] == "failed"]

    print(f"\n{'='*55}")
    print(f"📋 FINAL SUMMARY")
    print(f"{'='*55}")

    for r in results:
        icon = "✅" if r["status"] == "created" else "❌"
        print(f"   {icon} Mobile: {r['mobile']:<15} | "
              f"Scheduled: {r['scheduledAt']} | "
              f"Task ID: {r.get('taskId', '--')}")

    print(f"\n   ✅ Successfully queued : {len(success)} device(s)")
    print(f"   ❌ Failed              : {len(failed)} device(s)")

    return results


# ─────────────────────────────────────────
# RUN — Test values
# ─────────────────────────────────────────
if __name__ == "__main__":

    VIDEO_URL = "https://singapore-upgrade.geelark.com/open-upload/611903133815210283/20260525/O3awaW7i.mp4"

    CAPTION = (
        "Snap into nostalgia with this slap band! 🎉 Perfect for camping & backyard fun. "
    )

    # Device IDs provided for testing
    TEST_DEVICES = {
        "test_device_1": "613444913962418583",
        "test_device_2": "613444889417351587",
    }

    post_shorts_on_devices(
        video_url   = VIDEO_URL,
        title       = CAPTION,   # auto-truncated to 100 chars if over limit
        profile_ids = TEST_DEVICES,
    )
