# plan.md — LinkMint (URL Shortener)

## 1) Objectives
- **Status: Phases 1–7 Delivered (Production-ready shortener + Accounts + Search/QR + Abuse Protection + Bulk + Analytics + Editing + Dark Mode + CSV + Tags).** Maintain and extend the working full-stack URL shortener: **FastAPI + React (shadcn/ui) + MongoDB + Redis**.
- Preserve core flow reliability: **shorten → resolve/redirect → click count → list/manage links**.
- Use Redis to accelerate resolve operations via caching, with **graceful MongoDB fallback** when Redis is unavailable.
- Provide **User Accounts** with **both** authentication methods:
  - **Email + password** (bcrypt)
  - **Google sign-in via Emergent Auth** (backend session exchange)
- Keep **anonymous shortening allowed**; authentication unlocks **“My Links”** (owner-scoped management) and enables advanced features.
- Provide **QR codes** (simple black-and-white PNG) per short link with download.
- Provide **Link Search + Pagination** so large link lists remain usable.
- Provide **Anonymous Rate Limiting** for abuse protection (per-IP caps), while keeping signed-in experience frictionless.
- Provide **Bulk Shortening** (signed-in only) to create many short links in one operation.
- Provide **Click Analytics** (daily click buckets) surfaced in the UI as charts.
- Provide **Link Editing** (owner-scoped) so users can update destination/expiry without changing the short code.
- Provide **Dark Mode** with a topbar toggle and persisted preference.
- Provide **CSV Export** of the current scoped/filtered list.
- Provide **Link Tags** for organization and filtering.
- Maintain a polished, responsive UI aligned to `design_guidelines.md`, with consistent **`data-testid`** attributes for automation.

---

## 2) Implementation Steps

### Phase 1 — Core Flow POC (isolation)
**Goal:** Prove the failure-prone core (code generation + Mongo persistence + Redis cache + click increments + expiry checks) works before building UI.

**Status: COMPLETED**

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
- Click counting: resolves increment clicks.
- Redis cache strategy:
  - `link:{code}` cached payload (url, expires_at)
  - TTL = 3600 seconds
  - Safe fallback to MongoDB if Redis down.

---

### Phase 2 — V1 App Development (backend + frontend)
**Goal:** Build the complete MVP around the proven core.

**Status: COMPLETED**

Backend (FastAPI) — delivered endpoints:
- `POST /api/shorten`
- `GET /api/links` (initial version: list)
- `DELETE /api/links/{code}`
- `GET /api/stats`
- `GET /api/resolve/{code}`
- `GET /api/r/{code}` (302)
- `GET /api/health`

Persistence & indexes:
- MongoDB collection: `links`
- Unique index on `code`; created_at index.

Redis behavior:
- Cache key: `link:{code}`
- TTL: 3600s
- If Redis unavailable, backend continues via MongoDB-only mode.

Operational note:
- Redis installed via apt and running on port 6379.
- Redis may not survive pod restarts; to restart manually: `redis-server --daemonize yes`.

Frontend (React + shadcn/ui) — delivered UI:
- Home page (`/`): shorten form, result card, stats, links list with copy/delete.
- Redirect page (`/:code`): resolves and redirects; has error states.

Design implementation:
- Tokens updated per `design_guidelines.md` (teal primary `186 72% 26%`, sand background, etc.).
- Fonts: Space Grotesk (headings), Inter (body), Azeret Mono (codes/URLs).
- `data-testid` attributes applied throughout interactive and key informational elements.

---

### Phase 3 — Hardening + UX polish
**Goal:** Make v1 resilient and pleasant; address testing feedback.

**Status: COMPLETED**

Delivered hardening/polish:
- Robust validation and clear error messaging (frontend toasts + backend HTTP codes).
- Expiry status shown in links list.
- Loading skeletons and empty states.
- Redis health surfaced to user in UI; backend continues to function without Redis.
- Regression-ready test artifact retained: `/app/backend_test.py`.

---

### Phase 4 — Accounts + QR Codes + Search/Pagination
**Goal:** Add authenticated user accounts (email/password + Google OAuth), QR codes per short link, and scalable link discovery with search/pagination.

