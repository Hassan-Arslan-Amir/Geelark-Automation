# GeeLark Automation — Project Brain

> One-stop reference for developers and AI assistants.
> Explains what this project does, how every piece fits together, and where to find anything.

---

## Table of Contents

1. [What This Project Does](#1-what-this-project-does)
2. [Tech Stack & External Services](#2-tech-stack--external-services)
3. [Folder & File Map](#3-folder--file-map)
4. [Pipeline — End-to-End Flow](#4-pipeline--end-to-end-flow)
5. [File-by-File Reference](#5-file-by-file-reference)
6. [Database Schema](#6-database-schema)
7. [Authentication & Security](#7-authentication--security)
8. [Platform Registry](#8-platform-registry)
9. [Device Management](#9-device-management)
10. [Key Design Decisions](#10-key-design-decisions)
11. [Environment Variables](#11-environment-variables)
12. [How to Run](#12-how-to-run)
13. [Extending the Project](#13-extending-the-project)

---

## 1. What This Project Does

Fully automated social media posting pipeline that runs on a schedule:

1. **Downloads** today's UGC content (video or image) from a Google Drive folder.
2. **Uploads** the file to GeeLark's CDN so cloud phones can access it.
3. **Pushes** the file to 10 randomly selected cloud phone devices.
4. **Generates** an AI caption using OpenAI GPT-4o Vision (looks at the image or a mid-point frame of the video).
5. **Posts** on a randomly selected social platform (currently Instagram or TikTok) using GeeLark's RPA / Task API.
6. **Logs** everything to a Supabase PostgreSQL database.

The whole pipeline repeats every 2 hours via `scheduler.py`.

---

## 2. Tech Stack & External Services

| Layer        | Service / Library                               | Purpose                                                        |
| ------------ | ----------------------------------------------- | -------------------------------------------------------------- |
| Cloud Phones | **GeeLark** (`openapi.geelark.com/open/v1`)     | Runs Android cloud phones that actually post content           |
| File Source  | **Google Drive API** (OAuth2)                   | Downloads today's content from a dated subfolder               |
| AI Caption   | **OpenAI GPT-4o Vision**                        | Reads an image/frame and writes a platform-appropriate caption |
| Database     | **Supabase** (PostgreSQL)                       | Tracks devices, content records, post counts                   |
| Runtime      | **Python 3.x** (venv)                           | All scripts; dependencies in `venv/`                           |
| Config       | **python-dotenv** (`.env`)                      | API keys and credentials                                       |
| HTTP         | **requests** + custom `utils.py` retry wrapper  | All outbound API calls                                         |
| Dashboard    | **React 18 + TypeScript + Vite + Tailwind CSS** | Analytics dashboard — visualises `getStats.py` output          |

---

## 3. Folder & File Map

```
GeelarkAutomation/
│
├── main.py                  ← Pipeline entry point (run this for one cycle)
├── scheduler.py             ← Infinite loop — runs main.py every 2 hours
├── platforms.py             ← Platform registry + random platform/device selection
├── uploadContent.py         ← CDN upload + device start/stop + file push
├── createCaptions.py        ← OpenAI Vision caption generation
├── supabase_logger.py       ← All Supabase DB read/write operations
├── utils.py                 ← HTTP retry wrappers (api_post, api_put)
├── deviceIDs.json           ← Seed source: {mobile: {profile_id, username}} — used by seed_devices() to populate Supabase
├── schema.sql               ← Supabase DB schema (run once to set up tables)
├── getDeviceIds.py          ← One-time utility: fetch device IDs from GeeLark and write deviceIDs.json
├── getStats.py              ← Stats fetcher: pulls post metrics via HikerAPI for all devices in DB; writes to Supabase stats table + instagram_stats.json
├── .env                     ← API keys (never commit)
│
├── getContent/
│   ├── getContent.py        ← Google Drive downloader (checks Supabase before downloading)
│   ├── credentials.json     ← Google OAuth2 app credentials
│   ├── token.json           ← Cached Google OAuth2 token (auto-refreshed)
│   └── ugc_videos/          ← Downloaded files land here (organized by Drive folder name)
│
├── Instagram/
│   ├── postReelVideoOnInsta.py  ← Posts video reels via GeeLark RPA API
│   └── postReelImageOnInsta.py  ← Posts image reels via GeeLark RPA API
│
├── TikTok/
│   ├── __init__.py
│   └── postOnTikTok.py      ← Posts videos (taskType=1) and image sets (taskType=3) via GeeLark Task API
│
├── Facebook/
│   ├── __init__.py
│   └── postOnFacebook.py    ← STUB — not yet implemented, prints "NOT YET IMPLEMENTED"
│
├── venv/                    ← Python virtual environment (not in git)
│
└── Dashboard/               ← React/TypeScript analytics dashboard (Vite + Tailwind)
    ├── brain.md              ← Dashboard-specific brain document (detailed component reference)
    ├── .env                  ← REQUIRED: VITE_SUPABASE_URL + VITE_SUPABASE_ANON_KEY
    ├── src/
    │   ├── App.tsx           ← Root component; manages screen routing and search state
    │   ├── types.ts          ← TypeScript types: AnalyticsData, Account, Post, Stats
    │   ├── data.json         ← Legacy static file — no longer used; kept for reference
    │   ├── lib/
    │   │   └── supabase.ts   ← Supabase client singleton (null-safe if .env missing)
    │   ├── hooks/
    │   │   └── useSupabaseData.ts ← Fetches devices + stats from Supabase, builds Account[]
    │   └── components/
    │       ├── Sidebar.tsx           ← Navigation sidebar (Devices / Posts screens)
    │       ├── DevicesScreen.tsx     ← Per-device stats overview with search
    │       ├── PostsScreen.tsx       ← All posts across devices with search
    │       └── SearchBar.tsx         ← Reusable search by username / profile_id / mobile
    └── package.json          ← npm project (React, lucide-react, @supabase/supabase-js)
```

---

## 4. Pipeline — End-to-End Flow

```
scheduler.py
    └── every 2 hours calls run_pipeline()  ──────────────────────────────┐
                                                                          │
main.py → run_pipeline()                                                  │
    │                                                                     │
    ├─ [BOOT] seed_devices()          → populate Supabase devices table   │
    │                                   on first ever run (skips if done) │
    │                                                                     │
    ├─ [STEP 1] download_video()      → getContent/getContent.py          │
    │    ├── authenticate Google Drive (OAuth2, token auto-refreshed)     │
    │    ├── find today's subfolder in CLIENT_FOLDER_ID                   │
    │    ├── check Supabase: if already "posted" → skip (return None)     │
    │    └── download file → getContent/ugc_videos/<folder_name>/         │
    │                                                                     │
    ├─ [STEP 1b] detect media type from file extension                    │
    │    ├── VIDEO: .mp4 .mov .avi .mkv .webm                             │
    │    └── IMAGE: .jpg .jpeg .png .gif .webp                            │
    │                                                                     │
    ├─ [SELECT] select_devices(10)    → random 10 from Supabase           │
    ├─ [SELECT] select_platform()     → random platform supporting        │
    │                                   the detected media type           │
    │                                                                     │
    ├─ [LOG] create_content_record()  → Supabase: status="downloaded"     │
    │                                                                     │
    ├─ [STEP 2] upload_to_devices()   → uploadContent.py                  │
    │    ├── start_all_devices()      → GeeLark: boot 10 cloud phones     │
    │    │                              (waits 120s for boot)             │
    │    ├── upload_file_to_cdn()     → GeeLark: get presigned URL,       │
    │    │                              PUT file binary → CDN URL         │
    │    ├── push_file_to_devices()   → GeeLark: send CDN URL to          │
    │    │                              each device's file manager        │
    │    └── auto_stop logic:                                             │
    │         VIDEO → stop devices now (video RPA cold-starts fine)       │
    │         IMAGE → keep devices running (RPA needs live device)        │
    │                                                                     │
    ├─ [LOG] update_content_resource_url() → Supabase: status="uploaded"  │
    │                                                                     │
    ├─ [STEP 3] run_full_pipeline()   → createCaptions.py                 │
    │    ├── VIDEO: extract middle frame with OpenCV                      │
    │    ├── IMAGE: read file directly                                    │
    │    └── send base64 image to GPT-4o Vision → returns caption string  │
    │                                                                     │
    ├─ [STEP 4] post on platform      → platform-specific script          │
    │    ├── instagram + video  → postReelVideoOnInsta.py                 │
    │    ├── instagram + image  → postReelImageOnInsta.py                 │
    │    ├── tiktok    + video  → TikTok/postOnTikTok.py (taskType=1)     │
    │    ├── tiktok    + image  → TikTok/postOnTikTok.py (taskType=3)     │
    │    └── facebook           → STUB (not yet implemented)              │
    │                                                                     │
    ├─ [LOG] increment_device_post_counts() → Supabase devices table      │
    ├─ [LOG] update_content_caption()       → Supabase: status="posted"   │
    │                                                                     │
    └─ [STEP 5 — IMAGE ONLY]                                              │
         time.sleep(1800)  ← wait 30 min for RPA to finish posting        │
         stop_all_devices() ← then shut down the 10 cloud phones          │
                                                                          │
     ◄────────────────────────────────────────────────────────────────────┘
```

---

## 5. File-by-File Reference

### `main.py`

- **Role:** Orchestrator. Calls every other module in the correct order.
- **Entry points:**
  - `run_pipeline()` — called by scheduler or directly.
  - `if __name__ == "__main__": run_pipeline()` — run a single cycle manually.
- **Key constants:** `VIDEO_EXTENSIONS`, `IMAGE_EXTENSIONS` — define what counts as each media type.

---

### `scheduler.py`

- **Role:** Infinite loop wrapper. Runs `run_pipeline()` every `INTERVAL_HOURS` (default: 2).
- **Error handling:** Any exception inside the pipeline is caught and printed; the loop survives and continues to the next scheduled run.
- **Stop:** `Ctrl+C` cleanly prints a stop message and exits.
- **Run:** `python scheduler.py`

---

### `platforms.py`

- **Role:** Single source of truth for which platforms are active and what they support.
- **`PLATFORM_REGISTRY`** — dict of `{ platform_name: { "supports": ["video", "image"] } }`.
  - Active: `instagram`, `tiktok`
  - Commented out (stub exists): `facebook`
- **`select_platform(media_type)`** — randomly picks one active platform that supports the given media type.
- **`select_devices(count=10)`** — randomly samples `count` devices from the Supabase `devices` table.
- **To add a new platform:** Add an entry here AND implement the posting script.

---

### `uploadContent.py`

- **Role:** Everything to do with GeeLark device and CDN operations.
- **Key functions:**

| Function                                              | What it does                                                     |
| ----------------------------------------------------- | ---------------------------------------------------------------- |
| `start_all_devices(profile_ids)`                      | Boots cloud phones via GeeLark API, waits 120s                   |
| `upload_file_to_cdn(local_file)`                      | Gets presigned URL from GeeLark, PUTs binary, returns CDN URL    |
| `push_file_to_all_devices(resource_url, profile_ids)` | Tells each device to load the CDN file into its file manager     |
| `stop_all_devices(profile_ids)`                       | Shuts down cloud phones                                          |
| `run(local_file, profile_ids, auto_stop)`             | Calls all of the above in order. Main entry point from `main.py` |

- **`auto_stop` param:**
  - `True` (video) — devices stopped immediately after file is pushed.
  - `False` (image) — devices kept alive; `main.py` stops them 30 min later after the RPA completes.

---

### `createCaptions.py`

- **Role:** Uses OpenAI GPT-4o Vision to generate a social media caption.
- **Video input:** extracts the middle frame using OpenCV (`cv2`), converts to base64 JPEG.
- **Image input:** reads the file directly and converts to base64.
- **Output:** a plain text caption string ready to be passed to posting functions.
- **Main entry point:** `run_full_pipeline(media_path, media_type)`.

---

### `supabase_logger.py`

- **Role:** All database operations. Every other module imports from here — nothing else touches Supabase directly.
- **Functions:**

| Function                                                           | When called      | What it writes                                                                                                                                               |
| ------------------------------------------------------------------ | ---------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| `seed_devices()`                                                   | Pipeline boot    | Inserts devices from `deviceIDs.json` (with `username`) into `devices` table; backfills `username` for existing rows where it was null                       |
| `get_all_devices()`                                                | Pipeline runtime | Returns all devices as `{mobile: profile_id}` from Supabase `devices` table                                                                                  |
| `get_all_devices_full()`                                           | `getStats.py`    | Returns `[{id, mobile, profile_id, username}]` filtered to rows where `username IS NOT NULL` — used instead of a hardcoded device list                       |
| `get_content_status(content_key)`                                  | Before download  | Returns `"not_found"` / `"not_posted"` / `"posted"`. Exact match on relative key first; falls back to ILIKE for old absolute-path records                    |
| `create_content_record(local_path, platform)`                      | After download   | Inserts row in `content`, status=`"downloaded"`                                                                                                              |
| `update_content_resource_url(content_id, url)`                     | After CDN upload | Updates `resource_url`, status=`"uploaded"`                                                                                                                  |
| `update_content_caption(content_id, caption, device_ids)`          | After posting    | Updates `caption`, `device_ids`, status=`"posted"`                                                                                                           |
| `increment_device_post_counts(profile_ids)`                        | After posting    | Increments `no_of_posts` for each device that got a task                                                                                                     |
| `upsert_post_stats(device_id, username, posts)`                    | `getStats.py`    | Upserts per-post rows into the `stats` table. Conflict key: `permalink` → overwrites with latest values. Converts Unix timestamp to ISO via `_unix_to_iso()` |
| `update_device_aggregate_stats(device_id, views, likes, comments)` | `getStats.py`    | Overwrites `views`, `likes`, `comments` aggregate columns on the matching `devices` row                                                                      |

---

### `utils.py`

- **Role:** HTTP retry wrapper used by all API-calling modules.
- **`api_post(url, headers, json_data)`** — retries up to 5 times with linear backoff (3s, 6s, 9s…) on `ConnectionError`.
- **`api_put(url, data)`** — same retry logic for binary PUT uploads.

---

### `getContent/getContent.py`

- **Role:** Downloads today's UGC file from Google Drive.
- **Logic:**
  1. Authenticates with Google Drive OAuth2 (token cached in `token.json`, auto-refreshed).
  2. Lists subfolders inside `CLIENT_FOLDER_ID`.
  3. Finds the subfolder whose name starts with today's date (`DD-MM-YY` or `DD-MM-YYYY`).
  4. Checks Supabase (`get_content_status`) — if already `"posted"`, returns `None` (skip).
  5. Downloads the first file found in that folder to `ugc_videos/<folder_name>/`.
  6. Returns the absolute local path, or `None` if nothing to download.
- **Config to change:** `CLIENT_FOLDER_ID` at the top of the file (the Google Drive parent folder ID).

---

### `Instagram/postReelVideoOnInsta.py`

- **GeeLark API endpoint:** `POST /rpa/task/instagramPubReels`
- **Device ID field:** `id` (GeeLark profile ID)
- **Caption field:** `description`
- **Main function:** `post_reels_on_all_devices(video_urls, caption, profile_ids)`

---

### `Instagram/postReelImageOnInsta.py`

- **GeeLark API endpoint:** `POST /rpa/task/instagramPubReelsImages`
- **Device ID field:** `id`
- **Caption field:** `description`
- **Main function:** `post_images_on_all_devices(image_urls, caption, profile_ids)`

---

### `TikTok/postOnTikTok.py`

- **GeeLark API endpoint:** `POST /task/add`
- **Device ID field:** `envId` ← **different from Instagram which uses `id`**
- **Caption field:** `videoDesc`
- **Video field:** single string URL (not an array)
- **Response:** `data.taskIds[]`
- **Task types:**
  - `taskType: 1` → video post
  - `taskType: 3` → image set post
- **Schedule helpers:** `get_schedule_now()`, `get_schedule_after_minutes(n)`, `get_schedule_after_hours(n)`, `get_schedule_at("YYYY-MM-DD HH:MM:SS")`
- **Main functions:**
  - `post_videos_on_devices(video_urls, caption, profile_ids, ...)`
  - `post_images_on_devices(image_urls, caption, profile_ids, ...)`

---

### `Facebook/postOnFacebook.py`

- **Status: STUB** — functions exist but print `"NOT YET IMPLEMENTED"` and return `[]`.
- Functions: `post_videos_on_devices(...)`, `post_images_on_devices(...)`
- To implement: add real GeeLark API calls, then uncomment `facebook` in `platforms.py`.

---

### `deviceIDs.json`

- Format: `{ "mobile_number": {"profile_id": "geelark_id", "username": "account_username"}, ... }`
- All entries include a `username`. `seed_devices()` seeds the `username` column in Supabase and backfills it for any existing rows where it was previously null.
- **Runtime role: none.** Only consumed by `seed_devices()` in `supabase_logger.py`.
- All runtime device reads go through `get_all_devices()` → Supabase `devices` table.
- Generated/refreshed by: `getDeviceIds.py` (run once to pull latest from GeeLark API).

---

### `Dashboard/`

- **Role:** React/TypeScript analytics frontend. Reads **live data directly from Supabase** (`devices` + `stats` tables) and displays per-device and per-post stats.
- **Two screens:**
  - **Devices** — card-based overview of each account: total views, likes, comments, post count. Click any device to drill into its posts.
  - **Posts** — flat list of every post across all devices with full stats (views, likes, comments, reshares, reach, impressions, saves), media type badge, and Instagram permalink.
- **Search:** both screens support filtering by `username`, `profile_id`, or `mobile` number.
- **Data source:** Supabase — requires `Dashboard/.env` with `VITE_SUPABASE_URL` and `VITE_SUPABASE_ANON_KEY`. If the file is missing, the app shows a clear error screen instead of a blank page.
- **Data flow:** `useSupabaseData` hook fetches `devices` + `stats` on mount → groups stats by `device_id` → assembles `Account[]` → computes aggregate totals.
- **`data.json`** — legacy static file left from before the Supabase migration. Not imported anywhere; safe to delete.
- **Stack:** React 18, TypeScript, Vite, Tailwind CSS, lucide-react icons.
- **Detailed reference:** see `Dashboard/brain.md` for component-level documentation.
- **Run:** `cd Dashboard && npm install && npm run dev`

---

### `getStats.py`

- **Role:** Fetches Instagram post metrics for every device in the Supabase `devices` table via HikerAPI; writes results to both Supabase and a local JSON file.
- **External API:** HikerAPI (`hikerapi` Python client, token from `HIKER_ACCESS_KEY` in `.env`).
- **Device source:** calls `get_all_devices_full()` — reads all devices with a non-null `username` from Supabase. **No hardcoded device list.**
- **Flow per device:**
  1. `get_user_id(username)` — resolves Instagram username → numeric user ID (`user_by_username_v1`).
  2. `get_all_posts(user_id)` — paginates through all posts via `user_medias_gql` (12 per page).
  3. `get_post_stats(media_id)` — fetches per-post metrics via `media_info_by_id_v2` + `media_insight_v1`.
- **Metrics collected:** views (`play_count`), likes, comments, reshares, reach, impressions, saves, media type, timestamp, permalink.
- **DB writes (per device, after all its posts are processed):**
  - `upsert_post_stats(device_id, username, posts)` → upserts rows into `stats` table (conflict key: `permalink`).
  - `update_device_aggregate_stats(device_id, views, likes, comments)` → overwrites the aggregate columns on the `devices` row.
- **JSON output:** `_save_json()` writes `instagram_stats.json` **after every device** (not just at the end) so progress is never lost if the run is interrupted.
- **Problem device tracking:** devices where HikerAPI returns no user ID are logged as `🔴 Username Not Found`; devices with a valid account but zero posts are logged as `🟡 No Posts Found`. A summary of both lists is printed at the end.
- **Note:** Requires a funded HikerAPI account. Rate limit protection: 1-second sleep between devices, 0.5-second sleep between pagination pages.

---

### `schema.sql`

- Run once in **Supabase Dashboard → SQL Editor** to create both tables.
- Does not need to be re-run; it uses `CREATE TABLE IF NOT EXISTS`.

---

## 6. Database Schema

### `devices` table

| Column        | Type         | Description                                                         |
| ------------- | ------------ | ------------------------------------------------------------------- |
| `id`          | BIGSERIAL PK | Auto-increment                                                      |
| `mobile`      | TEXT UNIQUE  | Mobile number label (e.g. `"102"`)                                  |
| `profile_id`  | TEXT UNIQUE  | GeeLark cloud phone profile ID                                      |
| `username`    | TEXT         | Instagram/TikTok account username on this device (nullable)         |
| `no_of_posts` | INTEGER      | Running total of posts scheduled on this device                     |
| `views`       | INTEGER      | Aggregate total views across all posts — overwritten by getStats    |
| `likes`       | INTEGER      | Aggregate total likes across all posts — overwritten by getStats    |
| `comments`    | INTEGER      | Aggregate total comments across all posts — overwritten by getStats |
| `created_at`  | TIMESTAMPTZ  | Row creation time                                                   |

### `content` table

| Column         | Type         | Description                                       |
| -------------- | ------------ | ------------------------------------------------- |
| `id`           | BIGSERIAL PK | Auto-increment                                    |
| `date`         | DATE         | Date downloaded/posted                            |
| `local_path`   | TEXT         | Absolute path to downloaded file on local machine |
| `resource_url` | TEXT         | GeeLark CDN URL after upload                      |
| `caption`      | TEXT         | AI-generated caption                              |
| `platform`     | TEXT         | `"instagram"` / `"tiktok"` / `"facebook"`         |
| `device_ids`   | JSONB        | Array of profile IDs that received a post task    |
| `status`       | TEXT         | `"downloaded"` → `"uploaded"` → `"posted"`        |

### `stats` table

| Column        | Type         | Description                                                                      |
| ------------- | ------------ | -------------------------------------------------------------------------------- |
| `id`          | BIGSERIAL PK | Auto-increment                                                                   |
| `device_id`   | INTEGER (FK) | References `devices.id`                                                          |
| `username`    | TEXT         | Denormalised Instagram handle (for quick lookup without a join)                  |
| `permalink`   | TEXT UNIQUE  | Full Instagram post URL — used as the upsert conflict key                        |
| `media_type`  | INTEGER      | `1` = photo, `2` = video/reel (Instagram enum)                                   |
| `views`       | INTEGER      | Play count (reels) or view count (photos)                                        |
| `likes`       | INTEGER      |                                                                                  |
| `comments`    | INTEGER      |                                                                                  |
| `reshares`    | INTEGER      |                                                                                  |
| `reach`       | INTEGER      | From `media_insight_v1` (only available for owned accounts)                      |
| `impressions` | INTEGER      | From `media_insight_v1`                                                          |
| `saves`       | INTEGER      | From `media_insight_v1`                                                          |
| `posted_at`   | TIMESTAMPTZ  | Original post time — converted from Instagram Unix timestamp by `_unix_to_iso()` |
| `fetched_at`  | TIMESTAMPTZ  | Timestamp of the last `getStats.py` run that wrote this row                      |

> **Write pattern:** `getStats.py` upserts into this table on every run (conflict on `permalink` → overwrite). The Dashboard reads from this table live via Supabase.

---

## 7. Authentication & Security

### GeeLark API — Key Verification

Every request to GeeLark must include these headers (generated fresh per request):

```
appId   = from .env
traceId = UUIDv4 (uppercase)
ts      = current Unix milliseconds
nonce   = first 6 chars of traceId
sign    = SHA256(appId + traceId + ts + nonce + apiKey).upper()
```

Implemented in `get_headers()` inside each script (`uploadContent.py`, `Instagram/`, `TikTok/`).

### Google Drive — OAuth2

- `credentials.json` = OAuth2 app credentials from Google Cloud Console.
- `token.json` = cached access + refresh token (auto-refreshed when expired).
- Both files live in `getContent/`.

### Supabase

- Access via `SUPABASE_URL` + `SUPABASE_KEY` (service role key in `.env`).
- RLS is **disabled** on both tables — this is a private server-side automation script with no public access.

---

## 8. Platform Registry

Defined in `platforms.py`. To change which platforms are active, edit `PLATFORM_REGISTRY`:

```python
PLATFORM_REGISTRY = {
    "instagram": { "supports": ["video", "image"] },   # ✅ Active
    "tiktok":    { "supports": ["video", "image"] },   # ✅ Active
    # "facebook": { "supports": ["video", "image"] },  # ⏳ Stub — uncomment when ready
}
```

Each pipeline run picks **one random platform** from those compatible with the detected media type.

---

## 9. Device Management

- Total devices: stored in and read from Supabase `devices` table (source of truth). `deviceIDs.json` is only used for the initial one-time seeding via `seed_devices()`.
- Devices per run: **10** (random sample, configurable via `DEVICES_PER_RUN` in `platforms.py`).
- Device lifecycle per run:
  1. `start_all_devices()` — boots 10 phones, waits 120s.
  2. `push_file_to_all_devices()` — sends CDN URL to each phone.
  3. `stop_all_devices()` — shuts down phones.
     - Video: stopped immediately after file push.
     - Image: stopped 30 minutes after posting tasks are scheduled.

---

## 10. Key Design Decisions

| Decision                                               | Reason                                                                                                                                        |
| ------------------------------------------------------ | --------------------------------------------------------------------------------------------------------------------------------------------- |
| `auto_stop=False` for images                           | Image RPA requires the device to be actively running at task execution time. Video RPA is resilient to a cold restart from a stopped state.   |
| 30-minute wait before stopping image devices           | Gives the RPA enough time to open the app, navigate, and post before the device is killed.                                                    |
| Schedule time generated **inside** the per-device loop | Prevents stale timestamps. Each device gets `now + 60s` calculated fresh at the moment its task is created.                                   |
| Random platform + random devices per run               | Distributes posting across platforms and simulates organic behavior across the device pool.                                                   |
| Supabase status check before download                  | Prevents re-downloading and re-posting content that was already successfully handled. Also handles interrupted runs (`"not_posted"` → retry). |
| `utils.py` retry wrapper                               | Network flakiness is common with cloud phone APIs. 5-attempt linear backoff prevents single-failure crashes.                                  |

---

## 11. Environment Variables

All stored in `.env` at the project root. Never commit this file.

```env
# GeeLark
GEELARK_APP_ID=
GEELARK_API_KEY=
GEELARK_BEARER_TOKEN=      # (legacy — kept for compatibility)

# OpenAI
OPENAI_API_KEY=

# Supabase
SUPABASE_URL=
SUPABASE_KEY=

# HikerAPI (Instagram stats)
HIKER_ACCESS_KEY=
```

---

## 12. How to Run

```powershell
# Activate virtual environment (Windows)
Set-ExecutionPolicy -Scope Process -ExecutionPolicy RemoteSigned
& e:\BitBash\GeelarkAutomation\venv\Scripts\Activate.ps1

# Run a single pipeline cycle (for testing)
python main.py

# Start the automated scheduler (runs every 2 hours forever)
python scheduler.py

# Run the analytics dashboard
# Requires Dashboard/.env — create it first:
#   VITE_SUPABASE_URL=https://your-project.supabase.co
#   VITE_SUPABASE_ANON_KEY=your-anon-public-key  (from Supabase Dashboard → Settings → API)
cd Dashboard
npm install   # first time only
npm run dev
```

---

## 13. Extending the Project

### Add Facebook support

1. Implement real API calls in `Facebook/postOnFacebook.py`.
   - Match the function signatures: `post_videos_on_devices(video_urls, caption, profile_ids, ...)` and `post_images_on_devices(...)`.
   - Return a list of dicts with `{"profileId": ..., "status": "created"}` for successful tasks.
2. Uncomment `facebook` in `PLATFORM_REGISTRY` inside `platforms.py`.
3. No changes needed in `main.py` — the routing is already there.

### Add a new platform entirely

1. Create `NewPlatform/__init__.py` (empty).
2. Create `NewPlatform/postOnNewPlatform.py` with `post_videos_on_devices()` and/or `post_images_on_devices()`.
3. Add an entry to `PLATFORM_REGISTRY` in `platforms.py`.
4. Add `elif platform == "newplatform":` routing block in `main.py` under Step 4.

### Change run interval

Edit `INTERVAL_HOURS` in `scheduler.py`.

### Change number of devices per run

Edit `DEVICES_PER_RUN` in `platforms.py`. The `select_devices()` call in `main.py` uses this as the default.

### Add a new content source

Replace or wrap `getContent/getContent.py`. The function must return an absolute local file path on success, or `None` to signal "nothing to post today".
