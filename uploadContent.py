import sys
import requests
import time
import os
import uuid
import hashlib
import json
from dotenv import load_dotenv
from utils import api_post, api_put

# ─────────────────────────────────────────
# LOAD ENV VARIABLES
# ─────────────────────────────────────────
load_dotenv()

APP_ID         = os.getenv("GEELARK_APP_ID")
API_KEY        = os.getenv("GEELARK_API_KEY")
BEARER_TOKEN   = os.getenv("GEELARK_BEARER_TOKEN")

_json_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "deviceIDs.json")
with open(_json_path, "r") as _f:
    _device_data = json.load(_f)
PROFILE_IDS = list(_device_data.values())
PROFILE_MOBILE_MAP = {v: k for k, v in _device_data.items()}

BASE_URL = "https://openapi.geelark.com/open/v1"

def get_headers(multipart=False):
    """
    Generates headers using Geelark Key Verification method.
    Set multipart=True for file uploads (removes Content-Type).
    """
    # 1. traceId: Version 4 UUID (uppercase)
    trace_id = str(uuid.uuid4()).upper()
    
    # 2. ts: Timestamp in milliseconds
    ts = str(int(time.time() * 1000))
    
    # 3. nonce: First 6 characters of traceId
    nonce = trace_id[:6]
    
    # 4. sign: SHA256(appId + traceId + ts + nonce + apiKey)
    raw_str = f"{APP_ID}{trace_id}{ts}{nonce}{API_KEY}"
    sign = hashlib.sha256(raw_str.encode('utf-8')).hexdigest().upper()
    
    headers = {
        "appId": APP_ID,
        "traceId": trace_id,
        "ts": ts,
        "nonce": nonce,
        "sign": sign
    }

    if not multipart:
        headers["Content-Type"] = "application/json"
        
    return headers

# ─────────────────────────────────────────
# 1. TEST CONNECTION
# ─────────────────────────────────────────
def test_connection():
    print(f"\n{'='*50}")
    print(f"Testing connection using: KEY VERIFICATION method")
    print(f"{'='*50}")

    res = api_post(
        f"{BASE_URL}/phone/list",
        headers=get_headers(),
        json_data={"page": 1, "pageSize": 100}
    )

    if res.status_code == 200 and res.json().get("code") == 0:
        print("✅ Connection successful!")
        devices = res.json().get("data", {}).get("list", [])
        for d in devices:
            print(f"   → Profile: {d.get('name')} | ID: {d.get('id')} | Status: {d.get('status')}")
    else:
        print("❌ Connection failed!")
        print(f"   Status Code : {res.status_code}")
        print(f"   Response    : {res.text}")

    return res.status_code == 200

# ─────────────────────────────────────────
# 2. START ALL DEVICES
# ─────────────────────────────────────────
def start_all_devices(profile_ids: dict = None):
    """
    profile_ids : dict of {mobile: profile_id}. If None, starts all devices.
    """
    ids = list(profile_ids.values()) if profile_ids else PROFILE_IDS
    print(f"\n{'='*50}")
    print(f"Starting {len(ids)} cloud phone device(s)...")
    print(f"{'='*50}")

    valid_ids = [pid for pid in ids if pid]
    if not valid_ids:
        print("❌ No valid profile IDs found.")
        return

    res = api_post(
        f"{BASE_URL}/phone/start",
        headers=get_headers(),
        json_data={"ids": valid_ids}
    )
    data = res.json()
    if data.get("code") == 0:
        print(f"✅ Batch start command sent for {len(valid_ids)} devices.")
    else:
        print(f"❌ Failed to start devices.")
        print(f"   Reason: {data.get('msg', 'Unknown error')}")

    print("\n⏳ Waiting 120 seconds for all devices to fully boot...")
    time.sleep(120)
    print("✅ Devices should be ready now.")

# ─────────────────────────────────────────
# 3. UPLOAD FILE TO GEELARK SERVER
# ─────────────────────────────────────────
def upload_file(local_file_path: str) -> str | None:
    print(f"\n{'='*50}")
    print(f"Uploading file to GeeLark server...")
    print(f"File: {local_file_path}")
    print(f"{'='*50}")

    if not os.path.exists(local_file_path):
        print(f"❌ File not found: {local_file_path}")
        return None

    # Step 3a: Get Upload URL
    file_ext = os.path.splitext(local_file_path)[1].lower().replace(".", "")
    res = api_post(
        f"{BASE_URL}/upload/getUrl",
        headers=get_headers(),
        json_data={"fileType": file_ext}
    )
    
    data = res.json()
    if data.get("code") != 0:
        print(f"❌ Failed to get upload URL: {data.get('msg', 'Unknown error')}")
        return None
        
    upload_url = data["data"]["uploadUrl"]
    resource_url = data["data"]["resourceUrl"]
    
    # Step 3b: PUT file to the uploadUrl
    print("⏳ Uploading binary data to server...")
    with open(local_file_path, "rb") as f:
        put_res = api_put(upload_url, data=f)
        
    if put_res.status_code == 200:
        print(f"✅ File uploaded successfully!")
        print(f"   Resource URL: {resource_url}")
        return resource_url
    else:
        print(f"❌ Upload failed with status: {put_res.status_code}")
        return None

