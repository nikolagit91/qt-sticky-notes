"""Icon rendering: embedded SVG assets, cached rasterisation, and the tray icon.

Icons are SVGs (several from SVG Repo). Their licences are a MIX and are being
audited (see plan item 8) — do NOT rely on this file for a blanket licence claim;
coffee.svg in particular is unverified. Each icon is rendered once at the
requested size via QSvgRenderer and cached in _ICON_CACHE so all notes/rows
share pixmaps.
"""

import os

from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui import QIcon, QColor, QPainter, QPixmap, QPen, QBrush, QPainterPath

from .config import DATA_DIR

# ── Lock icons (SVG Repo — MIT licence) ───────────────────────────────────────
_SVG_LOCKED = b"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 18 18">
  <path fill="#494c4e" d="M14 7h-1V4a4 4 0 0 0-8 0v3H4a2.006 2.006 0 0 0-2 2v7a2.006 2.006 0 0 0 2 2h10a2.006 2.006 0 0 0 2-2V9a2.006 2.006 0 0 0-2-2zM7 4a2 2 0 0 1 4 0v3H7V4zm3 8.75V15a1 1 0 0 1-2 0v-2.27A1.92 1.92 0 0 1 7 11a2 2 0 0 1 4 0 1.953 1.953 0 0 1-1 1.75z"/>
</svg>"""

_SVG_UNLOCKED = b"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 18 18">
  <path fill="#494c4e" d="M14 0a4 4 0 0 0-4 4v3H2a2.006 2.006 0 0 0-2 2v7a2.006 2.006 0 0 0 2 2h10a2.006 2.006 0 0 0 2-2V9a2.006 2.006 0 0 0-2-2V4a2 2 0 0 1 4 0v4a1 1 0 0 0 2 0V4a4 4 0 0 0-4-4zM8 12.73V15a1 1 0 0 1-2 0v-2.27a2 2 0 1 1 2 0z"/>
</svg>"""

_SVG_PIN = b"""<svg xmlns="http://www.w3.org/2000/svg" fill="#000000" viewBox="-23.18 -4 100 100">
  <path fill-rule="evenodd" transform="translate(-770.683 -181)" d="M808.4,199.181c-.811.225.6.866.323,1.626V203.4c1.6,6.517,3.116,13.117,5.2,19.156,2.538.174,4.612-.788,6.814,0a10.3,10.3,0,0,1,1.953,2.274c0,1.3.647,1.946.647,3.246,1.035,1.669.993,4.419.974,7.142-.482.275-.468,1.045-.651,1.623-1.4,2.274-4.2,3.158-6.49,4.546a88.352,88.352,0,0,1-13.313.651c-.132,3.437.312,7.457-.327,10.389a100.3,100.3,0,0,1-.323,19.806c-.127,3.661.866,8.443-2.6,8.765-2.981-.48-3.293-3.631-3.895-6.495-1.028-2.326-1.194-5.515-1.623-8.44-.486-6.333-1.43-12.207-2.274-18.182v-5.195c-.555-.744-2.48-.119-3.571-.326h-3.894a26.361,26.361,0,0,1-10.389.326c-1.923-1.217-2.748-3.531-3.9-5.521.032-.459.058-.919-.323-.973-.234-2.4.365-3.965.323-6.168a36.918,36.918,0,0,1,5.524-4.872c.669-.193,2.13.4,2.27-.322.673-.194,2.133.4,2.274-.325,1.873.249,1.612-1.636,3.571-1.3-.169-9.367,2.254-16.143,3.9-23.7-.346-.736-2.04-.121-2.923-.324-1.225.249-1.552-.4-2.6-.325a12.769,12.769,0,0,1-4.548-4.87v-4.869c.848-.668-.228-3.26.652-3.9-.23-1.2,1.387-.561,1.622-1.3a6.137,6.137,0,0,0,1.949-.976c4.777.234,8.554-.535,13.313-.323,3.1-.9,7.438-.568,10.39-1.623h4.868a18.648,18.648,0,0,1,4.219,3.246c1.347,2.438,1.362,8.2.324,11.039-.313.009-.25.4-.324.649A13.517,13.517,0,0,1,808.4,199.181Z"/>
</svg>"""

