"""
Execute one scheduled post slot: download → upload → caption → post.
Called by task_worker.py for each due schedule_times entry.
"""
import os
import sys
import time
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "getContent"))
from getContent import download_content, to_content_key
from uploadContent import run as upload_to_devices, stop_all_devices
from Instagram.postReelVideoOnInsta import post_reels_on_all_devices
from Instagram.postReelImageOnInsta import post_images_on_all_devices
from TikTok.postOnTikTok import post_videos_on_devices as tiktok_post_videos
from TikTok.postOnTikTok import post_images_on_devices as tiktok_post_images
from Facebook.postOnFacebook import post_videos_on_devices as facebook_post_videos
from Facebook.postOnFacebook import post_images_on_devices as facebook_post_images
from YouTube.postOnYouTube import post_shorts_on_devices as youtube_post_videos
from createCaptions import run_full_pipeline
from supabase_logger import (
    create_content_record,
    update_content_resource_url,
    update_content_caption,
    increment_device_post_counts,
)

PLATFORM_CAPTION_LIMITS = {
    "instagram": 2200,
    "tiktok":    2200,
    "facebook":  200,
    "youtube":   100,
}

POST_SCHEDULE_DELAY_SECONDS = 120  # schedule Geelark post 2 min from when bot reaches this step
DEVICE_STAGGER_SECONDS = 30        # gap between devices when posting


def _normalize_caption_for_api(caption: str) -> str:
    """GeeLark requires description/title fields — use a space when no caption."""
    text = (caption or "").strip()
    return text if text else " "


def _post_schedule_time() -> int:
    return int(time.time()) + POST_SCHEDULE_DELAY_SECONDS


def _normalize_device_ids(raw) -> dict:
    """Ensure device_ids is {mobile: profile_id}."""
    if not raw:
        return {}
    if isinstance(raw, dict):
        return {str(k): str(v) for k, v in raw.items()}
    return {}


def execute_scheduled_post(task: dict, bot_settings: dict, slot_index: int) -> None:
    """
    Run one post for a scheduled task (one schedule_times slot).

    Raises on failure so the worker can mark the task as failed.
    """
    task_id = task["id"]
    platform = task["platform"]
    media_type = task["media_type"]
    devices = _normalize_device_ids(task.get("device_ids"))

    schedule_times = task.get("schedule_times") or []
    if not schedule_times and task.get("schedule_at"):
        schedule_times = [task["schedule_at"]]

    if slot_index >= len(schedule_times):
        raise ValueError(f"Task #{task_id} has no schedule time for slot {slot_index + 1}.")
    drive_url = (bot_settings.get("google_drive_url") or "").strip()

    if not drive_url:
        raise ValueError("Google Drive URL is not set in Dashboard Settings.")

    if not devices:
        raise ValueError(f"Task #{task_id} has no devices selected.")

    print(f"\n{'='*55}")
    print(f"   Executing task #{task_id} — post {slot_index + 1}/{task['content_count']}")
    print(f"   Platform: {platform.upper()} | Media: {media_type}")
    print(f"   Devices : {len(devices)}")
    print(f"{'='*55}")

    print("\n📥 Downloading content from Google Drive...")
    local_file = download_content(drive_url, media_type)
    if not local_file:
        raise RuntimeError("No new content available on Google Drive for this media type.")

    content_id = create_content_record(local_path=to_content_key(local_file), platform=platform)

    print("\n📤 Uploading to GeeLark devices...")
    resource_url = upload_to_devices(
        local_file,
        devices,
        auto_stop=(media_type == "video"),
    )
    if not resource_url:
        raise RuntimeError("Upload to GeeLark devices failed.")

    if content_id:
        update_content_resource_url(content_id, resource_url)

    caption = ""
    if task.get("caption_enabled"):
        api_key = (bot_settings.get("openai_api_key") or "").strip()
        prompt = (task.get("caption_prompt") or "").strip() or None

        if not api_key:
            print("\n⚠️  Caption is enabled but OpenAI API key is missing — posting without caption.")
        else:
            try:
                print("\n✍️  Generating caption with OpenAI...")
                caption = run_full_pipeline(
                    media_path=local_file,
                    media_type=media_type,
                    max_length=PLATFORM_CAPTION_LIMITS.get(platform, 2200),
                    custom_prompt=prompt,
                    openai_api_key=api_key,
                )
                if not (caption or "").strip():
                    print("\n⚠️  Caption generation returned empty — posting without caption.")
                    caption = ""
            except Exception as exc:
                print(f"\n⚠️  Caption generation failed ({exc}) — posting without caption.")
                caption = ""
    else:
        print("\n⏭  Caption generation disabled — posting without caption.")

    caption = _normalize_caption_for_api(caption)
    post_schedule_at = _post_schedule_time()
    post_time_readable = datetime.fromtimestamp(post_schedule_at).strftime("%Y-%m-%d %H:%M:%S")
    print(f"\n📲 Scheduling {platform.upper()} post at {post_time_readable} (+{DEVICE_STAGGER_SECONDS}s per device)...")

    results = _post_to_platform(
        platform=platform,
        media_type=media_type,
        resource_url=resource_url,
        caption=caption,
        devices=devices,
        schedule_at=post_schedule_at,
        stagger_seconds=DEVICE_STAGGER_SECONDS,
    )

    successful_ids = [r["profileId"] for r in results if r.get("status") == "created"]
    if not successful_ids:
        raise RuntimeError("Posting failed — no GeeLark tasks were created.")

    increment_device_post_counts(successful_ids)

    if content_id:
        update_content_caption(content_id, caption, successful_ids)

    if media_type == "image":
        print("\n⏳ Waiting 30 minutes for image posting tasks to complete...")
        time.sleep(1800)
        stop_all_devices(devices)
        print("✅ Devices stopped.")

    print(f"\n✅ Task #{task_id} post {slot_index + 1} completed successfully.")


