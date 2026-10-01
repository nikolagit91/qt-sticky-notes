"""Golden-file regression harness for note serialization.

INPUTS (below) are representative note-data dicts. For each we build a live
StickyNote, call get_data(), and compare to a frozen golden in tests/golden/.
Any refactor that silently changes serialization (fields, HTML normalization,
migration) makes a case fail with a diff.

  run tests:   python3 golden_suite.py
  regenerate:  python3 golden_suite.py --update      (after INTENTIONAL changes)

Must run headless (offscreen + dbus + isolated HOME), like the other tests.
Geometry is fixed per-input so output is deterministic under offscreen (no WM).
"""
import sys, os, json, difflib, tempfile, atexit, shutil

# Run fully headless AND sandboxed, no matter where/how this is launched:
# force the offscreen Qt platform (never touch the real X/Wayland server) and
# redirect HOME/XDG to a throwaway dir (never read or write your real notes,
# autostart entry, or dconf). This must happen before importing Qt/sticky_notes.
_SANDBOX = tempfile.mkdtemp(prefix="sn_golden_")
atexit.register(lambda: shutil.rmtree(_SANDBOX, ignore_errors=True))
os.environ["HOME"] = _SANDBOX
os.environ["XDG_CONFIG_HOME"] = os.path.join(_SANDBOX, ".config")
os.environ["XDG_DATA_HOME"]   = os.path.join(_SANDBOX, ".local", "share")
os.environ.setdefault("XDG_RUNTIME_DIR", _SANDBOX)
os.environ["QT_QPA_PLATFORM"] = "offscreen"
# The app's x11.py opens its OWN Xlib connection via $DISPLAY (independent of
# Qt's platform). Under offscreen the window ids are not real X windows, so any
# XChangeProperty would hit a real server with a bogus id → fatal BadWindow.
# Hide every display so those calls no-op (same as a headless machine).
os.environ.pop("DISPLAY", None)
os.environ.pop("WAYLAND_DISPLAY", None)
os.makedirs(os.path.join(_SANDBOX, ".local", "share", "sticky_notes"), exist_ok=True)

HERE = os.path.dirname(os.path.abspath(__file__))
GOLDEN = os.path.join(HERE, "golden")
# Project root = parent of tests/ (the folder that contains the sticky_notes
# package). Works regardless of where the script is launched from.
sys.path.insert(0, os.path.dirname(HERE))
from PyQt6.QtWidgets import QApplication, QMessageBox
QMessageBox.information = staticmethod(lambda *a, **k: None)
QMessageBox.exec = lambda self, *a, **k: QMessageBox.StandardButton.Ok

# Representative cases. Fixed geometry → deterministic get_data under offscreen.
INPUTS = {
    "plain": {
        "id": "g-plain", "content": "<p>Buy milk and eggs</p>", "content_type": "html",
        "title": "", "color": "#fff59d", "geometry": [100, 120, 260, 200],
        "font_size": 14, "font_family": "Sans",
    },
    "styled_titled": {
        "id": "g-styled", "content": "<p>Design notes</p>", "content_type": "html",
        "title": "My Title", "color": "#b3e5fc", "geometry": [50, 60, 320, 240],
        "font_size": 18, "font_family": "Serif",
    },
    "pinned_favorite": {
        "id": "g-pinfav", "content": "<p>Important</p>", "content_type": "html",
        "title": "", "color": "#fff59d", "geometry": [0, 0, 250, 200],
        "pinned": True, "pin_time": 111.0, "favorite": True, "fav_time": 222.0,
        "locked": True,
    },
    "reminder": {
        "id": "g-rem", "content": "<p>Call dentist</p>", "content_type": "html",
        "title": "", "color": "#fff59d", "geometry": [10, 10, 250, 200],
        "reminder": 1893456000.0,   # fixed epoch (2030-01-01)
    },
    # OLD format: pinned but NO favorite/fav_time keys → migration must set
    # favorite=True and fav_time=pin_time (see note.py __init__).
    "migration_old_pinned": {
        "id": "g-mig", "content": "<p>Legacy pinned note</p>", "content_type": "html",
        "title": "", "color": "#fff59d", "geometry": [5, 5, 250, 200],
        "pinned": True, "pin_time": 999.0,
    },
    "web_link": {
        "id": "g-link", "content": '<p>See <a href="https://example.com">example.com</a></p>',
        "content_type": "html", "title": "", "color": "#fff59d",
        "geometry": [7, 7, 260, 200],
    },
}

# Also load fixture inputs — real notes with rich content (checklists, file/web
# links) whose HTML is too large to inline here. Each tests/golden_inputs/<name>.json
# becomes an additional case named <name>.
_FIXTURES = os.path.join(HERE, "golden_inputs")
if os.path.isdir(_FIXTURES):
    for _fn in sorted(os.listdir(_FIXTURES)):
        if _fn.endswith(".json"):
            with open(os.path.join(_FIXTURES, _fn), encoding="utf-8") as _f:
                INPUTS[_fn[:-5]] = json.load(_f)


def build_output(app, data):
    from sticky_notes.note import StickyNote
    note = StickyNote(app, data.get("id"), data)
    out = note.get_data()
    note.hide(); note.deleteLater()
    return out

def main():
    update = "--update" in sys.argv
    os.makedirs(GOLDEN, exist_ok=True)
    from sticky_notes.app import StickyNotesApp
    app = StickyNotesApp(sys.argv[:1])
    # Brojevi se BROJE, ne izvode iz len(INPUTS). Ranije je prolaz bio
    # len(INPUTS)-fails, pa se slucaj koji je upravo ZAPISAN racunao kao prolaz:
    # obrisan golden davao je "9 PASS, 0 FAIL" i exit 0, a zastita je tiho
    # nestala. Zapisivanje je zato dopusteno SAMO uz --update.
    fails = passes = wrote = 0
    missing = []
    for name, data in INPUTS.items():
        out = build_output(app, dict(data))
        path = os.path.join(GOLDEN, name + ".json")
        rendered = json.dumps(out, indent=2, ensure_ascii=False, sort_keys=True)
        if update:
            open(path, "w", encoding="utf-8").write(rendered + "\n")
            print(f"  WROTE  {name}.json")
            wrote += 1
            continue
        if not os.path.exists(path):
            fails += 1
            missing.append(name)
            print(f"  FAIL   {name}  (golden NEDOSTAJE — ako je slucaj nov, "
                  f"pokreni jednom s --update)")
            continue
        expected = open(path, encoding="utf-8").read().rstrip("\n")
        if rendered == expected:
            passes += 1
            print(f"  PASS   {name}")
        else:
            fails += 1
            print(f"  FAIL   {name}  (serialization changed)")
            diff = difflib.unified_diff(expected.splitlines(), rendered.splitlines(),
                                        "golden", "current", lineterm="")
            for ln in list(diff)[:25]:
                print("      " + ln)
    if update:
        print(f"\nUPDATED goldens: {wrote}")
    else:
        tail = f"  ({len(missing)} NEDOSTAJE: {', '.join(missing)})" if missing else ""
        print(f"\n{passes} PASS, {fails} FAIL{tail}")
    sys.exit(1 if fails and not update else 0)

if __name__ == "__main__":
    main()