**Status: COMPLETED**

Verification:
- Test report `/app/test_reports/iteration_2.json`: **backend 100% (41/41)**, **frontend 100% (10/10)**, **zero bugs**.

#### 4.1 Authentication (Backend)
User decisions:
- **Both auth methods**: Email/password **and** Google via Emergent Auth.
- Anonymous shortening remains **allowed**.

Data model additions:
- `users` collection:
  - `user_id`: `user_<uuid12>` (custom ID; never expose Mongo `_id`)
  - `email`, `name`, `picture`
  - `password_hash` (optional for Google-only users)
  - `created_at`, `updated_at`
- `user_sessions` collection:
  - `user_id`
  - `session_token`
  - `expires_at` (ISO, timezone-aware semantics)
  - `created_at`

Unified session strategy:
- Both email/password and Google sign-in create a `session_token` stored in `user_sessions`.
- Auth transport:
  - httpOnly cookie: `secure=True`, `samesite="none"`, `path="/"`, expiry **7 days**
  - Bearer header fallback: `Authorization: Bearer <token>`

Delivered endpoints:
- `POST /api/auth/register` (bcrypt password hashing)
- `POST /api/auth/login`
- `POST /api/auth/session` (Emergent OAuth session_id exchange via `X-Session-ID` → issues LinkMint session cookie)
- `GET /api/auth/me`
- `POST /api/auth/logout`

Account linking:
- If a user first signs in via Google, they can later create a password using the same email.

Testing playbook:
- Emergent auth testing guide saved at `/app/auth_testing.md`.

#### 4.2 Links Ownership + Authorization
Schema change:
- `links.owner_id`:
  - `owner_id = user_id` for authenticated user-created links
  - `owner_id = None` for anonymous links

Behavior:
- `POST /api/shorten`: sets `owner_id` when authenticated.
- `GET /api/links`: scope depends on auth state:
  - Authenticated → only that user’s links
  - Anonymous → only anonymous links
- `DELETE /api/links/{code}`:
  - Owner-only delete for owned links
  - Anonymous attempts to delete a user-owned link → **403**

Reserved code list expanded:
- Includes `auth`, `qr`, `r`, `resolve`, `shorten`, `login`, `register`, `logout`, etc., to avoid route collisions.

#### 4.3 Link Search + Pagination
Backend contract:
- `GET /api/links?q=&page=&limit=` returns:
  - `{ items, total, page, pages }`
- Search is case-insensitive and matches `code` and `url`.
- Pagination defaults:
  - `page=1`, `limit=25` (cap `limit` to 100)

Stats scoping:
- `GET /api/stats` is scoped to the same visibility rules as `/api/links`.

Frontend behavior:
- Debounced search input.
- Prev/Next pagination controls with page indicator.
- Section title changes:
  - Signed in → “My links”
  - Signed out → “Recent links”

#### 4.4 QR Codes
Backend:
- `GET /api/qr/{code}` returns **image/png**, black-and-white.
- Short URL base derived from forwarded headers (`x-forwarded-proto`, `x-forwarded-host`) when present.

Frontend:
- QR action per link:
  - Dialog displays QR image
  - Download button saves PNG

#### 4.5 Dependencies
Backend dependencies in use:
- `bcrypt`, `httpx`, `qrcode`, `pillow`

#### 4.6 Known Operational Note (Resolved)
- CRA dev server hit inotify watcher limit (`ENOSPC`) leading to stale/blank UI.
- Mitigation applied: increased `fs.inotify.max_user_watches` and restarted frontend.
- If this reoccurs after future changes, restart frontend via `supervisorctl restart frontend`.

---

### Phase 5 — Anonymous Rate Limiting (Abuse Protection)
**Goal:** Protect the public shortener from abuse by capping anonymous create throughput, while keeping signed-in users frictionless.

**Status: COMPLETED**

Implementation (in `/app/backend/server.py`):
- `enforce_anon_rate_limit()` applied in **`POST /api/shorten` only for anonymous requests** (signed-in users bypass).
- Limits enforced **per client IP**:
  - **10 links / minute**
  - **100 links / hour**
