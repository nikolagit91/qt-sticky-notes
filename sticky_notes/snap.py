"""Pure geometry helpers for snapping note windows to a grid and to each other.

No Qt here — everything takes and returns plain ints so the logic can be
unit-tested in isolation. note.py feeds in values from QRect / the geometries
of the other notes and applies the result with setGeometry().

Position snapping is done per axis (X and Y independently) with a simple rule:
a nearby edge of another note wins when within `threshold`; otherwise the value
rounds to the grid (when grid snapping is on); otherwise it is left unchanged.
That lets one axis line up with a neighbour while the other lands on the grid.
"""


def snap_to_grid(value: int, grid: int) -> int:
    """Round a single coordinate to the nearest grid line."""
    if grid <= 0:
        return value
    return int(round(value / grid)) * grid


def snap_size(w: int, h: int, grid: int) -> tuple[int, int]:
    """Round width/height to the grid, never smaller than one cell."""
    if grid <= 0:
        return w, h
    return max(grid, snap_to_grid(w, grid)), max(grid, snap_to_grid(h, grid))


def _snap_axis(pos: int, size: int, others_1d, grid: int,
               use_grid: bool, use_notes: bool, threshold: int) -> int:
    """Snap one axis. others_1d is a list of (start, length) for the other notes
    on this axis. Neighbour edges (align or touch) take priority within
    threshold; then the grid; else unchanged."""
    if use_notes:
        best = None
        best_d = threshold + 1
        for (ostart, olen) in others_1d:
            # Candidate target positions for this note's leading edge:
            candidates = (
                ostart,                 # leading edges aligned  (my start = their start)
                ostart + olen - size,   # trailing edges aligned (my end   = their end)
                ostart - size,          # touch: my end   = their start (I'm before them)
                ostart + olen,          # touch: my start = their end   (I'm after them)
            )
            for cand in candidates:
                d = abs(pos - cand)
                if d <= threshold and d < best_d:
                    best_d = d
                    best = cand
        if best is not None:
            return best
    if use_grid:
        return snap_to_grid(pos, grid)
    return pos


def snap_position(x: int, y: int, w: int, h: int, others, grid: int,
                  use_grid: bool, use_notes: bool, threshold: int = 10) -> tuple[int, int]:
    """Snap a note's top-left. `others` is a list of (ox, oy, ow, oh) for the
    other visible notes. Returns the snapped (x, y)."""
    nx = _snap_axis(x, w, [(ox, ow) for (ox, oy, ow, oh) in others],
                    grid, use_grid, use_notes, threshold)
    ny = _snap_axis(y, h, [(oy, oh) for (ox, oy, ow, oh) in others],
                    grid, use_grid, use_notes, threshold)
    return nx, ny


def snap_to_edges(x: int, y: int, w: int, h: int,
                  sx: int, sy: int, sw: int, sh: int,
                  threshold: int = 10) -> tuple[int, int, bool, bool]:
    """Snap the note's edges flush to a screen work-area edge when within
    threshold. (sx, sy, sw, sh) is the available screen rect (top-left + size);
    pass availableGeometry so the note lands below the panel rather than under
    it. Each axis is independent: the near edge grabs the screen's near edge,
    the far edge grabs the far edge. Returns (nx, ny, x_hit, y_hit) where the
    *_hit flags say whether that axis actually snapped — the caller uses them to
    let an edge win over grid rounding near the boundary."""
    sright  = sx + sw
    sbottom = sy + sh
    nx, ny = x, y
    x_hit = y_hit = False
    if abs(x - sx) <= threshold:                 # left edge → screen left
        nx, x_hit = sx, True
    elif abs((x + w) - sright) <= threshold:     # right edge → screen right
        nx, x_hit = sright - w, True
    if abs(y - sy) <= threshold:                 # top edge → screen top
        ny, y_hit = sy, True
    elif abs((y + h) - sbottom) <= threshold:    # bottom edge → screen bottom
        ny, y_hit = sbottom - h, True
    return nx, ny, x_hit, y_hit
