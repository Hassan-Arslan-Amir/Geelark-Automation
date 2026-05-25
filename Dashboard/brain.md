# Dashboard — Brain Document

Complete reference for structure, data flow, and component responsibilities.
Intended for AI agents and new developers working in this folder.

---

## What Is This?

A **read-only analytics dashboard** built with React 18 + TypeScript + Vite + Tailwind CSS.
It pulls live data from a **Supabase** PostgreSQL database and visualises Instagram post
statistics across all cloud phone devices managed by the GeeLark automation pipeline.

There is **no backend server** for this project. The dashboard talks directly to Supabase
from the browser using the public anon key.

---

## Tech Stack

| Layer           | Library / Tool        | Version    |
| --------------- | --------------------- | ---------- |
| UI framework    | React                 | ^18.3.1    |
| Language        | TypeScript            | (via Vite) |
| Build tool      | Vite                  | ^5         |
| Styling         | Tailwind CSS          | ^3.4.1     |
| Icons           | lucide-react          | ^0.344.0   |
| Database client | @supabase/supabase-js | ^2.57.4    |

---

## Folder Structure

```
Dashboard/
├── brain.md                  ← this file
├── .env                      ← REQUIRED — Supabase credentials (never commit)
├── .gitignore
├── index.html                ← Vite entry point; loads Inter + JetBrains Mono fonts
├── package.json
├── vite.config.ts
├── tailwind.config.js        ← Custom design tokens (brand/surface colour scales)
├── postcss.config.js
├── tsconfig.json / tsconfig.app.json / tsconfig.node.json
└── src/
    ├── main.tsx              ← ReactDOM.createRoot entry
    ├── App.tsx               ← Root component — routing, state orchestration
    ├── types.ts              ← All shared TypeScript interfaces
    ├── index.css             ← Tailwind base directives + global resets
    ├── vite-env.d.ts         ← import.meta.env type declarations
    ├── data.json             ← Legacy static data file (no longer used; kept for reference)
    ├── lib/
    │   └── supabase.ts       ← Supabase client singleton
    ├── hooks/
    │   └── useSupabaseData.ts ← Data-fetching hook (devices + stats → Account[])
    └── components/
        ├── Sidebar.tsx       ← Left navigation panel (desktop fixed, mobile slide-over)
        ├── SearchBar.tsx     ← Category dropdown + text input (shared)
        ├── DevicesScreen.tsx ← Grid of device cards with aggregate stats
        └── PostsScreen.tsx   ← Grid of post cards with individual stats
```

---

## Environment Setup

Create `Dashboard/.env` before running the dev server:

```
VITE_SUPABASE_URL=https://your-project-id.supabase.co
VITE_SUPABASE_ANON_KEY=your-anon-public-key
```

**Where to find these values:** Supabase Dashboard → Settings → API.
Use the **anon / public** key — never the service role key.

> All Vite env vars must be prefixed with `VITE_`. Variables without that prefix are
> invisible to browser code at build time.

If `.env` is missing or the vars are empty, the app renders a clear error screen
(instead of a blank page) explaining exactly what to add.

---

## Running the Project

```bash
cd Dashboard
npm install      # first time only
npm run dev      # start dev server on http://localhost:5173
npm run build    # production build → dist/
npm run preview  # serve the production build locally
npm run typecheck  # TypeScript type check without building
```

---

## Data Flow — End to End

```
Supabase DB
  ├─ devices table  (id, mobile, profile_id, username, views, likes, comments)
  └─ stats table    (device_id, permalink, media_type, views, likes, comments,
                     reshares, reach, impressions, saves, posted_at, fetched_at)
          │
          │  fetched on mount via useSupabaseData hook
          ▼
    useSupabaseData.ts
      1. Reads all devices WHERE username IS NOT NULL
      2. Reads all stats rows
      3. Groups stats by device_id
      4. Assembles Account[] — each Account contains its posts[]
      5. Computes aggregate totals (views, likes, comments)
      6. Returns { data: AnalyticsData, loading, error }
          │
          ▼
    App.tsx  (receives data, loading, error)
      ├─ loading=true  → full-screen spinner
      ├─ error/no data → full-screen error message with instructions
      └─ data ready    → renders Sidebar + active screen
          │
          ├─ DevicesScreen  → receives accounts[], shows one card per device
          └─ PostsScreen    → flattens all posts into one list, filters by search
```

---

## TypeScript Types (`src/types.ts`)

