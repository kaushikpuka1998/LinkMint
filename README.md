<div align="center">

# LinkMint

**A self-hosted URL shortener with QR codes, click analytics, tags and CSV export.**

FastAPI · React · MongoDB · Redis

</div>

---

Shorten a URL anonymously in one click, or sign in to keep a private, searchable
library of links with per-link click charts, custom aliases, expiry dates and
tag-based filtering.

<img width="1286" height="1084" alt="Screenshot 2026-08-20 at 9 01 46 PM" src="https://github.com/user-attachments/assets/9e2b6b1b-fc55-4dfb-b2ed-5562145981a6" />
<img width="1232" height="1099" alt="Screenshot 2026-08-20 at 9 01 25 PM" src="https://github.com/user-attachments/assets/701f348c-c727-4dd9-a9db-2a9947a6a26d" />

<p align="center">
  <img width="600" height="700" alt="Screenshot 2026-08-20 at 9 01 58 PM" src="https://github.com/user-attachments/assets/c2d0d2a5-ab43-4b35-9a01-984b69d8dd5f" />
  <img width="600" height="700" alt="Screenshot 2026-08-20 at 9 01 39 PM" src="https://github.com/user-attachments/assets/8b1083cb-1a99-4adb-9299-58de1c52d696" />
  <img width="600" height="700" alt="Screenshot 2026-08-20 at 9 01 28 PM" src="https://github.com/user-attachments/assets/a2391f41-4813-4cb2-98be-0ee226ec3f06" />
</p>




## Features

**Shortening**
- Random base62 codes or custom aliases (validated, with reserved words blocked)
- Optional expiry dates — expired links return `410 Gone`
- Bulk mode: paste up to 50 URLs and get them all back at once (signed-in)
- URLs are normalised, so `example.com/path` works as well as the full form

**Links you own**
- Email + password accounts with bcrypt hashing and 7-day sessions
- Anonymous shortening stays available; signing in scopes the list to you
- Edit a link's destination or expiry without changing its short code
- Owner-checked deletes — a non-owner gets `403`
- Debounced search across codes and URLs, with pagination

**Insight**
- Click counts per link, recorded on every redirect
- Daily click buckets rendered as a 30-day area chart
- Up to 5 tags per link, with filter chips and a tag index
- CSV export that respects the current search and tag filter

**Other**
- Black-and-white QR code per link, downloadable as PNG
- Dark mode following system preference, with a manual toggle
- Redis-backed link cache and per-IP rate limiting for anonymous visitors,
  both degrading gracefully to Mongo-only / in-memory when Redis is down

## Stack

| Layer | Choice |
|---|---|
| API | FastAPI on uvicorn, async throughout |
| Database | MongoDB via motor |
| Cache / rate limiting | Redis (optional — the app runs without it) |
| Frontend | React 19, CRA + craco, React Router 7 |
| UI | Tailwind CSS + shadcn/ui (Radix primitives), Recharts, sonner |
| Auth | bcrypt + HttpOnly session cookies |

## Getting started

```bash
git clone <your-repo-url> linkmint
cd linkmint
./run-local.sh
```

That checks prerequisites, starts MongoDB and Redis, creates a Python virtualenv,
installs both dependency trees and runs the API on `:8001` and the frontend on
`:3000`. First run takes a few minutes; after that it starts in seconds.

You'll need Python 3.10+, Node 18 or 20, Yarn, and either Docker (for the bundled
`docker-compose.local.yml`) or Homebrew-installed MongoDB and Redis.

```bash
./run-local.sh setup      # install everything, don't start
./run-local.sh backend    # API only
./run-local.sh frontend   # frontend only
./run-local.sh env        # (re)create the .env files
./run-local.sh test       # run the API test suite against localhost
./run-local.sh stop       # stop the dockerised Mongo/Redis
```

See [LOCAL_DEV.md](LOCAL_DEV.md) for configuration details and troubleshooting.

## Configuration

`backend/.env`:

