"""#3 fix: a note the user hid must STAY hidden across a restart.

Before: hidden state lived only as runtime widget visibility, was never saved,
and _load_notes called note.show() on every note → hidden notes came back.
Now: NoteData has a `hidden` field, set_hidden() records the intent, get_data
persists it, and _load_notes only shows notes that aren't hidden.

Headless + sandboxed (offscreen + isolated HOME), same as the other tests.
Note: under offscreen isVisible() is unreliable, so we assert on isHidden()
and the persisted _hidden flag.
"""
import sys, os, json, tempfile, atexit, shutil

_SB = tempfile.mkdtemp(prefix="sn_hidden_")
atexit.register(lambda: shutil.rmtree(_SB, ignore_errors=True))
os.environ["HOME"] = _SB
os.environ["XDG_CONFIG_HOME"] = os.path.join(_SB, ".config")
os.environ["XDG_DATA_HOME"]   = os.path.join(_SB, ".local", "share")
os.environ.setdefault("XDG_RUNTIME_DIR", _SB)
os.environ["QT_QPA_PLATFORM"] = "offscreen"
os.environ.pop("DISPLAY", None)
os.environ.pop("WAYLAND_DISPLAY", None)
os.makedirs(os.path.join(_SB, ".local", "share", "sticky_notes"), exist_ok=True)
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PyQt6.QtWidgets import QApplication, QMessageBox
QMessageBox.information = staticmethod(lambda *a, **k: None)

fails = []
def check(name, cond):
    print(f"  {'PASS' if cond else 'FAIL'}   {name}")
    if not cond:
        fails.append(name)

from sticky_notes.app import StickyNotesApp
from sticky_notes.note import StickyNote
from sticky_notes.config import DATA_FILE
app = StickyNotesApp(sys.argv[:1])

# ── model / serialization ───────────────────────────────────────────────────
n = StickyNote(app, "h1", {"id": "h1", "content": "<p>hi</p>", "content_type": "html",
                           "geometry": [10, 10, 300, 200]})
check("new note default: not hidden", n._hidden is False)
check("get_data carries hidden=False", n.get_data()["hidden"] is False)

n.set_hidden(True)
check("set_hidden(True): _hidden flag set", n._hidden is True)
check("set_hidden(True): widget hidden", n.isHidden() is True)
check("get_data carries hidden=True", n.get_data()["hidden"] is True)

n.set_hidden(False)
check("set_hidden(False): _hidden cleared", n._hidden is False)

# a dict WITHOUT the key (old note) → not hidden (backward compatible)
old = StickyNote(app, "old", {"id": "old", "content": "<p>x</p>", "content_type": "html"})
check("legacy note without 'hidden' key → not hidden", old._hidden is False)

# ── the actual bug: _load_notes must honour a hidden note ────────────────────
seed = [
    {"id": "vis", "content": "<p>visible</p>", "content_type": "html",
     "geometry": [0, 0, 300, 200], "hidden": False},
    {"id": "hid", "content": "<p>hidden</p>", "content_type": "html",
     "geometry": [0, 0, 300, 200], "hidden": True},
]
with open(DATA_FILE, "w", encoding="utf-8") as f:
    json.dump(seed, f)

for existing in list(app.notes.values()):
    existing.hide(); existing.deleteLater()
app.notes.clear()
app._load_notes()

vis = app.notes.get("vis")
hid = app.notes.get("hid")
check("load: both notes constructed", vis is not None and hid is not None)
check("load: visible note is shown (not isHidden)", vis is not None and not vis.isHidden())
check("load: hidden note stays hidden (isHidden)", hid is not None and hid.isHidden())
check("load: hidden note keeps _hidden=True", hid is not None and hid._hidden is True)

# ── bulk + reveal paths keep the flag consistent ────────────────────────────
app.hide_all_notes()
check("hide_all_notes: every note _hidden=True", all(x._hidden for x in app.notes.values()))
app.show_all_notes()
check("show_all_notes: every note _hidden=False", all(not x._hidden for x in app.notes.values()))

app.notes["hid"].set_hidden(True)
app.reveal_note(app.notes["hid"])
check("reveal_note un-hides a hidden note", app.notes["hid"]._hidden is False)

# ── restoring a note that was hidden when trashed → shown, flag cleared ──────
app.trash_notes = [{"id": "t1", "content": "<p>t</p>", "content_type": "html",
                    "geometry": [0, 0, 300, 200], "hidden": True}]
app.restore_from_trash(app.trash_notes[0])
r = app.notes.get("t1")
check("restore from trash: note exists", r is not None)
check("restore from trash: shown (not isHidden)", r is not None and not r.isHidden())
check("restore from trash: hidden flag cleared", r is not None and r._hidden is False)

print(f"\n{len(fails)} FAIL" if fails else "\nALL PASS")
sys.exit(1 if fails else 0)
