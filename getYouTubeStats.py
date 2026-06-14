import os
import json
import time
import requests
from dotenv import load_dotenv
from datetime import datetime

load_dotenv()

YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY")

DEVICES = {
    "103": {
        "profile_id": "613444962649899427",
        "username": "@PollyVachon"
    },
    "102": {
        "profile_id": "613444917972173207",
        "username": "@JudithJohnson-t2f"
    },
    "6": {
        "profile_id": "613444510386487715",
        "username": "@KristyBurns-b1i"
    }
}


# ─────────────────────────────────────────
# STEP 1: Get Channel ID from Handle
# ─────────────────────────────────────────
def get_channel_id(handle: str):
    try:
        url = "https://www.googleapis.com/youtube/v3/channels"

        params = {
            "part": "id",
            "forHandle": handle,
            "key": YOUTUBE_API_KEY
        }

        response = requests.get(url, params=params)
        data = response.json()

        items = data.get("items", [])

        if not items:
            return None

        return items[0]["id"]

    except Exception as e:
        print(f"❌ Could not get channel ID for {handle}: {e}")
        return None


# ─────────────────────────────────────────
# STEP 2: Get Upload Playlist ID
# ─────────────────────────────────────────
def get_uploads_playlist(channel_id):
    try:
        url = "https://www.googleapis.com/youtube/v3/channels"

        params = {
            "part": "contentDetails",
            "id": channel_id,
            "key": YOUTUBE_API_KEY
        }

        response = requests.get(url, params=params)
        data = response.json()

        items = data.get("items", [])

        if not items:
            return None

        return items[0]["contentDetails"]["relatedPlaylists"]["uploads"]

    except Exception as e:
        print(f"❌ Could not get uploads playlist: {e}")
        return None


# ─────────────────────────────────────────
# STEP 3: Get ALL Videos
# ─────────────────────────────────────────
def get_all_videos(playlist_id):
    videos = []
    page_token = None

    try:
        while True:
            url = "https://www.googleapis.com/youtube/v3/playlistItems"

            params = {
                "part": "snippet",
                "playlistId": playlist_id,
                "maxResults": 50,
                "pageToken": page_token,
                "key": YOUTUBE_API_KEY
            }

            response = requests.get(url, params=params)
            data = response.json()

            for item in data.get("items", []):
                video_id = item["snippet"]["resourceId"]["videoId"]

                videos.append({
                    "video_id": video_id,
                    "title": item["snippet"]["title"]
                })

            page_token = data.get("nextPageToken")

            if not page_token:
                break

            time.sleep(0.3)

    except Exception as e:
        print(f"❌ Could not fetch videos: {e}")

    return videos


# ─────────────────────────────────────────
# STEP 4: Get Video Stats
# ─────────────────────────────────────────
def get_video_stats(video_id):
    try:
        url = "https://www.googleapis.com/youtube/v3/videos"

        params = {
            "part": "statistics,snippet",
            "id": video_id,
            "key": YOUTUBE_API_KEY
        }

        response = requests.get(url, params=params)
        data = response.json()

        items = data.get("items", [])

        if not items:
            return {}

        item = items[0]

        statistics = item.get("statistics", {})
        snippet = item.get("snippet", {})

        return {
            "views": int(statistics.get("viewCount", 0)),
            "likes": int(statistics.get("likeCount", 0)),
            "comments": int(statistics.get("commentCount", 0)),
            "timestamp": snippet.get("publishedAt"),
            "permalink": f"https://www.youtube.com/watch?v={video_id}"
        }

    except Exception as e:
        print(f"❌ Could not fetch stats for {video_id}: {e}")
        return {}


# ─────────────────────────────────────────
# SAVE JSON
# ─────────────────────────────────────────
def save_json(results, total_views, total_likes, total_comments):

    output = {
        "fetched_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "total_devices": len(results),
        "aggregate": {
            "total_views": total_views,
            "total_likes": total_likes,
            "total_comments": total_comments
        },
        "accounts": results
    }

    with open("instagram_stats.json", "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)


# ─────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────
def get_youtube_stats():

    print("\n" + "=" * 60)
    print("📊 FETCHING YOUTUBE STATS")
    print("=" * 60)

    results = []

    total_views = 0
    total_likes = 0
    total_comments = 0

    for index, (device_id, device) in enumerate(DEVICES.items(), start=1):

        print(
            f"\n[{index}/{len(DEVICES)}] "
            f"{device['profile_id']} | {device['username']}"
        )

        try:

            channel_id = get_channel_id(device["username"])

            if not channel_id:
                print("   ❌ Channel not found")
                continue

            print(f"   📺 Channel ID: {channel_id}")

            playlist_id = get_uploads_playlist(channel_id)

            if not playlist_id:
                print("   ❌ Upload playlist not found")
                continue

            videos = get_all_videos(playlist_id)

            if not videos:
                print("   ⚠️ No videos found")
                continue

            print(f"   📂 Total Videos Found: {len(videos)}")

            device_result = {
                "profile_id": device["profile_id"],
                "username": device["username"],
                "posts": []
            }

            device_views = 0
            device_likes = 0
            device_comments = 0

            for idx, video in enumerate(videos, start=1):

                stats = get_video_stats(video["video_id"])

                if not stats:
                    continue

                views = stats["views"]
                likes = stats["likes"]
                comments = stats["comments"]

                total_views += views
                total_likes += likes
                total_comments += comments

                device_views += views
                device_likes += likes
                device_comments += comments

                print(f"\n   📌 Video {idx}")
                print(f"      🎬 {video['title']}")
                print(f"      👁️ Views    : {views:,}")
                print(f"      ❤️ Likes    : {likes:,}")
                print(f"      💬 Comments : {comments:,}")

                device_result["posts"].append({
                    "title": video["title"],
                    "permalink": stats["permalink"],
                    "stats": stats
                })

            results.append(device_result)

            save_json(
                results,
                total_views,
                total_likes,
                total_comments
            )

            print("   💾 JSON Updated")

        except Exception as e:
            print(f"❌ Error: {e}")

        time.sleep(1)

    print("\n" + "=" * 60)
    print("📈 TOTAL YOUTUBE STATS")
    print("=" * 60)
    print(f"👁️ Total Views    : {total_views:,}")
    print(f"❤️ Total Likes    : {total_likes:,}")
    print(f"💬 Total Comments : {total_comments:,}")
    print("=" * 60)

    print("\n✅ Saved to instagram_stats.json")

    return results


if __name__ == "__main__":
    get_youtube_stats()