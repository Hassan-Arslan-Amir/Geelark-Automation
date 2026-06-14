import requests
import json
import os
import time
from geelark_config import build_geelark_headers, require_geelark_credentials

from supabase_logger import seed_devices

BASE_URL = "https://openapi.geelark.com/open/v1"
OUTPUT_FILE = "deviceIDs.json"


def get_headers():
    """Generates the required headers using Geelark Key Verification method."""
    return build_geelark_headers()


def fetch_all_devices():
    """Fetches all devices from the Geelark API handling pagination."""
    devices = []
    page = 1
    page_size = 100

    while True:
        print(f"Fetching page {page}...")
        res = requests.post(
            f"{BASE_URL}/phone/list",
            headers=get_headers(),
            json={"page": page, "pageSize": page_size},
        )
        data = res.json()

        if data.get("code") != 0:
            print(f"❌ API Error: {data.get('msg')}")
            break

        items = data.get("data", {}).get("items", [])
        if not items:
            break

        devices.extend(items)

        if len(items) < page_size:
            break
        page += 1

    return devices


def load_existing_data() -> dict:
    """Load deviceIDs.json and normalize to nested {mobile: {profile_id, username?}}."""
    if not os.path.exists(OUTPUT_FILE):
        print(f"✨ '{OUTPUT_FILE}' does not exist. Creating a new one.")
        return {}

    try:
        with open(OUTPUT_FILE, "r", encoding="utf-8") as f:
            raw = json.load(f)
    except json.JSONDecodeError:
        print(f"⚠️ '{OUTPUT_FILE}' was invalid or empty. Starting fresh.")
        return {}

    normalized = {}
    for mobile, value in raw.items():
        mobile = str(mobile)
        if isinstance(value, dict):
            profile_id = str(value.get("profile_id", ""))
            if profile_id:
                entry = {"profile_id": profile_id}
                if value.get("username"):
                    entry["username"] = value["username"]
                normalized[mobile] = entry
        elif isinstance(value, str) and value:
            # Legacy flat format: {mobile: profile_id}
            normalized[mobile] = {"profile_id": value}

    print(f"📄 Found existing '{OUTPUT_FILE}' with {len(normalized)} record(s).")
    return normalized


def build_device_entry(mobile: str, profile_id: str, serial_name: str, existing: dict | None) -> dict:
    """Build nested entry, preserving username from existing data when present."""
    entry = {"profile_id": profile_id}

    existing_username = (existing or {}).get("username")
    if existing_username:
        entry["username"] = existing_username
    elif serial_name and serial_name != "Unknown":
        # GeeLark device label — only used when no username is stored yet
        entry["username"] = serial_name

    return entry


def sync_devices_from_geelark() -> dict:
    """
    Fetch devices from GeeLark, save deviceIDs.json, and sync Supabase.
    Returns a summary dict. Raises on missing credentials or Supabase errors.
    """
    require_geelark_credentials()

    devices = fetch_all_devices()
    print(f"✅ Successfully fetched {len(devices)} device(s) from Geelark.")

    existing_data = load_existing_data()
    updates_count = 0

    for device in devices:
        mobile = str(device.get("serialNo", ""))
        profile_id = str(device.get("id", ""))
        serial_name = device.get("serialName", "Unknown")

        if not mobile or not profile_id:
            continue

        prev = existing_data.get(mobile)
        entry = build_device_entry(mobile, profile_id, serial_name, prev)

        if prev != entry:
            updates_count += 1

        existing_data[mobile] = entry

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(existing_data, f, indent=4)

    print(f"💾 Saved {len(existing_data)} device(s) to '{OUTPUT_FILE}'.")

    print("🔄 Syncing devices to Supabase...")
    seed_devices()

    return {
        "ok": True,
        "fetched_from_geelark": len(devices),
        "total_in_json": len(existing_data),
        "updated_entries": updates_count,
        "message": f"Synced {len(existing_data)} device(s) to the database.",
    }


def main():
    print("\n🚀 Geelark Device ID Fetcher")

    try:
        result = sync_devices_from_geelark()
    except Exception as exc:
        print(f"❌ {exc}")
        return

    if result["updated_entries"] > 0:
        print(f"   → Updated/added {result['updated_entries']} entr{'y' if result['updated_entries'] == 1 else 'ies'}.")
    else:
        print("   → No new updates needed. File is up to date.")

    print(f"✅ Done — {result['message']}")


if __name__ == "__main__":
    main()
