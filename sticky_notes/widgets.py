"""Reusable note sub-widgets: the text editor and the draggable header."""

import os
import re
import subprocess
import time

from PyQt6.QtWidgets import QTextEdit, QFrame, QWidget, QApplication, QPushButton
from PyQt6.QtCore import Qt, QUrl, QPoint, QRect, QRectF, QSize, pyqtSignal, QTimer
from PyQt6.QtGui import (
    QTextBlockFormat, QTextCharFormat, QTextFormat, QColor, QDesktopServices,
    QTextCursor, QPainter, QPen, QPixmap, QAction, QKeySequence, QBrush, QIcon,
    QTextListFormat, QFontMetricsF,
)

from .i18n import tr
from .icons import _make_lock_icon, _SVG_COPY, _HAS_SVG
from .theme import LINK_COLORS, link_color

# Matches http(s):// URLs and bare www. URLs in pasted plain text.
_URL_RE = re.compile(r'(https?://[^\s]+|www\.[^\s]+)')
# Light-note link colours (the dark-note variants live in theme.LINK_COLORS and
# are chosen per note by link_color(kind, dark) — see NoteTextEdit.link_dark).
_LINK_COLOR_WEB    = LINK_COLORS["web"][0]      # http/https — familiar blue
_LINK_COLOR_FOLDER = LINK_COLORS["folder"][0]   # local folders — warm amber
_LINK_COLOR_FILE   = LINK_COLORS["file"][0]     # local files — violet
_TRAIL_PUNCT = ').,;:!?]}\'"'

# Inline checklist: the box is a single clickable glyph at the start of a line,
# implemented as an anchor so the existing anchor-click path detects the click.
# Its href is a private sentinel the click handler treats as "toggle" (never
# opened as a URL), and which link-editing ignores so the box otherwise behaves
# like a normal character. Checked items get struck through and dimmed.
CHECK_EMPTY = "\u2610"          # ☐
CHECK_DONE  = "\u2611"          # ☑
CHECK_HREF  = "x-sticky-check"
# List indentation: bullet lists get their offset from the QTextList
# (level × LIST_INDENT_WIDTH), checklists are plain lines nudged in by a base
# left margin. Tuned so the two sit close together instead of "bullet way in,
# checkbox flush at the edge".
LIST_INDENT_WIDTH = 22          # was Qt's default 40 — brings bullets in
CHECK_LEFT_MARGIN = 10          # base inset for checklist lines (was flush at 0)
_CHECK_DONE_COLOR = "#9aa0a6"
_DRAG_LINE_COLOR  = "#2f6fed"   # insertion line during a checklist drag (UI accent)

CODE_FONT_FAMILY = "Monospace"   # code-block glyphs; system resolves it
CODE_BLOCK_RADIUS = 6            # rounded-corner radius of a code block's box (px)
CODE_BLOCK_MARGIN = 9            # text inset (block L/R margin) so glyphs aren't flush with the box
CODE_BLOCK_PAD_Y  = 8            # box grows this far past the code LINE box, top and bottom
CODE_BLOCK_GAP    = 3            # clear space left between the box and the lines outside it
CODE_INLINE_PAD_X = 1            # inline chip extends this far past the glyph INK (not the
                                 # advance box) on each side, so every chip shows the SAME
                                 # padding whatever glyphs sit at its edges (their side
                                 # bearings vary 0–1px)
CODE_INLINE_RADIUS = 4           # rounded-corner radius of an inline-code chip (px)
# Code (block AND inline) is MARKED by a TRANSPARENT background brush (a real
# brush, so the _is_* checks still detect it) instead of a visible fill: Qt paints
# backgrounds as plain rectangles with no corner radius, so the visible box/chip
# is drawn by paintEvent as a rounded rect instead. Transparent, not NoBrush.
_CODE_MARK_BG = QColor(0, 0, 0, 0)


class _DragOverlay(QWidget):
    """Transparent overlay over the editor viewport, shown only while a checklist
    line is being dragged. Paints a semi-transparent 'ghost' of the plucked row
    that follows the cursor, plus a horizontal insertion line marking where the
    row will drop. Mouse-transparent so the editor keeps receiving move/release."""

    def __init__(self, viewport):
        super().__init__(viewport)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        self._ghost = None       # QPixmap of the dragged row
        self._ghost_y = 0        # top Y (viewport coords) to paint the ghost
        self._line_y = None      # insertion line Y, or None to hide
        self._line_color = QColor(_DRAG_LINE_COLOR)
        self._halo_color = QColor(255, 255, 255, 150)
        self.hide()

    def start(self, pixmap: QPixmap, ghost_y: int, line_color: QColor, halo_color: QColor):
        self._ghost = pixmap
        self._ghost_y = ghost_y
        self._line_color = line_color
        self._halo_color = halo_color
        self._line_y = None
        self.setGeometry(self.parentWidget().rect())
        self.show()
        self.raise_()
        self.update()

    def update_drag(self, ghost_y: int, line_y):
        self._ghost_y = ghost_y
        self._line_y = line_y
        self.update()

    def finish(self):
        self._ghost = None
        self._line_y = None
        self.hide()

    def paintEvent(self, event):
        if self._ghost is None and self._line_y is None:
            return
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        if self._ghost is not None:
            gy = int(self._ghost_y)
            w, h = self._ghost.width(), self._ghost.height()
            # soft shadow so the row reads as 'lifted' off the list
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QColor(0, 0, 0, 45))
            p.drawRoundedRect(QRect(5, gy + 3, w, h), 5, 5)
            p.setOpacity(0.8)
            p.drawPixmap(4, gy, self._ghost)
            p.setOpacity(1.0)
        if self._line_y is not None:
            y = int(self._line_y)
            x1, x2 = 12, self.width() - 12
            # A faint opposite-tone halo under the line keeps it legible even on
            # mid-tone backgrounds; the main line is chosen to contrast the note.
            halo = QPen(self._halo_color, 4)
            halo.setCapStyle(Qt.PenCapStyle.RoundCap)
            p.setPen(halo)
            p.drawLine(x1, y, x2, y)
            main = QPen(self._line_color, 2)
            main.setCapStyle(Qt.PenCapStyle.RoundCap)
            p.setPen(main)
            p.drawLine(x1, y, x2, y)
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(self._line_color)
            p.drawEllipse(QRect(6, y - 4, 8, 8))


# Schemes a note may hand to xdg-open. Everything else is refused: pasted web
# HTML can carry any href it likes (javascript:, data:, …) behind innocuous link
# text, and this app has no use for those. Keep the list to what notes actually
# hold — web pages, local files/folders, e-mail addresses.
_SAFE_SCHEMES = ("http://", "https://", "file://", "mailto:")


def _open_url(href: str):
    """Open a URL / file path in the user's default app, detached and with its
    output silenced — so GTK startup chatter from the browser or file manager
    (e.g. the harmless 'atk-bridge' notice) never lands in our terminal. Falls
    back to Qt's opener if xdg-open isn't available.

    Refuses anything outside _SAFE_SCHEMES, and refuses .desktop files: on GNOME
    xdg-open LAUNCHES a desktop entry rather than showing it, so a link pasted
    from a web page could run a program the user never chose. The link text is
    attacker-controlled and can read like anything, which is why the decision
    can't be left to how the link looks."""
    low = href.strip().lower()
    if not low.startswith(_SAFE_SCHEMES):
        print(f"[link] refusing to open unsupported scheme: {href[:60]}")
        return
    if low.split("?")[0].split("#")[0].endswith(".desktop"):
        print(f"[link] refusing to open a desktop entry: {href[:60]}")
        return
    try:
        subprocess.Popen(
            ["xdg-open", href],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
        )
    except Exception:
        QDesktopServices.openUrl(QUrl(href))


