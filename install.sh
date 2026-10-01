#!/usr/bin/env bash
#
# Sticky Notes — automated installer for Ubuntu (24.04+, GNOME).
#
# Installs the required system packages, copies the app to a stable location,
# and launches it once so it registers its app-menu launcher, autostart entry
# and the three global shortcuts. Re-runnable (updates the copied code).
#
# Usage:   ./install.sh
# Install dir can be overridden:   INSTALL_DIR=~/Applications/sticky-notes ./install.sh
#
set -euo pipefail

APP_NAME="Sticky Notes"
INSTALL_DIR="${INSTALL_DIR:-$HOME/.local/share/sticky-notes-app}"

# The sticky_notes package must sit next to this script (repo root, or the
# extracted distributable). Resolve relative to the script, not the CWD.
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SRC="$SCRIPT_DIR/sticky_notes"

info() { printf '\033[36m▸ %s\033[0m\n' "$*"; }
ok()   { printf '\033[32m✓ %s\033[0m\n' "$*"; }
err()  { printf '\033[31m✗ %s\033[0m\n' "$*" >&2; }

# ── Preconditions ─────────────────────────────────────────────────────────────
[ -f "$SRC/__main__.py" ] || {
    err "Can't find the 'sticky_notes' folder next to this script:"
    err "  $SRC"
    err "Run install.sh from the folder that contains 'sticky_notes'."
    exit 1
}
command -v apt-get >/dev/null 2>&1 || {
    err "This is not a Debian/Ubuntu system (no apt). See docs/INSTALL.md for the manual route."
    exit 1
}

# ── 1) System packages ────────────────────────────────────────────────────────
info "Installing system packages (will ask for your sudo password)…"
sudo apt-get update -qq
sudo apt-get install -y \
    python3-pyqt6 python3-pyqt6.qtsvg python3-gi gir1.2-ayatanaappindicator3-0.1 \
    libcanberra-gtk3-module sound-theme-freedesktop fonts-noto-cjk
ok "Packages installed."

# ── 2) Verify the Python modules really import ────────────────────────────────
info "Checking Python modules…"
if ! python3 - <<'PY'
import importlib.util as u, sys
missing = [m for m in ("PyQt6.QtWidgets", "PyQt6.QtSvg", "PyQt6.QtDBus", "gi")
           if u.find_spec(m) is None]
if missing:
    print("Missing:", ", ".join(missing))
    sys.exit(1)
PY
then
    err "Some Python modules are missing (see above). Aborting."
    exit 1
fi
ok "Modules present."

# ── 3) Copy the app to a stable location ──────────────────────────────────────
# The first run bakes this parent path into ~/.local/share/sticky_notes/start.sh,
# so the code must live somewhere it won't be moved from afterwards.
info "Copying the app to $INSTALL_DIR …"
mkdir -p "$INSTALL_DIR"
rm -rf "${INSTALL_DIR:?}/sticky_notes"
cp -a "$SRC" "$INSTALL_DIR/sticky_notes"
find "$INSTALL_DIR/sticky_notes" -name __pycache__ -type d -prune -exec rm -rf {} + 2>/dev/null || true
ok "Code in place."

# ── 4) First run — registers launcher, autostart entry and global shortcuts ───
if [ -n "${DISPLAY:-}" ] || [ -n "${WAYLAND_DISPLAY:-}" ]; then
    info "Launching for the first time (registers launcher, autostart and shortcuts)…"
    ( cd "$INSTALL_DIR" && nohup python3 -m sticky_notes >/dev/null 2>&1 & )
    ok "Launched — the tray icon should appear in the top bar."
else
    info "No graphical session; run it manually once you log in:"
    info "  cd \"$INSTALL_DIR\" && python3 -m sticky_notes"
fi

cat <<EOF

────────────────────────────────────────────────
$APP_NAME installed.

  • Launch:      from the app menu (press Super → type "Sticky Notes"),
                 and it also starts itself on every login.
  • Shortcuts:   Super+Alt+N    → new note
                 Super+Shift+N  → new note from clipboard
                 Super+Shift+F  → search notes
  • Code:        $INSTALL_DIR/sticky_notes   (don't move it)
  • Data/backup: ~/.local/share/sticky_notes/

Uninstall and troubleshooting: docs/INSTALL.md
────────────────────────────────────────────────
EOF