_SVG_TOOLBAR = b"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 331.331 331.331">
<g>
<path style="fill:#010002;" d="M30.421,317.462l4.422-17.661l-12.194-4.814l-8.376,13.804c0,0,4.618,12.526-0.511,22.539C13.766,331.331,20.184,320.399,30.421,317.462z M22.229,309.358c1.501-0.615,3.231,0.087,3.851,1.561c0.625,1.474-0.087,3.171-1.588,3.786c-1.501,0.615-3.231-0.087-3.851-1.561C20.01,311.664,20.723,309.967,22.229,309.358z"/>
<path style="fill:#010002;" d="M158.353,112.621c-35.115,28.8-81.086,88.124-120.073,157.423l-0.022-0.027l-6.815,12.026l7.267,2.796l3.84-10.117c20.799-37.491,77.224-135.4,180.397-200.451c0,0,38.411-22.877,76.256-54.516c-9.214,7.702-27.391,17.356-37.247,23.584C236.088,59.683,204.166,75.043,158.353,112.621z"/>
<path style="fill:#010002;" d="M33.2,215.365c-7.985,28.223-7.528,49.718-4.438,55.625h4.83c13.337-27.625,77.572-127.693,117.554-159.016c41.424-32.455,73.378-51.339,100.253-65.111c9.437-4.835,19.118-11.384,27.848-17.949c10.601-8.36,21.348-17.302,30.758-26.053L282.728,20.75L294.89,2.148L271.67,25.759L286.78,0c-35.746,3.225-68.918,21.109-68.918,21.109c-13.271,15.741-23.959,40.782-23.959,40.782c-0.37-12.521,8.11-31.481,8.11-31.481c-6.266,2.861-30.073,16.459-30.073,16.459c-11.645,9.66-15.262,35.06-15.262,35.06c-2.214-10.019,5.526-29.333,5.526-29.333c-33.543,19.32-57.502,52.231-57.502,52.231c-16.584,32.553-2.948,57.953-8.11,51.872c-5.162-6.081-4.052-28.261-4.052-28.261c-35.017,33.63-38.699,49.724-38.699,49.724c-5.896,14.31-11.058,52.59-11.058,52.59c-3.318-3.579,0-23.611,0-23.611c-8.479,17.889-4.422,34.701-4.422,34.701C34.309,240.407,33.2,215.365,33.2,215.365z"/>
<path style="fill:#010002;" d="M310.01,14.191c0,0-13.483,13.065-30.758,26.053c-27.081,21.359-53.156,38.819-53.156,38.819C123.945,139.425,67.025,237.932,48.212,271.708h10.002c3.535-2.834,8.844-4.971,31.014-11.389c28.011-8.11,44.72-25.041,44.72-25.041s-25.553,14.31-37.595,12.88s-28.223,3.1-28.223,3.1s-6.179-2.861,24.291-7.392s80.596-38.634,80.596-38.634s-19.167,7.87-28.011,7.152c-8.844-0.718-30.714,0-30.714,0c14.495-3.34,28.011-1.43,50.126-9.779c22.115-8.349,20.886-7.631,20.886-7.631c25.063-8.349,35.474-34.342,35.474-34.342c-4.335,1.67-37.443,5.722-51.176,1.67c-13.734-4.052-37.132,0-37.132,0c22.115-7.392,27.032-4.052,32.433-4.291c5.406-0.239,22.855,1.191,57.502-10.731s44.475-26.711,44.475-26.711l-23.366,3.122c15.257-2.567,32.455-12.662,32.455-12.662c-10.568,2.861-27.032,4.291-27.032,4.291c19.412-4.291,30.225-10.253,30.225-10.253c18.183-13.832,22.36-34.342,22.36-34.342c-25.803,8.822-46.194,4.77-46.194,4.77c35.387-2.382,45.215-11.449,50.126-13.592c4.917-2.148,6.94-11.03,6.94-11.03c-17.878,6.44-38.15,7.511-38.15,7.511c21.93-3.399,40.722-14.49,40.722-14.49V32.792c-8.479,4.83-23.399,8.588-23.399,8.588l23.219-15.023C316.091,18.841,310.01,14.191,310.01,14.191z"/>
<polygon style="fill:#010002;" points="23.551,290.571 37.361,296.103 39.933,289.989 26.124,284.458"/>
<path style="fill:#010002;" d="M177.036,285.458c-45.628,21.936-89.462,36.888-147.758,38.846c-5.439,0.185-5.466,5.624,0,5.439c52.15-1.751,95.543-12.961,137.391-32.575c46.618-21.854,89.435-40.167,147.828-46.39c5.385-0.577,3.095-5.814-2.252-5.243C260.531,251.051,218.514,265.519,177.036,285.458z"/>
</g>
</svg>"""

_SVG_TRASH = b"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="-3 -3 30 30" fill="none">
<path d="M8 1.5V2.5H3C2.44772 2.5 2 2.94772 2 3.5V4.5C2 5.05228 2.44772 5.5 3 5.5H21C21.5523 5.5 22 5.05228 22 4.5V3.5C22 2.94772 21.5523 2.5 21 2.5H16V1.5C16 0.947715 15.5523 0.5 15 0.5H9C8.44772 0.5 8 0.947715 8 1.5Z" fill="#000000"/>
<path d="M3.9231 7.5H20.0767L19.1344 20.2216C19.0183 21.7882 17.7135 23 16.1426 23H7.85724C6.28636 23 4.98148 21.7882 4.86544 20.2216L3.9231 7.5Z" fill="#000000"/>
</svg>"""

