import os
import re
import argparse
import requests
from datetime import datetime
import yt_dlp
from urllib.parse import urlparse, parse_qs
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


def _fmt(n):
    try:
        return f"{int(n):,}"
    except Exception:
        return str(n)


def _compute_and_print(platform, url, views, likes, comments, shares):
    views = int(views) if views is not None else 0
    likes = int(likes) if likes is not None else 0
    comments = int(comments) if comments is not None else 0
    shares = int(shares) if shares is not None else 0

    engagement_rate = ((likes + comments + shares) / views * 100) if views > 0 else 0
    virality_rate = (shares / views * 100) if views > 0 else 0
    comment_rate = (comments / views * 100) if views > 0 else 0
    like_rate = (likes / views * 100) if views > 0 else 0

    print(f"\n===== {platform.upper()} ANALYSIS =====")
    print("URL:", url)
    print("Views:", _fmt(views))
    print("Likes:", _fmt(likes))
    print("Comments:", _fmt(comments))
    print("Shares:", _fmt(shares))
    print("\n===== PERFORMANCE =====")
    print(f"Engagement Rate: {engagement_rate:.2f}%")
    print(f"Virality Rate: {virality_rate:.2f}%")
    print(f"Comment Rate: {comment_rate:.2f}%")
    print(f"Like Rate: {like_rate:.2f}%")


def analyze_tiktok(url):
    api_url = f"https://www.tikwm.com/api/?url={url}"

    try:
        response = requests.get(api_url, timeout=20)
        response.raise_for_status()

        data = response.json()

        if "data" not in data:
            print("No video data found.")
            return

        video = data["data"]

        views = video.get("play_count", 0)
        likes = video.get("digg_count", 0)
        comments = video.get("comment_count", 0)
        shares = video.get("share_count", 0)

        _compute_and_print("TikTok", url, views, likes, comments, shares)

    except Exception as e:
        print("TikTok Error:", str(e))


def _extract_youtube_id(url):
    # handles many YouTube URL formats
    patterns = [
        r"(?:v=|/videos/|embed/|youtu\.be/)([A-Za-z0-9_-]{11})",
    ]
    for p in patterns:
        m = re.search(p, url)
        if m:
            return m.group(1)

    # fallback to query param
    parsed = urlparse(url)
    qs = parse_qs(parsed.query)
    if "v" in qs:
        return qs["v"][0]
    return None


def get_youtube_views_no_key(url):
    headers = {"User-Agent": "Mozilla/5.0"}
    try:
        r = requests.get(url, headers=headers, timeout=10)
        r.raise_for_status()
        text = r.text
        print(text)
        # print(r.json())
        m = re.search(r'"viewCount"\s*:\s*"([0-9,]+)"', text)
        if m:
            return int(m.group(1).replace(",", ""))
        m2 = re.search(r'([0-9,]+)\s+views', text)
        if m2:
            return int(m2.group(1).replace(",", ""))
    except Exception:
        return None
    return None


def get_instagram_counts_no_key(url):
    headers = {"User-Agent": "Mozilla/5.0"}
    try:
        r = requests.get(url, headers=headers, timeout=10)
        r.raise_for_status()
        text = r.text
        likes = None
        comments = None
        views = None
        m = re.search(r'"edge_media_preview_like"\s*:\s*\{\s*"count"\s*:\s*([0-9]+)\s*\}', text)
        if m:
            likes = int(m.group(1))
        m2 = re.search(r'"edge_media_to_comment"\s*:\s*\{\s*"count"\s*:\s*([0-9]+)\s*\}', text)
        if m2:
            comments = int(m2.group(1))
        # some reels/stories include view_count
        m3 = re.search(r'"view_count"\s*:\s*([0-9]+)', text)
        if m3:
            views = int(m3.group(1))
        return {"likes": likes, "comments": comments, "views": views, "shares": None}
    except Exception:
        return None


