import os
import sys
import json
import time
from hikerapi import Client
from dotenv import load_dotenv
from datetime import datetime

# Allow importing supabase_logger from the parent directory
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from supabase_logger import get_all_devices_full, upsert_post_stats, update_device_aggregate_stats

load_dotenv()


# ─────────────────────────────────────────
# CONFIG
# ─────────────────────────────────────────
cl = Client(token=os.getenv("HIKER_ACCESS_KEY"))

# ─────────────────────────────────────────
# STEP 1: Get User ID from Username
# ─────────────────────────────────────────
def get_user_id(username: str) -> str | None:
    """Get Instagram user ID from username."""
    try:
        user = cl.user_by_username_v1(username)
        return str(user.get("pk") or user.get("id"))
    except Exception as e:
        print(f"   ❌ Could not get user ID for @{username}: {e}")
        return None

# ─────────────────────────────────────────
# STEP 2: Get All Posts (paginated)
# ─────────────────────────────────────────
def get_all_posts(user_id: str) -> list:
    """Fetch ALL posts for a user, paginating through every page."""
    all_posts = []
    cursor    = None
    page      = 0
    try:
        while True:
            page  += 1
            result = cl.user_medias_gql(user_id, profile_grid_items_cursor=cursor, flat=True)
            items  = result.get("items", []) if isinstance(result, dict) else result
            all_posts.extend(items)
            if not result.get("more_available", False):
                break
            cursor = result.get("next_max_id")
            if not cursor:
                break
            time.sleep(0.5)   # small pause between pages
    except Exception as e:
        print(f"   ❌ Could not fetch posts (page {page}): {e}")
    return all_posts

# ─────────────────────────────────────────
# STEP 3: Get Post Insights/Stats
# ─────────────────────────────────────────
def get_post_stats(media_id: str) -> dict:
    """
    Fetch stats for a specific post using HikerAPI.
    Returns view count, likes, comments, and more.
    """
    try:
        # Get full media info — contains public stats
        response  = cl.media_info_by_id_v2(media_id)
        # response is wrapped under "media_or_ad"; fall back to bare dict if not present
        media_info = response.get("media_or_ad") or response

        stats = {
            # Reels use play_count; photos use like_count only (view_count is None)
            "views":      media_info.get("play_count") or media_info.get("view_count") or 0,
            "likes":      media_info.get("like_count") or 0,
            "comments":   media_info.get("comment_count") or 0,
            "reshares":   media_info.get("reshare_count") or 0,
            "media_type": media_info.get("media_type", "--"),
            "timestamp":  media_info.get("taken_at", "--"),
            "permalink":  f"https://instagram.com/p/{media_info.get('code', '')}",
        }

        # Also try dedicated insights endpoint
        try:
            insights = cl.media_insight_v1(media_id)
            if insights:
                stats["reach"]       = insights.get("reach", 0)
                stats["impressions"] = insights.get("impressions", 0)
                stats["saves"]       = insights.get("saves", 0)
        except:
            pass  # Insights only available for owned accounts

        return stats

    except Exception as e:
        print(f"   ❌ Could not fetch stats: {e}")
        return {}

# ─────────────────────────────────────────
# HELPER: Write current results to instagram_stats.json
# ─────────────────────────────────────────
def _save_json(results: list, total_views: int, total_likes: int, total_comments: int):
    output = {
        "fetched_at":    datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "total_devices": len(results),
        "aggregate": {
            "total_views":    total_views,
            "total_likes":    total_likes,
            "total_comments": total_comments,
        },
        "accounts": results,
    }
    with open("instagram_stats.json", "w") as f:
        json.dump(output, f, indent=2)


