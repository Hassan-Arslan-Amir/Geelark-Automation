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
def get_content_status(content_key: str) -> str:
    """Look up a content record by its machine-independent key (relative path, forward slashes).

    Backward compatibility: if no exact match is found, falls back to a pattern
    match against old records that stored full absolute paths.
    """
    client = get_client()

    # Primary: exact match on new relative-path key
    res = client.table("content") \
        .select("id, device_ids") \
        .eq("local_path", content_key) \
        .execute()

    if not res.data:
        # Backward compat: old records stored full absolute paths that end with
        # ugc_videos/<folder>/<file>.  Match using folder + filename wildcards so
        # records from any machine (different drive letters / install paths) are found.
        parts = content_key.split('/')
        if len(parts) >= 2:
            folder = parts[-2]
            fname  = parts[-1]
            res = client.table("content") \
                .select("id, device_ids") \
                .ilike("local_path", f"%{folder}%{fname}") \
                .execute()

    if not res.data:
        return "not_found"

    device_ids = res.data[0].get("device_ids")
    if not device_ids:
        return "not_posted"

    return "posted"


# ─────────────────────────────────────────
# SEED: Sync devices table from deviceIDs.json
# Inserts new devices, skips existing ones (upsert by profile_id)
# Safe to run on every pipeline start
# ─────────────────────────────────────────
def seed_devices():
    client = get_client()

    json_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "deviceIDs.json")
    with open(json_path, "r") as f:
        device_data = json.load(f)

    # Fetch existing devices from table
    existing_res = client.table("devices").select("profile_id, username").execute()
    existing     = {row["profile_id"]: row["username"] for row in (existing_res.data or [])}

    new_rows    = []
    update_rows = []

    for mobile, info in device_data.items():
        profile_id = info["profile_id"]
        username   = info.get("username")

        if profile_id not in existing:
            new_rows.append({"mobile": mobile, "profile_id": profile_id, "username": username})
        elif username and not existing[profile_id]:
            # Already in DB but username was null — backfill it
            update_rows.append({"profile_id": profile_id, "username": username})

    if new_rows:
        client.table("devices").insert(new_rows).execute()
        print(f"✅ Added {len(new_rows)} new device(s) to Supabase.")

    for row in update_rows:
        client.table("devices") \
            .update({"username": row["username"]}) \
            .eq("profile_id", row["profile_id"]) \
            .execute()

    if update_rows:
        print(f"✅ Updated username for {len(update_rows)} device(s).")

    if not new_rows and not update_rows:
        print(f"✅ Devices table up to date ({len(existing)} devices). No changes needed.")


def get_all_devices() -> dict:
    """Return all devices as {mobile: profile_id} from Supabase."""
    client = get_client()
    res = client.table("devices").select("mobile, profile_id").execute()
    return {row["mobile"]: row["profile_id"] for row in (res.data or [])}


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