#!/bin/bash
# Podigne Sticky Notes na PRAVOM GNOME-u s 50 nota, u ODVOJENOM $HOME-u.
#
#   sticky_notes_tests/manual/sandbox50.sh
#
# Cemu sluzi: stavke rucne checkliste koje ovise o BROJU nota. Najvazniji je
# slajder prozirnosti (nalaz P-1) — pri 2-5 nota je i pokvaren kod bio gladak
# (~14 ms), pa se na malom profilu ne moze dokazati nista. Pri 50 nota razlika
# je 1.8 ms (danas) vs 162.7 ms (stari _apply_color put) na istom sadrzaju.
# Isto vrijedi za stavku E "50 nota (puni kapacitet)".
#
# Zasto odvojen HOME: config.py izvodi DATA_DIR iz expanduser("~"), pa je HOME
# jedina poluga. Prave biljeske (~/.local/share/sticky_notes) se NE DIRAJU.
# Autostart i globalni precaci su u sandboxu iskljuceni da se ne pise u dconf.
#
# VAZNO: pravi app mora biti UGASEN. D-Bus single-instance ime (ipc.py) je isto
# bez obzira na HOME, pa bi druga instanca tiho izasla kao sekundarna.
#
# Sve zivi u /tmp/sn_sandbox50 i brise se pri sljedecem pokretanju.
set -e
HERE=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
REPO=$(cd "$HERE/../.." && pwd)
SB=/tmp/sn_sandbox50

rm -rf "$SB"
mkdir -p "$SB/.local/share/sticky_notes" "$SB/.config"

python3 - "$SB" "$HOME" <<'PY'
import json, sys, uuid, os

sb, real_home = sys.argv[1], sys.argv[2]
d = os.path.join(sb, ".local", "share", "sticky_notes")

# Sadrzaj po noti: tekst + link + inline kod + dvije kucice + code blok — da
# sweep funkcije (recolor_links, normalize_inline_code) imaju sto obici, kao u
# mjerenju iz prolaza 8 reviewa.
HTML = (
    '<html><body>'
    '<p>Biljeska {i} — obican tekst koji sluzi da dokument ima sto pretraziti.</p>'
    '<p><a href="{href}">https://example.org/link-{i}</a> i '
    '<span style="font-family:monospace; background-color:#e8e8e8;">inline_kod_{i}</span></p>'
    '<p><a href="x-sticky-check">&#9744;</a> zadatak jedan</p>'
    '<p><a href="x-sticky-check">&#9744;</a> zadatak dva</p>'
    '<p style="background-color:#e8e8e8; font-family:monospace;">'
    'def f_{i}(x):<br/>&nbsp;&nbsp;&nbsp;&nbsp;return x * {i}</p>'
    '</body></html>'
)

notes = []
for i in range(50):
    col, row = i % 10, i // 10
    notes.append({
        "id": str(uuid.uuid4()),
        "content": HTML.format(i=i, href=f"https://example.org/link-{i}"),
        "content_type": "html",
        "preview": "", "title": f"sandbox {i}", "display_title": f"sandbox {i}",
        "color": "#F3E5F5", "color_dark": "#2c3542",
        "locked": False, "pinned": False, "pin_time": 0.0,
        "favorite": False, "fav_time": 0.0, "hidden": False, "reminder": None,
        "font_size": 13, "font_family": "Ubuntu Sans",
        "geometry": [60 + col * 150, 60 + row * 160, 440, 300],
    })

json.dump(notes, open(os.path.join(d, "notes.json"), "w"))
json.dump([],    open(os.path.join(d, "closed.json"), "w"))
json.dump([],    open(os.path.join(d, "archived.json"), "w"))

# Krenimo od TVOJIH postavki (da se testira tvoja tema/font), ali bez icega sto
# pise izvan sandboxa.
src = os.path.join(real_home, ".local", "share", "sticky_notes", "settings.json")
try:
    s = json.load(open(src))
except Exception:
    s = {}
s.update(autostart=False, hotkey_enabled=False,
         hotkey_clip_enabled=False, hotkey_search_enabled=False,
         backup_interval=0, note_opacity=100)
json.dump(s, open(os.path.join(d, "settings.json"), "w"), indent=2)
print(f"sandbox spreman: {len(notes)} nota u {d}")
PY

cd "$REPO"
echo "--- pokrecem app (Ctrl+C u ovom terminalu ga gasi) ---"
HOME="$SB" XDG_CONFIG_HOME="$SB/.config" exec python3 -m sticky_notes
