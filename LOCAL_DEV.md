# Running LinkMint locally

LinkMint is a FastAPI + React URL shortener backed by MongoDB, with Redis in
front of it for link caching and anonymous rate limiting. This document covers
getting a development environment running and the handful of things that are
easy to get wrong.

---

## Quick start

```bash
cd linkmint
./run-local.sh
```

That checks prerequisites, starts Mongo and Redis, creates a Python venv,
installs both dependency trees, and runs the backend and frontend together.
The first run takes a few minutes (the frontend install is ~1200 packages);
subsequent runs start in seconds.

When it's up:

| | |
|---|---|
| App | http://localhost:3000 |
| API | http://localhost:8001/api |
| API docs | http://localhost:8001/docs |

`Ctrl-C` stops both processes. The Mongo and Redis containers keep running —
`./run-local.sh stop` shuts them down.

### Other commands

```bash
./run-local.sh setup      # install everything, don't start
./run-local.sh backend    # backend only, on :8001
./run-local.sh frontend   # frontend only, on :3000
./run-local.sh env        # (re)create the two .env files only
./run-local.sh test       # run backend_test.py against localhost
./run-local.sh stop       # stop the dockerised Mongo/Redis
```

If the script isn't executable yet:

```bash
chmod +x run-local.sh
```

---

## Prerequisites

- **Python 3.10+** — `brew install python@3.12`
- **Node 18 or 20** — `brew install node@20`. `react-scripts` 5 is fussy on
  very new Node majors; if the frontend dies with an OpenSSL or webpack error,
  this is the first thing to check.
- **Yarn** — `npm install -g yarn`. `package.json` pins `yarn@1.22.22`; npm
  works as a fallback but resolves the `resolutions` block differently.
- **Docker Desktop** *(easiest)* — supplies Mongo and Redis via
  `docker-compose.local.yml`.
  Without Docker, the script falls back to Homebrew services:
  ```bash
  brew tap mongodb/brew && brew install mongodb-community redis
  brew services start mongodb-community
  brew services start redis
  ```

Redis is genuinely optional — `server.py` catches the connection failure and
falls back to Mongo-only. You lose caching and the rate limiter uses an
in-memory counter instead.

---

## Setup files and configuration

| File | Purpose |
|---|---|
| `run-local.sh` | Bootstrap + launcher; also generates the two `.env` files |
| `docker-compose.local.yml` | Mongo 7 + Redis 7 |
| `backend/requirements.txt` | Runtime dependencies |
| `backend/requirements-dev.txt` | Runtime + test dependencies (what the venv installs) |

`backend/.env` and `frontend/.env` are written by `run-local.sh` on first run
rather than shipped as files — both paths are covered by `.gitignore`, so
nothing machine-specific gets committed. If they already exist they are left
alone; delete one and re-run `./run-local.sh env` to regenerate it.

**`backend/.env`**

| Key | Local value |
|---|---|
| `MONGO_URL` | `mongodb://localhost:27017` |
| `DB_NAME` | `linkmint_local` |
| `REDIS_URL` | `redis://localhost:6379/0` |
| `CORS_ORIGINS` | `http://localhost:3000` |
| `COOKIE_SECURE` / `COOKIE_SAMESITE` | `false` / `lax` |
| `ANON_LIMIT_PER_MIN` / `_PER_HOUR` | `1000` / `10000` |

**`frontend/.env`**: `REACT_APP_BACKEND_URL=http://localhost:8001`, `PORT=3000`,
`BROWSER=none`.

## The cookie flags matter locally

`server.py` sets the session cookie from two environment variables:

```python
COOKIE_SECURE = os.environ.get('COOKIE_SECURE', 'true').strip().lower() not in ('false', '0', 'no')
COOKIE_SAMESITE = os.environ.get('COOKIE_SAMESITE', 'none').strip().lower()
```

The defaults (`Secure` + `SameSite=None`) are what production needs. Browsers
**refuse to store a `Secure` cookie on `http://localhost`**, so with the defaults
in place local sign-in appears to succeed and then every subsequent request comes
back unauthenticated, with nothing in the console to explain it. `backend/.env`
therefore sets `COOKIE_SECURE=false` and `COOKIE_SAMESITE=lax`.

> `localhost:3000` and `localhost:8001` are *cross-origin* (so CORS matters)
> but *same-site* (SameSite ignores port), which is why `lax` is enough.

`backend_test.py` reads `LINKMINT_BASE_URL` so the suite can point at localhost
or any deployment.

## Gotchas worth knowing

**Auth is email/password only.** Register on the `/auth` page; there's no
third-party identity provider to configure.

**CORS must name an explicit origin.** The frontend sends credentials
(`withCredentials: true`), and browsers reject `Access-Control-Allow-Origin: *`
on credentialed requests. `backend/.env` sets
`CORS_ORIGINS=http://localhost:3000` rather than the production default of `*`.
If you change the frontend port, change this too.

**Short links resolve through the frontend.** `shortUrlFor()` builds
`window.location.origin + /<code>`, so a locally created link looks like
`http://localhost:3000/abc123`. React Router's `/:code` route calls
`/api/resolve/:code` and then redirects. The backend also exposes
`/api/r/<code>` if you want to test the redirect without the SPA.

**Anonymous rate limits are relaxed locally.** Production caps anonymous users
at 10 links/minute; `backend/.env` raises that to 1000 so a test run doesn't
trip a 429. Drop `ANON_LIMIT_PER_MIN` back to `10` if you're specifically
testing the limiter.

**The local database starts empty.** No links and no users — register a fresh
account on `/auth`.

---

## Poking at it directly

```bash
# health
curl -s localhost:8001/api/health

# shorten anonymously
curl -s -X POST localhost:8001/api/shorten \
  -H 'Content-Type: application/json' \
  -d '{"url":"https://example.com"}'

# register and keep the session cookie
curl -s -c /tmp/lm.jar -X POST localhost:8001/api/auth/register \
  -H 'Content-Type: application/json' \
  -d '{"email":"me@local.test","password":"secret123","name":"Me"}'

curl -s -b /tmp/lm.jar localhost:8001/api/auth/me

# inspect the data
docker exec -it linkmint-mongo mongosh linkmint_local --eval 'db.links.find().limit(5)'
```

## Resetting

```bash
./run-local.sh stop
docker compose -f docker-compose.local.yml down -v   # wipe the database
rm -rf backend/.venv frontend/node_modules           # wipe dependencies
```
