import requests
import json
import os
import uuid
import time
import hashlib
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

APP_ID = os.getenv("GEELARK_APP_ID")
API_KEY = os.getenv("GEELARK_API_KEY")
BASE_URL = "https://openapi.geelark.com/open/v1"
OUTPUT_FILE = "deviceIDs.json"

def get_headers():
    """Generates the required headers using Geelark Key Verification method."""
    trace_id = str(uuid.uuid4()).upper()
    ts = str(int(time.time() * 1000))
    nonce = trace_id[:6]
    
    raw_str = f"{APP_ID}{trace_id}{ts}{nonce}{API_KEY}"
    sign = hashlib.sha256(raw_str.encode('utf-8')).hexdigest().upper()
    
    return {
        "appId": APP_ID,
        "traceId": trace_id,
        "ts": ts,
        "nonce": nonce,
        "sign": sign,
        "Content-Type": "application/json"
    }

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
            json={
                "page": page,
                "pageSize": page_size
            }
        )
        data = res.json()
        
        if data.get("code") != 0:
            print(f"❌ API Error: {data.get('msg')}")
            break
            
        # According to format.md, the list is under data.items
        items = data.get("data", {}).get("items", [])
        if not items:
            break
            
        devices.extend(items)
        
        # If the number of items is less than page_size, we've reached the end
        if len(items) < page_size:
            break
            
        page += 1
        
    return devices

def main():
    print(f"\n🚀 Geelark Device ID Fetcher")
    
    if not APP_ID or not API_KEY:
        print("❌ Missing GEELARK_APP_ID or GEELARK_API_KEY in .env file.")
        return

    # 1. Get data from Geelark
    devices = fetch_all_devices()
    print(f"✅ Successfully fetched {len(devices)} devices from Geelark.")
    
    # 2. Check for existing deviceIDs.json
    existing_data = {}
    if os.path.exists(OUTPUT_FILE):
        try:
            with open(OUTPUT_FILE, 'r', encoding='utf-8') as f:
                existing_data = json.load(f)
            print(f"📄 Found existing '{OUTPUT_FILE}' with {len(existing_data)} records.")
        except json.JSONDecodeError:
            print(f"⚠️ '{OUTPUT_FILE}' was invalid or empty. Starting fresh.")
    else:
        print(f"✨ '{OUTPUT_FILE}' does not exist. Creating a new one.")
        
    # 3. Update the data
    updates_count = 0
    # We will store it as a dictionary with serialNo as the key, and id as the value
    # Example: {"1": "123456ABCDEF", "2": "987654XYZ"}
    for device in devices:
        serial_no = str(device.get("serialNo", ""))
        dev_id = str(device.get("id", ""))
        serial_name = device.get("serialName", "Unknown")
        
        if serial_no and dev_id:
            # We can store a dict object with id and name for better readability, 
            # but user requested just storing serial number and device ID. 
            # We'll use the serial number as the key and the device ID as the value.
            if existing_data.get(serial_no) != dev_id:
                updates_count += 1
            existing_data[serial_no] = dev_id
            
    # 4. Save to deviceIDs.json
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        json.dump(existing_data, f, indent=4)
        
    print(f"💾 Saved {len(existing_data)} devices to '{OUTPUT_FILE}'.")
    if updates_count > 0:
        print(f"   → Updated/Added {updates_count} entries.")
    else:
        print(f"   → No new updates needed. File is up to date.")

if __name__ == "__main__":
    main()