def get_facebook_counts_no_key(url):
    headers = {"User-Agent": "Mozilla/5.0"}
    try:
        r = requests.get(url, headers=headers, timeout=10)
        r.raise_for_status()
        text = r.text
        reactions = None
        comments = None
        shares = None
        views = None
        m = re.search(r'"reaction_count"\s*:\s*([0-9]+)', text)
        if m:
            reactions = int(m.group(1))
        m2 = re.search(r'"comment_count"\s*:\s*([0-9]+)', text)
        if m2:
            comments = int(m2.group(1))
        m3 = re.search(r'"share_count"\s*:\s*([0-9]+)', text)
        if m3:
            shares = int(m3.group(1))
        # fallback text matches
        m4 = re.search(r'([0-9,]+)\s+comments', text)
        if m4 and comments is None:
            comments = int(m4.group(1).replace(",", ""))
        m5 = re.search(r'([0-9,]+)\s+shares', text)
        if m5 and shares is None:
            shares = int(m5.group(1).replace(",", ""))
        return {"reactions": reactions, "comments": comments, "shares": shares, "views": views}
    except Exception:
        return None


def analyze_youtube(url, api_key=None, force_no_key=False):
    vid = _extract_youtube_id(url)
    if not vid:
        print("Could not extract YouTube video id from URL:", url)
        return

    if not api_key and not force_no_key:
        api_key = os.environ.get("YOUTUBE_API_KEY")
    if (not api_key) or force_no_key:
        # try a no-key fallback by scraping the public video page
        views = get_youtube_views_no_key(url)
        if views is None:
            print("YouTube API key not provided and scraping fallback failed. Set YOUTUBE_API_KEY env var or pass api_key.")
            return
        _compute_and_print("YouTube", url, views, None, None, None)
        return

    api = f"https://www.googleapis.com/youtube/v3/videos?part=statistics,snippet&id={vid}&key={api_key}"
    try:
        r = requests.get(api, timeout=15)
        r.raise_for_status()
        j = r.json()
        items = j.get("items", [])
        if not items:
            print("No YouTube video data found for id:", vid)
            return
        stats = items[0].get("statistics", {})
        views = int(stats.get("viewCount", 0))
        likes = int(stats.get("likeCount", 0)) if stats.get("likeCount") else 0
        comments = int(stats.get("commentCount", 0)) if stats.get("commentCount") else 0
        shares = 0

        _compute_and_print("YouTube", url, views, likes, comments, shares)

    except Exception as e:
        print("YouTube Error:", str(e))

# def analyze_youtube_2(url, api_key=None, force_no_key=False):
#     vid = _extract_youtube_id(url)
#     if not vid:
#         print("Could not extract YouTube video ID from URL:", url)
#         return

#     if not api_key:
#         api_key = os.environ.get("YOUTUBE_API_KEY")
#     if not api_key:
#         print("YouTube API key not provided. Set YOUTUBE_API_KEY env var.")
#         return

#     api = f"https://www.googleapis.com/youtube/v3/videos?part=statistics,snippet&id={vid}&key={api_key}"
#     try:
#         r = requests.get(api, timeout=15)
#         r.raise_for_status()
#         j = r.json()
#         items = j.get("items", [])
#         if not items:
#             print("No YouTube video found for ID:", vid)
#             return
#         stats = items[0].get("statistics", {})
#         views    = int(stats.get("viewCount", 0))
#         likes    = int(stats.get("likeCount", 0)) if stats.get("likeCount") else 0
#         comments = int(stats.get("commentCount", 0)) if stats.get("commentCount") else 0
#         shares   = 0  # YouTube API does not expose share counts

#         _compute_and_print("YouTube", url, views, likes, comments, shares)

#     except Exception as e:
#         print("YouTube Error:", str(e))

def analyze_youtube_3(url):
    ydl_opts = {
        'quiet': True,
        'skip_download': True,
        'no_warnings': True,
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)

            views    = info.get("view_count") or 0
            likes    = info.get("like_count") or 0
            comments = info.get("comment_count") or 0
            shares   = 0  # YouTube never exposes share count

            _compute_and_print("YouTube", url, views, likes, comments, shares)

    except Exception as e:
        print("YouTube Error:", str(e))


