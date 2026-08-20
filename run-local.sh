#!/usr/bin/env bash
#
# LinkMint — local development launcher.
#
#   ./run-local.sh            bootstrap if needed, then run backend + frontend
#   ./run-local.sh setup      bootstrap only (deps + datastores), don't run
#   ./run-local.sh backend    run only the FastAPI backend on :8001
#   ./run-local.sh frontend   run only the CRA dev server on :3000
#   ./run-local.sh env        (re)create backend/.env and frontend/.env only
#   ./run-local.sh test       run backend_test.py against the local backend
#   ./run-local.sh stop       stop the dockerised Mongo/Redis
#
# Written for macOS's stock bash 3.2 — no associative arrays, no `wait -n`.

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND="$ROOT/backend"
FRONTEND="$ROOT/frontend"
VENV="$BACKEND/.venv"
COMPOSE_FILE="$ROOT/docker-compose.local.yml"

BACKEND_PORT=8001
FRONTEND_PORT=3000

BOLD="$(printf '\033[1m')"; DIM="$(printf '\033[2m')"
GREEN="$(printf '\033[32m')"; YELLOW="$(printf '\033[33m')"
RED="$(printf '\033[31m')"; RESET="$(printf '\033[0m')"

say()  { printf '%s==>%s %s\n' "$BOLD" "$RESET" "$*"; }
ok()   { printf '  %s✓%s %s\n' "$GREEN" "$RESET" "$*"; }
warn() { printf '  %s!%s %s\n' "$YELLOW" "$RESET" "$*"; }
die()  { printf '  %s✗%s %s\n' "$RED" "$RESET" "$*" >&2; exit 1; }

have() { command -v "$1" >/dev/null 2>&1; }

port_open() {
  # macOS ships nc; fall back to bash's /dev/tcp.
  if have nc; then
    nc -z 127.0.0.1 "$1" >/dev/null 2>&1
  else
    (exec 3<>"/dev/tcp/127.0.0.1/$1") >/dev/null 2>&1
  fi
}

wait_for_port() {
  local port="$1" label="$2" tries="${3:-40}" i=0
  while [ "$i" -lt "$tries" ]; do
    if port_open "$port"; then return 0; fi
    i=$((i + 1)); sleep 1
  done
  return 1
}

# ---------------------------------------------------------------------------
# Prerequisites
# ---------------------------------------------------------------------------
check_prereqs() {
  say "Checking prerequisites"

  if have python3; then
    ok "python3 $(python3 -V 2>&1 | awk '{print $2}')"
  else
    die "python3 not found. Install it with: brew install python@3.12"
  fi

  if have node; then
    local major
    major="$(node -v | sed 's/^v\([0-9]*\).*/\1/')"
    ok "node $(node -v)"
    if [ "$major" -lt 18 ]; then
      warn "node $major is older than react-scripts 5 expects — 18 or 20 is safest."
    fi
  else
    die "node not found. Install it with: brew install node@20"
  fi

  if have yarn; then
    PKG=yarn
    ok "yarn $(yarn -v)  ${DIM}(package.json pins yarn)${RESET}"
  elif have npm; then
    PKG=npm
    warn "yarn not found, falling back to npm (package.json pins yarn@1.22.22)"
  else
    die "neither yarn nor npm found."
  fi
}

# ---------------------------------------------------------------------------
# Mongo + Redis
# ---------------------------------------------------------------------------
compose_cmd() {
  if docker compose version >/dev/null 2>&1; then
    echo "docker compose"
  elif have docker-compose; then
    echo "docker-compose"
  else
    echo ""
  fi
}