```
AnalyticsData
  fetched_at:    string (ISO)
  total_devices: number
  aggregate:     { total_views, total_likes, total_comments }
  accounts:      Account[]

Account
  profile_id:  string   — GeeLark cloud phone profile ID
  mobile:      string   — phone number label (e.g. "+1234567890")
  username:    string   — Instagram handle (without @)
  posts:       Post[]

Post
  permalink:  string    — full Instagram post URL
  stats:      Stats

Stats
  views, likes, comments, reshares: number
  reach, impressions, saves:        number
  media_type:  number   — 1 = image, 2 = video/reel
  timestamp:   number   — Unix seconds (converted from DB TIMESTAMPTZ in hook)
```

### Key conversion note

The `stats` table stores `posted_at` as a PostgreSQL `TIMESTAMPTZ` (ISO 8601 string).
The hook converts it to a **Unix timestamp in seconds** (`Math.floor(new Date(...).getTime() / 1000)`)
so `PostsScreen` can pass it directly to `new Date(timestamp * 1000)` for display.

---

## File-by-File Reference

### `src/lib/supabase.ts`

Single-responsibility: create and export the Supabase client.

```typescript
export const supabase = url && key ? createClient(url, key) : null;
```

- Exports `null` instead of calling `createClient(undefined, undefined)` when env vars
  are missing — prevents an import-time crash that would cause a blank screen.
- Every consumer must check `if (!supabase)` before calling any DB method.

---

### `src/hooks/useSupabaseData.ts`

The only place in the codebase that talks to Supabase.

**Responsibilities:**

1. Guard against `supabase === null` and surface a human-readable error.
2. Parallel-query `devices` and `stats` tables.
3. Group stats rows by `device_id` using a `Record<number, StatRow[]>` map.
4. Build the `Account[]` structure expected by all screen components.
5. Compute `AnalyticsData` aggregate totals.
6. Return `{ data, loading, error }`.

**Error handling:**
Supabase PostgREST errors are plain objects (not `instanceof Error`).
The `extractMessage()` helper reads `.message` from any object, falls back to
`err.message` for real `Error` instances, then falls back to a generic string.

**Adding a new DB column:**

1. Add the column to the `.select()` call for the relevant table.
2. Add it to the mapping inside the `.map()` call.
3. Add the property to the corresponding type in `types.ts`.

---

### `src/App.tsx`

State lives here. App has two screens (`'devices' | 'posts'`) and one piece of
cross-screen state: `selectedDevice`.

**Navigation logic:**

- Clicking a device card in `DevicesScreen` calls `handleDeviceClick(account)`.
  This sets `selectedDevice`, pre-fills the Posts search bar with that account's
  `username`, and switches to the Posts screen.
- Navigating back to Devices via the sidebar clears `selectedDevice` and resets
  the Posts search bar.

**Search state is per-screen.** Devices and Posts each have their own independent
`searchCategory` + `searchQuery` state pair so they don't interfere.

---

### `src/components/Sidebar.tsx`

Fixed 272 px left panel on desktop (`lg:translate-x-0`).
On mobile it becomes a slide-over drawer toggled by a hamburger button in a fixed
top header bar (`lg:hidden`). A semi-transparent overlay closes it on backdrop click.

Nav items: **Devices** (Smartphone icon) and **Posts** (BarChart3 icon).
Active item gets `bg-brand-600` highlight.

---

### `src/components/SearchBar.tsx`

Reusable. Accepts `category` (`'username' | 'profile_id' | 'mobile'`) and `query`
string as controlled props. Renders a `<select>` dropdown joined to a text `<input>`.
Shows a clear (×) button when `query` is non-empty.

Filtering itself is **not** done inside this component — each screen component
filters its own data array using the values passed down from `App.tsx`.

---

### `src/components/DevicesScreen.tsx`

Receives `accounts: Account[]` pre-filtered by the parent? No — it **filters itself**
using `searchCategory` and `searchQuery` props passed from `App.tsx`.

**Per-card aggregates** are computed inline:

- `totalViews(account)` = sum of `post.stats.views` across all posts
- `totalLikes(account)` = sum of `post.stats.likes`
- `totalComments(account)` = sum of `post.stats.comments`

Clicking a card calls `onDeviceClick(account)` which triggers cross-screen navigation
in `App.tsx` (see above).

Cards animate in with `animate-slide-up` + staggered `animationDelay` (60 ms per card).

---

### `src/components/PostsScreen.tsx`

