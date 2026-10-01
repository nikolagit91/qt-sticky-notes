"""A workspace switch must not re-assert window state (and re-raise the notes).

Measured on the user's GNOME with temporary instrumentation: switching away from
the notes' workspace makes Mutter UNMAP them, and switching back MAPS them again
— Qt delivers hide/show with spontaneous=True. Log excerpt:

    21:46:53.835  hide x3  spontaneous=True     ← leaving the workspace
    21:46:56.588  show x3  spontaneous=True     ← coming back

showEvent therefore ran on EVERY workspace switch, firing six X11 operations per
note: _detach_group / _apply_skip_taskbar / _apply_pin_above, immediately and
again deferred. Two of those are prime suspects for the reported "notes jump in
front of my applications when I come back to their workspace":

  * _detach_group changes WM_TRANSIENT_FOR on a MAPPED window, so Mutter
    re-evaluates it as an independent top-level and restacks it;
  * set_skip_taskbar does XChangeProperty(..., REPLACE) over the WHOLE
    _NET_WM_STATE, which EWMH does not allow on a mapped window (a client must
    use a client message there, the way set_above does) and which also wipes
    any state the WM itself owns.

Those three calls exist to re-assert state after WE map a window. On a WM-driven
re-map the X11 properties are still on the window, so re-asserting is redundant.
Hence: skip them when the show is spontaneous.

This test guards the split. Whether it actually stops the jumping is a WM
behaviour that cannot be reproduced offscreen — the user verifies that on GNOME.
"""
import sys, os, tempfile, atexit, shutil
_SB = tempfile.mkdtemp(prefix="sn_wsremap_")
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

from sticky_notes import x11
from sticky_notes.app import StickyNotesApp

app = StickyNotesApp(sys.argv[:1])
for e in list(app.notes.values()):
    e.hide(); e.deleteLater()
app.notes.clear()

hits = []
x11.set_skip_taskbar    = lambda win: hits.append("skip_taskbar")
x11.set_above           = lambda win, enable: hits.append(f"above={enable}")
x11.detach_window_group = lambda win: hits.append("detach")

note = app.create_new_note(content="ws")
note.show()
app.processEvents()

check("the re-assert body is split out so it can be tested at all",
      hasattr(note, "_reassert_window_state"))

# ── our OWN show() must still re-assert everything ───────────────────────────
hits.clear()
note._reassert_window_state(spontaneous=False)
app.processEvents()
check("our own show still detaches from the shared X11 group", "detach" in hits)
check("our own show still re-applies skip-taskbar", "skip_taskbar" in hits)
check("our own show still re-applies the pin state",
      any(h.startswith("above=") for h in hits))

# ── a WM-driven re-map (workspace switch) must touch nothing ─────────────────
hits.clear()
note._reassert_window_state(spontaneous=True)
app.processEvents()
check("a spontaneous re-map makes NO X11 calls at all", hits == [])

# ── and the wiring: showEvent has to pass the flag through ───────────────────
seen = []
note._reassert_window_state = lambda spontaneous: seen.append(spontaneous)
note.hide(); app.processEvents()
note.show(); app.processEvents()
# Our own show() is never spontaneous — if this reports True, the flag is
# inverted and every real workspace switch would still re-assert.
check("showEvent passes spontaneous=False for our own show()",
      seen and seen[-1] is False)

print()
print(f"{len(fails)} FAIL" if fails else "SVE PROŠLO")
sys.exit(1 if fails else 0)
