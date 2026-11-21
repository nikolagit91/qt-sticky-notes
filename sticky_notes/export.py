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
    # ODT is white paper = the light-note look: text with no colour of its own
    # gets the light-note ink, as on screen (else it is written colourless →
    # black, indistinguishable from a picked black).
    from .theme import DARK_INK, note_ink
    _ink_uncoloured(doc, DARK_INK.text)
    # Code box / inline chip backgrounds are transparent MARKERS on screen; ODF
    # has no alpha and wrote them solid black (inline code = dark text on a
    # black box). Real fills for white paper, as the PDF does for its page.
    _drop_empty_brushes(doc)
    _restore_code_fills(doc, note_ink(QColor("#ffffff")))
    _odt_join_code_lines(doc)
    _odt_code_blocks(doc)
    _odt_font_families(doc)
    _odt_checkboxes(doc)
    _flatten_alpha(doc)

    writer = QTextDocumentWriter(path)
    writer.setFormat(b"ODF")           # force ODF regardless of the file extension
    if not writer.write(doc):
        raise RuntimeError(f"Could not write {path}")
    _odt_code_padding(path)


def _draw_text(doc, painter, clip, text_color=None) -> None:
    """Paint `doc` inside `clip` like QTextDocument.drawContents, but with text
    that has no colour of its own drawn in `text_color` (the note's ink). On
    screen that colour comes from the editor's stylesheet; a cloned document has
    none, so drawContents used the default palette's BLACK — black on the dark
    page of a dark note's PDF (user report 2026-11-19)."""
    from PyQt6.QtGui import QAbstractTextDocumentLayout, QPalette
    ctx = QAbstractTextDocumentLayout.PaintContext()
    ctx.clip = clip
    if text_color:
        ctx.palette.setColor(QPalette.ColorRole.Text, QColor(text_color))
    painter.save()
    painter.setClipRect(clip)
    doc.documentLayout().draw(painter, ctx)
    painter.restore()


def _ink_uncoloured(doc, ink: str) -> None:
    """On a CLONE: give text with no colour of its own the explicit `ink`, so a
    format that has no "default text colour" (ODT) shows it as the note does.
    Links and checklist boxes (anchors) keep their own colour."""
    from PyQt6.QtGui import QTextCursor, QTextCharFormat
    runs = []
    blk = doc.begin()
    while blk.isValid():
        it = blk.begin()
        while not it.atEnd():
            frag = it.fragment()
            it += 1
            f = frag.charFormat()
            if not f.isAnchor() and f.foreground().style() == Qt.BrushStyle.NoBrush:
                runs.append((frag.position(), frag.position() + frag.length()))
        blk = blk.next()
    fmt = QTextCharFormat()
    fmt.setForeground(QColor(ink))
    for a, z in runs:
        c = QTextCursor(doc)
        c.setPosition(a)
        c.setPosition(z, QTextCursor.MoveMode.KeepAnchor)
        c.mergeCharFormat(fmt)


def _display_palette(doc, dark: bool) -> None:
    """On a CLONE: rewrite colours as DRAWN on a light/dark note (widgets.
    drawn_colour — on a dark note: dark-note palette twins, link colours, the
    checklist ink, a done item's stronger fade). The live document stores the
    light-note look and the editor's highlighter draws the rest; a cloned
    document has no highlighter, so the PDF of a dark note needs this."""
    if not dark:
        return
    from PyQt6.QtGui import QTextCursor, QTextCharFormat
    from .widgets import drawn_colour
    runs = []
    blk = doc.begin()
    while blk.isValid():
        it = blk.begin()
        while not it.atEnd():
            frag = it.fragment()
            it += 1
            col = drawn_colour(frag.charFormat(), blk.text(), True)
            if col is not None:
                runs.append((frag.position(), frag.position() + frag.length(), col))
        blk = blk.next()
    for a, z, col in runs:
        c = QTextCursor(doc)
        c.setPosition(a)
        c.setPosition(z, QTextCursor.MoveMode.KeepAnchor)
        nf = QTextCharFormat()
        nf.setForeground(col)
        c.mergeCharFormat(nf)


# A font with plain monochrome ☐ ☑ — what the note itself falls back to (fc-match).
_BOX_FONT = "DejaVu Sans"