start_services() {
  say "Starting datastores"

  local mongo_up=0 redis_up=0
  if port_open 27017; then mongo_up=1; fi
  if port_open 6379;  then redis_up=1; fi

  if [ "$mongo_up" = 1 ] && [ "$redis_up" = 1 ]; then
    ok "Mongo on :27017 and Redis on :6379 are already listening"
    return 0
  fi

  local dc; dc="$(compose_cmd)"
  if [ -n "$dc" ] && docker info >/dev/null 2>&1; then
    $dc -f "$COMPOSE_FILE" up -d
    wait_for_port 27017 mongo || die "Mongo did not come up on :27017"
    ok "Mongo on :27017"
    if wait_for_port 6379 redis 20; then
      ok "Redis on :6379"
    else
      warn "Redis did not come up — the app still works, just uncached"
    fi
    return 0
  fi

  # No Docker. Try Homebrew services.
  warn "Docker isn't running. Trying Homebrew services instead."
  if have brew; then
    if [ "$mongo_up" = 0 ]; then brew services start mongodb-community >/dev/null 2>&1 || true; fi
    if [ "$redis_up" = 0 ]; then brew services start redis >/dev/null 2>&1 || true; fi
    sleep 3
  fi

  if port_open 27017; then
    ok "Mongo on :27017"
  else
    die "MongoDB isn't running. Either start Docker Desktop and re-run, or:
       brew tap mongodb/brew && brew install mongodb-community
       brew services start mongodb-community"
  fi
  if port_open 6379; then
    ok "Redis on :6379"
  else
    warn "Redis not running — app falls back to Mongo-only (fine for dev)"
  fi
}

stop_services() {
  local dc; dc="$(compose_cmd)"
  if [ -n "$dc" ]; then
    say "Stopping datastores"
    $dc -f "$COMPOSE_FILE" down
    ok "stopped (data volume kept — add -v to wipe)"
  else
    warn "docker compose not available; nothing to stop"
  fi
}

# ---------------------------------------------------------------------------
# Dependencies
# ---------------------------------------------------------------------------
write_backend_env() {
  if [ -f "$BACKEND/.env" ]; then ok "backend/.env present"; return 0; fi
  cat > "$BACKEND/.env" <<'EOF'
# Local development environment for the LinkMint backend.
# Generated by run-local.sh. Gitignored — edit freely.

# --- MongoDB -------------------------------------------------------------
MONGO_URL=mongodb://localhost:27017
DB_NAME=linkmint_local

# --- Redis (optional) ----------------------------------------------------
# server.py degrades gracefully to Mongo-only if Redis is unreachable, but
# link caching and anonymous rate limiting are better with it running.
REDIS_URL=redis://localhost:6379/0

# --- CORS ----------------------------------------------------------------
# Must be an explicit origin (not "*") because the frontend sends credentials.
CORS_ORIGINS=http://localhost:3000

# --- Session cookie ------------------------------------------------------
# Production serves over HTTPS and uses Secure + SameSite=None. Browsers refuse
# to store a Secure cookie on http://localhost, which silently breaks sign-in,
# so local dev uses a plain Lax cookie instead.
COOKIE_SECURE=false
COOKIE_SAMESITE=lax

# --- Anonymous rate limits ----------------------------------------------
# Raised from the production 10/min + 100/hour so testing doesn't trip a 429.
ANON_LIMIT_PER_MIN=1000
ANON_LIMIT_PER_HOUR=10000
EOF
  ok "wrote backend/.env"
}

write_frontend_env() {
  if [ -f "$FRONTEND/.env" ]; then ok "frontend/.env present"; return 0; fi
  cat > "$FRONTEND/.env" <<'EOF'
# Local development environment for the LinkMint frontend.
# Generated by run-local.sh. Gitignored — edit freely.

# Backend origin. api.js appends /api itself, so no trailing path here.
REACT_APP_BACKEND_URL=http://localhost:8001

# CRA dev server
PORT=3000
BROWSER=none

GENERATE_SOURCEMAP=true
EOF
  ok "wrote frontend/.env"
}

setup_backend() {
  say "Backend dependencies"
  write_backend_env

  if [ ! -d "$VENV" ]; then
    python3 -m venv "$VENV"
    ok "created backend/.venv"
  fi
  # shellcheck disable=SC1091
  "$VENV/bin/python" -m pip install --quiet --upgrade pip
  "$VENV/bin/python" -m pip install --quiet -r "$BACKEND/requirements-dev.txt"
  ok "installed backend/requirements-dev.txt"
}

