import sys
import os
import time

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "getContent"))
from getContent import main as download_video, to_content_key
from uploadContent import run as upload_to_devices, stop_all_devices
from Instagram.postReelVideoOnInsta import post_reels_on_all_devices
from Instagram.postReelImageOnInsta import post_images_on_all_devices
from TikTok.postOnTikTok import post_videos_on_devices as tiktok_post_videos
from TikTok.postOnTikTok import post_images_on_devices as tiktok_post_images
from Facebook.postOnFacebook import post_videos_on_devices as facebook_post_videos
from Facebook.postOnFacebook import post_images_on_devices as facebook_post_images
from createCaptions import run_full_pipeline
from platforms import select_platform, select_devices
from supabase_logger import seed_devices, create_content_record, update_content_resource_url, update_content_caption, increment_device_post_counts

VIDEO_EXTENSIONS = {".mp4", ".mov", ".avi", ".mkv", ".webm"}
IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif", ".webp"}

# ─────────────────────────────────────────
# PIPELINE — callable from scheduler.py
#            or run directly via __main__
# ─────────────────────────────────────────
def run_pipeline():
    """
    Executes one full run of the pipeline:
      download → upload → caption → post → log

    Returns True on success, False if skipped or failed.
    Raises on unexpected errors (scheduler will catch and continue).
    """
    print("=" * 50)
    print("   GeeLark Automation — Full Pipeline")
    print("=" * 50)

    # Seed devices table on first ever run (skips if already populated)
    seed_devices()

    # Step 1: Download today's video from Google Drive
    print("\n📥 Fetching today's video from Google Drive...")
    local_file = download_video()

    if not local_file:
        print("\n⛔ Stopping — no new video available to upload.")
        return False
    # local_file=r"E:\BitBash\GeelarkAutomation\getContent\ugc_videos\11-05-26 BuzzPatch\11-05-26 Buzz Meta V9-9-16.png"

    # Determine media type from file extension
    ext = os.path.splitext(local_file)[1].lower()
    if ext in VIDEO_EXTENSIONS:
        media_type = "video"
    elif ext in IMAGE_EXTENSIONS:
        media_type = "image"
    else:
        print(f"\n⛔ Unsupported file extension '{ext}' — cannot determine media type.")
        return False

    # ── Random selection: 10 devices + 1 compatible platform ──────────────────
    selected_devices     = select_devices(10)               # {mobile: profile_id}
    selected_profile_ids = list(selected_devices.values())  # [profile_id, ...]
    platform             = select_platform(media_type)      # e.g. "instagram"
    print(f"\n🎯 This run: platform={platform.upper()}, devices={len(selected_devices)}, media={media_type}")

    # Log Step 1 → create content record with machine-independent key + chosen platform
    content_id = create_content_record(local_path=to_content_key(local_file), platform=platform)

    # Step 2: Upload to GeeLark CDN and push file to selected devices only
    # Video  → auto_stop=True  (devices stopped after upload; video RPA is resilient to cold restart)
    # Image  → auto_stop=False (devices kept running; image RPA needs stable device at execution time)
    resource_url = upload_to_devices(local_file, selected_devices, auto_stop=(media_type == "video"))
    # resource_url = "https://singapore-upgrade.geelark.com/open-upload/611903133815210283/20260511/4YykBelO.png"
    if not resource_url:
        print(f"\n⛔ Stopping — upload failed, skipping {platform} post.")
        return False

    # Log Step 2 → update content record with resource URL
    if content_id:
        update_content_resource_url(content_id, resource_url)

    # Step 3: Generate caption using OpenAI Vision
    # Caption length limits per platform
    PLATFORM_CAPTION_LIMITS = {
        "instagram": 2200,
        "tiktok":    2200,
        "facebook":  200,
    }
    print("\n✍️  Generating caption with OpenAI...")
    CAPTION = run_full_pipeline(
        media_path = local_file,
        media_type = media_type,
        max_length = PLATFORM_CAPTION_LIMITS.get(platform, 2200),
    )

    # Step 4: Post on the chosen platform using the selected devices
    print(f"\n📲 Scheduling {platform.upper()} post on {len(selected_devices)} devices...")

    if platform == "instagram":
        if media_type == "video":
            results = post_reels_on_all_devices(
                video_urls  = [resource_url],
                caption     = CAPTION,
                profile_ids = selected_devices,
            )
        else:  # image
            results = post_images_on_all_devices(
                image_urls  = [resource_url],
                caption     = CAPTION,
                profile_ids = selected_devices,
            )

    elif platform == "tiktok":
        if media_type == "video":
            results = tiktok_post_videos(
                video_urls  = [resource_url],
                caption     = CAPTION,
                profile_ids = selected_devices,
            )
        else:  # image
            results = tiktok_post_images(
                image_urls  = [resource_url],
                caption     = CAPTION,
                profile_ids = selected_devices,
            )

    elif platform == "facebook":
        if media_type == "video":
            results = facebook_post_videos(
                video_urls  = [resource_url],
                caption     = CAPTION,
                profile_ids = selected_devices,
            )
        else:  # image
            results = facebook_post_images(
                image_urls  = [resource_url],
                caption     = CAPTION,
                profile_ids = selected_devices,
            )

    else:
        print(f"\n⛔ Unknown platform '{platform}' — no posting action taken.")
        results = []

    # Step 5: Increment post count for each successfully tasked device
    successful_ids = [
        r["profileId"] for r in results if r.get("status") == "created"
    ]
    increment_device_post_counts(successful_ids)

    # Log Step 3 → update content record with caption + successful device IDs
    if content_id:
        update_content_caption(content_id, CAPTION, successful_ids)

    # Step 6: For image — devices were kept running (auto_stop=False).
    if media_type == "image":
        print("\n⏳ Waiting 30 minutes for all posting tasks to complete...")
        time.sleep(1800)
        stop_all_devices(selected_devices)
        print("✅ Devices stopped.")

    return True


# ─────────────────────────────────────────
# DIRECT RUN — single execution
# ─────────────────────────────────────────
if __name__ == "__main__":
    run_pipeline()