_SVG_EYE_OPEN = b"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none">
  <path fill-rule="evenodd" clip-rule="evenodd" d="M12.0001 3.96997C8.19618 3.96997 4.69299 5.94267 2.28282 9.27342C1.721 10.0475 1.46509 11.0419 1.46509 11.995C1.46509 12.9478 1.7209 13.942 2.28246 14.716C4.69264 18.0471 8.19599 20.02 12.0001 20.02C15.804 20.02 19.3072 18.0473 21.7174 14.7165C22.2792 13.9424 22.5351 12.948 22.5351 11.995C22.5351 11.0421 22.2793 10.0479 21.7177 9.27392C19.3075 5.94286 15.8042 3.96997 12.0001 3.96997ZM9.75012 12C9.75012 10.755 10.7551 9.75 12.0001 9.75C13.2451 9.75 14.2501 10.755 14.2501 12C14.2501 13.245 13.2451 14.25 12.0001 14.25C10.7551 14.25 9.75012 13.245 9.75012 12ZM12.0001 8.25C9.92669 8.25 8.25012 9.92657 8.25012 12C8.25012 14.0734 9.92669 15.75 12.0001 15.75C14.0736 15.75 15.7501 14.0734 15.7501 12C15.7501 9.92657 14.0736 8.25 12.0001 8.25Z" fill="#000000"/>
</svg>"""

_SVG_EYE_CLOSED = b"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none">
  <path fill-rule="evenodd" clip-rule="evenodd" d="M17.742 5.57955C15.9962 4.53817 14.0413 3.96997 11.9998 3.96997C8.19594 3.96997 4.69275 5.94267 2.28258 9.27342C1.72076 10.0475 1.46484 11.0419 1.46484 11.995C1.46484 12.9478 1.72065 13.942 2.28222 14.716C3.02992 15.7494 3.88282 16.6521 4.81727 17.4057L8.72514 13.83C8.42248 13.2886 8.25 12.664 8.25 12C8.25 9.92657 9.92657 8.25 12 8.25C12.7834 8.25 13.5113 8.48997 14.1129 8.90023L17.742 5.57955ZM6.0677 18.2947C7.86114 19.4096 9.88397 20.02 11.9998 20.02C15.8037 20.02 19.3069 18.0473 21.7171 14.7165C22.2789 13.9424 22.5348 12.948 22.5348 11.995C22.5348 11.0421 22.279 10.0479 21.7175 9.27392C20.9248 8.17837 20.0139 7.22973 19.0129 6.44988L6.0677 18.2947ZM15 11.25C15.4142 11.25 15.75 11.5858 15.75 12C15.75 14.0734 14.0734 15.75 12 15.75C11.5858 15.75 11.25 15.4142 11.25 15C11.25 14.5858 11.5858 14.25 12 14.25C13.245 14.25 14.25 13.245 14.25 12C14.25 11.5858 14.5858 11.25 15 11.25Z" fill="#000000"/>
  <path fill-rule="evenodd" clip-rule="evenodd" d="M22.5533 2.19366C22.8329 2.49926 22.8119 2.97366 22.5063 3.25328L19.3012 6.18591C18.9956 6.46553 18.5212 6.44447 18.2416 6.13888C17.962 5.83329 17.9831 5.35888 18.2886 5.07926L21.4937 2.14663C21.7993 1.86701 22.2737 1.88807 22.5533 2.19366ZM5.73136 17.5857C6.01098 17.8913 5.98992 18.3657 5.68433 18.6454L2.5063 21.5533C2.2007 21.8329 1.7263 21.8118 1.44668 21.5062C1.16706 21.2006 1.18812 20.7262 1.49371 20.4466L4.67175 17.5387C4.97734 17.2591 5.45175 17.2801 5.73136 17.5857Z" fill="#000000"/>
</svg>"""

