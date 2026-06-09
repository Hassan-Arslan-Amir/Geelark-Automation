-- ─────────────────────────────────────────
-- Supabase Database Schema
-- Run once in: Supabase Dashboard → SQL Editor → New Query
-- ─────────────────────────────────────────

-- Table: devices
-- Stores all GeeLark cloud phone devices.
-- Pre-populated from deviceIDs.json via seed_devices() in supabase_logger.py
CREATE TABLE IF NOT EXISTS devices (
    id          BIGSERIAL PRIMARY KEY,
    mobile      TEXT NOT NULL UNIQUE,
    profile_id  TEXT NOT NULL UNIQUE,
    username    TEXT,                   -- Instagram/TikTok username on this device
    no_of_posts INTEGER DEFAULT 0,
    created_at  TIMESTAMPTZ DEFAULT NOW()
);

-- Disable Row Level Security (private automation script — no public access)
ALTER TABLE devices DISABLE ROW LEVEL SECURITY;

-- Table: content
-- Stores each content piece downloaded from Google Drive and posted on Instagram.
CREATE TABLE IF NOT EXISTS content (
    id           BIGSERIAL PRIMARY KEY,
    date         DATE NOT NULL,         -- Date content was downloaded and posted
    local_path   TEXT,                  -- Local file path of downloaded content
    resource_url TEXT,                  -- GeeLark CDN URL after upload
    caption      TEXT,                  -- AI-generated Instagram caption
    platform     TEXT DEFAULT 'instagram',
    device_ids   JSONB,                 -- JSON array of selected device profile IDs
    status       TEXT DEFAULT 'downloaded', -- Progress: downloaded → uploaded → posted
    created_at   TIMESTAMPTZ DEFAULT NOW(),
    views        INTEGER DEFAULT 0,
    likes        INTEGER DEFAULT 0,
    comments     INTEGER DEFAULT 0,
);

-- Disable Row Level Security (private automation script — no public access)
ALTER TABLE content DISABLE ROW LEVEL SECURITY;

-- Table: stats
-- Stores per-post Instagram stats fetched via HikerAPI.
-- One row per post; upserted on each getStats.py run (permalink is unique key).
CREATE TABLE IF NOT EXISTS stats (
    id          BIGSERIAL PRIMARY KEY,
    device_id   BIGINT REFERENCES devices(id),
    username    TEXT,
    permalink   TEXT UNIQUE,            -- unique per post; used as upsert key
    media_type  INTEGER,                -- 1=photo, 2=video/reel
    views       INTEGER DEFAULT 0,
    likes       INTEGER DEFAULT 0,
    comments    INTEGER DEFAULT 0,
    reshares    INTEGER DEFAULT 0,
    reach       INTEGER DEFAULT 0,
    impressions INTEGER DEFAULT 0,
    saves       INTEGER DEFAULT 0,
    posted_at   TIMESTAMPTZ,            -- Instagram's taken_at timestamp
    fetched_at  TIMESTAMPTZ DEFAULT NOW()
);

-- Disable Row Level Security (private automation script — no public access)
ALTER TABLE stats DISABLE ROW LEVEL SECURITY;

-- Table: scheduled_posts
-- User-scheduled posts created from the Dashboard Schedule Post screen.
-- A Python worker can poll pending rows and dispatch GeeLark tasks.
CREATE TABLE IF NOT EXISTS scheduled_posts (
    id           BIGSERIAL PRIMARY KEY,
    platform     TEXT NOT NULL,
    media_type   TEXT NOT NULL DEFAULT 'video',
    resource_url TEXT NOT NULL,
    caption      TEXT,
    device_ids   JSONB NOT NULL,          -- {mobile: profile_id}
    schedule_at  TIMESTAMPTZ NOT NULL,
    status       TEXT DEFAULT 'pending',  -- pending | posted | failed
    error        TEXT,
    created_at   TIMESTAMPTZ DEFAULT NOW()
);

ALTER TABLE scheduled_posts DISABLE ROW LEVEL SECURITY;