def _odt_checkboxes(doc) -> None:
    """On a CLONE for ODT: make checklist boxes plain monochrome glyphs.
    - ☑ (U+2611) also has an emoji form, and the text font lacks it, so
      LibreOffice drew a colour emoji (blue tile, white tick). U+FE0E did not
      stop it; an explicit font that has the glyph did (rendered). Qt 6.4's
      ODF writer writes only the OLD font-family property, so set both.
    - The box is an anchor to the app-internal x-sticky-check, and the space
      after it carries an empty href — both went out as hyperlinks. Plain text.
    """
    from PyQt6.QtGui import QTextCursor, QTextFormat
    blk = doc.begin()
    while blk.isValid():
        if blk.text()[:1] in (CHECK_EMPTY, CHECK_DONE):
            ends = 2 if blk.text()[1:2] == " " else 1      # the box and its space
            for i in range(ends):
                c = QTextCursor(doc)
                c.setPosition(blk.position() + i)
                c.setPosition(blk.position() + i + 1, QTextCursor.MoveMode.KeepAnchor)
                f = c.charFormat()
                f.clearProperty(QTextFormat.Property.IsAnchor)
                f.clearProperty(QTextFormat.Property.AnchorHref)
                if i == 0:
                    f.setFontFamilies([_BOX_FONT])
                    f.setProperty(QTextFormat.Property.OldFontFamily, _BOX_FONT)
                c.setCharFormat(f)
        blk = blk.next()


def _flatten_alpha(doc, paper: str = "#ffffff") -> None:
    """ODF has no alpha: a translucent colour would be written at FULL strength
    — a done checklist item's faded text, and a translucent background (inline
    code chip overlay) as solid black. Pre-blend each onto the page colour (the
    chip onto the block's own box when it sits in a code block) in the cloned
    document so it reads as on screen."""
    from PyQt6.QtGui import QTextCursor, QTextCharFormat, QTextBlockFormat
    page = QColor(paper)

    def blend(col, under):
        a = col.alphaF()
        return QColor(round(col.red() * a + under.red() * (1 - a)),
                      round(col.green() * a + under.green() * (1 - a)),
                      round(col.blue() * a + under.blue() * (1 - a)))

    blk = doc.firstBlock()
    while blk.isValid():
        under = page
        bbr = blk.blockFormat().background()
        if bbr.style() != Qt.BrushStyle.NoBrush:
            if bbr.color().alpha() < 255:
                bf = QTextBlockFormat(blk.blockFormat())
                bf.setBackground(blend(bbr.color(), page))
                QTextCursor(blk).setBlockFormat(bf)
            under = blk.blockFormat().background().color()
        it = blk.begin()
        while not it.atEnd():
            frag = it.fragment()
            cf = QTextCharFormat()
            br = frag.charFormat().foreground()
            if br.style() != Qt.BrushStyle.NoBrush and br.color().alpha() < 255:
                cf.setForeground(blend(br.color(), under))
            bg = frag.charFormat().background()
            if bg.style() != Qt.BrushStyle.NoBrush and bg.color().alpha() < 255:
                cf.setBackground(blend(bg.color(), under))
            if cf.properties():
                cur = QTextCursor(doc)
                cur.setPosition(frag.position())
                cur.setPosition(frag.position() + frag.length(), QTextCursor.MoveMode.KeepAnchor)
                cur.mergeCharFormat(cf)
            it += 1
        blk = blk.next()


def _restore_code_fills(doc, ink, block_fill: bool = True) -> None:
    """Give a CLONED document opaque code fills for printing. On screen a code
    block's background and an inline chip's char background are transparent
    markers (the visible box/chip is painted by the editor's paintEvent, which
    drawContents does not run), so without this they'd vanish in the PDF.
    Inline code inside a code block sits on the box, so it gets the box-derived
    overlay (ink.code_inline_bg) rather than the paper tint. `block_fill=False`
    leaves code blocks' markers alone (the PDF paints their boxes itself)."""
    from PyQt6.QtGui import QTextCursor, QTextBlockFormat, QTextCharFormat
    code_bg, inline_bg = ink.code_bg, ink.inline_bg
    blk = doc.firstBlock()
    while blk.isValid():
        in_code = blk.blockFormat().background().style() != Qt.BrushStyle.NoBrush
        if in_code and block_fill:
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


def _code_regions(doc):
    """(first, last) block pairs of each run of consecutive code blocks (a code
    block carries a background brush — the editor's transparent marker)."""
    regions, blk, start, prev = [], doc.firstBlock(), None, None
    while blk.isValid():
        code = blk.blockFormat().background().style() != Qt.BrushStyle.NoBrush
        if code and start is None:
            start = blk
        elif not code and start is not None:
            regions.append((start, prev)); start = None
        prev = blk
        blk = blk.next()
    if start is not None:
        regions.append((start, prev))
    return regions