# ── Bell / reminder icon (SVG Repo — MIT licence) ─────────────────────────────
_SVG_BELL = b"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 512 512">
  <path fill="#494c4e" d="M193.499,459.298c5.237,30.54,31.518,52.702,62.49,52.702c30.98,0,57.269-22.162,62.506-52.702l0.32-1.86H193.179L193.499,459.298z"/>
  <path fill="#494c4e" d="M469.782,371.98c-5.126-5.128-10.349-9.464-15.402-13.661c-21.252-17.648-39.608-32.888-39.608-96.168v-50.194c0-73.808-51.858-138.572-123.61-154.81c2.876-5.64,4.334-11.568,4.334-17.655C295.496,17.718,277.777,0,255.995,0c-21.776,0-39.492,17.718-39.492,39.492c0,6.091,1.456,12.018,4.334,17.655c-71.755,16.238-123.61,81.002-123.61,154.81v50.194c0,63.28-18.356,78.521-39.608,96.168c-5.052,4.196-10.276,8.533-15.402,13.661l-0.466,0.466v49.798h428.496v-49.798L469.782,371.98z"/>
</svg>"""

_SVG_ARCHIVE = b"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="#494c4e">
  <path d="M22,4V8H2V4A1,1,0,0,1,3,3H21A1,1,0,0,1,22,4ZM5,21a1,1,0,0,1-1-1V10H20V20a1,1,0,0,1-1,1Zm2-7a1,1,0,0,0,1,1h8a1,1,0,0,0,0-2H8A1,1,0,0,0,7,14Z"/>
</svg>"""

_SVG_STAR = b"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="#f5b301">
  <path d="M12 17.27L18.18 21l-1.64-7.03L22 9.24l-7.19-.61L12 2 9.19 8.63 2 9.24l5.46 4.73L5.82 21z"/>
</svg>"""

_SVG_COPY = b"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none">
<path d="M19.53 8L14 2.47C13.8595 2.32931 13.6688 2.25018 13.47 2.25H11C10.2707 2.25 9.57118 2.53973 9.05546 3.05546C8.53973 3.57118 8.25 4.27065 8.25 5V6.25H7C6.27065 6.25 5.57118 6.53973 5.05546 7.05546C4.53973 7.57118 4.25 8.27065 4.25 9V19C4.25 19.7293 4.53973 20.4288 5.05546 20.9445C5.57118 21.4603 6.27065 21.75 7 21.75H14C14.7293 21.75 15.4288 21.4603 15.9445 20.9445C16.4603 20.4288 16.75 19.7293 16.75 19V17.75H17C17.7293 17.75 18.4288 17.4603 18.9445 16.9445C19.4603 16.4288 19.75 15.7293 19.75 15V8.5C19.7421 8.3116 19.6636 8.13309 19.53 8ZM14.25 4.81L17.19 7.75H14.25V4.81ZM15.25 19C15.25 19.3315 15.1183 19.6495 14.8839 19.8839C14.6495 20.1183 14.3315 20.25 14 20.25H7C6.66848 20.25 6.35054 20.1183 6.11612 19.8839C5.8817 19.6495 5.75 19.3315 5.75 19V9C5.75 8.66848 5.8817 8.35054 6.11612 8.11612C6.35054 7.8817 6.66848 7.75 7 7.75H8.25V15C8.25 15.7293 8.53973 16.4288 9.05546 16.9445C9.57118 17.4603 10.2707 17.75 11 17.75H15.25V19ZM17 16.25H11C10.6685 16.25 10.3505 16.1183 10.1161 15.8839C9.8817 15.6495 9.75 15.3315 9.75 15V5C9.75 4.66848 9.8817 4.35054 10.1161 4.11612C10.3505 3.8817 10.6685 3.75 11 3.75H12.75V8.5C12.7526 8.69811 12.8324 8.88737 12.9725 9.02747C13.1126 9.16756 13.3019 9.24741 13.5 9.25H18.25V15C18.25 15.3315 18.1183 15.6495 17.8839 15.8839C17.6495 16.1183 17.3315 16.25 17 16.25Z" fill="#000000"/>
</svg>"""

