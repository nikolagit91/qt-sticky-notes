"""Guard: formatting actions skip CHECKED (locked) checklist rows. A selection
that covers a checked row together with other lines formats the other lines
only; a selection inside a checked row changes nothing. Covers every toolbar /
shortcut formatting path: B/I/U/S, text colour, font family, absolute and ▲▼
font size, inline code, code block, bullet list.

Companion of test_checklist_checked_locked.py (the text lock, 2026-10-14).
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

from PyQt6.QtWidgets import QMessageBox
QMessageBox.information = staticmethod(lambda *a, **k: None)
from PyQt6.QtGui import QTextCursor, QTextCharFormat, QTextBlockFormat, QTextListFormat, QFont
from sticky_notes.app import StickyNotesApp
from sticky_notes.widgets import CHECK_DONE

app = StickyNotesApp(sys.argv[:1])
app._code_blocks = True
for e in list(app.notes.values()):
    e.hide(); e.deleteLater()
app.notes.clear()
note = app.create_new_note()
te = note.text_edit
doc = te.document()

def setup():
    # setPlainText inherits the current typing format — reset it, or the last
    # action's font/size leaks into the fresh text and the next one is a no-op.
    te.setCurrentCharFormat(QTextCharFormat())
    te.setPlainText("prvi\nmlijeko\ntreci")
    for bn in range(3):
        c = te.textCursor(); c.setPosition(doc.findBlockByNumber(bn).position())
        te.setTextCursor(c); te.toggle_checklist()
    te.toggle_checkbox(doc.findBlockByNumber(1).position())

def snapshot(bn):
    b = doc.findBlockByNumber(bn)
    frags, it = [], b.begin()
    while not it.atEnd():
        f = it.fragment()
        frags.append((f.position(), f.length(), QTextCharFormat(f.charFormat())))
        it += 1
    return (b.text(), QTextBlockFormat(b.blockFormat()), b.textList() is None, frags)

def select(a, b):
    c = te.textCursor(); c.setPosition(a); c.setPosition(b, QTextCursor.MoveMode.KeepAnchor)
    te.setTextCursor(c)

def select_all():
    select(0, doc.characterCount() - 1)

def text_fmt(bn):
    """Char format of the first TEXT char (past "☐ ") of row bn."""
    b = doc.findBlockByNumber(bn)
    c = QTextCursor(doc); c.setPosition(b.position() + 2)
    c.setPosition(b.position() + 3, QTextCursor.MoveMode.KeepAnchor)
    return c.charFormat()

def code(bn):
    return te._is_code_block(doc.findBlockByNumber(bn))

ACTIONS = [
    ("bold",        lambda: note._fmt_bold(),
                    lambda: text_fmt(0).fontWeight() >= QFont.Weight.DemiBold),
    ("italic",      lambda: note._fmt_italic(),       lambda: text_fmt(0).fontItalic()),
    ("underline",   lambda: note._fmt_underline(),    lambda: text_fmt(0).fontUnderline()),
    ("strike",      lambda: note._fmt_strike(),       lambda: text_fmt(0).fontStrikeOut()),
    ("text colour", lambda: note._apply_text_color("#c62828"),
                    lambda: text_fmt(0).foreground().color().name() == "#c62828"),
    ("font family", lambda: note._apply_font_family("DejaVu Sans"),
                    lambda: "DejaVu Sans" in (text_fmt(0).fontFamilies() or [])),
    ("font size",   lambda: note._apply_font_size(30, te.textCursor()),
                    lambda: text_fmt(0).fontPointSize() == 30),
    ("font size ▲", lambda: note._change_font_size(+4),
                    lambda: text_fmt(0).fontPointSize() == _size_before + 4),
    ("inline code", lambda: note._toggle_inline_code(), lambda: te._is_inline_code(text_fmt(0))),
    ("code block",  lambda: note._toggle_code_block(),  lambda: code(0) and code(2)),
    ("bullet list", lambda: note._fmt_bullet(QTextListFormat.Style.ListDisc),
                    lambda: doc.findBlockByNumber(0).textList() is not None),
]

for name, act, applied in ACTIONS:
    # whole note selected: other rows formatted, the checked row untouched
    setup(); _size_before = text_fmt(0).fontPointSize() or te.font().pointSizeF()
    before = snapshot(1)
    select_all(); act()
    check(f"{name}: applied to the unchecked rows (select-all)", applied())
    check(f"{name}: checked row unchanged (select-all)", snapshot(1) == before)
    # selection only inside the checked row: nothing changes there
    setup(); before = snapshot(1)
    b = doc.findBlockByNumber(1)
    select(b.position() + 2, b.position() + len(b.text())); act()
    check(f"{name}: selection inside the checked row changes nothing", snapshot(1) == before)

# code block split by a checked row: each part is its own region with edge spacing
setup(); select_all(); note._toggle_code_block()
check("code block around a checked row: row 0 has its bottom edge spacing",
      doc.findBlockByNumber(0).blockFormat().bottomMargin() > 0)
check("code block around a checked row: row 2 has its top edge spacing",
      doc.findBlockByNumber(2).blockFormat().topMargin() > 0)

# one formatting action = one undo step (the restore isn't a separate step)
setup(); before0 = snapshot(0); select_all(); note._fmt_bold(); doc.undo()
check("undo after a skipped-row format restores in ONE step", snapshot(0) == before0)

# toggles decide on/off from the UNLOCKED text only: the checked row never takes
# the format, so counting it made "all bold?" always False → a second press
# re-applied instead of turning it off (bug reported 2026-10-15).
TOGGLES = [
    ("bold",      note._fmt_bold,      lambda f: f.fontWeight() >= QFont.Weight.DemiBold),
    ("italic",    note._fmt_italic,    lambda f: f.fontItalic()),
    ("underline", note._fmt_underline, lambda f: f.fontUnderline()),
    ("strike",    note._fmt_strike,    lambda f: f.fontStrikeOut()),
]
for name, act, has in TOGGLES:
    setup(); before = snapshot(1)
    select_all(); act()
    check(f"{name} toggle: 1st press turns it on (select-all)", has(text_fmt(0)) and has(text_fmt(2)))
    select_all(); act()
    check(f"{name} toggle: 2nd press turns it OFF (select-all)",
          not has(text_fmt(0)) and not has(text_fmt(2)))
    check(f"{name} toggle: checked row unchanged after on+off", snapshot(1) == before)

print()
print("FAILED:" if fails else "ALL PASS", *fails, sep="\n  " if fails else "")
sys.exit(1 if fails else 0)