def _paint_code_boxes(doc, painter, colour) -> None:
    """Paint each code block's rounded box as the editor does on screen
    (NoteTextEdit._code_region_rect): CODE_BLOCK_MARGIN wider than the text
    column on each side — so it lines up with normal text and the code sits
    inset — and CODE_BLOCK_PAD_Y past the first/last line box. A cloned
    document can't do this with a block background: Qt starts that AFTER the
    block's margin, so the box was shifted right with its text flush against
    the edge (user report 2026-11-21)."""
    from PyQt6.QtCore import QRectF
    from .widgets import CODE_BLOCK_MARGIN, CODE_BLOCK_PAD_Y, CODE_BLOCK_RADIUS
    width = doc.pageSize().width() if doc.pageSize().width() > 0 else doc.textWidth()
    painter.save()
    painter.setRenderHint(painter.RenderHint.Antialiasing)
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(QColor(colour))
    for first, last in _code_regions(doc):
        fl, ll = first.layout(), last.layout()
        if fl.lineCount() == 0 or ll.lineCount() == 0:
            continue
        l0, ln = fl.lineAt(0), ll.lineAt(ll.lineCount() - 1)
        left = fl.position().x() + l0.x() - CODE_BLOCK_MARGIN
        top = fl.position().y() + l0.y() - CODE_BLOCK_PAD_Y
        bottom = ll.position().y() + ln.y() + ln.height() + CODE_BLOCK_PAD_Y
        painter.drawRoundedRect(QRectF(left, top, width - 2 * left, bottom - top),
                                CODE_BLOCK_RADIUS, CODE_BLOCK_RADIUS)
    painter.restore()


def _drop_empty_brushes(doc) -> None:
    """Clear background brushes that are explicitly EMPTY (NoBrush). Text typed
    after switching inline code off carries one; Qt's ODF writer writes it as a
    BLACK background (user report 2026-11-21)."""
    from PyQt6.QtGui import QTextCursor
    spans, blk = [], doc.firstBlock()
    while blk.isValid():
        bf = blk.blockFormat()
        if bf.hasProperty(bf.Property.BackgroundBrush) and bf.background().style() == Qt.BrushStyle.NoBrush:
            bf.clearBackground()
            QTextCursor(blk).setBlockFormat(bf)
        it = blk.begin()
        while not it.atEnd():
            frag = it.fragment(); f = frag.charFormat()
            if f.hasProperty(f.Property.BackgroundBrush) and f.background().style() == Qt.BrushStyle.NoBrush:
                spans.append((frag.position(), frag.length(), f))
            it += 1
        blk = blk.next()
    for pos, length, f in spans:                # collected first: rewriting re-fragments
        f.clearBackground()
        cur = QTextCursor(doc); cur.setPosition(pos)
        cur.setPosition(pos + length, QTextCursor.MoveMode.KeepAnchor)
        cur.setCharFormat(f)


def _odt_join_code_lines(doc) -> None:
    """Make each run of code lines ONE paragraph, its lines joined by line
    breaks (U+2028). In ODT every code line was its own paragraph, and
    LibreOffice fills each paragraph separately, anti-aliasing the shared edge
    into a LIGHTER LINE between code lines (user report 2026-11-21, measured
    46→64/57). Giving them an equal border+padding (LibreOffice then joins the
    borders) did NOT cure it in the user's own note — one paragraph = one fill
    does. The merged paragraph keeps the first line's format and the last
    line's bottom margin. Runs that touch a list are left alone (joining would
    drop the list membership)."""
    from PyQt6.QtGui import QTextCursor
    for first, last in reversed(_code_regions(doc)):
        if first == last:
            continue
        blocks, blk = [], first
        while True:
            blocks.append(blk)
            if blk == last:
                break
            blk = blk.next()
        if any(b.textList() is not None for b in blocks):
            continue
        bottom = last.blockFormat().bottomMargin()
        start = first.position()
        for b in reversed(blocks[:-1]):          # back to front: positions stay valid
            sep = b.position() + b.length() - 1  # the paragraph separator
            cur = QTextCursor(doc); cur.setPosition(sep)
            cur.setPosition(sep + 1, QTextCursor.MoveMode.KeepAnchor)
            cur.insertText("\u2028")
        merged = doc.findBlock(start)
        bf = merged.blockFormat(); bf.setBottomMargin(bottom)
        QTextCursor(merged).setBlockFormat(bf)


def _odt_code_blocks(doc) -> None:
    """ODT can't paint the editor's box, only a paragraph fill — which starts
    AFTER the paragraph margin. So drop the code block's L/R margin (the fill
    then lines up with normal text); the text inset and the box's top/bottom
    padding are added to the written file by _odt_code_padding, so take the
    padding out of the top/bottom margin here to keep the same spacing."""
    from PyQt6.QtGui import QTextCursor
    from .widgets import CODE_BLOCK_PAD_Y
    blk = doc.firstBlock()
    while blk.isValid():
        bf = blk.blockFormat()
        if bf.background().style() != Qt.BrushStyle.NoBrush:
            bf.setLeftMargin(0); bf.setRightMargin(0)
            if bf.topMargin() > 0:
                bf.setTopMargin(max(0.0, bf.topMargin() - CODE_BLOCK_PAD_Y))
            if bf.bottomMargin() > 0:
                bf.setBottomMargin(max(0.0, bf.bottomMargin() - CODE_BLOCK_PAD_Y))
            QTextCursor(blk).setBlockFormat(bf)
        blk = blk.next()