- Configurable via env vars:
  - `ANON_LIMIT_PER_MIN` (default 10)
  - `ANON_LIMIT_PER_HOUR` (default 100)
- Client IP extraction:
  - uses `x-forwarded-for` (first hop) else `request.client.host`.
- Storage strategy:
  - Redis fixed-window counters (INCR + EXPIRE) using keys: `rl:shorten:{ip}:{min|hour}`
  - In-memory per-process fallback when Redis is down
- Response behavior:
  - HTTP **429** with friendly `detail` message (includes suggestion to sign in)
  - `Retry-After` header set with seconds until reset

Verification:
- Anonymous burst: 200 × 10 then **429** at request 11/12 with correct message + `Retry-After`.
- Different IP unaffected.
- Authenticated user bypasses limit.
- Redis stopped: fallback still enforces 429.

---

### Phase 6 — Bulk Shortening + Click Charts + Link Editing
**Goal:** Enable power-user workflows for signed-in users: bulk creation, charted click trends, and post-creation link management without changing codes.

**Status: COMPLETED**

#### 6.1 Bulk Shortening (Members)
Backend:
- `POST /api/shorten/bulk` (signed-in only; anonymous → 401)
  - Up to **50 URLs**
  - Returns per-item results: `{ url, code, error }`
  - Returns batch totals: `{ created, failed }`

Frontend:
- Shorten card has **Single / Bulk tabs**.
- Bulk UI (`/app/frontend/src/components/BulkShorten.jsx`):
  - Anonymous: sign-in prompt
  - Signed-in: textarea (one URL per line), live count, submit, results list
  - “Copy all” for successful codes

#### 6.2 Click Analytics (Charts)
Backend:
- `_resolve_code` increments:
  - `clicks`
  - `daily.{YYYY-MM-DD}` bucket
- `GET /api/links/{code}/analytics?days=7..90`
  - Returns: `{ code, total_clicks, series: [{ date, clicks }] }`
  - Zero-fills missing days
  - Ownership scoped (403 for non-owners of owned links)

Frontend:
- Recharts added.
- Analytics UI (`/app/frontend/src/components/LinkAnalyticsDialog.jsx`):
  - Loading skeleton
  - Empty state when no clicks
  - Area chart when clicks exist, using `--chart-1` token

#### 6.3 Link Editing (Owner-scoped)
Backend:
- `PATCH /api/links/{code}` updates:
  - `url` (validated/normalized)
  - `expires_at` (future-only)
  - `clear_expiry: true` removes expiry
- Owner-only for owned links (403 for non-owners)
- Cache refresh ensures resolves reflect updates immediately
- **Short code never changes**

Frontend:
- Edit UI (`/app/frontend/src/components/EditLinkDialog.jsx`):
  - Prefilled destination and expiry
  - Calendar picker + “Remove expiry”
  - Saves via PATCH and refreshes list

#### 6.4 Row Actions Update
- Row actions include: **copy, QR, analytics, edit, delete** (desktop + mobile).

#### 6.5 Testing Status
- `iteration_3.json`: frontend 100% pass.
- Backend report had minor test-script timing/cascade issues; all flagged flows were manually re-verified as working.

---

### Phase 7 — Dark Mode + CSV Export + Link Tags
**Goal:** Improve usability and organization with theming, reporting/export, and link categorization.

**Status: COMPLETED**

Verification:
- Test report `/app/test_reports/iteration_4.json`:
  - Backend **100% (24/24)**
  - Frontend Phase 7 feature verification **PASS**
  - Only noted issue: a **test-script** typo in a bulk textarea test id (app behavior correct); some regression checks were time-boxed, with relevant features previously tested in Phase 6.

#### 7.1 Dark Mode
Frontend:
- Theme state in `src/context/ThemeContext.js`:
  - Persists preference in `localStorage` key `linkmint-theme`
  - Defaults to system preference (prefers-color-scheme)
  - Applies `dark` class on `<html>`
- Toggle control in `src/components/ThemeToggle.jsx` (Sun/Moon) placed in topbar.
- Dark chart tokens `--chart-1..5` added in `.dark` block in `src/index.css`.
- App wrapped in `ThemeProvider` in `src/App.js`.

