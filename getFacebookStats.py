import os
import json
import requests
import time
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

# ─────────────────────────────────────────
# APP CREDENTIALS (from .env)
# ─────────────────────────────────────────
APP_ID     = os.getenv("FB_APP_ID")
APP_SECRET = os.getenv("FB_APP_SECRET")
GRAPH_URL  = "https://graph.facebook.com/v19.0"

# ─────────────────────────────────────────
# TEST DEVICES — Hardcoded for testing
# ─────────────────────────────────────────
DEVICES = [
    {
        "mobile":    "Phone 5",
        "email":     "IrvineBollom68@outlook.com",
        "password":  "Vpa2pto3S",
        "page_id":   "61588266630253",
        "page_url":  "https://www.facebook.com/profile.php?id=61588266630253"
    },
    {
        "mobile":    "Phone 6",
        "email":     "SheilahLagana3437@outlook.com",
        "password":  "QqKl*VCK4",
        "page_id":   "61588197364850",
        "page_url":  "https://www.facebook.com/profile.php?id=61588197364850"
    },
]

# ─────────────────────────────────────────
# STEP 1: Get App Access Token
# ─────────────────────────────────────────
def get_app_token() -> str | None:
    """
    Generates an App Access Token using App ID and App Secret.
    This token allows reading PUBLIC page data without user login.
    """
    print(f"\n{'='*55}")
    print("🔑 Generating App Access Token...")
    print(f"{'='*55}")

    try:
        res = requests.get(
            f"{GRAPH_URL}/oauth/access_token",
            params={
                "client_id":     APP_ID,
                "client_secret": APP_SECRET,
                "grant_type":    "client_credentials"
            }
        )
        data = res.json()
        if "access_token" in data:
            print(f"✅ App Token generated successfully!")
            return data["access_token"]
        else:
            print(f"⚠️  Falling back to direct token format...")
            return f"{APP_ID}|{APP_SECRET}"

    except Exception as e:
        print(f"⚠️  Falling back to direct format: {e}")
        return f"{APP_ID}|{APP_SECRET}"

# ─────────────────────────────────────────
# STEP 2: Get All Posts for a Page
# ─────────────────────────────────────────
def get_page_posts(page_id: str, app_token: str) -> list:
    """
    Fetches ALL posts from a Facebook Page using its Page ID.
    Paginates through all available posts.
    """
    all_posts = []
    url       = f"{GRAPH_URL}/{page_id}/posts"
    page_num  = 0

    try:
        while url:
            page_num += 1
            res  = requests.get(
                url,
                params={
                    "fields":       "id,message,story,created_time,permalink_url",
                    "limit":        100,
                    "access_token": app_token
                }
            )
            data = res.json()

            if "error" in data:
                print(f"   ❌ API Error: {data['error'].get('message', 'Unknown error')}")
                break

            posts = data.get("data", [])
            all_posts.extend(posts)

            # Check for next page
            next_url = data.get("paging", {}).get("next")
            url      = next_url if next_url else None
            time.sleep(0.5)

    except Exception as e:
        print(f"   ❌ Could not fetch posts: {e}")

    return all_posts

# ─────────────────────────────────────────
# STEP 3: Get Stats for a Single Post
# ─────────────────────────────────────────
def get_post_stats(post_id: str, app_token: str) -> dict:
    """
    Fetches stats for a single Facebook post.
    Stats: Likes, Comments, Shares, Video Views, Post URL
    """
    try:
        res = requests.get(
            f"{GRAPH_URL}/{post_id}",
            params={
                "fields": (
                    "id,"
                    "message,"
                    "created_time,"
                    "permalink_url,"
                    "likes.summary(true),"
                    "comments.summary(true),"
                    "shares,"
                    "video_insights"
                ),
                "access_token": app_token
            }
        )
        data = res.json()

        if "error" in data:
            print(f"      ❌ Post error: {data['error'].get('message')}")
            return {}

        # ── Extract stats ─────────────────────
        likes    = data.get("likes", {}).get("summary", {}).get("total_count", 0)
        comments = data.get("comments", {}).get("summary", {}).get("total_count", 0)
        shares   = data.get("shares", {}).get("count", 0)
        post_url = data.get("permalink_url", "--")
        created  = data.get("created_time", "--")
        message  = data.get("message", data.get("story", "--"))

        # ── Video views ───────────────────────
        video_views    = 0
        video_insights = data.get("video_insights", {}).get("data", [])
        for insight in video_insights:
            if insight.get("name") == "total_video_views":
                video_views = insight.get("values", [{}])[0].get("value", 0)
                break

        # Convert timestamp to readable date
        if created != "--":
            try:
                dt      = datetime.strptime(created, "%Y-%m-%dT%H:%M:%S%z")
                created = dt.strftime("%Y-%m-%d %H:%M:%S")
            except:
                pass

        return {
            "post_id":     post_id,
            "post_url":    post_url,
            "message":     message[:100] if message != "--" else "--",
            "created_at":  created,
            "likes":       likes,
            "comments":    comments,
            "shares":      shares,
            "video_views": video_views,
        }

    except Exception as e:
        print(f"      ❌ Could not fetch post stats: {e}")
        return {}

