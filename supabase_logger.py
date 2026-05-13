import os
import json
from datetime import date
from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

_client: Client = None

def get_client() -> Client:
    global _client
    if _client is None:
        _client = create_client(SUPABASE_URL, SUPABASE_KEY)
    return _client

# ─────────────────────────────────────────
# CHECK: Return posting status of a file by its local path
# Used by getContent.py to decide whether to download a file
#
# Returns:
#   "not_found"  → not in DB at all         → download
#   "not_posted" → in DB but no device_ids  → download (was interrupted before posting)
#   "posted"     → in DB and has device_ids → skip
# ─────────────────────────────────────────
def get_content_status(local_path: str) -> str:
    client = get_client()

    res = client.table("content") \
        .select("id, device_ids") \
        .eq("local_path", local_path) \
        .execute()

    if not res.data:
        return "not_found"

    device_ids = res.data[0].get("device_ids")
    if not device_ids:
        return "not_posted"

    return "posted"


# ─────────────────────────────────────────
# SEED: Populate devices table from deviceIDs.json
# Runs automatically on first ever use (when table is empty)
# ─────────────────────────────────────────
def seed_devices():
    client = get_client()

    existing = client.table("devices").select("id", count="exact").execute()
    if existing.count and existing.count > 0:
        print(f"✅ Devices table already seeded ({existing.count} devices found). Skipping.")
        return

    print("🌱 Seeding devices table from deviceIDs.json...")

    json_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "deviceIDs.json")
    with open(json_path, "r") as f:
        device_data = json.load(f)

    rows = [
        {"mobile": mobile, "profile_id": profile_id}
        for mobile, profile_id in device_data.items()
    ]

    client.table("devices").insert(rows).execute()
    print(f"✅ Seeded {len(rows)} devices into Supabase.")

# ─────────────────────────────────────────
# STEP 1: Create content record after download
# Returns the inserted content row id
# ─────────────────────────────────────────
def create_content_record(
    local_path: str,
    platform:   str = "instagram",
) -> int | None:
    client = get_client()

    row = {
        "date":       date.today().isoformat(),
        "local_path": local_path,
        "platform":   platform,
        "status":     "downloaded",
    }

    res = client.table("content").insert(row).execute()

    if res.data:
        content_id = res.data[0]["id"]
        print(f"✅ Content record created in Supabase (ID: {content_id})")
        return content_id
    else:
        print(f"❌ Failed to create content record in Supabase.")
        return None

# ─────────────────────────────────────────
# STEP 2: Update content record with resource URL after upload
# ─────────────────────────────────────────
def update_content_resource_url(content_id: int, resource_url: str):
    client = get_client()

    client.table("content") \
        .update({"resource_url": resource_url, "status": "uploaded"}) \
        .eq("id", content_id) \
        .execute()

    print(f"✅ Resource URL saved to Supabase (ID: {content_id})")

# ─────────────────────────────────────────
# STEP 3: Update content record with caption + device_ids after posting
# ─────────────────────────────────────────
def update_content_caption(content_id: int, caption: str, device_ids: list):
    client = get_client()

    client.table("content") \
        .update({"caption": caption, "device_ids": device_ids, "status": "posted"}) \
        .eq("id", content_id) \
        .execute()

    print(f"✅ Caption and device IDs saved to Supabase (ID: {content_id})")

# ─────────────────────────────────────────
# UPDATE: Increment no_of_posts for each
# device that received a successful task
# ─────────────────────────────────────────
def increment_device_post_counts(profile_ids: list):
    client = get_client()

    success = 0
    for profile_id in profile_ids:
        # Fetch current count
        res = client.table("devices") \
            .select("id, no_of_posts") \
            .eq("profile_id", profile_id) \
            .single() \
            .execute()

        if not res.data:
            print(f"   ⚠️  Device not found in Supabase: {profile_id}")
            continue

        new_count = res.data["no_of_posts"] + 1
        client.table("devices") \
            .update({"no_of_posts": new_count}) \
            .eq("profile_id", profile_id) \
            .execute()
        success += 1

    print(f"✅ Updated post counts for {success}/{len(profile_ids)} devices.")
