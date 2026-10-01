"""Collapsing the chrome must repaint the whole note, so its painted border
isn't left cleared.

The note is a WA_TranslucentBackground widget whose rounded body + 1px border
are drawn in paintEvent over the full w×h. When the header collapses (clean
mode), the transparent, RECTANGULAR text edit expands up over the header's old
area and clears it — and nothing forced the note (the parent) to repaint there,
so the border vanished on the top and sides while remnants stayed at the bottom
(the bottom bar) and in the rounded corners (which the rectangular child never
covers). The window size never changes across the toggle, so a full repaint is
the fix.

Offscreen can't check painted pixels, so this guards the invariant it needs:
the collapse/reveal animations drive a full note repaint.
"""
import sys, os, tempfile, atexit, shutil
_SB = tempfile.mkdtemp(prefix="sn_border_")
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
app._clean_mode = True
for e in list(app.notes.values()):
    e.hide(); e.deleteLater()
app.notes.clear()
n = app.create_new_note(content="hello")

# Spy on the note's repaint.
calls = {"n": 0}
n.update = lambda *a, **k: calls.__setitem__("n", calls["n"] + 1)

# Each frame of the header collapse must repaint the note, or the exposed strip
# is left cleared (translucent) with no border painted back.
calls["n"] = 0
n._header_anim.valueChanged.emit(19)
check("a header-animation frame repaints the note", calls["n"] > 0)

calls["n"] = 0
n._toolbar_anim.valueChanged.emit(16)
check("a toolbar-animation frame repaints the note", calls["n"] > 0)

# And the final state (animation finished) must repaint too, so the settled
# note isn't left with the border half-erased.
calls["n"] = 0
n._on_header_anim_finished()
check("the header animation's end repaints the note", calls["n"] > 0)

calls["n"] = 0
n._on_toolbar_anim_finished()
check("the toolbar animation's end repaints the note", calls["n"] > 0)

# The window size stays constant across the toggle — the border must cover the
# same full rect before and after, so a repaint is all that's needed.
before = (n.width(), n.height())
n._hide_chrome(); n._on_header_anim_finished(); n._on_toolbar_anim_finished()
check("the note doesn't resize when the chrome hides", (n.width(), n.height()) == before)

print(f"\n{len(fails)} FAIL" if fails else "\nALL PASS")
sys.exit(1 if fails else 0)