# ─────────────────────────────────────────
# STEP 4: Get Stats for ONE Device
# ─────────────────────────────────────────
def get_device_stats(device: dict, app_token: str) -> dict | None:
    """
    Fetches all post stats for a single Facebook device/page.
    """
    print(f"\n{'─'*55}")
    print(f"📱 {device['mobile']} | Page ID: {device['page_id']}")
    print(f"   Email : {device['email']}")
    print(f"{'─'*55}")

    posts = get_page_posts(device["page_id"], app_token)

    if not posts:
        print(f"   ⚠️  No posts found for this page.")
        print(f"   💡 Possible reasons:")
        print(f"      → Page has no public posts")
        print(f"      → App token does not have access to this page")
        print(f"      → Page ID is incorrect")
        return None

    print(f"   📂 Total posts found: {len(posts)}")

    device_result = {
        "mobile":    device["mobile"],
        "email":     device["email"],
        "page_id":   device["page_id"],
        "page_url":  device["page_url"],
        "posts":     [],
        "aggregate": {
            "total_posts":       0,
            "total_likes":       0,
            "total_comments":    0,
            "total_shares":      0,
            "total_video_views": 0,
        }
    }

    for j, post in enumerate(posts, 1):
        post_id = post.get("id")
        stats   = get_post_stats(post_id, app_token)

        if not stats:
            continue

        likes       = stats.get("likes", 0)
        comments    = stats.get("comments", 0)
        shares      = stats.get("shares", 0)
        video_views = stats.get("video_views", 0)

        print(f"\n   📌 Post {j}: {stats.get('post_url', '--')}")
        print(f"      📅 Posted     : {stats.get('created_at', '--')}")
        print(f"      💬 Caption    : {stats.get('message', '--')[:60]}...")
        print(f"      ❤️  Likes      : {likes:,}")
        print(f"      💬 Comments   : {comments:,}")
        print(f"      🔁 Shares     : {shares:,}")
        print(f"      👁️  Video Views : {video_views:,}")

        device_result["aggregate"]["total_posts"]       += 1
        device_result["aggregate"]["total_likes"]       += likes
        device_result["aggregate"]["total_comments"]    += comments
        device_result["aggregate"]["total_shares"]      += shares
        device_result["aggregate"]["total_video_views"] += video_views

        device_result["posts"].append(stats)
        time.sleep(0.5)

    # ── Device Summary ────────────────────
    agg = device_result["aggregate"]
    print(f"\n   {'─'*45}")
    print(f"   📊 DEVICE SUMMARY — {device['mobile']}")
    print(f"   {'─'*45}")
    print(f"   📄 Total Posts        : {agg['total_posts']:,}")
    print(f"   ❤️  Total Likes        : {agg['total_likes']:,}")
    print(f"   💬 Total Comments     : {agg['total_comments']:,}")
    print(f"   🔁 Total Shares       : {agg['total_shares']:,}")
    print(f"   👁️  Total Video Views  : {agg['total_video_views']:,}")

    return device_result

# ─────────────────────────────────────────
# MAIN: Get Stats From All Test Devices
# ─────────────────────────────────────────
def get_facebook_stats():
    print(f"\n{'='*55}")
    print(f"📘 FACEBOOK STATS — TEST RUN")
    print(f"   Devices  : {len(DEVICES)}")
    print(f"   Fetched  : {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*55}")

    # Step 1: Get App Token
    app_token = get_app_token()
    if not app_token:
        print("⛔ Cannot proceed without App Token.")
        return

    all_results    = []
    total_likes    = 0
    total_comments = 0
    total_views    = 0
    total_shares   = 0
    failed_devices = []

    # Step 2: Loop through each device
    for i, device in enumerate(DEVICES, 1):
        print(f"\n[{i}/{len(DEVICES)}]", end="")

        result = get_device_stats(device, app_token)

        if result:
            all_results.append(result)
            total_likes    += result["aggregate"]["total_likes"]
            total_comments += result["aggregate"]["total_comments"]
            total_views    += result["aggregate"]["total_video_views"]
            total_shares   += result["aggregate"]["total_shares"]
        else:
            failed_devices.append(device["mobile"])

        time.sleep(1)

    # ── Overall Summary ───────────────────
    print(f"\n{'='*55}")
    print(f"📈 OVERALL SUMMARY — ALL DEVICES")
    print(f"{'='*55}")
    print(f"   ✅ Successful  : {len(all_results)} device(s)")
    print(f"   ❌ Failed      : {len(failed_devices)} device(s)")
    if failed_devices:
        for d in failed_devices:
            print(f"      → {d}")
    print(f"\n   ❤️  Total Likes        : {total_likes:,}")
    print(f"   💬 Total Comments     : {total_comments:,}")
    print(f"   🔁 Total Shares       : {total_shares:,}")
    print(f"   👁️  Total Video Views  : {total_views:,}")

    # ── Save to JSON ──────────────────────
    output = {
        "fetched_at":    datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "total_devices": len(all_results),
        "aggregate": {
            "total_likes":       total_likes,
            "total_comments":    total_comments,
            "total_shares":      total_shares,
            "total_video_views": total_views,
        },
        "devices": all_results
    }

    with open("facebook_stats.json", "w") as f:
        json.dump(output, f, indent=2)

    print(f"\n✅ Full stats saved to facebook_stats.json")
    return all_results


# ─────────────────────────────────────────
# RUN
# ─────────────────────────────────────────
if __name__ == "__main__":
    get_facebook_stats()