#!/usr/bin/env bash
#
# Build a distributable Sticky Notes tarball for Ubuntu.
#
# Produces sticky-notes-ubuntu.tar.gz containing, under a `sticky-notes/` folder:
#   sticky_notes/               – the app package
#   install.sh                  – the automated installer
#   INSTALL.md                  – the step-by-step guide
#
# The recipient extracts it and runs `sticky-notes/install.sh`.
#
# Usage:   ./package.sh [output.tar.gz]
#
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
OUT="${1:-$ROOT/sticky-notes-ubuntu.tar.gz}"

STAGE="$(mktemp -d)"
trap 'rm -rf "$STAGE"' EXIT
PKG="$STAGE/sticky-notes"
mkdir -p "$PKG"

cp -a "$ROOT/sticky_notes"                 "$PKG/sticky_notes"
cp -a "$ROOT/install.sh"                    "$PKG/install.sh"
cp -a "$ROOT/docs/INSTALL.md"               "$PKG/INSTALL.md"

# Drop Python caches so the archive is clean and reproducible.
find "$PKG" -name __pycache__ -type d -prune -exec rm -rf {} + 2>/dev/null || true
find "$PKG" -name '*.py[co]' -delete 2>/dev/null || true
chmod +x "$PKG/install.sh"

tar -C "$STAGE" -czf "$OUT" sticky-notes
printf '\033[32m✓ Zapakirano:\033[0m %s\n' "$OUT"
tar -tzf "$OUT" | sed 's/^/    /'