| Variable | Default | Purpose |
|---|---|---|
| `MONGO_URL` | — | **Required.** MongoDB connection string |
| `DB_NAME` | — | **Required.** Database name |
| `REDIS_URL` | `redis://localhost:6379/0` | Optional; app falls back to Mongo-only |
| `CORS_ORIGINS` | `*` | Comma-separated. Must be explicit in production — the frontend sends credentials |
| `COOKIE_SECURE` | `true` | Set `false` for plain-HTTP local dev |
| `COOKIE_SAMESITE` | `none` | Use `lax` when frontend and API share a site |
| `ANON_LIMIT_PER_MIN` | `10` | Anonymous link creations per IP per minute |
| `ANON_LIMIT_PER_HOUR` | `100` | Anonymous link creations per IP per hour |

`frontend/.env`:

| Variable | Purpose |
|---|---|
| `REACT_APP_BACKEND_URL` | API origin, e.g. `http://localhost:8001` (no trailing `/api`) |

## API

All routes are under `/api`. Authentication is an HttpOnly `session_token`
cookie, or `Authorization: Bearer <token>` for non-browser clients.

| Method | Path | Notes |
|---|---|---|
| `GET` | `/health` | Liveness + datastore status |
| `POST` | `/shorten` | `{url, custom_alias?, expires_at?, tags?}` — rate limited when anonymous |
| `POST` | `/shorten/bulk` | `{urls: []}`, up to 50 — signed-in only |
| `GET` | `/links` | Owner-scoped, paginated; `?q=&tag=&page=&limit=` |
| `PATCH` | `/links/{code}` | `{url?, expires_at?, clear_expiry?, tags?}` — owner only |
| `DELETE` | `/links/{code}` | Owner only |
| `GET` | `/links/{code}/analytics` | Daily click buckets; `?days=30` |
| `GET` | `/links/export.csv` | CSV of the current scope; `?q=&tag=` |
| `GET` | `/tags` | Distinct tags for the current scope |
| `GET` | `/stats` | Totals, scoped to the signed-in user |
| `GET` | `/qr/{code}` | PNG QR code |
| `GET` | `/resolve/{code}` | Destination lookup used by the SPA redirect route |
| `GET` | `/r/{code}` | Server-side 302 redirect |
| `POST` | `/auth/register` | `{name, email, password}` |
| `POST` | `/auth/login` | `{email, password}` |
| `GET` | `/auth/me` | Current user |
| `POST` | `/auth/logout` | Clears the session |

Interactive docs are at `http://localhost:8001/docs` when the API is running.

## How redirects work

The frontend owns the short-link namespace. `https://yourdomain/abc123` hits
React Router's `/:code` route, which calls `GET /api/resolve/abc123` and then
navigates to the destination — so the click is recorded and expiry is enforced
before the browser leaves. `GET /api/r/abc123` issues a plain 302 server-side
if you'd rather not involve the SPA.

Codes are checked against a reserved list (`api`, `auth`, `admin`, `qr`, `r`,
`health`, …) so a short code can never shadow a real route.

## Tests

`backend_test.py` exercises the full API surface — shortening, aliases, expiry,
redirects and click counting, ownership rules, rate limiting, bulk mode,
analytics, tags and CSV export.

```bash
./run-local.sh test
# or against any deployment:
LINKMINT_BASE_URL=https://your-host/api python backend_test.py
```

## Deploying

The API is a standard ASGI app (`backend.server:app`) — run it behind uvicorn or
gunicorn with uvicorn workers. The frontend is a static build (`yarn build`).

Two things to get right in production:

1. Serve both over HTTPS and leave `COOKIE_SECURE=true`. If the frontend and API
   are on different sites, keep `COOKIE_SAMESITE=none`; if they share one, `lax`
   is stricter and works fine.
2. Set `CORS_ORIGINS` to your actual frontend origin. The wildcard default will
   be rejected by browsers on credentialed requests.

## License

No license has been chosen yet — add one before accepting outside contributions.
# LinkMint