def _post_to_platform(
    platform: str,
    media_type: str,
    resource_url: str,
    caption: str,
    devices: dict,
    schedule_at: int,
    stagger_seconds: int = 0,
) -> list:
    if platform == "instagram":
        if media_type == "video":
            return post_reels_on_all_devices(
                video_urls=[resource_url],
                caption=caption,
                profile_ids=devices,
                schedule_at=schedule_at,
                stagger_seconds=stagger_seconds,
            )
        return post_images_on_all_devices(
            image_urls=[resource_url],
            caption=caption,
            profile_ids=devices,
            schedule_at=schedule_at,
            stagger_seconds=stagger_seconds,
        )

    if platform == "tiktok":
        if media_type == "video":
            return tiktok_post_videos(
                video_urls=[resource_url],
                caption=caption,
                profile_ids=devices,
                schedule_at=schedule_at,
                stagger_seconds=stagger_seconds,
            )
        return tiktok_post_images(
            image_urls=[resource_url],
            caption=caption,
            profile_ids=devices,
            schedule_at=schedule_at,
            stagger_seconds=stagger_seconds,
        )

    if platform == "facebook":
        if media_type == "video":
            return facebook_post_videos(
                video_urls=[resource_url],
                caption=caption,
                profile_ids=devices,
                schedule_at=schedule_at,
                stagger_seconds=stagger_seconds,
            )
        return facebook_post_images(
            image_urls=[resource_url],
            caption=caption,
            profile_ids=devices,
            schedule_at=schedule_at,
            stagger_seconds=stagger_seconds,
        )

    if platform == "youtube":
        if media_type != "video":
            raise ValueError("YouTube only supports video content.")
        return youtube_post_videos(
            video_url=resource_url,
            title=caption,
            profile_ids=devices,
            schedule_at=schedule_at,
            stagger_seconds=stagger_seconds,
        )

    raise ValueError(f"Unknown platform: {platform}")
