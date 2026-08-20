# plan.md — LinkMint (URL Shortener)

## 1) Objectives
- **Status: Phases 1–4 Delivered (Production-ready MVP + Accounts/Search/QR).** Maintain and extend the working full-stack URL shortener: **FastAPI + React (shadcn/ui) + MongoDB + Redis**.
- Preserve core flow reliability: **shorten → resolve/redirect → click count → list/manage links**.
- Use Redis to accelerate resolve operations via caching, with **graceful MongoDB fallback** when Redis is unavailable.
- Provide **User Accounts** with **both** authentication methods:
  - **Email + password** (bcrypt)
  - **Google sign-in via Emergent Auth** (backend session exchange)
- Keep **anonymous shortening allowed**; authentication unlocks **“My Links”** (owner-scoped management).
- Provide **QR codes** (simple black-and-white PNG) per short link with download.
- Provide **Link Search + Pagination** so large link lists remain usable.
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
- Click counting: resolves increment clicks (Mongo `$inc`).
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
- If a user first signs in via Google, they can later create a password using the same email (password gets added to existing user).

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

## 3) Next Actions
**Current status: All planned phases complete.** Next actions are optional enhancements.

1) **Analytics (Optional)**
- Add click trend charts (Recharts) and per-link analytics page.

2) **Link Management (Optional)**
- Edit link settings (expiry, destination) and regenerate codes.

3) **Operational Hardening (Optional)**
- Add Redis auto-start strategy (if permitted) or health-based auto-disable messaging.
- Add rate limiting/abuse protection.

4) **Testing/Regression (Ongoing)**
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
