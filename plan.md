# plan.md — LinkMint (URL Shortener)

## 1) Objectives
- **Status: Delivered (MVP complete).** Ship and maintain a working full-stack URL shortener: **FastAPI + React (shadcn/ui) + MongoDB + Redis**.
- Ensure core flow reliability: **shorten → resolve/redirect → click count → list/manage links**.
- Use Redis to accelerate resolve operations via caching, with **graceful MongoDB fallback** when Redis is unavailable.
- Provide a polished, responsive UI aligned to `design_guidelines.md`, with consistent **`data-testid`** attributes for automation.

---

## 2) Implementation Steps

### Phase 1 — Core Flow POC (isolation)
**Goal:** Prove the failure-prone core (code generation + Mongo persistence + Redis cache + click increments + expiry checks) works before building UI.

**Status: COMPLETED** (validated via integrated implementation + E2E tests)

Delivered outcomes:
- URL normalization (auto `https://` prefix when scheme missing).
- Short code generation (random base62-like) + optional custom alias.
- Alias validation:
  - Invalid alias → 422
  - Duplicate alias → 409
  - Reserved alias words (e.g., `api`) → 409
- Expiration handling:
  - Future expiry accepted
  - Past expiry rejected (422)
  - Expired link resolve returns 410
- Click counting: resolves increment clicks (Mongo `$inc`).
- Redis cache strategy:
  - `link:{code}` cached payload (url, expires_at)
  - TTL = 3600 seconds
  - Safe fallback to MongoDB if Redis down.

---

### Phase 2 — V1 App Development (backend + frontend)
**Goal:** Build the complete MVP around the proven core.

**Status: COMPLETED** (backend + frontend built and verified)

Backend (FastAPI) — delivered endpoints:
- `POST /api/shorten`
  - URL normalization
  - optional `custom_alias`
  - optional `expires_at` validation (must be in the future)
- `GET /api/links` (newest-first list)
- `DELETE /api/links/{code}`
- `GET /api/stats` (total_links, total_clicks, active_links)
- `GET /api/resolve/{code}` (returns destination; increments clicks)
- `GET /api/r/{code}` (HTTP 302 redirect)
- `GET /api/health` (mongo/redis status)

Persistence & indexes:
- MongoDB collection: `links`
- Unique index on `code`; created_at index.
- Stored fields: `id (uuid)`, `code`, `url`, `clicks`, `created_at (ISO)`, `expires_at (ISO|null)`

Redis behavior:
- Cache key: `link:{code}`
- TTL: 3600s
- If Redis unavailable, backend continues via MongoDB-only mode.

Operational note:
- Redis was installed via apt and is running on port 6379.
- Redis may not survive pod restarts; to restart manually: `redis-server --daemonize yes`.

Frontend (React + shadcn/ui) — delivered UI:
- Home page (`/`):
  - Topbar with brand and Redis status pill:
    - Shows `Redis cache: ok` or `Cache offline — Mongo fallback`
  - Hero mesh section and shorten form:
    - Long URL input
    - Optional alias input
    - Optional expiry date picker (Popover + Calendar)
  - Result card:
    - Animated appearance
    - Copy short link + open-in-new-tab
    - Sonner toasts
  - Stats cards:
    - Total links, total clicks, active links
  - Recent links:
    - Desktop: table
    - Mobile: card list fallback
    - Row actions: copy + delete (AlertDialog confirmation)
- Redirect page (`/:code`):
  - Loading state while resolving
  - Redirect via `window.location.replace`
  - Error state for 404/410 with back-home CTA

Design implementation:
- Tokens updated per `design_guidelines.md` (teal primary `186 72% 26%`, sand background, etc.).
- Fonts: Space Grotesk (headings), Inter (body), Azeret Mono (codes/URLs).
- `data-testid` attributes applied throughout interactive and key informational elements.

End-of-phase verification:
- E2E testing executed via `testing_agent_v3` with **100% pass rate**.

---

### Phase 3 — Hardening + UX polish
**Goal:** Make v1 resilient and pleasant; address testing feedback.

**Status: COMPLETED** (no bugs found in the first comprehensive test iteration)

Delivered hardening/polish:
- Robust validation and clear error messaging (frontend toasts + backend HTTP codes).
- Expiry status shown in links list (active vs expired).
- Loading skeletons for links table and clear empty states.
- Redis health surfaced to user in UI; backend continues to function without Redis.
- Regression-ready test artifact retained: `/app/backend_test.py`.

---

## 3) Next Actions
**Current status: MVP done.** Next actions are optional enhancements and operationalization.

1. **Stability / Ops**
   - (Optional) Add a lightweight startup script to ensure Redis is launched automatically (if allowed by the environment).
   - (Optional) Add stronger Redis error logging and cache invalidation on delete (already implemented) + future update hooks.

2. **Product enhancements (optional)**
   - Add per-link analytics view (click trend over time) using Recharts.
   - Add pagination/search for links.
   - Add QR code generation for short links.
   - Add rate limiting / abuse protection.
   - Add authentication (“My links” per user) if required.

3. **Regression workflow**
   - Re-run `testing_agent_v3` after any backend/frontend changes.
   - Keep `/app/backend_test.py` as a repeatable smoke/regression suite.

---

## 4) Success Criteria
**Met (MVP complete):**
- End-to-end flow works: shorten → resolve/redirect → click increments → list → delete.
- Custom alias + expiry behave correctly (conflicts rejected; expired links don’t resolve).
- Redis status visible; **Mongo fallback works** when Redis is unavailable.
- UI matches design guidelines, is responsive, and includes required `data-testid` attributes.
- E2E tests pass with no critical bugs (`/app/test_reports/iteration_1.json`: backend 17/17, frontend 100%).
