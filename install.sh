#!/bin/sh
# COUNCIL installer for macOS and Linux.
#   curl -fsSL https://raw.githubusercontent.com/musalkeremlboz/council/main/install.sh | sh
# Installs into ~/.council (its own Python environment, no administrator rights), then runs
# `council install`, which starts the service, connects Claude Code, imports the memory you already
# have and turns on automatic updates. Options after `sh -s --` are passed on, e.g. --no-auto-update.
set -eu

REPO="musalkeremlboz/council"
DIR="${COUNCIL_HOME:-$HOME/.council}"

fail() {
    printf 'COUNCIL could not be installed: %s\n' "$*" >&2
    exit 1
}

command -v git >/dev/null 2>&1 || fail "git is not installed."
PY=""
for c in python3.14 python3.13 python3.12 python3.11 python3; do
    if command -v "$c" >/dev/null 2>&1 &&
        "$c" -c 'import sys; sys.exit(0 if sys.version_info >= (3, 11) else 1)' 2>/dev/null; then
        PY="$c"
        break
    fi
done
[ -n "$PY" ] || fail "Python 3.11 or later is needed (https://www.python.org/downloads/)."

if [ -n "${COUNCIL_SOURCE:-}" ]; then
    SRC="$COUNCIL_SOURCE"
else
    TAG="$(curl -fsSL "https://api.github.com/repos/$REPO/releases/latest" 2>/dev/null |
        sed -n 's/.*"tag_name": *"\([^"]*\)".*/\1/p' | head -n 1 || true)"
    SRC="git+https://github.com/$REPO@${TAG:-main}"
fi

printf 'Installing COUNCIL into %s ...\n' "$DIR"
"$PY" -m venv "$DIR/venv"
"$DIR/venv/bin/python" -m pip install --quiet --disable-pip-version-check --upgrade "$SRC" || fail "the download failed."
exec "$DIR/venv/bin/python" -m council.cli --data "$DIR" install "$@"