# ─────────────────────────────────────────
# 4. PUSH FILE TO ALL DEVICES
# ─────────────────────────────────────────
def push_file_to_all_devices(resource_url: str, profile_ids: dict = None) -> list:
    """
    profile_ids : dict of {mobile: profile_id}. If None, pushes to all devices.
    """
    devices     = profile_ids if profile_ids else {PROFILE_MOBILE_MAP.get(pid, "?"): pid for pid in PROFILE_IDS if pid}
    device_list = list(devices.items())   # [(mobile, profile_id)]
    print(f"\n{'='*50}")
    print(f"Pushing file to {len(device_list)} cloud phone device(s)...")
    print(f"{'='*50}")

    task_ids = []
    total = len(device_list)
    count = 0

    for mobile, profile_id in device_list:
        if not profile_id:
            continue
        count += 1
        res = api_post(
            f"{BASE_URL}/phone/uploadFile",
            headers=get_headers(),
            json_data={
                "id": profile_id,
                "fileUrl": resource_url
            }
        )
        data = res.json()
        if data.get("code") == 0:
            task_id = data.get("data", {}).get("taskId")
            task_ids.append({
                "profileId": profile_id,
                "mobile":    mobile,
                "taskId":    task_id
            })
            print(f"✅ Queued [{count}/{total}] → Mobile: {mobile} | Profile: {profile_id} | Task ID: {task_id}")
        else:
            print(f"❌ Failed [{count}/{total}] → Mobile: {mobile} | Profile: {profile_id}")
            print(f"   Reason: {data.get('msg', 'Unknown error')}")
        time.sleep(1)

    return task_ids

# ─────────────────────────────────────────
# 5. CHECK DELIVERY STATUS
# ─────────────────────────────────────────
def check_delivery_status(task_ids: list):
    print(f"\n{'='*50}")
    print("Checking file delivery status...")
    print(f"{'='*50}")

    print("⏳ Waiting 5 seconds for transfers to complete...")
    time.sleep(5)

    all_success = True
    for item in task_ids:
        res = api_post(
            f"{BASE_URL}/phone/uploadFile/result",
            headers=get_headers(),
            json_data={"taskId": item["taskId"]}
        )
        data = res.json()
        status = data.get("data", {}).get("status", 0)

        if status == 2:
            print(f"✅ Delivered → Profile: {item['profileId']}")
        elif status == 1:
            print(f"⏳ Pending   → Profile: {item['profileId']} (still transferring)")
            all_success = False
        else:
            print(f"❌ Failed    → Profile: {item['profileId']} | Status Code: {status}")
            all_success = False

    return all_success

# ─────────────────────────────────────────
# 6. STOP ALL DEVICES (optional cleanup)
# ─────────────────────────────────────────
def stop_all_devices(profile_ids: dict = None):
    """
    profile_ids : dict of {mobile: profile_id}. If None, stops all devices.
    """
    ids = list(profile_ids.values()) if profile_ids else PROFILE_IDS
    print(f"\n{'='*50}")
    print(f"Stopping {len(ids)} cloud phone device(s)...")
    print(f"{'='*50}")

    valid_ids = [pid for pid in ids if pid]
    if not valid_ids:
        return

    res = api_post(
        f"{BASE_URL}/phone/stop",
        headers=get_headers(),
        json_data={"ids": valid_ids}
    )
    data = res.json()
    if data.get("code") == 0:
        print(f"✅ Batch stop command sent for {len(valid_ids)} devices.")
    else:
        print(f"❌ Failed to stop devices.")
        print(f"   Reason: {data.get('msg', 'Unknown error')}")

# ─────────────────────────────────────────
# UPLOAD WORKFLOW — callable from main.py
# ─────────────────────────────────────────
def run(local_file: str, profile_ids: dict = None, auto_stop: bool = True) -> str | None:
    """
    profile_ids : dict of {mobile: profile_id} for selected devices.
                  If None, uses all devices.
    auto_stop   : If True (default), stops devices after upload.
                  Pass False when calling from main.py so devices stay
                  running through the posting phase — prevents RPA failures
                  caused by devices restarting mid-task.
    Returns     : resource_url string on success, None on failure.
    """
    device_count = len(profile_ids) if profile_ids else len([p for p in PROFILE_IDS if p])
    print("\n🚀 GeeLark File Upload Script")
    print(f"   Auth Method : KEY VERIFICATION")
    print(f"   Devices     : {device_count}")
    print(f"   File        : {local_file}")

    # Step 1: Test connection first
    connected = test_connection()
    if not connected:
        print("\n⛔ Stopping — fix connection issue before proceeding.")
        return None

    # Step 2: Start selected devices
    start_all_devices(profile_ids)

    # Step 3: Upload file to GeeLark server
    resource_url = upload_file(local_file)
    if not resource_url:
        print("\n⛔ Stopping — file upload failed.")
        return None

    # Step 4: Push file to selected devices
    task_ids = push_file_to_all_devices(resource_url, profile_ids)

    # Step 5: Check delivery status
    success = check_delivery_status(task_ids)

    if success:
        print("\n" + "="*50)
        print("🎉 All files delivered successfully!")
        print("="*50)
    else:
        print("\n⚠️  Some transfers are still pending.")
        print("   Wait a few more seconds and check the GeeLark dashboard.")

    # Step 6: Stop selected devices (only if auto_stop is enabled)
    # When called from main.py, auto_stop=False keeps devices running
    # so RPA posting tasks can execute without needing a cold restart.
    if auto_stop:
        stop_all_devices(profile_ids)
    else:
        print("\n⏩ Skipping device stop — caller will stop devices after posting.")

    return resource_url

if __name__ == "__main__":
    import sys as _sys
    if len(_sys.argv) < 2:
        print("Usage: python uploadContent.py <path_to_video>")
        _sys.exit(1)
    run(_sys.argv[1])