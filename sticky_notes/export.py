"""Per-note export to plain text, OpenDocument (.odt), and PDF.

Plain text needs a little work: Qt's toPlainText() drops list markers — bullets
are document structure, not characters — so we walk the blocks and re-add the
markers ourselves to keep lists readable, preserving the note's 5 list styles
(disc / square / decimal / lower-alpha / lower-roman).

ODF and PDF go through Qt's own writers; see to_odt / to_pdf for the per-format
quirks (notably the pixel-vs-point default-font fix).
"""

import re

from PyQt6.QtCore import Qt, QRectF, QPoint
from PyQt6.QtGui import QTextListFormat, QPixmap, QPainter, QColor

from .widgets import CHECK_EMPTY, CHECK_DONE


def _roman(n: int) -> str:
    if n <= 0:
        return str(n)
    vals = [(1000, "m"), (900, "cm"), (500, "d"), (400, "cd"), (100, "c"),
            (90, "xc"), (50, "l"), (40, "xl"), (10, "x"), (9, "ix"),
            (5, "v"), (4, "iv"), (1, "i")]
    out = []
    for v, s in vals:
        while n >= v:
            out.append(s)
            n -= v
    return "".join(out)


def _marker(style, index: int) -> str:
    """Bullet/number marker for a list item (index is 0-based within its list)."""
    S = QTextListFormat.Style
    if style == S.ListDecimal:
        return f"{index + 1}. "
    if style == S.ListLowerAlpha:
        return f"{chr(ord('a') + index % 26)}. "
    if style == S.ListUpperAlpha:
        return f"{chr(ord('A') + index % 26)}. "
    if style == S.ListLowerRoman:
        return f"{_roman(index + 1)}. "
    if style == S.ListUpperRoman:
        return f"{_roman(index + 1).upper()}. "
    if style == S.ListSquare:
        return "▪ "
    if style == S.ListCircle:
        return "○ "
    return "● "   # ListDisc and any fallback


def to_plain_text(document) -> str:
    """Plain text with list markers and nested-list indentation preserved."""
    lines = []
    block = document.firstBlock()
    while block.isValid():
        text = block.text()
        try:
            lst = block.textList()
        except Exception:
            lst = None
        if lst is not None:
            fmt = lst.format()
            indent = max(0, fmt.indent() - 1)
            marker = _marker(fmt.style(), lst.itemNumber(block))
            lines.append("    " * indent + marker + text)
        else:
            # Render checklist boxes as ASCII so .txt stays readable everywhere.
            if text[:1] in (CHECK_EMPTY, CHECK_DONE):
                mark = "[x] " if text[0] == CHECK_DONE else "[ ] "
                rest = text[2:] if (len(text) > 1 and text[1] == " ") else text[1:]
                lines.append(mark + rest)
            else:
                lines.append(text)
        block = block.next()
    return "\n".join(lines).rstrip() + "\n"


def suggest_filename(plain_text: str) -> str:
    """Derive a safe base filename (no extension) from the note's first line."""
    first = ""
    for line in plain_text.splitlines():
        if line.strip():
            first = line.strip()
            break
    if not first:
        return "note"
    # Strip characters unsafe in filenames on Linux and most other filesystems.
    safe = re.sub(r'[\\/:*?"<>|\x00-\x1f]', "", first)
    safe = re.sub(r"\s+", " ", safe).strip()
    safe = safe[:40].strip()
    return safe or "note"


