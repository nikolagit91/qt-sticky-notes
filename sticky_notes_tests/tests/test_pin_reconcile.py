"""Pinning one note must not drag the others up. Root cause (confirmed via xprop):
Qt marks each note WM_TRANSIENT_FOR a shared leader window, and Mutter stacks all
transients of one parent together — so a pinned note (with _NET_WM_STATE_ABOVE)
pulls its transient siblings up even though THEY have no ABOVE. The fix:
x11.detach_window_group now also DELETES WM_TRANSIENT_FOR; _reconcile_pin_stacking
re-detaches every note after a pin (deferred), so each becomes independent.

Headless: detach_window_group is spied (no-ops off X11); we assert it's called
for every note on reconcile and (deferred) after a pin toggle.
"""
import sys, os, tempfile, atexit, shutil, time

_SB = tempfile.mkdtemp(prefix="sn_rec_")
atexit.register(lambda: shutil.rmtree(_SB, ignore_errors=True))
os.environ["HOME"] = _SB
os.environ["XDG_CONFIG_HOME"] = os.path.join(_SB, ".config")
os.environ["XDG_DATA_HOME"]   = os.path.join(_SB, ".local", "share")
os.environ.setdefault("XDG_RUNTIME_DIR", _SB)
os.environ["QT_QPA_PLATFORM"] = "offscreen"
os.environ.pop("DISPLAY", None); os.environ.pop("WAYLAND_DISPLAY", None)
os.makedirs(os.path.join(_SB, ".local", "share", "sticky_notes"), exist_ok=True)
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PyQt6.QtWidgets import QApplication, QMessageBox
QMessageBox.information = staticmethod(lambda *a, **k: None)

fails = []
def check(name, cond):
    print(f"  {'PASS' if cond else 'FAIL'}   {name}")
    if not cond: fails.append(name)

from sticky_notes.app import StickyNotesApp
from sticky_notes.note import StickyNote
import sticky_notes.x11 as x11mod
app = StickyNotesApp(sys.argv[:1])
app._snap_to_grid = app._snap_to_notes = app._snap_size = False

detached = []
x11mod.detach_window_group = lambda wid: detached.append(wid)

def pump(ms):
    end = time.monotonic() + ms / 1000.0
    while time.monotonic() < end:
        QApplication.processEvents(); time.sleep(0.01)

a = StickyNote(app, "a", {"id": "a", "geometry": [10, 10, 300, 200]})
b = StickyNote(app, "b", {"id": "b", "geometry": [350, 10, 300, 200]})
c = StickyNote(app, "c", {"id": "c", "geometry": [10, 250, 300, 200], "pinned": True})
app.notes.update(a=a, b=b, c=c)
a.show(); b.show(); c.show(); QApplication.processEvents()
a_wid, b_wid, c_wid = int(a.winId()), int(b.winId()), int(c.winId())

# ── reconcile re-detaches EVERY visible note (pinned included) ───────────────
detached.clear()
app._reconcile_pin_stacking()
touched = set(detached)
check("reconcile: detaches note a", a_wid in touched)
check("reconcile: detaches note b", b_wid in touched)
check("reconcile: detaches pinned note c too (clears its transient_for)", c_wid in touched)

# ── _toggle_pin schedules the reconcile (deferred) ──────────────────────────
detached.clear()
a._toggle_pin()            # pin a
pump(400)                  # let singleShot(0) + singleShot(250) fire
touched = set(detached)
check("pin a: reconcile ran (deferred) — siblings re-detached", b_wid in touched and c_wid in touched)
check("pin a: pinned note itself re-detached", a_wid in touched)

for w in (a, b, c):
    w.hide(); w.deleteLater()
print(f"\n{len(fails)} FAIL" if fails else "\nALL PASS")
sys.exit(1 if fails else 0)