setup_frontend() {
  say "Frontend dependencies"
  write_frontend_env

  if [ -d "$FRONTEND/node_modules" ]; then
    ok "node_modules present (delete it and re-run to force a reinstall)"
    return 0
  fi
  say "This first install pulls ~1200 packages and takes a few minutes."
  if [ "$PKG" = yarn ]; then
    (cd "$FRONTEND" && yarn install)
  else
    (cd "$FRONTEND" && npm install --legacy-peer-deps)
  fi
  ok "frontend deps installed"
}

# ---------------------------------------------------------------------------
# Run
# ---------------------------------------------------------------------------
run_backend() {
  cd "$BACKEND"
  exec "$VENV/bin/python" -m uvicorn server:app --reload --host 0.0.0.0 --port "$BACKEND_PORT"
}

run_frontend() {
  cd "$FRONTEND"
  if [ "$PKG" = yarn ]; then exec yarn start; else exec npm start; fi
}

BACK_PID=""
FRONT_PID=""

cleanup() {
  trap - INT TERM EXIT
  say "Shutting down"
  [ -n "$FRONT_PID" ] && kill "$FRONT_PID" 2>/dev/null || true
  [ -n "$BACK_PID" ]  && kill "$BACK_PID"  2>/dev/null || true
  wait 2>/dev/null || true
  ok "bye"
}

run_both() {
  trap cleanup INT TERM EXIT

  say "Starting backend on http://localhost:$BACKEND_PORT"
  ( cd "$BACKEND" && "$VENV/bin/python" -m uvicorn server:app --reload --host 0.0.0.0 --port "$BACKEND_PORT" ) &
  BACK_PID=$!

  if wait_for_port "$BACKEND_PORT" backend 30; then
    ok "backend up"
    if have curl; then
      printf '  %shealth:%s %s\n' "$DIM" "$RESET" \
        "$(curl -fsS "http://localhost:$BACKEND_PORT/api/health" 2>/dev/null || echo 'no response yet')"
    fi
  else
    die "backend failed to start — scroll up for the traceback"
  fi

  say "Starting frontend on http://localhost:$FRONTEND_PORT"
  ( cd "$FRONTEND" && if [ "$PKG" = yarn ]; then yarn start; else npm start; fi ) &
  FRONT_PID=$!

  printf '\n%sLinkMint is running%s\n' "$BOLD$GREEN" "$RESET"
  printf '  app      http://localhost:%s\n' "$FRONTEND_PORT"
  printf '  api      http://localhost:%s/api\n' "$BACKEND_PORT"
  printf '  docs     http://localhost:%s/docs\n' "$BACKEND_PORT"
  printf '  %sCtrl-C stops both.%s\n\n' "$DIM" "$RESET"

  wait "$BACK_PID" "$FRONT_PID"
}

run_tests() {
  say "Running backend_test.py against localhost:$BACKEND_PORT"
  port_open "$BACKEND_PORT" || die "backend isn't running — start it first (./run-local.sh)"
  LINKMINT_BASE_URL="http://localhost:$BACKEND_PORT/api" "$VENV/bin/python" "$ROOT/backend_test.py"
}

# ---------------------------------------------------------------------------
main() {
  case "${1:-run}" in
    setup)
      check_prereqs; start_services; setup_backend; setup_frontend
      printf '\n%sSetup complete.%s Run %s./run-local.sh%s to start.\n' "$BOLD$GREEN" "$RESET" "$BOLD" "$RESET"
      ;;
    backend)
      check_prereqs; start_services; setup_backend; run_backend ;;
    frontend)
      check_prereqs; setup_frontend; run_frontend ;;
    test)
      check_prereqs; run_tests ;;
    env)
      say "Writing .env files"; write_backend_env; write_frontend_env ;;
    stop)
      stop_services ;;
    run|"")
      check_prereqs; start_services; setup_backend; setup_frontend; run_both ;;
    *)
      die "unknown command '$1' — try: setup | run | backend | frontend | test | stop" ;;
  esac
}

main "$@"