def to_odt(document, path: str) -> None:
    """Write the note to an OpenDocument (.odt) file via Qt's native ODF writer.

    Opens natively in LibreOffice and also in Word, fully editable, with all
    formatting preserved (bold/italic, colours, fonts, sizes, lists).

    The note's text edit uses a PIXEL default font (QSS "font-size: 16px"), which
    Qt would otherwise serialise as an invalid "-1pt" size for any text that
    inherits it. So we clone the document and convert the default font to points
    first (16px → 12pt at 96 DPI), matching the on-screen size. Same root cause
    as the PDF size bug, different cure (ODF has no device resolution to lean on).
    """
    from PyQt6.QtGui import QTextDocumentWriter, QFont

    doc = document.clone()
    df = QFont(document.defaultFont())
    if df.pointSize() <= 0 and df.pixelSize() > 0:
        df.setPointSizeF(df.pixelSize() * 72.0 / 96.0)
    doc.setDefaultFont(df)

    writer = QTextDocumentWriter(path)
    writer.setFormat(b"ODF")           # force ODF regardless of the file extension
    if not writer.write(doc):
        raise RuntimeError(f"Could not write {path}")


def _restore_code_fills(doc, ink) -> None:
    """Give a CLONED document opaque code fills for printing. On screen a code
    block's background and an inline chip's char background are transparent
    markers (the visible box/chip is painted by the editor's paintEvent, which
    drawContents does not run), so without this they'd vanish in the PDF.
    Inline code inside a code block sits on the box, so it gets the box-derived
    overlay (ink.code_inline_bg) rather than the paper tint."""
    from PyQt6.QtGui import QTextCursor, QTextBlockFormat, QTextCharFormat
    code_bg, inline_bg = ink.code_bg, ink.inline_bg
    blk = doc.firstBlock()
    while blk.isValid():
        in_code = blk.blockFormat().background().style() != Qt.BrushStyle.NoBrush
        if in_code:
            bf = QTextBlockFormat(blk.blockFormat())
            bf.setBackground(code_bg)
            cur = QTextCursor(doc); cur.setPosition(blk.position())
            cur.setBlockFormat(bf)
        # Block code's own chars never carry a char background, so any here is inline.
        chip_bg = ink.code_inline_bg if in_code else inline_bg
        it = blk.begin()
        while not it.atEnd():
            frag = it.fragment()
            if frag.isValid() and frag.charFormat().background().style() != Qt.BrushStyle.NoBrush:
                cf = QTextCharFormat(); cf.setBackground(chip_bg)
                cur = QTextCursor(doc)
                cur.setPosition(frag.position())
                cur.setPosition(frag.position() + frag.length(), QTextCursor.MoveMode.KeepAnchor)
                cur.mergeCharFormat(cf)
            it += 1
        blk = blk.next()


