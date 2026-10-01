"""Plain, serializable model of a sticky note's persisted state (review #3 A5).

`NoteData` mirrors exactly what `StickyNote.get_data()` produces and what the
loader consumes — it is the single serialization boundary. Step 1 only routes
`get_data()` through it (output side); state still lives on the widget. Pure
data, no Qt, no other project imports → leaf module, no cycles.

Field order below matches get_data()'s dict so `to_dict()` is byte-identical
to the previous hand-built dict (on-disk shape unchanged).
"""
from dataclasses import dataclass, asdict, fields
from typing import Optional, List


@dataclass
class NoteData:
    # Defaults mirror the loader's legacy fallbacks for ABSENT keys (so
    # from_dict reproduces __init__'s behaviour exactly). get_data() always
    # supplies every field explicitly, so these defaults never affect the
    # serialized output — only parsing of older/partial records.
    id: Optional[str] = None
    content: str = ""
    content_type: str = ""          # "" = infer from content (legacy notes)
    preview: str = ""
    title: str = ""
    display_title: str = ""
    color: str = "#fff59d"
    color_dark: str = ""            # dark-mode fill; "" = unset (uses the dark default)
    locked: bool = False
    pinned: bool = False
    pin_time: float = 0.0
    favorite: bool = False
    fav_time: float = 0.0
    hidden: bool = False            # user hid the note (eye / X); stays hidden across restarts
    reminder: Optional[float] = None
    font_size: int = 13
    font_family: str = ""           # "" = keep the app's current family
    geometry: Optional[List[int]] = None

    def to_dict(self) -> dict:
        """Serialize to the exact dict shape persisted in notes.json."""
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> "NoteData":
        """Build from a persisted dict. Unknown keys are ignored and missing
        keys fall back to defaults, so a partial or slightly-off record never
        raises here."""
        known = {f.name for f in fields(cls)}
        return cls(**{k: v for k, v in d.items() if k in known})