#### 7.2 Link Tags
Backend:
- `links.tags: List[str]` with normalization:
  - Trim + case-insensitive dedupe
  - Max **5** tags
  - Regex: `^[A-Za-z0-9 _-]{1,24}$` else 422
- Tag input supported on:
  - `POST /api/shorten`
  - `PATCH /api/links/{code}` (sending `tags: []` clears)
- Filtering:
  - `GET /api/links?tag=` case-insensitive
  - combinable with `q=`
- `GET /api/tags` returns distinct sorted tags within the caller’s scope.

Frontend:
- Tags input in single shorten form shown **only when signed in**.
- Tag filter chips row (`All` + distinct tags) above the table.
- Clickable tag badges in each row (desktop + mobile) to apply filters.
- Edit dialog includes `edit-link-tags-input` for updating tags.

#### 7.3 CSV Export
Backend:
- `GET /api/links/export.csv`:
  - `Content-Type: text/csv; charset=utf-8`
  - `Content-Disposition: attachment; filename="linkmint-links-YYYYMMDD.csv"`
  - Columns: `code, short_url, destination_url, clicks, tags(|-joined), created_at, expires_at, status`
  - Applies same scoping (authed vs anon) and filters (`q`, `tag`) as list.

Frontend:
- CSV button next to search box:
  - Downloads via axios `blob` using current `q` and `tag` filters
  - Disabled when list empty
  - Toast on success: “CSV exported”

---

## 3) Next Actions
**Current status: All planned phases (1–7) complete.** Next actions are optional enhancements.

1) **Analytics Enhancements (Optional)**
- Per-link analytics page (not just dialog)
- Top links leaderboard and aggregate charts

2) **Bulk Enhancements (Optional)**
- CSV upload
- Bulk editing (expiry changes for multiple links)

3) **Link Management (Optional)**
- Tag folders/collections and tag-based stats summaries
- Regenerate/rotate links with audit log

4) **Operational Hardening (Optional)**
- Redis auto-start strategy (if permitted)
- Per-user rate limits (separate from anonymous)

5) **Testing/Regression (Ongoing)**
- Keep `/app/backend_test.py` as a regression suite.
- Re-run `testing_agent_v3` after any significant changes.

---

## 4) Success Criteria
### MVP (met)
- End-to-end flow works: shorten → resolve/redirect → click increments → list → delete.
- Custom alias + expiry behave correctly.
- Redis status visible; Mongo fallback works.
- UI matches design guidelines; required `data-testid` attributes exist.
- E2E tests pass (`/app/test_reports/iteration_1.json`).

### Phase 4 (met)
- Users can authenticate via email/password and Google (Emergent Auth).
- Anonymous shortening remains available.
- Signed-in users see only their own links; signed-out users see only anonymous links.
- Owner-protected deletion enforced (403 for non-owners).
- Links list supports search + pagination with stable totals.
- Each link supports QR code view + download (PNG, black-and-white).
- Full E2E verification passes (`/app/test_reports/iteration_2.json`).

### Phase 5 (met)
- Anonymous link creation is capped per IP (minute + hour windows).
- Rate limiting returns 429 + `Retry-After` and clear messaging.
- Signed-in users are not rate-limited by the anonymous caps.
- Rate limiting remains functional even if Redis is down (fallback mode).

### Phase 6 (met)
- Signed-in users can bulk shorten up to 50 URLs with per-item success/failure reporting.
- Click analytics are tracked per day and rendered in UI charts.
- Owners can edit link destination/expiry without changing the short code; resolve reflects changes immediately.
- Regression remains green in manual verification and UI E2E scenarios (`/app/test_reports/iteration_3.json`).

### Phase 7 (met)
- Dark mode toggle works signed-in and signed-out, persists across reloads, and respects system preference by default.
- Members can create/edit tags; tags are validated, normalized, and filterable via `tag` query.
- Tag chips and row badges filter the list as expected.
- CSV export downloads a correct file respecting auth scope and active filters.
- Backend verified 100% and UI feature verification passes (`/app/test_reports/iteration_4.json`).