# ─────────────────────────────────────────
# MAIN: Get stats from ALL devices
# ─────────────────────────────────────────
def get_all_devices_stats() -> list:
    """
    Fetch Instagram stats for ALL posts on each device.
    Devices are loaded from Supabase — no hardcoded list needed.
    """
    devices = get_all_devices_full()

    print(f"\n{'='*60}")
    print(f"📊 Fetching Instagram stats from {len(devices)} devices...")
    print(f"   Powered by: HikerAPI")
    print(f"{'='*60}")

    results        = []
    total_views    = 0
    total_likes    = 0
    total_comments = 0
    no_user_devices  = []   # username not found on HikerAPI
    no_post_devices  = []   # account exists but has no posts

    for i, device in enumerate(devices, 1):
        print(f"\n[{i}/{len(devices)}] {device['mobile']} | @{device['username']}")

        try:
            user_id = get_user_id(device["username"])
            if not user_id:
                no_user_devices.append(device)
                continue

            posts = get_all_posts(user_id)
            if not posts:
                print(f"   ⚠️  No posts found.")
                no_post_devices.append(device)
                continue
            print(f"   📂 Total posts found: {len(posts)}")

            device_result = {
                "profile_id": device["profile_id"],
                "mobile":     device["mobile"],
                "username":   device["username"],
                "posts":      [],
            }

            device_views    = 0
            device_likes    = 0
            device_comments = 0

            for j, post in enumerate(posts, 1):
                media_id = str(post.get("pk") or post.get("id"))
                stats    = get_post_stats(media_id)

                if not stats:
                    continue

                views    = stats.get("views", 0)
                likes    = stats.get("likes", 0)
                comments = stats.get("comments", 0)
                reshares = stats.get("reshares", 0)

                total_views    += views
                total_likes    += likes
                total_comments += comments
                device_views    += views
                device_likes    += likes
                device_comments += comments

                print(f"   📌 Post {j}: {stats.get('permalink', '--')}")
                print(f"      👁️  Views    : {views:,}")
                print(f"      ❤️  Likes    : {likes:,}")
                print(f"      💬 Comments : {comments:,}")
                print(f"      🔁 Reshares : {reshares:,}")
                if stats.get("reach"):
                    print(f"      📣 Reach    : {stats['reach']:,}")

                device_result["posts"].append({
                    "permalink": stats.get("permalink", "--"),
                    "stats":     stats,
                })

            if device_result["posts"]:
                results.append(device_result)
                # Write stats to Supabase
                upsert_post_stats(device["id"], device["username"], device_result["posts"])
                update_device_aggregate_stats(device["id"], device_views, device_likes, device_comments)
                # Update JSON after each device
                _save_json(results, total_views, total_likes, total_comments)
                print(f"   💾 JSON updated ({len(results)} device(s) so far)")

        except Exception as e:
            print(f"   ❌ Error: {e}")

        time.sleep(1)   # Rate limit protection

    # ── Aggregate Summary ─────────────────
    print(f"\n{'='*60}")
    print(f"📈 TOTAL STATS ACROSS ALL {len(results)} DEVICES")
    print(f"{'='*60}")
    print(f"   👁️  Total Views    : {total_views:,}")
    print(f"   ❤️  Total Likes    : {total_likes:,}")
    print(f"   💬 Total Comments : {total_comments:,}")
    print(f"   📊 Avg Views/Device: {total_views // max(len(results), 1):,}")

    print(f"\n✅ Full stats saved to instagram_stats.json")

    # ── Problem Devices Summary ─────────────
    print(f"\n{'='*60}")
    print(f"⚠️  PROBLEM DEVICES SUMMARY")
    print(f"{'='*60}")

    print(f"\n🔴 Username Not Found ({len(no_user_devices)} device(s)):")
    if no_user_devices:
        for d in no_user_devices:
            print(f"   • {d['mobile']} | @{d['username']}")
    else:
        print(f"   None")

    print(f"\n🟡 No Posts Found ({len(no_post_devices)} device(s)):")
    if no_post_devices:
        for d in no_post_devices:
            print(f"   • {d['mobile']} | @{d['username']}")
    else:
        print(f"   None")

    print(f"{'='*60}")

    return results


# ─────────────────────────────────────────
# RUN
# ─────────────────────────────────────────
if __name__ == "__main__":
    get_all_devices_stats()