def analyze_facebook(url, access_token=None, force_no_key=False):
    # Uses Facebook Graph API to get engagement counts for a URL (post or video)
    if not access_token and not force_no_key:
        access_token = os.environ.get("FACEBOOK_ACCESS_TOKEN")
    if (not access_token) or force_no_key:
        # try scraping fallback for public pages/posts
        fb = get_facebook_counts_no_key(url)
        if not fb:
            print("Facebook access token not provided and scraping fallback failed. Set FACEBOOK_ACCESS_TOKEN env var or pass access_token.")
            return
        _compute_and_print("Facebook", url, fb.get("views"), fb.get("reactions"), fb.get("comments"), fb.get("shares"))
        return

    api = f"https://graph.facebook.com/v17.0/?id={url}&fields=engagement&access_token={access_token}"
    try:
        r = requests.get(api, timeout=15)
        r.raise_for_status()
        j = r.json()
        engagement = j.get("engagement", {})
        reaction_count = engagement.get("reaction_count") or 0
        comment_count = engagement.get("comment_count") or 0
        share_count = engagement.get("share_count") or 0
        views = engagement.get("view_count") or 0

        _compute_and_print("Facebook", url, views, reaction_count, comment_count, share_count)

    except Exception as e:
        print("Facebook Error:", str(e))


def analyze_instagram(url, access_token=None, force_no_key=False):
    # Instagram metrics are available via the Facebook Graph API for Instagram Business/Creator accounts.
    # This function attempts to use the same Graph endpoint for a public URL's engagement summary.
    if not access_token and not force_no_key:
        access_token = os.environ.get("FACEBOOK_ACCESS_TOKEN")
    if (not access_token) or force_no_key:
        # try scraping fallback for public Instagram posts
        ig = get_instagram_counts_no_key(url)
        if not ig:
            print("Instagram access token not provided and scraping fallback failed. Set FACEBOOK_ACCESS_TOKEN env var (Instagram Graph uses FB token) or pass access_token.")
            return
        _compute_and_print("Instagram", url, ig.get("views"), ig.get("likes"), ig.get("comments"), ig.get("shares"))
        return

    api = f"https://graph.facebook.com/v17.0/?id={url}&fields=engagement&access_token={access_token}"
    try:
        r = requests.get(api, timeout=15)
        r.raise_for_status()
        j = r.json()
        engagement = j.get("engagement", {})
        reaction_count = engagement.get("reaction_count") or 0
        comment_count = engagement.get("comment_count") or 0
        share_count = engagement.get("share_count") or 0
        views = engagement.get("view_count") or 0

        _compute_and_print("Instagram", url, views, reaction_count, comment_count, share_count)

    except Exception as e:
        print("Instagram Error:", str(e))


if __name__ == "__main__":
    # Example usage: set YOUTUBE_API_KEY and FACEBOOK_ACCESS_TOKEN in your environment
    # export YOUTUBE_API_KEY=your_key
    # export FACEBOOK_ACCESS_TOKEN=your_token

    tiktok_url = "https://www.tiktok.com/@toysrus_il/video/7637136602791185671"
    # yt_url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
    yt_url = "https://www.youtube.com/watch?v=pTZkBtQkrDo"
    fb_url = "https://www.facebook.com/zuck/posts/10102577175875681"
    ig_url = "https://www.instagram.com/reel/DYXksy4ylwL/?utm_source=ig_web_copy_link&igsh=NTc4MTIwNjQ2YQ=="

    parser = argparse.ArgumentParser()
    parser.add_argument("--no-key", action="store_true", help="Force no-key scraping for platforms even if keys/tokens are present")
    args = parser.parse_args()

    force_no_key = args.no_key or os.environ.get("FORCE_NO_KEY") in ("1", "true", "True")

    print("Running analyzers (force_no_key={}):".format(force_no_key))
    # analyze_tiktok(tiktok_url)
    analyze_youtube(yt_url, force_no_key=force_no_key)
    # analyze_youtube_3(yt_url)
    # analyze_facebook(fb_url, force_no_key=force_no_key)
    # analyze_instagram(ig_url, force_no_key=force_no_key)
