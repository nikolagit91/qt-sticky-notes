"""Single source of truth for keyboard shortcuts.

Holds the QKeySequence strings the note wires up (DUPLICATE/EXPORT/TRASH) and
produces the catalog the cheat-sheet renders via sections(). Kept free of Qt and
PyGObject imports in its data layer so it is trivially testable; global-shortcut
labels are resolved lazily from hotkey.py at call time so a rebind made in GNOME
Settings stays reflected in the cheat-sheet."""

DUPLICATE = "Ctrl+D"
EXPORT    = "Ctrl+E"
TRASH     = "Ctrl+W"


# Caveats shown once under a section's rows, keyed by section title. Kept beside
# the catalog so the dialog stays a dumb renderer of this module.
SECTION_NOTES = {
    "Global": "Turn these on or off in Settings.",
    "Note":   "These act on the note you are using right now.",
    "Code":   "These only do anything while \"Enable code blocks\" is on "
              "(Settings → Note).",
}


def sections():
    """Return the cheat-sheet as [(section_title, [row, ...]), ...].

    Each row is {"label": str, "keys": [token, ...], "new": bool}. Global rows
    pull their live accelerator from hotkey.py (falling back to the default
    binding when the shortcut is not registered).

    Section titles double as the cheat-sheet's TAB LABELS, so they are kept
    short; a longer caveat belongs in SECTION_NOTES. Adding a section here adds
    a tab there, with no change to the dialog."""
    from . import hotkey

    def gk(hk):
        _, binding = hotkey.get_state(hk)
        label = hotkey.accel_to_label(binding or hk.default_binding)
        return label.split("+")

    return [
        ("Global", [
            {"label": "New note",                "keys": gk(hotkey.NEW_NOTE),      "new": False},
            {"label": "New note from clipboard", "keys": gk(hotkey.NEW_NOTE_CLIP), "new": False},
            {"label": "Search notes",            "keys": gk(hotkey.SEARCH),        "new": False},
        ]),
        ("Note", [
            {"label": "Rename",        "keys": ["F2"],                  "new": True},
            {"label": "Always on top", "keys": ["Ctrl", "P"],           "new": True},
            {"label": "Lock / unlock", "keys": ["Ctrl", "L"],           "new": True},
            {"label": "Duplicate",     "keys": ["Ctrl", "D"],           "new": True},
            {"label": "Export…",       "keys": ["Ctrl", "E"],           "new": True},
            {"label": "Move to trash", "keys": ["Ctrl", "W"],           "new": True},
            {"label": "Move note",     "keys": ["↑ ↓ ← →"],             "new": False,
                                       "hint": "Click the note's header first"},
        ]),
        # Text formatting lives here (not on the Note tab) so each tab stays a
        # readable length, and because Bold/size ARE text — not note commands.
        ("Text & lists", [
            {"label": "Bold / Italic / Underline / Strikethrough",
                                       "keys": ["Ctrl", "B / I / U / S"], "new": False},
            {"label": "Font size",     "keys": ["Ctrl", "= / -"],       "new": True},
            {"label": "Move checklist item ↑ / ↓", "keys": ["Alt", "↑ / ↓"], "new": False},
            {"label": "Indent checklist item",     "keys": ["Tab"],          "new": True,
                                                   "hint": "Makes it a sub-item of the one above"},
            {"label": "Outdent checklist item",    "keys": ["Shift", "Tab"], "new": True},
            {"label": "Paste as plain text",       "keys": ["Ctrl", "Shift", "V"], "new": True,
                                                   "hint": "Plain Ctrl+V keeps the source formatting"},
        ]),
        ("Code", [
            {"label": "Code block",      "keys": ["Ctrl", "Shift", "M"], "new": True},
            {"label": "Inline code",     "keys": ["Ctrl", "M"],     "new": True},
            {"label": "Exit code block", "keys": ["Ctrl", "Enter"], "new": True,
                                         "hint": "Starts a plain line below; plain Enter stays in the block"},
        ]),
        ("Windows", [
            {"label": "Keyboard shortcuts (this window)", "keys": ["F1"], "new": True},
            {"label": "Close dialog / manager", "keys": ["Esc"], "new": False},
        ]),
    ]