Flattens `accounts[]` into a single `FlatPost[]` array (each post carries a copy of its
account's `username`, `profile_id`, and `mobile` for display + filtering).

**Aggregate bar** at the top recalculates totals from `filteredPosts` so it always
reflects the current search filter.

**Media type icon:** `media_type === 2` → Film icon (orange) = video/reel;
otherwise → Image icon (green) = photo.

Clicking a post card opens `post.permalink` in a new tab.

`formatDate(timestamp)` converts Unix seconds → `"May 25, 2026"` style string using
`Intl.DateTimeFormat`.

---

## Design System (Tailwind)

All custom tokens are defined in `tailwind.config.js`:

### Colour Scales

| Token              | Usage                                                     |
| ------------------ | --------------------------------------------------------- |
| `brand-*`          | Blue (500 = #3b82f6) — primary actions, active nav, icons |
| `surface-0`        | Pure white — card backgrounds                             |
| `surface-50`       | Off-white — page background                               |
| `surface-100..300` | Light greys — borders, dividers, disabled                 |
| `surface-400..600` | Mid greys — secondary text, icons                         |
| `surface-700..950` | Dark — primary text, sidebar background                   |

### Shadows

- `shadow-card` — subtle resting card shadow
- `shadow-card-hover` — elevated shadow on hover
- `shadow-sidebar` — right-side shadow on the sidebar panel

### Animations

- `animate-fade-in` — opacity 0→1 over 0.4 s
- `animate-slide-up` — translateY(8px)→0 + fade over 0.4 s (used for card grids)
- `animate-scale-in` — scale(0.95)→1 over 0.2 s

### Fonts

- `font-sans` → Inter (loaded via Google Fonts in `index.html`)
- `font-mono` → JetBrains Mono (used for profile IDs, permalinks)

---

## Supabase Tables Reference

### `devices`

| Column     | Type         | Notes                                     |
| ---------- | ------------ | ----------------------------------------- |
| id         | integer (PK) | Referenced by stats.device_id             |
| mobile     | text         | Phone number label                        |
| profile_id | text         | GeeLark cloud phone ID                    |
| username   | text         | Instagram handle; NULL = not yet assigned |
| views      | integer      | Aggregate — updated by getStats.py        |
| likes      | integer      | Aggregate — updated by getStats.py        |
| comments   | integer      | Aggregate — updated by getStats.py        |

### `stats`

| Column                                                      | Type                      | Notes                                  |
| ----------------------------------------------------------- | ------------------------- | -------------------------------------- |
| id                                                          | integer (PK)              |                                        |
| device_id                                                   | integer (FK → devices.id) |                                        |
| username                                                    | text                      | Denormalised for quick lookup          |
| permalink                                                   | text (UNIQUE)             | Used as upsert conflict key            |
| media_type                                                  | integer                   | 1=image, 2=video                       |
| views, likes, comments, reshares, reach, impressions, saves | integer                   |                                        |
| posted_at                                                   | timestamptz               | Original post time (from Instagram)    |
| fetched_at                                                  | timestamptz               | When getStats.py last updated this row |

> Stats are written by the Python `getStats.py` script, never by this dashboard.
> The dashboard is strictly read-only.

---

## Common Tasks

### Add a new stat column to the UI

1. Add the column to the `stats` SELECT in `useSupabaseData.ts`.
2. Add it to the `Stats` interface in `types.ts`.
3. Map it in the hook's `.map((stat) => ({ stats: { ... newField: stat.newField ?? 0 } }))`.
4. Display it in `PostsScreen.tsx` or `DevicesScreen.tsx`.

### Add a new screen

1. Add a new `id` to the `items` array in `Sidebar.tsx`.
2. Extend the `currentScreen` union type in `App.tsx`.
3. Create a new component in `src/components/`.
4. Add a conditional render block in `App.tsx` alongside the existing `DevicesScreen`/`PostsScreen` blocks.

### Change which devices appear

Edit the Supabase query in `useSupabaseData.ts`:

```typescript
.from('devices')
.select('id, mobile, profile_id, username')
.not('username', 'is', null)   // ← adjust or remove this filter
```

---

## Known Quirks

- `src/data.json` — legacy static data file left from before the Supabase integration.
  It is **not imported anywhere** in the current codebase. Safe to delete if desired.
- The `AnalyticsData.aggregate` totals computed in the hook are across all devices/posts.
  The per-screen aggregate bars in `PostsScreen` recompute from the filtered list, so
  they will differ when a search is active — this is intentional behaviour.
- `media_type` uses Instagram's numeric enum (1 = photo, 2 = video). Any value other
  than 2 is treated as a photo in the PostsScreen icon logic.
