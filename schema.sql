-- ─────────────────────────────────────────
-- Supabase Database Schema
-- Run once in: Supabase Dashboard → SQL Editor → New Query
-- ─────────────────────────────────────────

-- Table: devices
-- Stores all GeeLark cloud phone devices.
-- Pre-populated from deviceIDs.json via seed_devices() in supabase_logger.py
CREATE TABLE IF NOT EXISTS devices (
    id          BIGSERIAL PRIMARY KEY,
    mobile      TEXT NOT NULL UNIQUE,   -- Mobile number (e.g. "102")
    profile_id  TEXT NOT NULL UNIQUE,   -- GeeLark profile ID
    no_of_posts INTEGER DEFAULT 0,      -- Total posts scheduled on this device
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
    created_at   TIMESTAMPTZ DEFAULT NOW()
);

-- Disable Row Level Security (private automation script — no public access)
ALTER TABLE content DISABLE ROW LEVEL SECURITY;