def _odt_code_padding(path: str) -> None:
    """Give the written ODT's code paragraphs padding (Qt's ODF writer has none,
    so this edits content.xml): it insets EVERY line of the box — a first-line
    indent left a soft-wrapped tail and the joined lines (_odt_join_code_lines)
    flush against the edge — and gives the box vertical padding like the note.
    Also drops the stray <text:tab/> Qt 6.4's writer puts before every
    <text:line-break/> (U+2028: joined code lines, and Shift+Enter)."""
    import re, zipfile, os
    from .widgets import CODE_BLOCK_MARGIN, CODE_BLOCK_PAD_Y
    pt = lambda px: f"{px * 72.0 / 96.0:g}pt"
    extra = (f' fo:padding-left="{pt(CODE_BLOCK_MARGIN)}" fo:padding-right="{pt(CODE_BLOCK_MARGIN)}"'
             f' fo:padding-top="{pt(CODE_BLOCK_PAD_Y)}" fo:padding-bottom="{pt(CODE_BLOCK_PAD_Y)}"')

    def pad(m):                         # <… fo:background-color="#c" …/> → + padding
        return f'{m.group(1)}{extra}{m.group(2)}'

    with zipfile.ZipFile(path) as z:
        items = [(i, z.read(i.filename)) for i in z.infolist()]
    tmp = path + ".tmp"
    with zipfile.ZipFile(tmp, "w") as out:   # same entries/order: mimetype stays first, stored
        for info, data in items:
            if info.filename == "content.xml":
                xml = re.sub(r'(<style:paragraph-properties\b[^>]*?fo:background-color="[^"]+"[^>]*?)\s*(/?>)',
                             pad, data.decode("utf-8"))
                data = re.sub(r'<text:tab/>\s*(<text:line-break/>)', r'\1', xml).encode("utf-8")
            out.writestr(info, data)
    os.replace(tmp, path)


def _odt_font_families(doc) -> None:
    """Qt 6.4's ODF writer writes only the OLD font-family property (0x2000);
    fonts set with setFontFamilies (code, a picked font) came out in the default
    "Sans". Mirror the first family into the old property."""
    from PyQt6.QtGui import QTextCursor, QTextCharFormat, QTextFormat
    old = QTextFormat.Property.OldFontFamily
    spans, blk = [], doc.firstBlock()
    while blk.isValid():
        it = blk.begin()
        while not it.atEnd():
            frag = it.fragment(); f = frag.charFormat()
            fams = f.fontFamilies()
            if fams and not f.hasProperty(old):
                spans.append((frag.position(), frag.length(), fams[0]))
            it += 1
        blk = blk.next()
    for pos, length, fam in spans:
        cf = QTextCharFormat(); cf.setProperty(old, fam)
        cur = QTextCursor(doc); cur.setPosition(pos)
        cur.setPosition(pos + length, QTextCursor.MoveMode.KeepAnchor)
        cur.mergeCharFormat(cf)


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
    # not run). The PDF paints the same boxes itself (_paint_code_boxes); inline
    # chips get an opaque fill. Derived from the page colour.
    ink_text = None                     # uncoloured text: Qt's default black
    code_box = None
    if page_color:
        from .theme import note_ink
        ink = note_ink(QColor(page_color))
        ink_text = ink.text             # …or, on a note page, the note's ink
        code_box = ink.code_bg
        _restore_code_fills(doc, ink, block_fill=False)
        # The page is the note's colour: on a dark one draw palette colours as
        # their dark twins, as the editor does (its highlighter isn't in a clone).
        _display_palette(doc, ink.dark)

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
            if code_box is not None:
                # A box overhangs its lines by CODE_BLOCK_PAD_Y: let it reach
                # into the page padding at the very top and bottom (inner page
                # breaks still cut it, like the text).
                bclip = clip.adjusted(0, -pad if pg == 0 else 0,
                                      0, pad if pg == pages - 1 else 0)
                painter.save(); painter.setClipRect(bclip)
                _paint_code_boxes(doc, painter, code_box)
                painter.restore()
            painter.setClipRect(clip)
            _draw_text(doc, painter, clip, ink_text)
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
