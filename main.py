import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "getContent"))
from getContent import main as download_video
from uploadContent import run as upload_to_devices

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

    # local_file = r"E:\BitBash\GeelarkAutomation\getContent\ugc_videos\08-05-26 Mosquito Kit\08-06-26 Mosquito Kit Travel Bundle Ad.png"
    # Step 2: Upload to GeeLark and push to all devices
    upload_to_devices(local_file)
