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

from sticky_notes import shortcuts
check("DUPLICATE", shortcuts.DUPLICATE == "Ctrl+D")
check("EXPORT", shortcuts.EXPORT == "Ctrl+E")
check("TRASH", shortcuts.TRASH == "Ctrl+W")

secs = shortcuts.sections()
titles = [t for t, _ in secs]
# Section titles double as TAB LABELS in the cheat-sheet, so they stay short.
check("sections are the five tabs, in order",
      titles == ["Global", "Note", "Text & lists", "Code", "Windows"])
check("every title is short enough for a tab", all(len(t) <= 14 for t in titles))

rows = [r for _, rr in secs for r in rr]
labels = [r["label"] for r in rows]
check("Duplicate row present", "Duplicate" in labels)
check("Search row present", any("Search" in l for l in labels))
check("Move note row present (was Nudge)", "Move note" in labels)
check("Move note carries the click-header hint",
      any(r.get("hint") for r in rows if r["label"] == "Move note"))
check("checklist row reworded (not 'Move line')",
      any("checklist" in l.lower() for l in labels) and "Move line up / down" not in labels)
check("every row has keys list", all(isinstance(r["keys"], list) and r["keys"] for r in rows))
check("every row has bool new", all(isinstance(r["new"], bool) for r in rows))
new_labels = [r["label"] for r in rows if r["new"]]
check("Duplicate flagged new", "Duplicate" in new_labels)
check("Bold row NOT new", not any(r["new"] for r in rows if r["label"].startswith("Bold")))

# ── the cheat-sheet must document every key the app actually binds ────────────
# The window renders sections() and nothing else (app.show_shortcuts), so a
# shortcut missing here is a shortcut the user can never discover.
def keys_for(label_part, secs):
    for _, rr in secs:
        for r in rr:
            if label_part.lower() in r["label"].lower():
                return " ".join(r["keys"])
    return None

check("Rename documented (F2)", keys_for("Rename", secs) == "F2")
check("Pin documented (Ctrl+P)", keys_for("top", secs) == "Ctrl P")
check("Lock documented (Ctrl+L)", keys_for("Lock", secs) == "Ctrl L")
check("Font size documented (Ctrl+= / Ctrl+-)",
      keys_for("Font size", secs) == "Ctrl = / -")
check("Code block documented (Ctrl+Shift+M)",
      keys_for("Code block", secs) == "Ctrl Shift M")
check("F1 documented (opens this very window)", keys_for("Keyboard shortcuts", secs) == "F1")
check("Ctrl+Shift+V documented (paste as plain text)",
      keys_for("plain text", secs) == "Ctrl Shift V")
check("Tab documented (indent checklist item)", keys_for("Indent", secs) == "Tab")
check("Shift+Tab documented (outdent checklist item)",
      keys_for("Outdent", secs) == "Shift Tab")

# ── the Code tab is always listed ────────────────────────────────────────────
# It costs nothing in its own tab, so it is shown whether or not the setting is
# on — a section note carries the caveat instead of the rows disappearing.
check("Ctrl+M documented", keys_for("Inline code", secs) == "Ctrl M")
check("Ctrl+Enter documented", keys_for("Exit code block", secs) == "Ctrl Enter")
check("sections() takes no arguments any more",
      shortcuts.sections() == shortcuts.sections())

# ── section notes ────────────────────────────────────────────────────────────
notes = shortcuts.SECTION_NOTES
check("the Code tab warns it needs the setting",
      "Enable code blocks" in notes.get("Code", ""))
check("the Global tab keeps its Settings note", "Settings" in notes.get("Global", ""))
check("every section note names a real section",
      all(k in titles for k in notes))

print(f"\n{len(fails)} FAIL" if fails else "\nALL PASS")
sys.exit(1 if fails else 0)
