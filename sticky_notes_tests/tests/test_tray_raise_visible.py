import sys, os, tempfile, atexit, shutil
_SB = tempfile.mkdtemp(prefix="sn_test_")
atexit.register(lambda: shutil.rmtree(_SB, ignore_errors=True))
os.environ["HOME"] = _SB
os.environ["XDG_CONFIG_HOME"] = os.path.join(_SB, ".config")
os.environ["XDG_DATA_HOME"]   = os.path.join(_SB, ".local", "share")
os.environ.setdefault("XDG_RUNTIME_DIR", _SB)
os.environ["QT_QPA_PLATFORM"] = "offscreen"
os.environ.pop("DISPLAY", None); os.environ.pop("WAYLAND_DISPLAY", None)
os.makedirs(os.path.join(_SB, ".local", "share", "sticky_notes"), exist_ok=True)
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

fails = []
def check(name, cond):
    print(f"  {'PASS' if cond else 'FAIL'}   {name}")
    if not cond: fails.append(name)

from sticky_notes.app import StickyNotesApp
app = StickyNotesApp(sys.argv[:1])
app._snap_to_grid = app._snap_to_notes = app._snap_size = False
for e in list(app.notes.values()):
    e.hide(); e.deleteLater()
app.notes.clear()

# A,B visible+active; C hidden; D pinned. raise_visible_notes must front ONLY {A, B}.
A = app.create_new_note(); B = app.create_new_note()
C = app.create_new_note(); D = app.create_new_note()
C._hidden = True
D._pinned = True

fronted = []
app._bring_to_front = lambda n: fronted.append(n)

app.raise_visible_notes()

check("fronts exactly the visible non-pinned notes", set(fronted) == {A, B})
check("hidden note not fronted", C not in fronted)
check("pinned note not fronted", D not in fronted)
check("does not touch _hidden of any note",
      A._hidden is False and B._hidden is False and C._hidden is True and D._hidden is False)
check("does not touch _pinned of any note", D._pinned is True and A._pinned is False)

# raise_visible_notes exists as a bound method on the app
check("raise_visible_notes is callable", callable(getattr(app, "raise_visible_notes", None)))
# tray scroll handler exists (wired to the Ayatana scroll-event on GNOME)
check("_on_tray_scroll handler exists", callable(getattr(app, "_on_tray_scroll", None)))

print(f"\n{len(fails)} FAIL" if fails else "\nALL PASS")
sys.exit(1 if fails else 0)
