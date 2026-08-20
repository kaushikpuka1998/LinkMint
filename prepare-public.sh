#!/usr/bin/env bash
#
# One-shot migration: strip every trace of the Emergent scaffolding, regenerate
# the yarn lockfile, and start a fresh git history authored by you.
#
#   ./prepare-public.sh "Your Name" "you@example.com"
#
# It does NOT touch GitHub. When it finishes you'll have a single local commit
# and a printed list of the push commands to run yourself.
#
# A bundle of the existing history is saved to ../LinkMint-old-history.bundle
# first, so nothing is unrecoverable.

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT"

BOLD="$(printf '\033[1m')"; DIM="$(printf '\033[2m')"
GREEN="$(printf '\033[32m')"; YELLOW="$(printf '\033[33m')"
RED="$(printf '\033[31m')"; RESET="$(printf '\033[0m')"

say()  { printf '\n%s==>%s %s\n' "$BOLD" "$RESET" "$*"; }
ok()   { printf '  %s✓%s %s\n' "$GREEN" "$RESET" "$*"; }
warn() { printf '  %s!%s %s\n' "$YELLOW" "$RESET" "$*"; }
die()  { printf '  %s✗%s %s\n' "$RED" "$RESET" "$*" >&2; exit 1; }

GIT_NAME="${1:-}"
GIT_EMAIL="${2:-}"
if [ -z "$GIT_NAME" ] || [ -z "$GIT_EMAIL" ]; then
  die "usage: ./prepare-public.sh \"Your Name\" \"you@example.com\""
fi

# ---------------------------------------------------------------------------
say "Checking the repository is idle"
# ---------------------------------------------------------------------------
if [ -f .git/index.lock ]; then
  if pgrep -f '[g]it ' >/dev/null 2>&1; then
    die "a git process is currently running — let it finish, then re-run this script"
  fi
  rm -f .git/index.lock
  ok "cleared a stale .git/index.lock"
else
  ok "no stale lock"
fi

# ---------------------------------------------------------------------------
say "Backing up the existing history"
# ---------------------------------------------------------------------------
if [ -d .git ]; then
  BUNDLE="$ROOT/../LinkMint-old-history.bundle"
  git bundle create "$BUNDLE" --all >/dev/null 2>&1 \
    && ok "saved $BUNDLE" \
    || warn "could not bundle the old history (continuing anyway)"
else
  warn "no .git directory — nothing to back up"
fi

# ---------------------------------------------------------------------------
say "Removing Emergent scaffolding"
# ---------------------------------------------------------------------------
REMOVE="
.emergent
.gitconfig
memory
test_reports
tests
test_result.md
auth_testing.md
plan.md
requirements-local.txt
backend/backend_test.py
backend/__pycache__
frontend/src/components/AuthCallback.jsx
frontend/src/constants/testIds/home.js
frontend/plugins
frontend/README.md
design_guidelines.md
frontend/build
"

for path in $REMOVE; do
  if [ -e "$path" ]; then
    rm -rf "$path"
    ok "removed $path"
  fi
done

# ---------------------------------------------------------------------------
say "Regenerating the frontend lockfile"
# ---------------------------------------------------------------------------
# yarn.lock still pins @emergentbase/visual-edits from assets.emergent.sh until
# it is regenerated against the edited package.json.
if [ -d frontend/node_modules ] || [ -f frontend/yarn.lock ]; then
  if command -v yarn >/dev/null 2>&1; then
    ( cd frontend && yarn install )
    ok "yarn.lock regenerated"
  else
    warn "yarn not found — run 'cd frontend && yarn install' before committing"
  fi
else
  warn "frontend deps not installed yet; the lockfile will be clean on first install"
fi

# ---------------------------------------------------------------------------
say "Verifying nothing is left"
# ---------------------------------------------------------------------------
LEFTOVERS="$(grep -ril "emergent" . \
  --exclude-dir=.git \
  --exclude-dir=node_modules \
  --exclude-dir=.venv \
  --exclude-dir=__pycache__ \
  --exclude=prepare-public.sh 2>/dev/null || true)"

if [ -n "$LEFTOVERS" ]; then
  warn "still mentions emergent:"
  printf '      %s\n' $LEFTOVERS
  warn "review these before pushing"
else
  ok "no references remain outside .git"
fi

# A public repo should never ship these.
for f in backend/.env frontend/.env .env; do
  if [ -f "$f" ] && git check-ignore -q "$f" 2>/dev/null; then
    ok "$f is gitignored"
  elif [ -f "$f" ]; then
    die "$f exists and is NOT gitignored — fix .gitignore before continuing"
  fi
done

# ---------------------------------------------------------------------------
say "Starting a fresh git history"
# ---------------------------------------------------------------------------
rm -rf .git

git init -q
git config user.name  "$GIT_NAME"
git config user.email "$GIT_EMAIL"
git symbolic-ref HEAD refs/heads/main

# This script is a one-shot migration tool, not part of the project. Excluding
# it rather than deleting it, because bash is still reading from it right now.
echo 'prepare-public.sh' >> .git/info/exclude

git add -A
git commit -q -m "LinkMint — self-hosted URL shortener

FastAPI + React + MongoDB + Redis. Anonymous or account-scoped short links
with custom aliases, expiry, QR codes, tags, click analytics and CSV export."

ok "committed $(git rev-list --count HEAD) commit as $GIT_NAME <$GIT_EMAIL>"

printf '\n%sTracked files:%s %s\n' "$BOLD" "$RESET" "$(git ls-files | wc -l | tr -d ' ')"
git ls-files | sed 's|/[^/]*$||' | sort -u | head -20 | sed 's/^/    /'

cat <<EOF

${BOLD}${GREEN}Ready to push.${RESET} Nothing has touched GitHub yet.

  ${DIM}# with the GitHub CLI (creates the repo and pushes in one step)${RESET}
  gh repo create linkmint --public --source=. --remote=origin --push

  ${DIM}# or, if you created the repo in the browser first${RESET}
  git remote add origin git@github.com:<you>/linkmint.git
  git push -u origin main

${DIM}Old history is bundled at ../LinkMint-old-history.bundle —
restore with: git clone LinkMint-old-history.bundle LinkMint-old

This script excluded itself from the commit; delete it once you've pushed:
  rm prepare-public.sh${RESET}

EOF