def to_pdf(document, path: str, page_color: str = None) -> None:
    """Render the note's document to a PDF at `path`.

    Fills each page edge-to-edge with the note's colour (the sticky-note look),
    then lays the text inside the margins. Uses QPdfWriter (QtGui — no
    QtPrintSupport dependency) with manual pagination, which is what lets us
    paint a full-page background and add page numbers; QTextDocument.print()
    can do neither.

    Rendered at 96 DPI on purpose: the note's text edit is styled with a PIXEL
    font size (QSS "font-size: 16px"), so text inheriting the document's default
    font is pixel-sized. At QPdfWriter's default 1200 DPI those pixels become
    ~1pt (microscopic: 16 × 72 / 1200 = 0.96pt). 96 DPI maps 16px → 12pt, matching
    the screen, while explicit point sizes stay correct (points are DPI-independent).

    Page numbers appear only when the note spans more than one page — a lone
    sticky note shouldn't be stamped with "1". The document is cloned so the live
    on-screen note is never disturbed.
    """
    from PyQt6.QtGui import QPdfWriter, QPageSize, QPageLayout, QPainter, QColor, QFont
    from PyQt6.QtCore import QMarginsF, QRectF, QSizeF, Qt

    writer = QPdfWriter(path)
    writer.setResolution(96)
    writer.setPageSize(QPageSize(QPageSize.PageSizeId.A4))
    writer.setPageMargins(QMarginsF(15, 15, 15, 15), QPageLayout.Unit.Millimeter)

    doc = document.clone()
    doc.setDefaultFont(document.defaultFont())

    # On screen a code block's background is a transparent marker (the visible
    # rounded box is painted by the editor's paintEvent, which drawContents does
    # not run). Restore an opaque fill on the clone so the box still shows in the
    # PDF — a plain rectangle here, but visible. Derived from the page colour.
    if page_color:
        from .theme import note_ink
        _restore_code_fills(doc, note_ink(QColor(page_color)))

    painter = QPainter()
    if not painter.begin(writer):
        raise RuntimeError(f"Could not open {path} for writing")
    try:
        res    = writer.resolution()
        layout = writer.pageLayout()
        full   = layout.fullRectPixels(res)     # whole page (device px)
        paint  = layout.paintRectPixels(res)    # area inside margins
        off_x, off_y = paint.x(), paint.y()     # painter (0,0) == page (off_x, off_y)
        vp = QRectF(painter.viewport())         # content area, origin (0,0)

        pad      = 14                           # extra text inset inside the margins
        footer_h = 22                           # reserved strip for the page number
        inner_w  = vp.width() - 2 * pad

        # Does the note fit on one page (so no footer is needed)?
        doc.setPageSize(QSizeF(inner_w, vp.height() - 2 * pad))
        multipage = doc.pageCount() > 1
        if multipage:
            text_h = vp.height() - 2 * pad - footer_h
            doc.setPageSize(QSizeF(inner_w, text_h))
            pages = doc.pageCount()
        else:
            text_h = vp.height() - 2 * pad
            pages = 1

        for pg in range(pages):
            if pg > 0:
                writer.newPage()

            if page_color:                      # full-bleed note colour
                painter.fillRect(
                    QRectF(-off_x, -off_y, full.width(), full.height()),
                    QColor(page_color))

            painter.save()                      # text slice for this page
            painter.translate(pad, pad - pg * text_h)
            clip = QRectF(0, pg * text_h, inner_w, text_h)
            painter.setClipRect(clip)
            doc.drawContents(painter, clip)
            painter.restore()

            if multipage:                       # subtle centred page number
                painter.save()
                f = QFont(); f.setPointSize(9)
                painter.setFont(f)
                painter.setPen(QColor("#9a9a9a"))
                painter.drawText(
                    QRectF(0, vp.height() - footer_h, vp.width(), footer_h),
                    Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignVCenter,
                    str(pg + 1))
                painter.restore()
    finally:
        painter.end()


PNG_SCALE = 3   # render at 3x the note's on-screen size, so the image stays crisp when zoomed


def render_note_png(note, path: str, scale: int = PNG_SCALE) -> None:
    """Save a clean card image of `note` as PNG: the note's colour as a solid,
    rounded rectangle with the note's live text composited on top (no header or
    toolbar). The note's opacity setting is ignored — the paper is fully opaque.

    Rendered at `scale`x the on-screen size onto a high-DPI pixmap so glyphs are
    rasterised at full resolution (crisp when zoomed), not upscaled afterwards.
    Raises IOError if the file can't be written."""
    te = note.text_edit
    w, h = te.width(), te.height()

    canvas = QPixmap(w * scale, h * scale)
    canvas.setDevicePixelRatio(scale)         # paint in logical coords, store at scale x
    canvas.fill(Qt.GlobalColor.transparent)
    painter = QPainter(canvas)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.setRenderHint(QPainter.RenderHint.TextAntialiasing)
    paper = QColor(note.color)
    paper.setAlpha(255)                       # solid, regardless of note opacity
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(paper)
    painter.drawRoundedRect(QRectF(0, 0, w, h), 10.0, 10.0)
    # DrawChildren (not the window background) keeps the text_edit's transparent
    # backdrop from painting over the paper — only the text is drawn.
    te.render(painter, QPoint(0, 0), flags=te.RenderFlag.DrawChildren)
    painter.end()

    if not canvas.save(path, "PNG"):
        raise IOError(f"Could not write PNG to {path}")
