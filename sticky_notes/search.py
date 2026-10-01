"""Shared note-search helpers used by both the Notes Manager and the global
quick-search palette, so matching behaves identically in both places.

Kept deliberately small and dependency-light (only QTextDocument, to render a
stored note's HTML to plain text) so the matching logic lives in exactly one
place rather than being duplicated and drifting apart.
"""

from PyQt6.QtGui import QTextDocument


def note_search_text(data: dict, note) -> str:
    """Full, lowercased text to match a note against: an open note's live body,
    or a stored/trashed note's HTML rendered to plain text, plus its custom
    title (so a rename that isn't in the body is still findable)."""
    if note is not None:
        body = note.text_edit.toPlainText()
    else:
        doc = QTextDocument()
        doc.setHtml(data.get("content", ""))
        body = doc.toPlainText()
    return (body + " " + data.get("title", "")).lower()


def make_snippet(plain: str, query: str, radius: int = 40) -> str:
    """A short one-line excerpt of `plain` centred on the first occurrence of
    `query`, with ellipses where text is cut. Falls back to the start of the
    text when there is no query or no match. Whitespace/newlines are collapsed
    so the excerpt stays on one line in the results list."""
    flat = " ".join(plain.split())
    if not flat:
        return ""
    i = flat.lower().find(query.lower()) if query else -1
    if i < 0:
        head = flat[: radius * 2]
        return head + ("…" if len(flat) > radius * 2 else "")
    start = max(0, i - radius)
    end   = min(len(flat), i + len(query) + radius)
    snippet = flat[start:end]
    if start > 0:
        snippet = "…" + snippet
    if end < len(flat):
        snippet = snippet + "…"
    return snippet


def find_live_matches(query: str, notes):
    """Return matching live notes as a list of ``(note, title, snippet)``.

    `notes` is the app's ``id -> StickyNote`` dict. An empty query returns every
    note (dict order). Notes whose *title* matches are placed before notes that
    match only in the body, so the most relevant results surface first.
    """
    q = query.strip().lower()
    title_hits, body_hits = [], []
    for note in notes.values():
        try:
            body  = note.text_edit.toPlainText()
            title = note.display_title()
            custom = note._title if hasattr(note, "_title") else ""
        except Exception:
            continue
        hay = (body + " " + (custom or "")).lower()
        title_match = bool(q) and q in title.lower()
        if q and q not in hay and not title_match:
            continue
        entry = (note, title, make_snippet(body, query))
        (title_hits if title_match else body_hits).append(entry)
    return title_hits + body_hits
