import os
import json
import random

# ─────────────────────────────────────────
# CONFIGURATION
# ─────────────────────────────────────────
DEVICES_PER_RUN = 10   # Number of random devices selected per run

# ─────────────────────────────────────────
# PLATFORM REGISTRY
# Defines which content types each platform supports.
# Add new platforms here when their scripts are ready.
# ─────────────────────────────────────────
PLATFORM_REGISTRY = {
    "instagram": {
        "supports": ["video", "image"],
    },
    "tiktok": {
        "supports": ["video", "image"],
    },
    # "facebook": {
    #     "supports": ["video", "image"],
    # },
}

# ─────────────────────────────────────────
# SELECT PLATFORM
# Randomly picks one platform compatible
# with the given media type.
# ─────────────────────────────────────────
def select_platform(media_type: str) -> str:
    """
    Randomly select a platform that supports the given media type.

    media_type : "video" or "image"
    Returns    : platform name e.g. "instagram"
    """
    compatible = [
        name for name, cfg in PLATFORM_REGISTRY.items()
        if media_type in cfg["supports"]
    ]

    if not compatible:
        raise ValueError(f"No platform supports media type: '{media_type}'")

    chosen = random.choice(compatible)
    print(f"🎲 Platform selected: {chosen.upper()} "
          f"(from {len(compatible)} compatible: {', '.join(compatible)})")
    return chosen

# ─────────────────────────────────────────
# SELECT DEVICES
# Randomly picks N devices from deviceIDs.json
# Returns dict of {mobile: profile_id}
# ─────────────────────────────────────────
def select_devices(count: int = DEVICES_PER_RUN) -> dict:
    """
    Randomly select `count` devices from deviceIDs.json.

    count   : Number of devices to select (default DEVICES_PER_RUN)
    Returns : dict of {mobile: profile_id} for selected devices
    """
    json_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "deviceIDs.json")
    with open(json_path, "r") as f:
        all_devices = json.load(f)

    items    = list(all_devices.items())
    selected = random.sample(items, min(count, len(items)))
    result   = dict(selected)

    print(f"🎲 Devices selected ({len(result)}/{len(items)}): "
          f"mobiles {', '.join(result.keys())}")
    return result