_SVG_STAR_O = b"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="#9a9a9a" stroke-width="1.8" stroke-linejoin="round">
  <path d="M12 17.27L18.18 21l-1.64-7.03L22 9.24l-7.19-.61L12 2 9.19 8.63 2 9.24l5.46 4.73L5.82 21z"/>
</svg>"""

# Detect SVG support once at import — QtSvg ships with pip PyQt6 but may be
# missing on apt installs without python3-pyqt6.qtsvg
try:
    from PyQt6.QtSvg import QSvgRenderer as _QSvgRenderer
    from PyQt6.QtCore import QByteArray as _QByteArray
    _HAS_SVG = True
except ImportError:
    _HAS_SVG = False

_ICON_CACHE: dict = {}

# Directory of bundled SVG asset files (shipped inside the package).
_ASSETS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets")

def about_icon_pixmap(dark: bool, fill: str, size: int = 44) -> QPixmap:
    """Render the About-dialog title icon (note-text SVG) at `size` px, recoloured
    to `fill`. The filled variant is used on dark themes, the outline on light;
    both ship black, so recolouring to the theme's text colour keeps the icon
    visible on either background. Returns a null pixmap if SVG is unavailable."""
    if not _HAS_SVG:
        return QPixmap()
    name = "about_icon_dark.svg" if dark else "about_icon_light.svg"
    try:
        with open(os.path.join(_ASSETS_DIR, name), "rb") as f:
            svg_bytes = f.read()
    except OSError:
        return QPixmap()
    import re
    svg_bytes = re.sub(rb'fill="#[0-9a-fA-F]{6}"', f'fill="{fill}"'.encode(), svg_bytes)
    renderer = _QSvgRenderer(_QByteArray(svg_bytes))
    px = QPixmap(size, size)
    px.fill(Qt.GlobalColor.transparent)
    painter = QPainter(px)
    renderer.render(painter)
    painter.end()
    return px

_COFFEE_SVG: bytes = None   # lazily loaded once; see coffee_button_icon

def coffee_button_icon(size: int = 20, fill: str = None) -> QIcon:
    """Coffee-cup icon for the About donate button, read from assets/coffee.svg.
    With `fill` given, recolours every fill to it (e.g. "#ffffff" to sit on the
    accent button); without it the SVG's own colours render. Returns a null
    QIcon when SVG support is unavailable, so callers can fall back to text.

    The asset bytes are cached in a module global so their id() is stable: the
    shared _ICON_CACHE keys on id(svg_bytes), so re-reading the file on each call
    would never hit the cache (and would leak a cache entry per open, risking an
    id() collision with a future icon). Every other caller passes a module-level
    bytes constant for the same reason."""
    global _COFFEE_SVG
    if not _HAS_SVG:
        return QIcon()
    if _COFFEE_SVG is None:
        try:
            with open(os.path.join(_ASSETS_DIR, "coffee.svg"), "rb") as f:
                _COFFEE_SVG = f.read()
        except OSError:
            return QIcon()
    return _make_lock_icon(_COFFEE_SVG, size, fill=fill)

def _make_lock_icon(svg_bytes: bytes, size: int = 18, fill: str = None) -> QIcon:
    """Render SVG at exact size via QSvgRenderer, cached so identical icons are
    rendered only once and shared across all notes/rows (avoids pixmap buildup).

    If `fill` is given, replaces all fill colours in the SVG with it (e.g. for
    a faded/disabled variant of the same icon).
    """
    if not _HAS_SVG:
        return QIcon()
    cache_key = (id(svg_bytes), size, fill)
    cached = _ICON_CACHE.get(cache_key)
    if cached is not None:
        return cached
    if fill:
        import re
        svg_bytes = re.sub(rb'fill:#[0-9a-fA-F]{6}', f'fill:{fill}'.encode(), svg_bytes)
        svg_bytes = re.sub(rb'fill="#[0-9a-fA-F]{6}"', f'fill="{fill}"'.encode(), svg_bytes)
        # Some icons (e.g. trash) leave their <path> with no fill and rely on the
        # default black. If the root <svg> has no fill of its own, set it so those
        # shapes inherit the requested colour instead of staying black.
        if re.search(rb'<svg[^>]*\sfill=', svg_bytes) is None:
            svg_bytes = re.sub(rb'<svg', f'<svg fill="{fill}"'.encode(), svg_bytes, count=1)
    renderer = _QSvgRenderer(_QByteArray(svg_bytes))
    px = QPixmap(size, size)
    px.fill(Qt.GlobalColor.transparent)
    painter = QPainter(px)
    renderer.render(painter)
    painter.end()
    icon = QIcon(px)
    _ICON_CACHE[cache_key] = icon
    return icon

_CHECK_SVG = (b'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 16 16">'
              b'<path fill="none" stroke="{stroke}" stroke-width="2.2" '
              b'stroke-linecap="round" stroke-linejoin="round" '
              b'd="M3.5 8.5 L6.7 11.7 L12.5 4.6"/></svg>')
_check_path_cache: dict = {}

def checkmark_png_path(stroke: str = "#ffffff", size: int = 16) -> str:
    """Render a checkmark to a cached PNG on disk and return its path (for use as
    a Qt stylesheet `image: url(...)` — QSS url() needs a real file, not a data
    URI). Used to draw a visible tick inside dark-mode checkbox indicators."""
    key = (stroke, size)
    cached = _check_path_cache.get(key)
    if cached and os.path.exists(cached):
        return cached
    if not _HAS_SVG:
        return ""
    svg = _CHECK_SVG.replace(b"{stroke}", stroke.encode())
    renderer = _QSvgRenderer(_QByteArray(svg))
    px = QPixmap(size, size)
    px.fill(Qt.GlobalColor.transparent)
    painter = QPainter(px)
    renderer.render(painter)
    painter.end()
    try:
        os.makedirs(DATA_DIR, exist_ok=True)
        path = os.path.join(DATA_DIR, f"_checkmark_{stroke.lstrip('#')}_{size}.png")
        px.save(path, "PNG")
    except Exception:
        return ""
    path = path.replace(os.sep, "/")   # QSS url() wants forward slashes
    _check_path_cache[key] = path
    return path

def _set_btn_icon(btn, svg_bytes: bytes, size: int, fallback: str, fill: str = None):
    """Apply SVG icon to button, or a text fallback if SVG rendering is unavailable.
    `fill` recolours the icon (e.g. to the note's ink) when given."""
    if _HAS_SVG:
        btn.setIcon(_make_lock_icon(svg_bytes, size, fill=fill))
        btn.setIconSize(QSize(size, size))
        btn.setText("")
    else:
        btn.setIcon(QIcon())
        btn.setText(fallback)


# ── Tray icon ─────────────────────────────────────────────────────────────────
def create_tray_icon(dark: bool = False) -> QIcon:
    """The sticky-note tray/dock icon. `dark=True` returns a dark-note variant
    (charcoal body) that matches the dark theme; its header stripe and ruled
    lines stay light so the glyph is legible on any panel colour."""
    if dark:
        # Charcoal note; header/lines/border kept light so the glyph reads on any
        # panel. Lines + border a touch brighter for a cleaner, more modern look.
        body, border, header, lines = "#33373d", "#7b828d", "#454b54", "#c6cbd4"
    else:
        body, border, header, lines = "#FFEE58", "#F9A825", "#FDD835", "#F9A825"

    px = QPixmap(64, 64)
    px.fill(Qt.GlobalColor.transparent)
    p = QPainter(px)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)

    # Shadow
    p.setBrush(QBrush(QColor(0, 0, 0, 40)))
    p.setPen(Qt.PenStyle.NoPen)
    p.drawRoundedRect(6, 10, 54, 50, 5, 5)

    # Note body
    p.setBrush(QBrush(QColor(body)))
    p.setPen(QPen(QColor(border), 1.5))
    p.drawRoundedRect(4, 6, 54, 50, 5, 5)

    # Header stripe
    p.setBrush(QBrush(QColor(header)))
    p.setPen(Qt.PenStyle.NoPen)
    path = QPainterPath()
    path.addRoundedRect(4, 6, 54, 14, 5, 5)
    p.drawPath(path)
    p.fillRect(4, 14, 54, 6, QColor(header))

    # Lines
    p.setPen(QPen(QColor(lines), 1.5))
    for y in [30, 39, 48]:
        p.drawLine(13, y, 51, y)

    p.end()
    return QIcon(px)
