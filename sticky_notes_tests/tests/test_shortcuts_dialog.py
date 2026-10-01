"""The cheat-sheet is a tabbed window: one tab per catalog section.

It used to stack every section in one column, which grew taller with each
shortcut added. Tabs keep it a fixed, small window as the catalog grows — and
sections() stays the single source of truth: a new section there becomes a new
tab here with no change to this dialog.
"""
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

from PyQt6.QtWidgets import QLabel, QDialog, QTabWidget
from sticky_notes import shortcuts
from sticky_notes.app import StickyNotesApp
app = StickyNotesApp(sys.argv[:1])

app.show_shortcuts()
dlgs = [w for w in app._open_windows if isinstance(w, QDialog)
        and w.windowTitle() == "Keyboard shortcuts"]
check("dialog opened once", len(dlgs) == 1)
dlg = dlgs[0]

tabs = dlg.findChildren(QTabWidget)
check("the cheat-sheet is tabbed", len(tabs) == 1)
tw = tabs[0]

secs = shortcuts.sections()
check("one tab per catalog section", tw.count() == len(secs))
check("tab labels are the section titles",
      [tw.tabText(i) for i in range(tw.count())] == [t for t, _ in secs])

# ── each tab holds its own rows, and only its own ────────────────────────────
def labels_of(i):
    return [l.text() for l in tw.widget(i).findChildren(QLabel)]

by_title = {tw.tabText(i): labels_of(i) for i in range(tw.count())}
check("the Note tab holds Duplicate", any("Duplicate" in t for t in by_title["Note"]))
check("Duplicate is not on the Global tab",
      not any("Duplicate" in t for t in by_title["Global"]))
check("the Code tab holds Inline code", any("Inline code" in t for t in by_title["Code"]))
check("the Text tab holds Paste as plain text",
      any("plain text" in t for t in by_title["Text & lists"]))
check("the Windows tab holds Esc", "Esc" in by_title["Windows"])

# ── keycaps and hints still render ───────────────────────────────────────────
check("shows a Ctrl keycap", "Ctrl" in by_title["Note"])
check("shows a D keycap", "D" in by_title["Note"])
check("shows the click-header hint", any("header first" in t for t in by_title["Note"]))
check("shows the Global settings note", any("Settings" in t for t in by_title["Global"]))
check("the Code tab warns the setting must be on",
      any("Enable code blocks" in t for t in by_title["Code"]))

# ── the window no longer grows with the catalog ──────────────────────────────
check("the window stays compact", dlg.sizeHint().height() <= 460)

# ── tabs bought room, so the text is bigger than the app's dense chrome ───────
# Checked through the RESOLVED font (what Qt paints) rather than the QSS string.
# Sizes are local to this dialog: UI.LABEL_STYLE is shared app-wide and must not
# grow just because the cheat-sheet wanted bigger text.
def px(widget):
    widget.ensurePolished()
    return widget.font().pixelSize()

note_rows = [l for l in tw.widget(1).findChildren(QLabel)]
row_lbl = next(l for l in note_rows if l.text() == "Duplicate")
keycap  = next(l for l in note_rows if l.text() == "D")
check("row labels are bigger than the shared 13px chrome label", px(row_lbl) >= 15)
# Keycap size was tuned on a real screen: 17px shouted, 14px was a touch small,
# 15px settled it. Pinned rather than bounded so a future "make the cheat-sheet
# bigger" can't quietly drag them along again.
check("keycaps stay at the tuned 15px", px(keycap) == 15)

from sticky_notes.theme import UI
check("the shared label style was NOT bumped app-wide", "13px" in UI.LABEL_STYLE)

app.show_shortcuts()   # second call must focus the existing one, not open a 2nd
dlgs2 = [w for w in app._open_windows if isinstance(w, QDialog)
         and w.windowTitle() == "Keyboard shortcuts"]
check("no duplicate dialog on re-open", len(dlgs2) == 1)

print(f"\n{len(fails)} FAIL" if fails else "\nALL PASS")
sys.exit(1 if fails else 0)
