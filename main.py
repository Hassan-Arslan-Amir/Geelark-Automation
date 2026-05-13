import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "getContent"))
from getContent import main as download_video
from uploadContent import run as upload_to_devices
from postReelVideoOnInsta import post_reels_on_all_devices
from postReelImageOnInsta import post_images_on_all_devices
from createCaptions import run_full_pipeline

VIDEO_EXTENSIONS = {".mp4", ".mov", ".avi", ".mkv", ".webm"}
IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif", ".webp"}

# ─────────────────────────────────────────
# ENTRY POINT
# ─────────────────────────────────────────
if __name__ == "__main__":
    print("=" * 50)
    print("   GeeLark Automation — Full Pipeline")
    print("=" * 50)

    # Step 1: Download today's video from Google Drive
    print("\n📥 Fetching today's video from Google Drive...")
    local_file = download_video()

    if not local_file:
        print("\n⛔ Stopping — no new video available to upload.")
        sys.exit(0)
    # local_file=r"E:\BitBash\GeelarkAutomation\getContent\ugc_videos\11-05-26 BuzzPatch\11-05-26 Buzz Meta V9-9-16.png"

    # Step 2: Upload to GeeLark CDN and push file to all devices
    resource_url = upload_to_devices(local_file)
    # resource_url = "https://singapore-upgrade.geelark.com/open-upload/611903133815210283/20260511/4YykBelO.png"
    if not resource_url:
        print("\n⛔ Stopping — upload failed, skipping Instagram post.")
        sys.exit(1)

    # Step 3: Generate caption using OpenAI Vision
    ext = os.path.splitext(local_file)[1].lower()
    if ext in VIDEO_EXTENSIONS:
        media_type = "video"
    elif ext in IMAGE_EXTENSIONS:
        media_type = "image"
    else:
        print(f"\n⛔ Unsupported file extension '{ext}' — cannot post to Instagram.")
        sys.exit(1)

    print("\n✍️  Generating caption with OpenAI...")
    CAPTION = run_full_pipeline(media_path=local_file, media_type=media_type)

    # Step 4: Post on Instagram across all devices based on content type
    print("\n📲 Scheduling Instagram post on all devices...")

    if media_type == "video":
        print(f"   Content type: VIDEO ({ext})")
        post_reels_on_all_devices(
            video_urls = [resource_url],
            caption    = CAPTION,
        )
    elif media_type == "image":
        print(f"   Content type: IMAGE ({ext})")
        post_images_on_all_devices(
            image_urls = [resource_url],
            caption    = CAPTION,
        )