class NoteTextEdit(QTextEdit):
    """QTextEdit with bullet-exit on Enter and formatting shortcuts (Ctrl+B/I/U/S)."""

    # Emitted when Enter drops the caret out of a bullet list in place (the caret
    # position is unchanged, so cursorPositionChanged doesn't fire) — lets the
    # toolbar refresh the bullet button instead of leaving it stuck highlighted.
    list_exited = pyqtSignal()

    def __init__(self):
        super().__init__()
        # ClickFocus, not the QTextEdit default (WheelFocus, which carries the
        # TabFocus bit): a note is a passive desktop widget, and TabFocus made Qt
        # auto-focus the editor whenever the WM merely ACTIVATED the note window
        # (at login, or when another app closed) — a blinking caret with no user
        # intent. Click (or an explicit setFocus for a brand-new note) still edits.
        self.setFocusPolicy(Qt.FocusPolicy.ClickFocus)
        # Populated by StickyNote after construction: Qt.Key → callable
        self._fmt_shortcuts = {}
        self._press_pos = None   # left-press start, to tell a click from a drag
        self.checkbox_text_color = "#000000"   # note's text colour; set by StickyNote
        self.code_bg_color = QColor(0, 0, 0, 18)   # note's code-block bg; set by StickyNote
        self.code_fg_color = QColor("#e8e8e8")   # note's code-block text; set by StickyNote
        self.paper_alpha = 255   # note bg opacity (0–255); code box follows it; set by StickyNote
        self.code_revert_family = None   # note's family for un-coding; set by StickyNote
        # One-shot: toggle_code_block sets this when it makes a code block on an
        # empty doc ("click { } then type" flow), so the empty-doc cleanup keeps
        # the block. Cleared as soon as the cleanup sees it — a later delete-all
        # then falls through to a clean plain block. See note._on_text_changed.
        self._pending_empty_code = False
        self.inline_bg_color = QColor(0, 0, 0, 20)   # inline-code char bg; set by StickyNote
        self.code_inline_bg_color = QColor(255, 255, 255, 46)   # inline code inside a code block; set by StickyNote
        self._copy_btn = None       # lazily-created hover "Copy" overlay
        self._copy_flash = None     # single-shot timer that undoes the "copied" flash
        self._copy_region = None    # (first, last) block numbers under the pointer
        self._dbl_ms = 0.0               # last double-click time (for triple-click detection)
        self._dbl_pos = QPoint()
        self._drag_block = None  # block number being drag-reordered (from its box)
        self._dragging = False
        self._drag_span = None   # (first, last) block range dragged (subtree)
        self._drag_overlay = None
        self._ghost_grab_dy = 0  # cursor offset within the grabbed row
        self.note_bg_color = "#fff59d"  # note background; set by StickyNote
        self.link_dark = False          # note has a dark fill → light link colours
        self.setMouseTracking(True)
        self.viewport().setMouseTracking(True)
        # Scrolling would leave the copy button at a stale spot; hide it instead
        # of tracking (it reappears on the next hover over a code block).
        self.verticalScrollBar().valueChanged.connect(self._hide_copy_btn)
        # Keep the typing font glued to the caret's context so monospace never
        # "bleeds" out of a code block (or the note font into one). See
        # _sync_typing_font_to_caret.
        self.cursorPositionChanged.connect(self._sync_typing_font_to_caret)
        # Promote orphaned sub-items (indented lines left with no parent above
        # them) after a deletion — e.g. deleting a parent row, checked or not.
        # Deferred so the document is settled first; guarded so its own reformat
        # (which reports removed == added) never re-triggers it.
        self._promoting = False
        self._reflowing_code = False
        self._prev_block_count = self.document().blockCount()
        self.document().contentsChange.connect(self._on_contents_change)

    def _on_contents_change(self, pos, removed, added):
        # Only a NET text removal can orphan a sub-item; a manual indent reports
        # removed == added (a format reflow), so it won't trip this.
        if removed > added and not self._promoting:
            QTimer.singleShot(0, self._promote_orphans)
        # A line added or removed (block count changed) can move a code region's
        # start/end — re-assert the edge margins so a neighbour never overlaps the
        # box (e.g. Enter then Backspace on the last code line). Deferred + guarded
        # so the margin reflow (which keeps the block count) can't re-trigger it.
        bc = self.document().blockCount()
        if bc != self._prev_block_count and not self._reflowing_code:
            self._prev_block_count = bc
            QTimer.singleShot(0, self._deferred_code_reflow)
        # Code boxes and inline chips are painted wider than the text, so Qt's
        # per-line edit repaint can leave their side/corner pixels stale when an
        # edit shifts or resizes them. A full viewport repaint keeps them correct.
        if not self._reflowing_code:
            self.viewport().update()

    def _deferred_code_reflow(self):
        if self._reflowing_code:
            return
        self._reflowing_code = True
        try:
            self._reflow_code_spacing()
        finally:
            self._reflowing_code = False
        # A code box is painted wider than the text (out to the note edges), so
        # Qt's per-line edit repaint leaves the box's side/corner pixels stale
        # when a region splits or shifts (e.g. Ctrl+Enter mid-block). Force a full
        # viewport repaint so every box redraws in full.
        self.viewport().update()

    def _promote_orphans(self):
        """Shift orphaned checklist sub-items — indented lines with no parent line
        above them (e.g. after their parent was deleted) — left one level, together
        with their own subtrees, until every indented item has a parent. Snapshot
        per pass so sibling orphans move together (a shifted sibling never becomes
        another's parent). Preserves relative nesting; a no-op when there are no
        orphans."""
        if self._promoting:
            return
        doc = self.document()
        self._promoting = True
        cur = QTextCursor(doc)
        cur.beginEditBlock()
        try:
            for _ in range(7):                       # indent is clamped to 0..6
                orphans = [bn for bn in range(doc.blockCount())
                           if (self._check_indent(bn) or 0) > 0
                           and self._parent_of(bn) is None]
                if not orphans:
                    break
                to_shift = set()
                for bn in orphans:
                    to_shift.add(bn)
                    to_shift.update(self._descendants(bn))
                for bn in sorted(to_shift):
                    b = doc.findBlockByNumber(bn)
                    dc = QTextCursor(doc)
                    dc.setPosition(b.position())
                    bf = dc.blockFormat()
                    if bf.indent() > 0:
                        bf.setIndent(bf.indent() - 1)
                        dc.setBlockFormat(bf)
            self._reconcile_checklist()
        finally:
            cur.endEditBlock()
            self._promoting = False

    def keyPressEvent(self, event):
        # Ctrl+Shift+V pastes PLAIN unformatted text; plain Ctrl+V keeps the
        # source formatting (the standard QTextEdit paste). The right-click menu
        # offers both too.
        mods = event.modifiers()
        if (mods & Qt.KeyboardModifier.ControlModifier
                and mods & Qt.KeyboardModifier.ShiftModifier
                and not (mods & Qt.KeyboardModifier.AltModifier)
                and event.key() == Qt.Key.Key_V and not self.isReadOnly()):
            self.paste_as_plain_text()
            return

        # Formatting shortcuts — handled here so the selection is guaranteed
        # intact when the callback fires.
        if event.modifiers() == Qt.KeyboardModifier.ControlModifier:
            cb = self._fmt_shortcuts.get(event.key())
            if cb:
                cb()
                return

        # Checklist editing keys: indent (Tab), reorder (Alt+↑/↓), and whole-row
        # delete on a checked item. Only act on checklist lines / when editable.
        if not self.isReadOnly() and self._handle_checklist_keys(event):
            return

        # Checklist: Enter continues the list (new item) or, on an empty item,
        # removes the box and drops back to a plain line. Handled before the
        # link/bullet logic so a checklist line never falls through to them.
        if (event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter)
                and not (event.modifiers() & Qt.KeyboardModifier.ShiftModifier)):
            if self._handle_checklist_enter():
                return

        # Keep links non-editable: Backspace/Delete remove a whole link, and
        # typing never edits inside or extends one (it lands just after it).
        if self._handle_link_edit(event):
            return

        # Backspace on an EMPTY code line: normally this merges into the line
        # above, but that misbehaves in two cases — on the first line it's a
        # no-op (nothing before it), and above an empty non-code line the code
        # background "lifts" up onto that line instead of vanishing. In both,
        # un-code this line in place instead (a keyboard undo of the { } toggle)
        # so the overlay disappears on the first press. When the line above is
        # itself a code line we DON'T intervene — merging up (removing the blank
        # row, staying code) is the wanted behaviour; likewise a non-empty line
        # above absorbs the merge and drops the code cleanly.
        if (event.key() == Qt.Key.Key_Backspace
                and not self.textCursor().hasSelection()):
            blk = self.textCursor().block()
            if (self._is_code_block(blk) and blk.text() == ""
                    and self.textCursor().positionInBlock() == 0):
                prev = blk.previous()
                if not prev.isValid() or (not self._is_code_block(prev)
                                          and prev.text() == ""):
                    self.toggle_code_block()
                    return

        # Ctrl+Enter exits a code block: drop a fresh PLAIN line AFTER THE WHOLE
        # block (not the current line) and move there. Exiting from a middle line
        # used to split the block in two with a cramped plain line wedged between —
        # confusing; "leave the code block" is the clearer intent.
        if (event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter)
                and (event.modifiers() & Qt.KeyboardModifier.ControlModifier)):
            cursor = self.textCursor()
            if self._is_code_block(cursor.block()):
                revert = self.code_revert_family or self.document().defaultFont().family()
                cf = QTextCharFormat(); cf.setFontFamilies([revert])
                _, last = self.code_region_at(cursor.block())
                cursor.setPosition(self.document().findBlockByNumber(last).position())
                cursor.movePosition(QTextCursor.MoveOperation.EndOfBlock)
                cursor.insertBlock(QTextBlockFormat(), cf)   # plain block, note font
                self.setTextCursor(cursor)
                self._reflow_code_spacing()   # code region now ends here → reserve bottom space
                self.viewport().update()
                return

        if event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            cursor = self.textCursor()
            if self._is_code_block(cursor.block()):
                # Continue the code block: copy its background + monospace so the
                # new line stays code (blank code lines are allowed). Drop any
                # inline-code marker so the new line isn't an inline chip.
                fmt = QTextBlockFormat(cursor.blockFormat())
                cf = QTextCharFormat(cursor.charFormat())
                cf.setBackground(QBrush()); cf.setFontFamilies([CODE_FONT_FAMILY])
                cursor.insertBlock(fmt, cf)
                self.setTextCursor(cursor)
                self._reflow_code_spacing()   # new interior line → drop stray edge margins
                return
            lst = cursor.currentList()
            if lst and cursor.block().text() == "":
                # Empty bullet + Enter → exit list cleanly (no fake event)
                lst.remove(cursor.block())
                block_fmt = cursor.blockFormat()
                block_fmt.setIndent(0)
                cursor.setBlockFormat(block_fmt)
                self.setTextCursor(cursor)
                self.list_exited.emit()   # caret didn't move → refresh toolbar
                return
            if not lst:
                # Not in a list — insert clean block directly so residual list
                # state can never convert a plain Enter into a bullet. Drop any
                # inline-code marker (and its monospace) so the new line is plain.
                block_fmt = QTextBlockFormat()
                block_fmt.setIndent(0)
                cf = QTextCharFormat(cursor.charFormat())
                if self._is_inline_code(cf):
                    revert = self.code_revert_family or self.document().defaultFont().family()
                    cf.setBackground(QBrush()); cf.setFontFamilies([revert])
                cursor.insertBlock(block_fmt, cf)
                self.setTextCursor(cursor)
                return

        # Text typed into a DONE checklist item is struck + dimmed like the rest of
        # the item. Qt derives the typing format from the character left of the
        # caret (the box glyph / its trailing space — not struck), so force it here
        # for printable input; without it, typing into a checked item (especially an
        # empty one just ticked) came in un-struck.
        if (not self.isReadOnly() and event.text() and event.text() >= " "
                and not (mods & (Qt.KeyboardModifier.ControlModifier
                                 | Qt.KeyboardModifier.AltModifier
                                 | Qt.KeyboardModifier.MetaModifier))
                and not self.textCursor().hasSelection()):
            blk = self.textCursor().block()
            if self._is_check_line(blk.text()) and blk.text()[:1] == CHECK_DONE:
                cur2 = self.textCursor()
                fmt = cur2.charFormat()
                fmt.setFontStrikeOut(True)
                fmt.setForeground(QColor(_CHECK_DONE_COLOR))
                cur2.insertText(event.text(), fmt)
                self.setTextCursor(cur2)
                return
        super().keyPressEvent(event)

    # ── Links are atomic / non-editable ─────────────────────────────────────────
    def _href_right(self, pos: int) -> str:
        """href of the character occupying [pos, pos+1) (i.e. to the right of the
        cursor position), or '' if that character isn't part of a link."""
        doc = self.document()
        if pos < 0 or pos >= doc.characterCount() - 1:
            return ""
        c = QTextCursor(doc)
        c.setPosition(pos)
        c.movePosition(QTextCursor.MoveOperation.NextCharacter,
                       QTextCursor.MoveMode.KeepAnchor)
        f = c.charFormat()
        if f.isAnchor():
            href = f.anchorHref()
            # Treat the checkbox box as a plain char for editing purposes — it is
            # not a link to step out of or delete as a run.
            return "" if href == CHECK_HREF else href
        return ""

    def _link_run(self, pos: int):
        """If the character to the right of pos is a link, return (start, end) of
        the whole contiguous run sharing that href; otherwise None.

        CLAMPED TO THE BLOCK: a link never spans paragraphs, and walking raw
        document positions stepped onto the neighbouring paragraph separator
        (whose char format still carries the href). Deleting such a run removed
        the separator, merging the line into the one above — which destroyed the
        list item and made its bullet disappear. Only a link on the very first
        block was safe, since position 0 can't step back."""
        href = self._href_right(pos)
        if not href:
            return None
        block = self.document().findBlock(pos)
        b_start = block.position()
        b_end = b_start + len(block.text())      # excludes the paragraph separator
        start = pos
        while start > b_start and self._href_right(start - 1) == href:
            start -= 1
        end = min(pos + 1, b_end)
        while end < b_end and self._href_right(end) == href:
            end += 1
        return (start, end)

    def merge_format_preserving_links(self, fmt):
        """Merge `fmt` across the selection but SKIP characters inside a link, so
        a link keeps the two cues that say "this is a link" — its colour and its
        underline. Used for the colour/underline actions only; bold, italic and
        size stay free to apply everywhere. With no selection this is just the
        normal typing-format merge."""
        cur = self.textCursor()
        if not cur.hasSelection():
            self.mergeCurrentCharFormat(fmt)
            return
        doc = self.document()
        start, end = cur.selectionStart(), cur.selectionEnd()
        edit = QTextCursor(doc)
        edit.beginEditBlock()
        pos = start
        while pos < end:
            is_link = bool(self._href_right(pos))
            run_end = pos + 1
            while run_end < end and bool(self._href_right(run_end)) == is_link:
                run_end += 1
            if not is_link:
                seg = QTextCursor(doc)
                seg.setPosition(pos)
                seg.setPosition(run_end, QTextCursor.MoveMode.KeepAnchor)
                seg.mergeCharFormat(fmt)
            pos = run_end
        edit.endEditBlock()

    def _delete_run(self, run):
        start, end = run
        c = self.textCursor()
        c.setPosition(start)
        c.setPosition(end, QTextCursor.MoveMode.KeepAnchor)
        c.removeSelectedText()
        self.setTextCursor(c)

    def _handle_link_edit(self, event) -> bool:
        """Returns True if the event was fully handled (caller should stop)."""
        cursor = self.textCursor()
        if cursor.hasSelection():
            return False   # a selected link is replaced/deleted wholesale — fine
        key = event.key()
        pos = cursor.position()

        if key == Qt.Key.Key_Backspace:
            run = self._link_run(pos - 1)       # link just to the left
            if run:
                self._delete_run(run)
                return True
            return False
        if key == Qt.Key.Key_Delete:
            run = self._link_run(pos)           # link just to the right
            if run:
                self._delete_run(run)
                return True
            return False

        # Inserting keys (a printable char, or Enter): must not land inside a
        # link or extend it.
        inserts = (key in (Qt.Key.Key_Return, Qt.Key.Key_Enter)
                   or (event.text() != "" and event.text().isprintable()
                       and key not in (Qt.Key.Key_Tab, Qt.Key.Key_Backtab)))
        if inserts:
            left = self._href_right(pos - 1)
            right = self._href_right(pos)
            moved = False
            if left and left == right:          # strictly inside → step out to the end
                run = self._link_run(pos)
                if run:
                    cursor.setPosition(run[1])
                    moved = True
            fmt = cursor.charFormat()
            if fmt.isAnchor():                  # never extend a link at its edge
                fmt.setAnchor(False)
                fmt.setAnchorHref("")
                fmt.setFontUnderline(False)
                # Drop the link's colour too, or text typed after a link (and the
                # next line after Enter) comes out in link blue/violet/amber.
                # CLEAR rather than set: the text then falls back to the note's
                # default ink, which follows auto-contrast.
                fmt.clearForeground()
                cursor.setCharFormat(fmt)
                moved = True
            if moved:
                self.setTextCursor(cursor)
        return False   # let the default handler do the actual insertion

    # ── Paste / links ──────────────────────────────────────────────────────────
    def canInsertFromMimeData(self, source):
        if source.hasUrls():
            return True
        return super().canInsertFromMimeData(source)

    def _insert_code_text(self, cursor, text):
        """Paste plain text into a code block keeping EVERY resulting line code.
        Each new line gets the SAME block contract toggle_code_block makes: the
        TRANSPARENT marker background (so paintEvent draws the rounded box — an
        opaque background makes Qt fill a square edge-to-edge rectangle over it),
        the L/R text-inset margins, and the light code foreground. The normal
        paste path resets the char format and gives newline-split blocks a default
        block format, which drops the pasted lines out of the code block."""
        cf = QTextCharFormat()
        cf.setFontFamilies([CODE_FONT_FAMILY])
        cf.setForeground(self.code_fg_color)
        bf = QTextBlockFormat()
        bf.setBackground(_CODE_MARK_BG)          # transparent marker; box drawn in paintEvent
        bf.setLeftMargin(CODE_BLOCK_MARGIN)      # inset text off the box edges
        bf.setRightMargin(CODE_BLOCK_MARGIN)
        lines = text.replace("\r\n", "\n").replace("\r", "\n").split("\n")
        cursor.beginEditBlock()
        for i, line in enumerate(lines):
            if i:
                cursor.insertBlock(bf, cf)   # each further line is its own code block
            cursor.insertText(line, cf)
        cursor.endEditBlock()
        self._reflow_code_spacing()          # region grew → fix top/bottom edge spacing
        self.viewport().update()             # repaint the box in full

    def insertFromMimeData(self, source):
        cursor = self.textCursor()

        # Paste inside a code block → keep it all code (plain, monospace, on the
        # code background). Must run before the link/url/rich handling below, which
        # would otherwise strip the code format off the pasted lines.
        if source.hasText() and self._is_code_block(
                self.document().findBlock(cursor.selectionStart())):
            self._insert_code_text(cursor, source.text())
            self.setTextCursor(cursor)
            return

        # Paste inside an inline-code span → keep the pasted text inline (mono +
        # char background), mirroring the code-block case and matching how typing
        # continues inline. Without this the plain-text path inserts it "clean"
        # and splits the span with unformatted text.
        if source.hasText() and self._is_inline_code(cursor.charFormat()):
            f = QTextCharFormat()
            f.setFontFamilies([CODE_FONT_FAMILY])
            f.setBackground(self.inline_bg_color)
            cursor.insertText(source.text(), f)   # replaces any selection
            self.setTextCursor(cursor)
            return

        # Never paste inside a link — step out to its end first.
        if not cursor.hasSelection():
            pos = cursor.position()
            left = self._href_right(pos - 1)
            if left and left == self._href_right(pos):
                run = self._link_run(pos)
                if run:
                    cursor.setPosition(run[1])
                    self.setTextCursor(cursor)

        base_fmt = cursor.charFormat()
        if base_fmt.isAnchor():     # don't let inserted text inherit a link
            base_fmt = QTextCharFormat(base_fmt)
            base_fmt.setAnchor(False)
            base_fmt.setAnchorHref("")
            base_fmt.setFontUnderline(False)

        # 1) Files/folders or URLs copied from the file manager / browser
        if source.hasUrls() and source.urls():
            first = True
            for url in source.urls():
                if not first:
                    cursor.insertText("\n", base_fmt)
                first = False
                if url.isLocalFile():
                    path = url.toLocalFile()
                    name = os.path.basename(path.rstrip("/")) or path
                    kind = "folder" if os.path.isdir(path) else "file"
                    self._insert_link(cursor, name, url.toString(), base_fmt, kind)
                else:
                    self._insert_link(cursor, url.toString(), url.toString(), base_fmt, "web")
            self.setTextCursor(cursor)
            return

        # 2) Plain text — no formatting in the source, so insert it CLEAN (the
        # note's default body style) instead of inheriting the cursor's current
        # emphasis. Sitting next to a bold/large word makes the cursor's format
        # bold/large, and that used to leak into the pasted text. URLs still
        # become links. (Ctrl+Shift+V routes here too, via paste_as_plain_text.)
        if source.hasText() and not source.hasHtml():
            self._insert_text_linkified(cursor, source.text(), QTextCharFormat())
            self.setTextCursor(cursor)
            return

        # 3) Rich text / HTML / anything else — keep its own formatting, then
        # NORMALIZE it. Reset the insertion format first so the cursor's current
        # emphasis (a bold/large run it sat in) doesn't leak into pasted runs that
        # don't set that property. After inserting, convert any PIXEL font sizes
        # to points: web HTML is pixel-sized, and pixel sizes ignore later
        # point-size changes and read as 0pt in the size box — the root of the
        # "resize does nothing / only some rows react" bugs. Normalizing on entry
        # keeps the whole note point-based so everything downstream just works.
        # Colours, bold, families and the visual size are all preserved.
        self.setCurrentCharFormat(QTextCharFormat())
        cur = self.textCursor()
        start = cur.selectionStart() if cur.hasSelection() else cur.position()
        # Qt's HTML insert carries its OWN block format, which REPLACES the
        # current one — pasting a browser-copied link into a bullet line knocked
        # that line out of its QTextList, so the bullet vanished at paste time.
        # Remember the host line's list + block format and put the pasted blocks
        # back into it. (The hasUrls and plain-text paths never had this problem;
        # outside a list host_list is None and nothing is forced.)
        host_block = self.document().findBlock(start)
        host_list = QTextCursor(host_block).currentList()
        # Keep the list FORMAT by value, not the QTextList itself: when the paste
        # knocks out its last item Qt destroys the list object, leaving a dangling
        # reference.
        host_list_fmt = QTextListFormat(host_list.format()) if host_list is not None else None
        super().insertFromMimeData(source)
        end = self.textCursor().position()
        if host_list_fmt is not None and QTextCursor(
                self.document().findBlock(start)).currentList() is None:
            c = QTextCursor(self.document())
            c.setPosition(start)
            c.setPosition(end, QTextCursor.MoveMode.KeepAnchor)
            c.createList(host_list_fmt)      # same style/indent as the host line
        self._normalize_pasted_formatting(start, end)

    # Qt renders HTML headings (<h1>..<h6>) at a multiple of the default font via
    # a "heading level", NOT an explicit font size — so pasted headings can't be
    # resized and read as the default size in the toolbar. These are Qt's own
    # heading scales; we bake them into an explicit point size instead.
    _HEADING_SCALE = {1: 2.0, 2: 1.5, 3: 1.17, 4: 1.0, 5: 0.83, 6: 0.67}

    def _normalize_pasted_formatting(self, start: int, end: int):
        """Make pasted rich text behave like the note's own text:
        (1) rewrite PIXEL font sizes as POINT sizes (px*72/96, the CSS reference);
        (2) FLATTEN HTML headings into normal blocks that carry an EXPLICIT point
            size (default * the heading's scale) with their bold kept — so a
            pasted heading stays its size but becomes editable and resizable like
            any other text, and the size box reports it correctly.
        Each run keeps its other formatting (bold, colour, family)."""
        if end <= start:
            return
        doc = self.document()
        base = doc.defaultFont().pointSizeF()
        if base <= 0:
            base = 13.0
        guard = QTextCursor(doc)
        guard.beginEditBlock()
        # 1) per character: pixel size → points, and clear Qt's heading
        #    FontSizeAdjustment. Headings (<h1>..<h6>) carry a RELATIVE size
        #    modifier (+3 for h1, …) that Qt applies when rendering, and it
        #    OVERRIDES the point size — so setFontPointSize() changed the model
        #    but the rendered heading never moved (the "resize does nothing on
        #    headings" bug). Clearing it makes headings resize like normal text.
        pos = start
        while pos < end:
            ch = QTextCursor(doc)
            ch.setPosition(pos)
            ch.setPosition(pos + 1, QTextCursor.MoveMode.KeepAnchor)
            f = ch.charFormat()
            changed = False
            px = f.font().pixelSize()
            if px > 0:
                f.setFontPointSize(round(px * 72.0 / 96.0))
                f.clearProperty(QTextFormat.Property.FontPixelSize)
                changed = True
            if f.hasProperty(QTextFormat.Property.FontSizeAdjustment):
                f.clearProperty(QTextFormat.Property.FontSizeAdjustment)
                changed = True
            # Pasted links arrive in the SOURCE's colour (Qt's default #0000ff,
            # or whatever the page styled them). Normalise them to this app's
            # link colours + underline so links look the same however they got
            # here. The checkbox glyph is an anchor too — leave it alone.
            href = f.anchorHref()
            if f.isAnchor() and href and href != CHECK_HREF:
                want = link_color(self.link_kind(href), self.link_dark)
                if f.foreground().color().name() != want or not f.fontUnderline():
                    f.setForeground(QColor(want))
                    f.setFontUnderline(True)
                    changed = True
            if changed:
                ch.setCharFormat(f)
            pos += 1
        # 2) flatten headings → explicit point size, and strip the paragraph
        #    margins that web <p>/<h1> blocks carry (typed text has none). Those
        #    margins are why pasted paragraphs show big vertical gaps, and they
        #    make pasted blocks structurally unlike typed ones — clearing them
        #    keeps pasted text consistent with the rest of the note.
        _MARGINS = (QTextFormat.Property.BlockTopMargin,
                    QTextFormat.Property.BlockBottomMargin)
        b = doc.findBlock(start)
        while b.isValid() and b.position() < end:
            bf = b.blockFormat()
            level = bf.headingLevel()
            if level > 0:
                size = max(8, round(base * self._HEADING_SCALE.get(level, 1.0)))
                sel = QTextCursor(b)
                sel.movePosition(QTextCursor.MoveOperation.StartOfBlock)
                sel.movePosition(QTextCursor.MoveOperation.EndOfBlock,
                                 QTextCursor.MoveMode.KeepAnchor)
                cf = QTextCharFormat()
                cf.setFontPointSize(size)
                sel.mergeCharFormat(cf)          # add explicit size, keep bold etc.
                bf.setHeadingLevel(0)            # no longer a heading → normal block
            for prop in _MARGINS:
                bf.clearProperty(prop)
            QTextCursor(b).setBlockFormat(bf)
            b = b.next()
        guard.endEditBlock()

    @staticmethod
    def link_kind(href: str) -> str:
        """Classify a link so it gets the right colour: a local folder, a local
        file, or a web address."""
        if href.startswith("file:"):
            path = QUrl(href).toLocalFile()
            return "folder" if os.path.isdir(path) else "file"
        return "web"

    def _insert_link(self, cursor, text, href, base_fmt, kind=None):
        fmt = QTextCharFormat(base_fmt)
        fmt.setAnchor(True)
        fmt.setAnchorHref(href)
        fmt.setForeground(QColor(link_color(kind or self.link_kind(href), self.link_dark)))
        fmt.setFontUnderline(True)
        cursor.insertText(text, fmt)
        cursor.setCharFormat(base_fmt)   # don't let the link format bleed into later text

    # Every colour a link has ever been given by this app, plus Qt's own HTML
    # default — used to recognise a link colour stranded on a BLOCK char format.
    _LINK_COLOR_SET = frozenset(
        [c.lower() for pair in LINK_COLORS.values() for c in pair] + ["#0000ff"])

    def recolor_links(self):
        """Re-apply link colours for the note's current ink (light vs dark fill).
        Fixed colours were unreadable on dark notes — violet measured 1.72:1 on
        charcoal. The checkbox glyph is an anchor too, so it is skipped.

        Also scrubs a link colour off the BLOCK char format: Qt paints a list
        item's bullet with that format, so a colour stranded there (old notes
        carry Qt's #0000ff) drew a blue bullet. Only recognised link colours are
        cleared, so a colour the user chose themselves is left alone."""
        doc = self.document()
        edit = QTextCursor(doc)
        edit.beginEditBlock()
        b = doc.begin()
        while b.isValid():
            bcf = b.charFormat()
            if bcf.foreground().style() != Qt.BrushStyle.NoBrush and \
                    bcf.foreground().color().name().lower() in self._LINK_COLOR_SET:
                clean = QTextCharFormat(bcf)
                clean.setForeground(QColor(self.checkbox_text_color))
                clean.setAnchor(False)
                clean.setAnchorHref("")
                clean.setFontUnderline(False)
                QTextCursor(b).setBlockCharFormat(clean)
            start = b.position()
            for i in range(b.length() - 1):     # exclude the block separator
                c = QTextCursor(doc)
                c.setPosition(start + i)
                c.setPosition(start + i + 1, QTextCursor.MoveMode.KeepAnchor)
                f = c.charFormat()
                href = f.anchorHref()
                if not f.isAnchor() or not href or href == CHECK_HREF:
                    continue
                want = link_color(self.link_kind(href), self.link_dark)
                if f.foreground().color().name() != want:
                    nf = QTextCharFormat()
                    nf.setForeground(QColor(want))
                    c.mergeCharFormat(nf)
            b = b.next()
        edit.endEditBlock()

    def _insert_text_linkified(self, cursor, text, base_fmt):
        last = 0
        for m in _URL_RE.finditer(text):
            if m.start() > last:
                cursor.insertText(text[last:m.start()], base_fmt)
            url = m.group(0)
            trail = ""
            while url and url[-1] in _TRAIL_PUNCT:
                trail = url[-1] + trail
                url = url[:-1]
            href = url if "://" in url else "http://" + url
            self._insert_link(cursor, url, href, base_fmt)
            if trail:
                cursor.insertText(trail, base_fmt)
            last = m.end()
        if last < len(text):
            cursor.insertText(text[last:], base_fmt)

    def paste_as_plain_text(self):
        """Insert the clipboard's TEXT only, as clean unformatted text. Crucially
        it does NOT inherit the cursor's current character format (bold / large
        size / colour) — inheriting it is exactly what made a plain paste next to
        a bold or large run come out bold and huge. The text takes the note's
        default body style; URLs are still turned into clickable links."""
        src = QApplication.clipboard().mimeData()
        if src is None or not src.hasText():
            return
        cursor = self.textCursor()
        # In a code block, keep the paste all-code (same as the rich paste path).
        if self._is_code_block(self.document().findBlock(cursor.selectionStart())):
            self._insert_code_text(cursor, src.text())
            self.setTextCursor(cursor)
            return
        # If the cursor sits inside a link, step out to its end first (same guard
        # as insertFromMimeData) so a link isn't split.
        if not cursor.hasSelection():
            pos = cursor.position()
            left = self._href_right(pos - 1)
            if left and left == self._href_right(pos):
                run = self._link_run(pos)
                if run:
                    cursor.setPosition(run[1])
        # A default (empty) char format → the inserted text renders in the note's
        # default body font, not whatever emphasis the cursor was carrying.
        self._insert_text_linkified(cursor, src.text(), QTextCharFormat())
        self.setTextCursor(cursor)

    def contextMenuEvent(self, event):
        # Standard right-click menu (Undo/Cut/Copy/Paste/…) plus our own
        # "Paste as plain text" right after the normal Paste, so the user can
        # pick formatted paste (the default) or clean unformatted text per paste.
        menu = self.createStandardContextMenu()
        if not self.isReadOnly():
            plain = QAction(tr("Paste as plain text"), menu)
            cb = QApplication.clipboard().mimeData()
            plain.setEnabled(bool(cb) and cb.hasText())
            plain.triggered.connect(self.paste_as_plain_text)
            # Show shortcut hints that match the keys (Ctrl+V = plain, Ctrl+Shift+V
            # = formatted). These are display-only here — the menu is transient, so
            # the actual keys are handled in keyPressEvent, not by these actions.
            plain.setShortcut(QKeySequence("Ctrl+Shift+V"))
            acts = menu.actions()

            def _is_paste(a):
                return (a.objectName() == "edit-paste"
                        or a.shortcut() == QKeySequence(QKeySequence.StandardKey.Paste))

            idx = next((i for i, a in enumerate(acts) if _is_paste(a)), None)
            if idx is not None and idx + 1 < len(acts):
                menu.insertAction(acts[idx + 1], plain)   # just after standard Paste
            else:
                menu.addAction(plain)
        menu.exec(event.globalPos())
        menu.deleteLater()

    def _anchor_at_event(self, event):
        return self.anchorAt(event.position().toPoint())

    def _text_start(self, block) -> int:
        """Position where a line's editable TEXT begins — past the "☐ " marker on
        a checklist line. The box is a real character, so without this it lands in
        selections and gets restyled with the text (a monospaced box renders
        smaller). Treat it like a list marker: never part of the text."""
        t = block.text()
        if self._is_check_line(t):
            return block.position() + (2 if t[1:2] == " " else 1)
        return block.position()

    def select_block_text(self, block):
        """Select a paragraph's TEXT only, excluding the trailing paragraph
        separator (so the caret stays on that line) and any checklist marker. Qt's
        own triple-click selects the block WITH its newline, which drops the caret
        onto the next line and makes per-line actions (code block, checklist)
        spill onto it."""
        c = self.textCursor()
        c.setPosition(self._text_start(block))
        c.setPosition(block.position() + max(0, block.length() - 1),
                      QTextCursor.MoveMode.KeepAnchor)
        self.setTextCursor(c)

    def mouseDoubleClickEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._dbl_ms = time.monotonic() * 1000.0
            self._dbl_pos = event.position().toPoint()
        super().mouseDoubleClickEvent(event)

    def mousePressEvent(self, event):
        # Remember where a left press began so the release can tell a click from
        # a drag — links open / boxes toggle only on a clean click. A press that
        # lands on a checkbox also primes a possible drag-reorder of that line.
        left = (event.button() == Qt.MouseButton.LeftButton)
        # Triple-click (a left press right after a double-click, same spot) → select
        # just the line's text, so the caret stays put and per-line toggles don't
        # reach the line below. Handled globally here, not per feature.
        if (left and not self.isReadOnly()
                and (time.monotonic() * 1000.0 - self._dbl_ms) <= QApplication.doubleClickInterval()
                and (event.position().toPoint() - self._dbl_pos).manhattanLength() <= 4):
            self._dbl_ms = 0.0
            self._press_pos = None
            self._drag_block = None
            self._dragging = False
            self.select_block_text(self.cursorForPosition(event.position().toPoint()).block())
            return
        self._press_pos = event.position().toPoint() if left else None
        self._drag_block = None
        self._dragging = False
        if left and not self.isReadOnly():
            pt = event.position().toPoint()
            if self.anchorAt(pt) == CHECK_HREF:
                self._drag_block = self.cursorForPosition(pt).block().blockNumber()
        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event):
        was_drag = self._dragging
        src = self._drag_block
        super().mouseReleaseEvent(event)
        if was_drag and src is not None and event.button() == Qt.MouseButton.LeftButton:
            a, b = self._drag_span if self._drag_span is not None else (src, src)
            ins, _ = self._drop_boundary(event.position().toPoint().y())
            if self._drag_overlay is not None:
                self._drag_overlay.finish()
            self.viewport().setCursor(Qt.CursorShape.IBeamCursor)
            self._reset_drag()
            self.move_range(a, b, ins, keep_cursor=True)   # whole subtree as a unit
            return
        if (event.button() == Qt.MouseButton.LeftButton
                and self._press_pos is not None
                and not self.textCursor().hasSelection()):
            pos = event.position().toPoint()
            if (pos - self._press_pos).manhattanLength() <= 4:
                href = self.anchorAt(pos)
                if href == CHECK_HREF:
                    block = self.cursorForPosition(pos).block()
                    self.toggle_checkbox(block.position())
                elif href:
                    _open_url(href)
        self._reset_drag()

    def mouseMoveEvent(self, event):
        if self._drag_block is None:      # not dragging a checklist row
            self._update_copy_btn(event.position().toPoint())
        # Drag-reorder: once a press that started on a box moves far enough, take
        # over as a line drag (suppressing text selection) until release, showing
        # the ghost row + insertion line.
        if self._drag_block is not None and (event.buttons() & Qt.MouseButton.LeftButton):
            y = event.position().toPoint().y()
            if (not self._dragging and self._press_pos is not None
                    and (event.position().toPoint() - self._press_pos).manhattanLength() > 6):
                self._dragging = True
                self.viewport().setCursor(Qt.CursorShape.ClosedHandCursor)
                self._begin_drag_visual()
            if self._dragging:
                self._update_drag_visual(y)
                return
        # Otherwise show the hand cursor over a link/box so it reads as clickable.
        # Measured on real GNOME (temporary instrumentation, since removed): this
        # handler costs ~0.1ms and the shape flips in the same move event the
        # pointer enters the link — nothing overrides it, so no throttling or
        # reordering is warranted here.
        href = self._anchor_at_event(event)
        on_link = bool(href)
        self.viewport().setCursor(
            Qt.CursorShape.PointingHandCursor if on_link else Qt.CursorShape.IBeamCursor)
        # Show where the link actually GOES. A link pasted from a web page can
        # carry any href behind any text ("banka.hr" pointing elsewhere), and
        # nothing in the note revealed the real destination before the click.
        # The checkbox glyph is an anchor too — it is not a link, so no tooltip.
        self.viewport().setToolTip(href if on_link and href != CHECK_HREF else "")
        super().mouseMoveEvent(event)

    def leaveEvent(self, event):
        if self._copy_btn is not None:
            self._copy_btn.hide()
        self._copy_region = None
        super().leaveEvent(event)

    # ── Copy-code-block hover overlay ───────────────────────────────────────────
    @staticmethod
    def _copy_icon():
        return _make_lock_icon(_SVG_COPY, 15, fill="#ffffff") if _HAS_SVG else QIcon()

    def _ensure_copy_btn(self):
        if self._copy_btn is None:
            b = QPushButton(self.viewport())
            b.setToolTip(tr("Copy"))
            b.setCursor(Qt.CursorShape.PointingHandCursor)
            # Fixed size so the box doesn't change width between the icon and the
            # "✓" flash — otherwise a reposition on the next mouse move made the
            # button jump sideways over the code overlay.
            b.setFixedSize(26, 22)
            b.setStyleSheet(
                "QPushButton { background: rgba(0,0,0,0.55); color: #fff; border: none;"
                " border-radius: 4px; font-size: 12px; }"
                "QPushButton:hover { background: rgba(0,0,0,0.72); }")
            if _HAS_SVG:
                b.setIcon(self._copy_icon()); b.setIconSize(QSize(15, 15))
            else:
                b.setText(tr("Copy"))
            b.clicked.connect(self._copy_current_region)
            b.hide()
            self._copy_btn = b
            # PARENTED TO THE BUTTON on purpose. An unparented
            # QTimer.singleShot(1000, …) kept firing after the note was gone
            # (copy a code block, then Ctrl+W within the second) and blew up on
            # the deleted QPushButton. As a child of the button this timer is
            # destroyed with it, so the restore can never outlive its target.
            # One reused timer, not one per click — repeated copies would
            # otherwise pile up child timers on the button.
            self._copy_flash = QTimer(b)
            self._copy_flash.setSingleShot(True)
            self._copy_flash.timeout.connect(self._restore_copy_btn)
        return self._copy_btn

    def _restore_copy_btn(self):
        """Undo the brief "copied" flash — put the copy icon back."""
        self._copy_btn.setText("")
        if _HAS_SVG:
            self._copy_btn.setIcon(self._copy_icon())

    def _update_copy_btn(self, viewport_pos):
        """Show + position the copy button when the pointer is over a code block."""
        blk = self.cursorForPosition(viewport_pos).block()
        scroll = self.verticalScrollBar().value()
        layout = self.document().documentLayout()
        # cursorForPosition clamps to the last block for anything below the text,
        # so ignore hovers that fall below the block's actual bottom (e.g. empty
        # space under the last line when that line is code).
        below = viewport_pos.y() > int(layout.blockBoundingRect(blk).bottom()) - scroll
        if below or not (self._is_code_block(blk) and not self.isReadOnly()):
            if self._copy_btn is not None:
                self._copy_btn.hide()
            self._copy_region = None
            return
        self._copy_region = self.code_region_at(blk)
        btn = self._ensure_copy_btn()
        box = self._code_region_rect(*self._copy_region)   # same rect the box is painted at
        x = int(box.right()) - btn.width() - 6             # inside the box, top-right
        top = int(box.top()) + 4
        btn.move(max(0, x), max(0, top))
        btn.show(); btn.raise_()

    def _hide_copy_btn(self, *args):
        """Hide the copy button (on scroll or when leaving) rather than tracking
        it — it reappears when the pointer next moves over a code block."""
        if self._copy_btn is not None:
            self._copy_btn.hide()
        self._copy_region = None

    def _copy_current_region(self):
        if self._copy_region is None:
            return
        QApplication.clipboard().setText(self.code_region_text(*self._copy_region))
        btn = self._ensure_copy_btn()
        btn.setIcon(QIcon()); btn.setText("✓")     # brief "copied" flash
        self._copy_flash.start(1000)

    # ── Rounded code-block box ───────────────────────────────────────────────────
    def paintEvent(self, event):
        """Draw each code block's box as a ROUNDED rect behind the text, then let
        the base class paint the (transparent-backed) text on top. Qt paints block
        backgrounds as plain rectangles, so the visible box is drawn here instead;
        the block keeps a transparent background purely as the code marker."""
        self._paint_code_boxes()
        super().paintEvent(event)

    def _code_region_rect(self, first, last):
        """Viewport-coordinate rect of the code box for blocks [first..last].
        Computed from cursorRect (which already accounts for the QSS padding and
        scroll) so it maps correctly on both sides — a document-coordinate rect
        was off by the padding on the right. Symmetric about the text column, so
        the box has equal left/right breathing room from the note edges; the
        block's own L/R margins inset the text inside it."""
        doc = self.document()
        c1 = QTextCursor(doc.findBlockByNumber(first))          # start of first line
        c2 = QTextCursor(doc.findBlockByNumber(last))
        c2.movePosition(QTextCursor.MoveOperation.EndOfBlock)   # end of last line
        r1 = self.cursorRect(c1)
        r2 = self.cursorRect(c2)
        inset = r1.left() - CODE_BLOCK_MARGIN                   # text col left → box left
        # Hug the code LINE box (which sits tight around the glyphs — leading is
        # ~0.1px) with equal padding top and bottom. Because the code line is
        # centred between its neighbours (equal reserved margins), equal padding
        # here makes the OUTER gaps to the lines above/below equal too, and an
        # empty line's caret is padded evenly. Integer edges → no sub-pixel drift.
        # Never overhang above the viewport top: a first-row region sits at the
        # document margin (4px) and Qt IGNORES a first block's top margin, so the
        # PAD_Y overhang would clip the rounded top into square corners. Clamp to 0
        # so the arc always draws (costs a few px of top padding for that one case).
        top = max(round(r1.top()) - CODE_BLOCK_PAD_Y, 0)
        bottom = round(r2.bottom()) + CODE_BLOCK_PAD_Y
        return QRectF(inset, top,
                      self.viewport().width() - 2 * inset, bottom - top)

    def _paint_code_boxes(self):
        doc = self.document()
        painter = QPainter(self.viewport())
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(Qt.PenStyle.NoPen)
        # Follow the note's background opacity so the box is as see-through as the
        # paper (not an opaque rectangle floating on a translucent note).
        fill = QColor(self.code_bg_color); fill.setAlpha(self.paper_alpha)
        painter.setBrush(fill)
        b = doc.begin()
        while b.isValid():
            if self._is_code_block(b):
                first, last = self.code_region_at(b)
                painter.drawRoundedRect(self._code_region_rect(first, last),
                                        CODE_BLOCK_RADIUS, CODE_BLOCK_RADIUS)
                b = doc.findBlockByNumber(last).next()
                continue
            b = b.next()
        # Inline-code chips: rounded, padded, same opacity scaling. Painted after
        # the boxes so a chip INSIDE a code block lands on top of its box — and
        # uses a colour derived from that box (code_inline_bg_color): the paper
        # tint vanished on a light note's dark box and lifted a dark note's panel
        # under the light code text.
        def scaled(c):
            c = QColor(c); c.setAlpha(c.alpha() * self.paper_alpha // 255); return c
        on_paper, in_block = scaled(self.inline_bg_color), scaled(self.code_inline_bg_color)
        for rect, in_code in self._inline_runs():
            painter.setBrush(in_block if in_code else on_paper)
            painter.drawRoundedRect(rect, CODE_INLINE_RADIUS, CODE_INLINE_RADIUS)
        painter.end()

    def _inline_run_rects(self):
        """Chip rects only — see _inline_runs."""
        return [rect for rect, _ in self._inline_runs()]

    def _inline_runs(self):
        """(rect, in_code_block) for every inline-code run, one rect per visual
        line the run occupies (a run wraps rarely, but then each line segment gets
        its own chip). Each chip extends exactly CODE_INLINE_PAD_X past the edge
        glyphs' INK, so every chip shows the same padding whatever letters sit at
        its edges.

        Positions come straight from the text layout (QTextLine.cursorToX, which
        is fractional), NOT from cursorRect(): cursorRect returns an INTEGER rect,
        while with slight hinting (GNOME's default) glyphs are drawn at fractional
        x. Building the chip from the truncated caret put its edge 0-1px off the
        real glyph, a different amount per position, so the same letter showed
        ~1px of padding in one chip and none in another. The edges stay fractional
        for the same reason (rounding would reintroduce that error); both the chip
        and the glyphs are antialiased at the same sub-pixel offset."""
        doc = self.document()
        hscroll = self.horizontalScrollBar().value()
        out = []
        b = doc.begin()
        while b.isValid():
            layout = b.layout()
            bstart = b.position()
            lx = layout.position().x() - hscroll        # layout x -> viewport x
            in_code = self._is_code_block(b)
            it = b.begin()
            while not it.atEnd():
                frag = it.fragment()
                if frag.isValid() and self._is_inline_code(frag.charFormat()):
                    s = frag.position()
                    e = s + frag.length()
                    fm = QFontMetricsF(frag.charFormat().font())
                    pos = s
                    while pos < e:
                        ln = layout.lineForTextPosition(pos - bstart)
                        if not ln.isValid():
                            break
                        seg_end = min(e, bstart + ln.textStart() + ln.textLength())
                        if seg_end <= pos:
                            break
                        r1 = self._caret_rect(pos)               # vertical extent only
                        # Both edges ON this visual line: also correct when the run
                        # wraps (cursorRect(seg_end) would jump to the next line).
                        x0 = lx + ln.cursorToX(pos - bstart)[0]
                        x1 = lx + ln.cursorToX(seg_end - bstart)[0]
                        # Ink edges = advance box minus the side bearing. A space has
                        # no ink (Qt reports rightBearing ~ its whole advance), so
                        # using its bearing ended the chip BEFORE a trailing space —
                        # the space typed in inline mode looked un-chipped until the
                        # next letter. Whitespace counts as its full advance box.
                        c0 = doc.characterAt(pos)
                        c1 = doc.characterAt(seg_end - 1)
                        ink_left = x0 + (0.0 if c0.isspace() else fm.leftBearing(c0))
                        ink_right = x1 - (0.0 if c1.isspace() else fm.rightBearing(c1))
                        left = ink_left - CODE_INLINE_PAD_X
                        right = ink_right + CODE_INLINE_PAD_X
                        out.append((QRectF(left, r1.top(), right - left, r1.height()), in_code))
                        pos = seg_end
                it += 1
            b = b.next()
        return out

    def _caret_rect(self, pos):
        c = QTextCursor(self.document()); c.setPosition(pos)
        return self.cursorRect(c)

    # ── Inline checklist ────────────────────────────────────────────────────────
    def _box_format(self, base=None):
        """Char format for the box glyph: a neutral (note-coloured, not blue)
        anchor carrying the sentinel href so clicks toggle it. Based on `base`
        when given so the box inherits the line's font size/family."""
        fmt = QTextCharFormat(base) if base is not None else QTextCharFormat()
        fmt.setAnchor(True)
        fmt.setAnchorHref(CHECK_HREF)
        fmt.setForeground(QColor(self.checkbox_text_color))
        fmt.setFontUnderline(False)
        fmt.setFontStrikeOut(False)
        return fmt

    def _plain_format(self, base=None):
        """Char format for non-box characters on a checklist line (the space and
        typed text): explicitly not an anchor, normal colour, no strikethrough."""
        fmt = QTextCharFormat(base) if base is not None else QTextCharFormat()
        fmt.setAnchor(False)
        fmt.setAnchorHref("")
        fmt.setFontUnderline(False)
        fmt.setFontStrikeOut(False)
        fmt.setForeground(QColor(self.checkbox_text_color))
        return fmt

    # ── checklist tree (implicit from indent levels) ────────────────────────────
    @staticmethod
    def _is_check_line(text: str) -> bool:
        return text[:1] in (CHECK_EMPTY, CHECK_DONE)

    def _check_indent(self, bn: int):
        """Indent level of block bn if it is a checklist line, else None — a
        non-checklist line acts as a separator that breaks parent/child chains."""
        b = self.document().findBlockByNumber(bn)
        if not b.isValid() or not self._is_check_line(b.text()):
            return None
        return QTextCursor(b).blockFormat().indent()

    def _descendants(self, bn: int):
        """Block numbers in the subtree under bn: the following contiguous
        checklist lines whose indent is greater than bn's."""
        base = self._check_indent(bn)
        if base is None:
            return []
        out, n, total = [], bn + 1, self.document().blockCount()
        while n < total:
            ind = self._check_indent(n)
            if ind is None or ind <= base:
                break
            out.append(n)
            n += 1
        return out

    def _parent_of(self, bn: int):
        """Nearest preceding checklist line with a smaller indent, or None if a
        separator (non-checklist line) or the document start comes first."""
        base = self._check_indent(bn)
        if base is None:
            return None
        n = bn - 1
        while n >= 0:
            ind = self._check_indent(n)
            if ind is None:
                return None
            if ind < base:
                return n
            n -= 1
        return None

    def _is_done(self, bn: int) -> bool:
        b = self.document().findBlockByNumber(bn)
        return b.isValid() and b.text()[:1] == CHECK_DONE

    def _apply_check(self, bn: int, checked: bool):
        """Set one checklist line to checked/unchecked (glyph + strike/dim),
        idempotent so re-applying the same state is a no-op."""
        doc = self.document()
        block = doc.findBlockByNumber(bn)
        if not block.isValid() or not self._is_check_line(block.text()):
            return
        text = block.text()
        if (text[0] == CHECK_DONE) == checked:
            return
        start = block.position()
        probe = QTextCursor(doc)
        probe.setPosition(start)
        probe.movePosition(QTextCursor.MoveOperation.NextCharacter,
                           QTextCursor.MoveMode.KeepAnchor, 1)
        box_fmt = self._box_format(probe.charFormat())
        c = QTextCursor(doc)
        c.setPosition(start)
        c.movePosition(QTextCursor.MoveOperation.NextCharacter,
                       QTextCursor.MoveMode.KeepAnchor, 1)
        c.insertText(CHECK_DONE if checked else CHECK_EMPTY, box_fmt)
        skip = 2 if (len(text) > 1 and text[1] == " ") else 1
        body = QTextCursor(doc)
        body.setPosition(start + skip)
        body.movePosition(QTextCursor.MoveOperation.EndOfBlock,
                          QTextCursor.MoveMode.KeepAnchor)
        fmt = QTextCharFormat()
        fmt.setFontStrikeOut(checked)
        fmt.setForeground(QColor(_CHECK_DONE_COLOR if checked else self.checkbox_text_color))
        body.mergeCharFormat(fmt)

    def toggle_checkbox(self, block_pos: int):
        """Toggle a box with cascade: checking/unchecking an item forces its whole
        subtree to match, then every ancestor is re-evaluated (a parent is checked
        only when all of its descendants are). One undo step for the whole cascade."""
        doc = self.document()
        block = doc.findBlock(block_pos)
        if not block.isValid() or not self._is_check_line(block.text()):
            return
        bn = block.blockNumber()
        target = (block.text()[0] == CHECK_EMPTY)   # toggling: empty → checked
        cur = QTextCursor(doc)
        cur.beginEditBlock()
        # 1) self + all descendants forced to the new state
        for b in [bn] + self._descendants(bn):
            self._apply_check(b, target)
        # 2) re-evaluate ancestors bottom-up: checked iff all descendants checked
        a = self._parent_of(bn)
        while a is not None:
            kids = self._descendants(a)
            self._apply_check(a, bool(kids) and all(self._is_done(d) for d in kids))
            a = self._parent_of(a)
        cur.endEditBlock()
        # A box is toggled by clicking it, which leaves the caret on the box glyph.
        # Move it to the end of that line so the user can keep typing the item
        # naturally (text lands after "☑ ", not before the box).
        tail = QTextCursor(doc)
        tail.setPosition(doc.findBlockByNumber(bn).position())
        tail.movePosition(QTextCursor.MoveOperation.EndOfBlock)
        self.setTextCursor(tail)

    def _reconcile_checklist(self):
        """Re-establish the parent invariant across the document: every checklist
        line that has descendants is checked iff all of them are. Run after
        STRUCTURAL edits (add / delete / indent / reorder) — clicking a box is
        already reconciled inside toggle_checkbox. Processed bottom-up so a nested
        parent settles before the parent above it. Idempotent, and the glyph swap
        keeps each line the same length, so block numbers stay stable. Call it
        inside the caller's edit block so the whole change is one undo step."""
        doc = self.document()
        for bn in range(doc.blockCount() - 1, -1, -1):
            kids = self._descendants(bn)
            if kids:
                self._apply_check(bn, all(self._is_done(d) for d in kids))

    def toggle_checklist(self):
        """Toolbar action: turn the selected line(s) into checklist items, or —
        if the first line is already one — strip the boxes back to plain text."""
        doc = self.document()
        cur = self.textCursor()
        first = doc.findBlock(cur.selectionStart())
        last  = doc.findBlock(cur.selectionEnd())
        positions, b = [], first
        while b.isValid():
            positions.append(b.position())
            if b.blockNumber() >= last.blockNumber():
                break
            b = b.next()
        making = not self._is_check_line(first.text())

        cur.beginEditBlock()
        for pos in reversed(positions):   # last→first so earlier positions hold
            block = doc.findBlock(pos)
            text = block.text()
            is_check = self._is_check_line(text)
            c = QTextCursor(doc)
            c.setPosition(block.position())
            if making and not is_check:
                base = c.charFormat()
                c.insertText(CHECK_EMPTY, self._box_format(base))
                c.insertText(" ", self._plain_format(base))
            elif (not making) and is_check:
                skip = 2 if (len(text) > 1 and text[1] == " ") else 1
                c.movePosition(QTextCursor.MoveOperation.NextCharacter,
                               QTextCursor.MoveMode.KeepAnchor, skip)
                c.removeSelectedText()
                line = QTextCursor(doc)
                line.setPosition(block.position())
                line.movePosition(QTextCursor.MoveOperation.EndOfBlock,
                                  QTextCursor.MoveMode.KeepAnchor)
                clear = QTextCharFormat()
                clear.setFontStrikeOut(False)
                clear.setForeground(QColor(self.checkbox_text_color))
                line.mergeCharFormat(clear)
        self._reconcile_checklist()   # new/removed items re-parent neighbours
        cur.endEditBlock()
        self._apply_check_margins()
        self.setFocus()

    @staticmethod
    def _is_code_block(block) -> bool:
        """A code block is marked by a block-level background — nothing else in
        the app sets one, so it's an exclusive, round-trip-safe marker."""
        return block.blockFormat().background().style() != Qt.BrushStyle.NoBrush

    def _sync_typing_font_to_caret(self):
        """Glue the typing (current char) font family to the caret's context so
        the monospace code font never bleeds past a code-block boundary — and the
        note font never leaks into one. Runs on every caret move; only the FONT
        FAMILY of the typing format is touched, so existing text and other
        attributes (bold/size/…) are untouched.

        On the real X11/GNOME widget Qt sometimes carries the wrong format across
        a block boundary; forcing it here fixes that by construction (the offscreen
        test platform already derives it correctly, so this is belt-and-braces)."""
        cur = self.textCursor()
        if cur.hasSelection():
            return   # mergeCurrentCharFormat would reformat the selection
        # Monospace when the caret sits in a code block OR inside an inline-code
        # span (so inline code keeps typing monospace on an otherwise-plain line).
        mono = self._is_code_block(cur.block()) or self._is_inline_code(
            self.currentCharFormat())
        want = (CODE_FONT_FAMILY if mono else
                (self.code_revert_family or self.document().defaultFont().family()))
        if (self.currentCharFormat().fontFamilies() or [None])[:1] != [want]:
            f = QTextCharFormat()
            f.setFontFamilies([want])
            self.mergeCurrentCharFormat(f)

    def toggle_code_block(self):
        """Toolbar action: turn the selected line(s) into a code block (monospace
        + background), or — if the first line already is one — revert to plain."""
        doc = self.document()
        cur = self.textCursor()
        first = doc.findBlock(cur.selectionStart())
        last  = doc.findBlock(cur.selectionEnd())
        # A selection ending exactly at a block's start (triple-click includes the
        # trailing newline) shouldn't pull that next line into the code block.
        if (cur.hasSelection() and cur.selectionEnd() == last.position()
                and last.blockNumber() > first.blockNumber()):
            last = last.previous()
        making = not self._is_code_block(first)
        # Making a code block on an empty doc is the "click { } then type" flow:
        # tell the empty-doc cleanup to keep this block rather than reset it.
        if making and self.document().isEmpty():
            self._pending_empty_code = True
        # Un-coding restores the note's chosen family (not the app default).
        revert_family = self.code_revert_family or doc.defaultFont().family()
        positions, b = [], first
        while b.isValid():
            positions.append(b.position())
            if b.blockNumber() >= last.blockNumber():
                break
            b = b.next()
        cur.beginEditBlock()
        for pos in positions:
            block = doc.findBlock(pos)
            bf = block.blockFormat()
            cf = QTextCharFormat()
            if making:
                bf.setBackground(_CODE_MARK_BG)   # transparent marker; box drawn in paintEvent
                bf.setLeftMargin(CODE_BLOCK_MARGIN)     # inset text off the box edges
                bf.setRightMargin(CODE_BLOCK_MARGIN)
                cf.setFontFamilies([CODE_FONT_FAMILY])
                cf.setForeground(self.code_fg_color)   # light text on the dark box
            else:
                bf.clearBackground()
                bf.setLeftMargin(0); bf.setRightMargin(0)
                bf.setTopMargin(0); bf.setBottomMargin(0)
                cf.setFontFamilies([revert_family])
            bc = QTextCursor(doc); bc.setPosition(block.position())
            bc.setBlockFormat(bf)                       # replace: keeps indent etc.
            # Also set the BLOCK char format so an EMPTY code line has monospace
            # metrics — otherwise it renders at the note's (taller) default font
            # and the whole line + box shrinks the moment the first char is typed.
            # NOT on a list item: Qt draws the bullet marker with the block char
            # format, so monospace there shifts the marker out of line.
            if block.textList() is None:
                bcf = QTextCharFormat()
                bcf.setFontFamilies([CODE_FONT_FAMILY] if making else [revert_family])
                bc.mergeBlockCharFormat(bcf)
            line = QTextCursor(doc)
            line.setPosition(self._text_start(block))   # never restyle a checklist box
            line.movePosition(QTextCursor.MoveOperation.EndOfBlock,
                              QTextCursor.MoveMode.KeepAnchor)
            line.mergeCharFormat(cf)
            if not making:
                # Drop the code foreground so the text follows the note ink again
                # (merge can't clear a property — rebuild each char without it).
                self._strip_code_fg(block)
        cur.endEditBlock()
        # Point the caret's typing format at the right font so text typed into a
        # freshly-toggled (often empty) line comes out monospace — or plain again
        # after reverting.
        # ONLY with no selection: with one, mergeCurrentCharFormat applies to the
        # whole selection, which stamps the monospace font onto the BLOCK char
        # format stored at each paragraph separator inside it — and Qt draws a
        # list item's bullet with that font, so the marker shifted out of line.
        # The selected text was already formatted per-block above.
        if not self.textCursor().hasSelection():
            if making:
                typing = QTextCharFormat()
                typing.setFontFamilies([CODE_FONT_FAMILY])
                typing.setForeground(self.code_fg_color)
                self.mergeCurrentCharFormat(typing)
            else:
                # Un-coding: rebuild the typing format so text typed next drops
                # both the monospace font AND the code foreground (merge can't
                # clear the foreground), following the note ink again.
                typing = QTextCharFormat(self.currentCharFormat())
                typing.setFontFamilies([revert_family])
                typing.clearForeground()
                self.setCurrentCharFormat(typing)
        self._reflow_code_spacing()   # region edges changed → fix box spacing
        self.viewport().update()      # repaint the box in full
        self.setFocus()

    def code_region_at(self, block):
        """(first, last) block numbers of the maximal run of consecutive code
        blocks containing `block` (which must itself be a code block)."""
        first = last = block.blockNumber()
        b = block.previous()
        while b.isValid() and self._is_code_block(b):
            first = b.blockNumber(); b = b.previous()
        b = block.next()
        while b.isValid() and self._is_code_block(b):
            last = b.blockNumber(); b = b.next()
        return first, last

    def code_region_text(self, first, last):
        """The plain text of blocks [first..last], newline-joined."""
        doc = self.document()
        return "\n".join(doc.findBlockByNumber(n).text()
                         for n in range(first, last + 1))

    @staticmethod
    def _is_inline_code(fmt) -> bool:
        """Inline code is marked by a character-level background — the checkbox
        uses a char FOREGROUND and block code uses a BLOCK background, so a char
        background is an exclusive inline marker."""
        return fmt.background().style() != Qt.BrushStyle.NoBrush

    def toggle_inline_code(self):
        """Toggle inline code (monospace + char background) on the selection, or —
        with no selection — flip the typing format so what's typed next is (or
        stops being) inline. Mirrors how Bold behaves."""
        cur = self.textCursor()
        revert = self.code_revert_family or self.document().defaultFont().family()

        def make_fmt(making):
            f = QTextCharFormat()
            if making:
                f.setBackground(_CODE_MARK_BG)     # transparent marker; chip drawn in paintEvent
                f.setFontFamilies([CODE_FONT_FAMILY])
            else:
                f.setBackground(QBrush())          # clear the char background
                f.setFontFamilies([revert])
            return f

        if cur.hasSelection():
            # Apply per block, clamped past any checklist marker: the box is a real
            # character, so a selection dragged over it would otherwise restyle it
            # (a monospaced box renders smaller). Decide making from the first real
            # TEXT char, not the box.
            doc = self.document()
            start, end = cur.selectionStart(), cur.selectionEnd()
            first = doc.findBlock(start)
            probe_at = max(start, self._text_start(first))
            probe = QTextCursor(doc)
            probe.setPosition(probe_at)
            probe.setPosition(min(probe_at + 1, end), QTextCursor.MoveMode.KeepAnchor)
            fmt = make_fmt(not self._is_inline_code(probe.charFormat()))
            edit = QTextCursor(doc)
            edit.beginEditBlock()
            b = doc.findBlock(start)
            while b.isValid() and b.position() < end:
                s = max(start, self._text_start(b))
                e = min(end, b.position() + b.length() - 1)
                if s < e:
                    seg = QTextCursor(doc)
                    seg.setPosition(s)
                    seg.setPosition(e, QTextCursor.MoveMode.KeepAnchor)
                    seg.mergeCharFormat(fmt)
                b = b.next()
            edit.endEditBlock()
        else:
            self.mergeCurrentCharFormat(make_fmt(not self._is_inline_code(self.currentCharFormat())))
        self.viewport().update()      # repaint the inline chip in full
        self.setFocus()

    def _handle_checklist_enter(self) -> bool:
        """Enter on a checklist line: empty item → drop the box (exit); otherwise
        start a fresh checklist item below. Returns True if handled."""
        cur = self.textCursor()
        if cur.hasSelection():
            return False
        block = cur.block()
        text = block.text()
        if not self._is_check_line(text):
            return False
        skip = 2 if (len(text) > 1 and text[1] == " ") else 1
        doc = self.document()
        if text[skip:].strip() == "":
            self._drop_check_marker(block)
            return True
        # Caret at/before the "☐ " prefix (clicked in front of the checklist):
        # push the whole row down and leave a PLAIN empty line above — don't add
        # a box. The content block keeps its own checklist format (incl. nesting);
        # the fresh line above is reset to plain.
        if cur.position() <= block.position() + skip:
            orig = QTextBlockFormat(cur.blockFormat())
            c = QTextCursor(doc)
            c.beginEditBlock()
            c.setPosition(block.position())
            c.insertBlock(orig)                          # row moves down intact
            prev = c.block().previous()
            above = QTextCursor(doc)
            above.setPosition(prev.position())
            above.setBlockFormat(QTextBlockFormat())     # new line above → plain
            self._reconcile_checklist()   # a plain line can split a parent chain
            c.endEditBlock()
            self.setTextCursor(c)
            self._apply_check_margins()
            return True

        # Caret within the text: split into two checklist items.
        base = cur.charFormat()
        c = QTextCursor(doc)
        c.beginEditBlock()
        c.setPosition(cur.position())
        blk = QTextBlockFormat()
        blk.setIndent(cur.blockFormat().indent())   # keep the current indent level
        c.insertBlock(blk)
        c.insertText(CHECK_EMPTY, self._box_format(base))
        c.insertText(" ", self._plain_format(base))
        self._reconcile_checklist()   # new empty child → its parent reverts to unchecked
        c.endEditBlock()
        self.setTextCursor(c)
        self._apply_check_margins()   # new checklist item → give it the base inset
        return True

    def checklist_progress(self):
        """(done, total) over LEAF checklist items only — an item that has nested
        children (a parent) is excluded, since it just auto-reflects its children.
        A flat list (no nesting) still counts every item, as each is a leaf."""
        total = done = 0
        doc = self.document()
        for bn in range(doc.blockCount()):
            ch = doc.findBlockByNumber(bn).text()[:1]
            if ch not in (CHECK_EMPTY, CHECK_DONE):
                continue
            base = self._check_indent(bn)
            nxt = self._check_indent(bn + 1)
            if nxt is not None and nxt > base:      # has a child → parent, skip
                continue
            total += 1
            if ch == CHECK_DONE:
                done += 1
        return done, total

    def normalize_checkboxes(self):
        """Re-apply the neutral box format to every box glyph. Qt re-underlines
        anchors (and can recolour them) when a note is reloaded from saved HTML,
        so after setHtml the boxes need restyling to stay neutral, not link-like."""
        doc = self.document()
        cur = QTextCursor(doc)
        cur.beginEditBlock()
        b = doc.begin()
        while b.isValid():
            if b.text()[:1] in (CHECK_EMPTY, CHECK_DONE):
                c = QTextCursor(doc)
                c.setPosition(b.position())
                c.movePosition(QTextCursor.MoveOperation.NextCharacter,
                               QTextCursor.MoveMode.KeepAnchor, 1)
                c.setCharFormat(self._box_format(c.charFormat()))
            b = b.next()
        cur.endEditBlock()
        self._apply_check_margins()

    def _strip_code_fg(self, block):
        """Remove the code-block foreground from every character of `block` that
        still carries it, so un-coded text follows the note ink (QTextEdit
        default) again. merge can't clear a property, so each char is rebuilt
        from its own format minus the foreground. A colour the user chose inside
        the block (≠ code_fg_color) is left alone."""
        doc = self.document()
        want = self.code_fg_color.name().lower()
        start = self._text_start(block)
        end = block.position() + block.length() - 1     # exclude block separator
        for i in range(start, end):
            c = QTextCursor(doc)
            c.setPosition(i)
            c.setPosition(i + 1, QTextCursor.MoveMode.KeepAnchor)
            f = c.charFormat()
            if (f.foreground().style() != Qt.BrushStyle.NoBrush
                    and f.foreground().color().name().lower() == want):
                nf = QTextCharFormat(f)
                nf.clearForeground()
                c.setCharFormat(nf)

    def normalize_code_blocks(self):
        """Re-apply the current code background + monospace + light foreground to
        every code block (a block that carries a background). Runs after load and
        whenever the note colour changes, so the dark box + light text track the
        note's ink."""
        doc = self.document()
        edit = QTextCursor(doc)
        edit.beginEditBlock()
        b = doc.begin()
        while b.isValid():
            if self._is_code_block(b):
                bf = b.blockFormat()
                bf.setBackground(_CODE_MARK_BG)   # transparent marker; box drawn in paintEvent
                bf.setLeftMargin(CODE_BLOCK_MARGIN)
                bf.setRightMargin(CODE_BLOCK_MARGIN)
                self._set_code_edge_margins(bf, b)   # top/bottom only at region edges
                bc = QTextCursor(doc); bc.setPosition(b.position())
                bc.setBlockFormat(bf)
                if b.textList() is None:              # not a bullet — safe to set (marker font)
                    bcf = QTextCharFormat(); bcf.setFontFamilies([CODE_FONT_FAMILY])
                    bc.mergeBlockCharFormat(bcf)       # empty code line keeps monospace height
                line = QTextCursor(doc); line.setPosition(self._text_start(b))
                line.movePosition(QTextCursor.MoveOperation.EndOfBlock,
                                  QTextCursor.MoveMode.KeepAnchor)
                cf = QTextCharFormat()
                cf.setFontFamilies([CODE_FONT_FAMILY])
                cf.setForeground(self.code_fg_color)
                line.mergeCharFormat(cf)
            b = b.next()
        edit.endEditBlock()

    def _set_code_edge_margins(self, bf, block):
        """Reserve layout space at the code region's OUTER edges (where the block
        above/below isn't code) for the box's growth (CODE_BLOCK_PAD_Y) plus a
        clear gap to the neighbouring line (CODE_BLOCK_GAP), so those lines don't
        touch the box — while a run of consecutive code lines stays tight inside
        one box (no interior gaps)."""
        edge = CODE_BLOCK_PAD_Y + CODE_BLOCK_GAP
        prev_code = block.previous().isValid() and self._is_code_block(block.previous())
        next_code = block.next().isValid() and self._is_code_block(block.next())
        bf.setTopMargin(0 if prev_code else edge)
        bf.setBottomMargin(0 if next_code else edge)

    def _reflow_code_spacing(self):
        """Re-assert every code block's region-edge top/bottom margins after a
        structural edit that can change where regions begin/end (toggle, Enter to
        continue/exit a block). Leaves colours/fonts alone — margins only."""
        doc = self.document()
        # An empty doc is a single block with no neighbours: nothing to reflow,
        # and a setBlockFormat here would re-fire the empty-note cleanup (which
        # resets a freshly-toggled empty code block back to plain).
        if doc.isEmpty():
            return
        edit = QTextCursor(doc)
        edit.beginEditBlock()
        b = doc.begin()
        while b.isValid():
            if self._is_code_block(b):
                bf = b.blockFormat()
                edge = CODE_BLOCK_PAD_Y + CODE_BLOCK_GAP
                want_top = 0 if (b.previous().isValid() and self._is_code_block(b.previous())) else edge
                want_bot = 0 if (b.next().isValid() and self._is_code_block(b.next())) else edge
                if bf.topMargin() != want_top or bf.bottomMargin() != want_bot:
                    bf.setTopMargin(want_top); bf.setBottomMargin(want_bot)
                    c = QTextCursor(doc); c.setPosition(b.position()); c.setBlockFormat(bf)
            b = b.next()
        edit.endEditBlock()

    def normalize_inline_code(self):
        """Re-apply the current inline background + monospace to every inline-code
        run (a character that carries a background). Char-level sibling of
        normalize_code_blocks; runs on load and note-colour change so inline code
        tracks the note colour. (Block-code chars carry a BLOCK background, not a
        char background, so they're never touched here.)"""
        doc = self.document()
        edit = QTextCursor(doc)
        edit.beginEditBlock()
        b = doc.begin()
        while b.isValid():
            start = b.position()
            for i in range(b.length() - 1):     # exclude the block separator
                c = QTextCursor(doc)
                c.setPosition(start + i)
                c.setPosition(start + i + 1, QTextCursor.MoveMode.KeepAnchor)
                if self._is_inline_code(c.charFormat()):
                    f = QTextCharFormat()
                    f.setBackground(_CODE_MARK_BG)   # transparent marker; chip drawn in paintEvent
                    f.setFontFamilies([CODE_FONT_FAMILY])
                    c.mergeCharFormat(f)
            b = b.next()
        edit.endEditBlock()

    def _apply_check_margins(self):
        """Give every checklist line a small base left margin so lists don't sit
        flush at the edge, and strip it from lines that are no longer checklist
        items. One idempotent sweep keeps the inset right across create / exit /
        indent / reload — merge (not set) so each line's indent level survives."""
        doc = self.document()
        edit = QTextCursor(doc)
        edit.beginEditBlock()
        b = doc.begin()
        while b.isValid():
            want = float(CHECK_LEFT_MARGIN) if self._is_check_line(b.text()) else 0.0
            c = QTextCursor(doc)
            c.setPosition(b.position())
            if c.blockFormat().leftMargin() != want:
                mbf = QTextBlockFormat()
                mbf.setLeftMargin(want)
                c.mergeBlockFormat(mbf)
            b = b.next()
        edit.endEditBlock()

    def recolor_checklist(self, old_hex, new_hex):
        """Recolour default-coloured checklist glyphs and text from old_hex to
        new_hex so boxes and text stay readable when the note's ink flips (a dark
        note needs light boxes/text). Only chars matching the old default are
        touched — done-item grey and any user-picked colours are left alone."""
        old, new = QColor(old_hex), QColor(new_hex)
        if old == new:
            return
        doc = self.document()
        fmt = QTextCharFormat()
        fmt.setForeground(new)
        edit = QTextCursor(doc)
        edit.beginEditBlock()
        b = doc.begin()
        while b.isValid():
            if self._is_check_line(b.text()):
                start = b.position()
                for i in range(b.length() - 1):     # exclude the block separator
                    c = QTextCursor(doc)
                    c.setPosition(start + i)
                    c.setPosition(start + i + 1, QTextCursor.MoveMode.KeepAnchor)
                    if c.charFormat().foreground().color() == old:
                        c.mergeCharFormat(fmt)
            b = b.next()
        edit.endEditBlock()

    def _handle_checklist_keys(self, event) -> bool:
        """Keys that act on a checklist line: Alt+↑/↓ reorders, Tab/Shift+Tab
        indents/outdents (sub-items), and Backspace/Delete on a *checked* item
        removes the whole row. Returns True when handled."""
        cur = self.textCursor()
        block = cur.block()
        if not self._is_check_line(block.text()):
            return False
        key, mods = event.key(), event.modifiers()
        if (mods & Qt.KeyboardModifier.AltModifier) and key in (Qt.Key.Key_Up, Qt.Key.Key_Down):
            step = -1 if key == Qt.Key.Key_Up else 1
            self.move_block(block.blockNumber(), block.blockNumber() + step, keep_cursor=True)
            return True
        if key == Qt.Key.Key_Tab:
            self._change_indent(block, +1)
            return True
        if key == Qt.Key.Key_Backtab:
            self._change_indent(block, -1)
            return True
        if (key in (Qt.Key.Key_Backspace, Qt.Key.Key_Delete)
                and not cur.hasSelection() and block.text()[:1] == CHECK_DONE):
            self._delete_whole_line(block)
            return True
        # Unchecked item: treat the box like a list marker. On an EMPTY item either
        # key drops the box and the line goes plain (mirrors Enter). While the line
        # still has text, neither key may eat the "☐ " prefix — Backspace removes
        # the char BEFORE the caret (so guard <= the text start), Delete the one AT
        # it (guard < the text start, or typing/deleting real text would break).
        if (key in (Qt.Key.Key_Backspace, Qt.Key.Key_Delete)
                and not cur.hasSelection()):
            text = block.text()
            skip = 2 if (len(text) > 1 and text[1] == " ") else 1
            if text[skip:].strip() == "":
                self._drop_check_marker(block)
                return True
            limit = block.position() + skip
            if (cur.position() <= limit if key == Qt.Key.Key_Backspace
                    else cur.position() < limit):
                return True          # protect the marker; the text stays put
        return False

    def _drop_check_marker(self, block):
        """Turn a checklist line back into a plain line: remove the "☐ " marker,
        reset the char format and the indent. Shared by Enter and Backspace on an
        empty item."""
        doc = self.document()
        c = QTextCursor(doc)
        c.beginEditBlock()
        c.setPosition(block.position())
        c.movePosition(QTextCursor.MoveOperation.EndOfBlock,
                       QTextCursor.MoveMode.KeepAnchor)
        c.removeSelectedText()
        c.setCharFormat(self._plain_format())
        bf = c.blockFormat()                # exit to the left margin, like bullets
        bf.setIndent(0)
        c.setBlockFormat(bf)
        self._reconcile_checklist()   # this line is no longer a checklist item
        c.endEditBlock()
        self.setTextCursor(c)
        self._apply_check_margins()   # this line is plain now → clear its inset

    def _change_indent(self, block, delta: int):
        """Indent/outdent a checklist line for sub-items (0–6 levels). Re-parents
        the line, so reconcile both the old and new parent afterwards."""
        doc = self.document()
        c = QTextCursor(doc)
        c.beginEditBlock()
        c.setPosition(block.position())
        bf = c.blockFormat()
        bf.setIndent(max(0, min(6, bf.indent() + delta)))
        c.setBlockFormat(bf)
        self._reconcile_checklist()
        c.endEditBlock()

    def _delete_whole_line(self, block):
        """Remove an entire line (and close the gap) — used when Backspace/Delete
        is pressed on a checked item. Deleting a checklist PARENT promotes its
        descendants one indent level (shift the whole subtree left by one) so they
        take the parent's place instead of being left indented under nothing."""
        doc = self.document()
        bn, total = block.blockNumber(), doc.blockCount()
        n_desc = len(self._descendants(bn)) if self._is_check_line(block.text()) else 0
        c = QTextCursor(doc)
        c.setPosition(block.position())
        c.beginEditBlock()
        c.movePosition(QTextCursor.MoveOperation.StartOfBlock)
        c.movePosition(QTextCursor.MoveOperation.EndOfBlock, QTextCursor.MoveMode.KeepAnchor)
        c.removeSelectedText()
        if total > 1:
            if bn < total - 1:
                c.deleteChar()            # pull the next line up
            else:
                c.deletePreviousChar()    # last line → drop the separator before it
        # Promote the former subtree: after the delete its lines sit at bn..bn+n-1.
        for i in range(n_desc):
            d = doc.findBlockByNumber(bn + i)
            if not d.isValid() or not self._is_check_line(d.text()):
                break
            dc = QTextCursor(doc)
            dc.setPosition(d.position())
            bf = dc.blockFormat()
            bf.setIndent(max(0, bf.indent() - 1))
            dc.setBlockFormat(bf)
        self._reconcile_checklist()   # removing a child can complete/uncomplete its parent
        c.endEditBlock()
        self.setTextCursor(c)

    # ── reorder (Alt+↑/↓ and drag) ──────────────────────────────────────────────
    def _block_fragment(self, block):
        c = QTextCursor(self.document())
        c.setPosition(block.position())
        c.movePosition(QTextCursor.MoveOperation.StartOfBlock)
        c.movePosition(QTextCursor.MoveOperation.EndOfBlock, QTextCursor.MoveMode.KeepAnchor)
        return c.selection()

    def _block_fmt(self, block):
        c = QTextCursor(self.document())
        c.setPosition(block.position())
        return QTextBlockFormat(c.blockFormat())

    def _replace_block_at(self, pos: int, frag, blk_fmt):
        doc = self.document()
        c = QTextCursor(doc)
        c.setPosition(pos)
        c.movePosition(QTextCursor.MoveOperation.StartOfBlock)
        c.movePosition(QTextCursor.MoveOperation.EndOfBlock, QTextCursor.MoveMode.KeepAnchor)
        c.removeSelectedText()
        c.insertFragment(frag)
        c.setBlockFormat(blk_fmt)

    def _swap_adjacent(self, i: int, j: int):
        """Swap two adjacent blocks (content + block format, e.g. indent)."""
        if j < i:
            i, j = j, i                  # ensure i < j (== i+1)
        doc = self.document()
        bi, bj = doc.findBlockByNumber(i), doc.findBlockByNumber(j)
        if not bi.isValid() or not bj.isValid():
            return
        pi, pj = bi.position(), bj.position()
        fragI, fmtI = self._block_fragment(bi), self._block_fmt(bi)
        fragJ, fmtJ = self._block_fragment(bj), self._block_fmt(bj)
        # Rewrite the later block first so the earlier position stays valid.
        self._replace_block_at(pj, fragI, fmtI)
        self._replace_block_at(pi, fragJ, fmtJ)

    def move_block(self, src_bn: int, dst_bn: int, keep_cursor: bool = False):
        """Move the block at src_bn to dst_bn by walking adjacent swaps (small
        lists, so cost is negligible) — preserves each line's formatting/indent."""
        doc = self.document()
        if dst_bn < 0 or dst_bn >= doc.blockCount() or src_bn == dst_bn:
            return
        step = 1 if dst_bn > src_bn else -1
        cur = QTextCursor(doc)
        cur.beginEditBlock()
        bn = src_bn
        while bn != dst_bn:
            self._swap_adjacent(bn, bn + step)
            bn += step
        self._reconcile_checklist()   # reordering changes subtree membership
        cur.endEditBlock()
        self.normalize_checkboxes()
        if keep_cursor:
            c = QTextCursor(doc)
            c.setPosition(doc.findBlockByNumber(dst_bn).position())
            c.movePosition(QTextCursor.MoveOperation.EndOfBlock)
            self.setTextCursor(c)

    def _reset_drag(self):
        self._press_pos = None
        self._drag_block = None
        self._dragging = False
        self._drag_span = None

    def _remove_block_range(self, a: int, b: int):
        """Delete blocks a..b inclusive (with one separator) to close the gap."""
        doc = self.document()
        total = doc.blockCount()
        c = QTextCursor(doc)
        if b < total - 1:
            c.setPosition(doc.findBlockByNumber(a).position())
            c.setPosition(doc.findBlockByNumber(b + 1).position(), QTextCursor.MoveMode.KeepAnchor)
        else:                                   # range ends at the last block
            if a > 0:
                prev = doc.findBlockByNumber(a - 1)
                c.setPosition(prev.position() + len(prev.text()))
            else:
                c.setPosition(0)
            last = doc.findBlockByNumber(b)
            c.setPosition(last.position() + len(last.text()), QTextCursor.MoveMode.KeepAnchor)
        c.removeSelectedText()

    def _insert_blocks_at_gap(self, gap: int, captured):
        """captured = [(text_fragment, block_format), …]. Insert as new blocks so
        they occupy indices [gap .. gap+len-1]; neighbouring blocks keep format.
        Two phases: insert the text as blocks, then assign block formats by index
        (simpler and more robust than juggling formats during the split)."""
        doc = self.document()
        total = doc.blockCount()
        gap = max(0, min(gap, total))
        fmts = [bfmt for _, bfmt in captured]
        n = len(captured)
        neighbor_fmt = (QTextCursor(doc.findBlockByNumber(gap)).blockFormat()
                        if gap < total else None)

        c = QTextCursor(doc)
        if gap >= total:                         # append at end
            c.movePosition(QTextCursor.MoveOperation.End)
            for frag, _ in captured:
                c.insertBlock()
                c.insertFragment(frag)
        else:                                    # insert before block `gap`
            c.setPosition(doc.findBlockByNumber(gap).position())
            for frag, _ in captured:
                c.insertFragment(frag)
                c.insertBlock()

        for k in range(n):                       # phase 2: formats by index
            blk = doc.findBlockByNumber(gap + k)
            if blk.isValid():
                QTextCursor(blk).setBlockFormat(fmts[k])
        if neighbor_fmt is not None:
            blk = doc.findBlockByNumber(gap + n)
            if blk.isValid():
                QTextCursor(blk).setBlockFormat(neighbor_fmt)

    def move_range(self, a: int, b: int, dst: int, keep_cursor: bool = False):
        """Move the contiguous block range [a..b] so it is inserted before block
        index `dst` (a gap index). No-op if dst falls inside the range. Used to
        drag a whole subtree (parent + descendants) as one unit."""
        doc = self.document()
        total = doc.blockCount()
        if not (0 <= a <= b < total) or (a <= dst <= b + 1):
            return
        count = b - a + 1
        captured = []
        for bn in range(a, b + 1):
            blk = doc.findBlockByNumber(bn)
            sel = QTextCursor(doc)
            sel.setPosition(blk.position())
            sel.movePosition(QTextCursor.MoveOperation.EndOfBlock, QTextCursor.MoveMode.KeepAnchor)
            captured.append((sel.selection(), self._block_fmt(blk)))

        cur = QTextCursor(doc)
        cur.beginEditBlock()
        self._remove_block_range(a, b)
        dst_after = dst - count if dst > b else dst
        self._insert_blocks_at_gap(dst_after, captured)
        cur.endEditBlock()
        self.normalize_checkboxes()
        if keep_cursor:
            tgt = doc.findBlockByNumber(min(dst_after, doc.blockCount() - 1))
            c = QTextCursor(doc)
            c.setPosition(tgt.position())
            c.movePosition(QTextCursor.MoveOperation.EndOfBlock)
            self.setTextCursor(c)

    # ── drag visuals (ghost + insertion line) ───────────────────────────────────
    def _ensure_overlay(self):
        if self._drag_overlay is None:
            self._drag_overlay = _DragOverlay(self.viewport())
        return self._drag_overlay

    def _block_viewport_span(self, block):
        """(top, bottom) Y of a block in viewport coordinates."""
        c = QTextCursor(block)
        top = self.cursorRect(c).top()
        c.movePosition(QTextCursor.MoveOperation.EndOfBlock)
        bottom = self.cursorRect(c).bottom()
        return top, bottom

    def _gap_y(self, ins: int) -> int:
        """Viewport Y of gap `ins` (top of block ins, or bottom of the last)."""
        doc = self.document()
        total = doc.blockCount()
        if ins >= total:
            _, bottom = self._block_viewport_span(doc.findBlockByNumber(total - 1))
            return bottom
        top, _ = self._block_viewport_span(doc.findBlockByNumber(max(0, ins)))
        return top

    def _drop_boundary(self, y: int):
        """For a viewport y, return (insertion_gap, line_y). When a subtree is
        being dragged, the gap is clamped to lie outside the dragged range so a
        subtree can't be dropped inside itself."""
        block = self.cursorForPosition(QPoint(8, max(0, y))).block()
        top, bottom = self._block_viewport_span(block)
        ins = block.blockNumber() if y < (top + bottom) / 2 else block.blockNumber() + 1
        if self._drag_span is not None:
            a, b = self._drag_span
            if a < ins <= b:                       # strictly inside the subtree
                ins = a if (ins - a) <= (b + 1 - ins) else b + 1
        return ins, self._gap_y(ins)

    def _line_colors(self):
        """A line colour that contrasts the note background (dark on light notes,
        light on dark) plus an opposite-tone halo for legibility on mid-tones."""
        c = QColor(self.note_bg_color)
        lum = (0.299 * c.red() + 0.587 * c.green() + 0.114 * c.blue()) / 255.0
        if lum > 0.5:
            return QColor("#1d1d1f"), QColor(255, 255, 255, 150)
        return QColor("#fafafa"), QColor(0, 0, 0, 150)

    def _begin_drag_visual(self):
        doc = self.document()
        a = self._drag_block
        desc = self._descendants(a)
        b = desc[-1] if desc else a
        self._drag_span = (a, b)
        block_a = doc.findBlockByNumber(a)
        block_b = doc.findBlockByNumber(b)
        if not block_a.isValid():
            return
        top, _ = self._block_viewport_span(block_a)
        _, bottom = self._block_viewport_span(block_b)
        h = max(1, bottom - top)
        pix = self.viewport().grab(QRect(0, max(0, top), self.viewport().width(), h))
        self._ghost_grab_dy = (self._press_pos.y() - top) if self._press_pos else h // 2
        line_color, halo_color = self._line_colors()
        self._ensure_overlay().start(pix, top, line_color, halo_color)

    def _update_drag_visual(self, y: int):
        _, line_y = self._drop_boundary(y)
        self._ensure_overlay().update_drag(y - self._ghost_grab_dy, line_y)


class NoteHeader(QFrame):
    """QFrame subclass that handles arrow key movement when focused."""

    def __init__(self, note: "StickyNote"):
        super().__init__()
        self.note = note
        self._dragging = False
        self._drag_origin = None
        self._note_origin = None
        self.setFocusPolicy(Qt.FocusPolicy.ClickFocus)

    def mousePressEvent(self, event):
        if self.note.locked:
            self.clearFocus()
            return
        if event.button() == Qt.MouseButton.LeftButton:
            # Drag the note ourselves instead of QWindow.startSystemMove(): the
            # WM-driven move did NOT reliably deliver a final moveEvent on drop
            # (especially for a slow, small drag), so snap-to-grid never fired and
            # the note was left between grid lines. Tracking the drag gives us a
            # guaranteed mouseReleaseEvent to snap at.
            self._drag_origin = event.globalPosition().toPoint()
            self._note_origin = self.note.pos()
            self._dragging = True
            self.setFocus()

    def mouseMoveEvent(self, event):
        if self._dragging:
            delta = event.globalPosition().toPoint() - self._drag_origin
            self.note.move(self._note_origin + delta)

    def mouseDoubleClickEvent(self, event):
        # Pin this note's chrome open while editing (clean mode only) — see
        # note._toggle_chrome_lock. The gesture is free here: the header has no
        # other double-click meaning, and the drag handler above is unaffected
        # (a double-click never moves the note).
        #
        # NOT gated on note.locked: a read-only note is orthogonal to whether the
        # header is pinned. Blocking it here meant that once you pinned the chrome
        # open and then locked the note, the double-click died — and you could no
        # longer toggle the header (or reach the unlock button comfortably).
        if event.button() == Qt.MouseButton.LeftButton:
            self._dragging = False
            self.note._toggle_chrome_lock()

    def mouseReleaseEvent(self, event):
        if self._dragging and event.button() == Qt.MouseButton.LeftButton:
            self._dragging = False
            self.note._snap_timer.stop()   # avoid a redundant delayed snap
            self.note._apply_snap()        # snap at the final drop position (self-guards if snapping off)

    def keyPressEvent(self, event):
        if self.note.locked:
            super().keyPressEvent(event)
            return
        key = event.key()
        arrows = (Qt.Key.Key_Left, Qt.Key.Key_Right, Qt.Key.Key_Up, Qt.Key.Key_Down)
        if key not in arrows:
            super().keyPressEvent(event)
            return
        shift = bool(event.modifiers() & Qt.KeyboardModifier.ShiftModifier)
        app = self.note.app_ref
        if getattr(app, "_snap_to_grid", False):
            # Snap to grid is on: step in whole grid cells so the note moves
            # cleanly from one grid line to the next, instead of nudging a single
            # pixel only to be snapped straight back. The position is aligned to
            # the grid first so every press lands exactly on a line. To move
            # freely or nudge off the grid, turn Snap to grid off in Settings.
            grid  = max(1, getattr(app, "_grid_size", 20))
            d     = (5 if shift else 1) * grid      # Shift jumps several cells
            base_x = round(self.note.x() / grid) * grid
            base_y = round(self.note.y() / grid) * grid
        else:
            d      = 10 if shift else 1             # free pixel nudging
            base_x, base_y = self.note.x(), self.note.y()
        deltas = {
            Qt.Key.Key_Left:  (-d, 0),
            Qt.Key.Key_Right: ( d, 0),
            Qt.Key.Key_Up:    (0, -d),
            Qt.Key.Key_Down:  (0,  d),
        }
        dx, dy = deltas[key]
        screen = self.note.screen().availableGeometry()
        x = max(screen.left(), min(base_x + dx, screen.right()  - self.note.width()))
        y = max(screen.top(),  min(base_y + dy, screen.bottom() - self.note.height()))
        self.note.move(x, y)
        self.note._save_timer.start(400)
