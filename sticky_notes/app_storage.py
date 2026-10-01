"""Storage layer extracted from app.py (review #3 A3).

Note/trash/archive persistence, daily backups, import/export, and corrupt-file
recovery. This is a mixin: StickyNotesApp inherits it, so every method still
operates on `self` (the app) exactly as before — pure relocation, no behaviour
change. Dependencies are neutral modules (config/i18n/note/PyQt6); no import
cycle (note.py does not import app).
"""
import os
import json
import shutil
import uuid
import datetime

from PyQt6.QtWidgets import QFileDialog, QMessageBox

from .config import DATA_DIR, DATA_FILE, TRASH_FILE, ARCHIVE_FILE, ACTIVE_LIMIT
from .i18n import tr
from .note import StickyNote

BACKUP_DIR = os.path.join(DATA_DIR, "backups")
MAX_BACKUP_GENERATIONS = 5
# One generation = these three files sharing one date-time tag, e.g.
# notes-2026-07-08_16-30-45.bak
_BACKUP_MEMBERS = (("notes", DATA_FILE), ("archived", ARCHIVE_FILE), ("closed", TRASH_FILE))
_PREFIX_FOR_PATH = {DATA_FILE: "notes", ARCHIVE_FILE: "archived", TRASH_FILE: "closed"}
_BACKUP_TS_FMT = "%Y-%m-%d_%H-%M-%S"


class StorageMixin:

    def save_notes(self):
        """Schedule a save — max one per second regardless of how many notes trigger it."""
        if self._global_save_timer.isActive():
            return
        self._global_save_timer.start()

    def _do_save(self):
        """Actually write notes to disk — called by global save timer."""
        try:
            data, failed = [], []
            for n in self.notes.values():
                try:
                    data.append(n.get_data())
                except Exception as e:
                    failed.append((n.note_id, e))
            if failed:
                # One unserializable note must not cost EVERY other note its
                # edits. This used to be a single list comprehension, so any
                # exception aborted the whole save and the user silently kept
                # working against a file that had stopped updating.
                # _load_notes already tolerates a bad record and skips it; the
                # save side now matches. The failed note keeps its last good
                # copy from disk (read only in this rare path, so the normal
                # save costs nothing extra) rather than being dropped.
                previous = {d.get("id"): d
                            for d in (self._try_read_list(DATA_FILE) or [])
                            if isinstance(d, dict)}
                for nid, err in failed:
                    print(f"[save] skipping unserializable note {nid}: {err}")
                    if nid in previous:
                        data.append(previous[nid])
            tmp  = DATA_FILE + ".tmp"
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            os.replace(tmp, DATA_FILE)
            self._maybe_backup()
        except Exception as e:
            print(f"[save] error: {e}")

    def _write_export(self, note_dicts, default_name, parent):
        """Shared writer for every export action: pick a path, dump the given
        note dicts as JSON (re-importable via Import), report the outcome."""
        path, _ = QFileDialog.getSaveFileName(
            parent, "Export Notes", os.path.join(os.path.expanduser("~"), default_name),
            "JSON Files (*.json)"
        )
        self._trim_memory()   # return file dialog memory to OS
        if not path:
            return
        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(note_dicts, f, indent=2, ensure_ascii=False)
            QMessageBox.information(parent, tr("Export Complete"),
                tr("Exported {} note(s) to:\n{}").format(len(note_dicts), path))
        except Exception as e:
            QMessageBox.warning(parent, tr("Export Failed"), str(e))

    def _export_notes(self, parent):
        today = datetime.date.today().strftime("%Y-%m-%d")
        self._write_export([n.get_data() for n in self.notes.values()],
                           f"sticky_notes_export_{today}.json", parent)

    def export_archived_notes(self, parent):
        """Export every archived note. Archive is otherwise un-exportable (the
        Settings export only covers active notes)."""
        if not self.archived_notes:
            QMessageBox.information(parent, tr("Export"),
                                    tr("There are no archived notes to export."))
            return
        today = datetime.date.today().strftime("%Y-%m-%d")
        self._write_export(list(self.archived_notes),
                           f"sticky_notes_archive_{today}.json", parent)

    def export_single_note(self, note_data, parent):
        """Export a single note (Manager per-row right-click → Export)."""
        nid = str(note_data.get("id", "note"))[:8]
        self._write_export([note_data], f"sticky_note_{nid}.json", parent)

    def _import_notes(self, parent):
        path, _ = QFileDialog.getOpenFileName(
            parent, "Import Notes", os.path.expanduser("~"),
            "JSON Files (*.json)"
        )
        self._trim_memory()   # return file dialog memory to OS
        if not path:
            return

        # Load and validate
        try:
            with open(path, encoding="utf-8") as f:
                data = json.load(f)
            if not isinstance(data, list):
                raise ValueError("Expected a JSON array of notes.")
            for item in data:
                if not isinstance(item, dict) or "content" not in item:
                    raise ValueError("One or more entries are missing required fields.")
        except Exception as e:
            QMessageBox.warning(parent, tr("Import Failed"),
                tr("Could not read export file:\n{}").format(e))
            return

        # Check capacity
        current  = len(self.notes)
        capacity = ACTIVE_LIMIT - current
        incoming = len(data)

        if capacity <= 0:
            QMessageBox.warning(parent, tr("Import Failed"),
                tr("You already have {} active notes — the maximum.\nMove some notes to Trash before importing.").format(ACTIVE_LIMIT))
            return

        if incoming > capacity:
            msg = QMessageBox(parent)
            msg.setWindowTitle(tr("Import — Limit Reached"))
            msg.setIcon(QMessageBox.Icon.Warning)
            msg.setText(
                tr("You have {} active note(s). The export file contains {} note(s).\n\nYou can import at most {} note(s).\n\nImport the first {} and skip the rest?").format(
                    current, incoming, capacity, capacity)
            )
            msg.setStandardButtons(
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
            msg.setDefaultButton(QMessageBox.StandardButton.No)
            choice = msg.exec()
            msg.deleteLater()
            if choice != QMessageBox.StandardButton.Yes:
                return
            data = data[:capacity]

        # Import — assign fresh UUIDs, cascade positions, and rebuild each note
        # from its FULL data so title, formatting (content_type), pin, favorite,
        # reminder, font, and lock all survive the round-trip.
        screen  = self.primaryScreen().availableGeometry()
        offset  = 0
        imported = 0
        for item in data:
            try:
                item = dict(item)
                item["id"] = str(uuid.uuid4())   # fresh UUID — avoid collisions
                # Cascade + clamp to the current screen so nothing lands off-view
                # (export geometries may come from a different monitor layout).
                if isinstance(item.get("geometry"), list) and len(item["geometry"]) == 4:
                    x, y, w, h = item["geometry"]
                    x = min(x + offset, screen.right()  - w)
                    y = min(y + offset, screen.bottom() - h)
                    item["geometry"] = [max(x, screen.left()), max(y, screen.top()), w, h]
                offset += 24
                note = StickyNote(self, item.get("id"), item)
                self.notes[note.note_id] = note
                note._hidden = False    # imported notes are shown (ignore a saved hidden flag)
                note.show()
                imported += 1
            except Exception as e:
                print(f"[import] skipping note: {e}")

        self.save_notes()
        self._refresh_manager()
        QMessageBox.information(parent, tr("Import Complete"),
            tr("Imported {} note(s) successfully.").format(imported))

    def _force_backup(self):
        """Create a NEW backup generation now — used by the interval timer and
        the "Backup Now" button. Saves current state, then snapshots it as a
        fresh generation (rotating; the oldest drops off past MAX_BACKUP_GENERATIONS)."""
        try:
            self._do_save()
            self._save_trash_notes()
            self._save_archived_notes()
            self._new_backup_generation()
        except Exception as e:
            print(f"[backup] error: {e}")

    def _maybe_backup(self):
        """Daily auto-backup: refresh the NEWEST generation's contents with the
        current state, at most once per 24h. Does NOT create a new generation
        (the interval / "Backup Now" do that) — it just keeps the latest restore
        point current. Creates the first generation if none exist yet."""
        gens = self.list_backups()
        if gens:
            age = datetime.datetime.now().timestamp() - gens[0]["mtime"]
            if age < 86400:
                return
        self._refresh_newest_backup()

    # ── Backup generations (folder: BACKUP_DIR) ────────────────────────────────
    def list_backups(self):
        """Backup generations, newest first (by file mtime, so the daily refresh
        of the newest keeps it on top). Each: {tag, when (datetime), mtime,
        label, files: {prefix: path}}."""
        try:
            names = os.listdir(BACKUP_DIR)
        except OSError:
            return []
        gens: dict = {}
        for nm in names:
            if not nm.endswith(".bak"):
                continue
            for prefix, _src in _BACKUP_MEMBERS:
                pre = prefix + "-"
                if nm.startswith(pre):
                    tag = nm[len(pre):-len(".bak")]
                    gens.setdefault(tag, {})[prefix] = os.path.join(BACKUP_DIR, nm)
                    break
        out = []
        for tag, files in gens.items():
            try:
                mtime = max(os.path.getmtime(p) for p in files.values())
            except OSError:
                continue
            when = datetime.datetime.fromtimestamp(mtime)
            out.append({"tag": tag, "when": when, "mtime": mtime, "files": files,
                        "label": when.strftime("%Y-%m-%d  %H:%M:%S")})
        out.sort(key=lambda g: g["mtime"], reverse=True)
        return out

    @staticmethod
    def _write_backup_member(src, dst):
        """Put data file `src` into backup file `dst`. If `src` doesn't exist,
        write an empty list instead — so every generation always contains all
        three members (notes + archived + closed) and a restore is a complete
        point-in-time."""
        if os.path.exists(src):
            shutil.copy2(src, dst)
        else:
            with open(dst, "w", encoding="utf-8") as f:
                f.write("[]")

    def _new_backup_generation(self, tag=None):
        """Snapshot all three data files into BACKUP_DIR under a fresh date-time
        tag (empty list for any that doesn't exist yet), then keep only the
        newest MAX_BACKUP_GENERATIONS. `tag` is injectable for tests."""
        try:
            os.makedirs(BACKUP_DIR, exist_ok=True)
            if tag is None:
                tag = datetime.datetime.now().strftime(_BACKUP_TS_FMT)
            for prefix, src in _BACKUP_MEMBERS:
                self._write_backup_member(src, os.path.join(BACKUP_DIR, f"{prefix}-{tag}.bak"))
            self._prune_backups()
            return tag
        except Exception as e:
            print(f"[backup] new generation error: {e}")
            return None

    def _prune_backups(self):
        for old in self.list_backups()[MAX_BACKUP_GENERATIONS:]:
            for p in old["files"].values():
                try:
                    os.remove(p)
                except OSError:
                    pass

    def _refresh_newest_backup(self):
        """Overwrite the newest generation's files with the current state
        (keeping their names, so it stays newest). Creates the first generation
        if none exist yet."""
        gens = self.list_backups()
        if not gens:
            self._new_backup_generation()
            return
        newest = gens[0]
        try:
            os.makedirs(BACKUP_DIR, exist_ok=True)
            for prefix, src in _BACKUP_MEMBERS:
                dst = newest["files"].get(prefix) or os.path.join(
                    BACKUP_DIR, f"{prefix}-{newest['tag']}.bak")
                self._write_backup_member(src, dst)
        except Exception as e:
            print(f"[backup] refresh error: {e}")

    def _migrate_old_bak(self):
        """One-time: fold the legacy ``<file>.bak`` copies (older versions kept
        them next to the data files) into BACKUP_DIR as one generation, then
        delete them — so there's a single backup location. No-op once done."""
        legacy = [(prefix, src + ".bak") for prefix, src in _BACKUP_MEMBERS]
        present = [(pre, b) for pre, b in legacy if os.path.exists(b)]
        if not present:
            return
        try:
            os.makedirs(BACKUP_DIR, exist_ok=True)
            mt = max(os.path.getmtime(b) for _, b in present)
            tag = datetime.datetime.fromtimestamp(mt).strftime(_BACKUP_TS_FMT)
            for prefix, bak in legacy:
                dst = os.path.join(BACKUP_DIR, f"{prefix}-{tag}.bak")
                # fold the legacy .bak in (empty list if that member never had one)
                self._write_backup_member(bak, dst)
                if os.path.exists(bak):
                    os.remove(bak)
            self._prune_backups()
        except Exception as e:
            print(f"[backup] migrate error: {e}")

    def restore_backup(self, tag) -> bool:
        """Replace the live data (notes + archive + trash) with backup
        generation `tag`, then reload. Overwrites the current notes and is NOT
        auto-undone — the user keeps the current state by pressing "Backup Now"
        first. Returns True on success."""
        chosen = next((g for g in self.list_backups() if g["tag"] == tag), None)
        if chosen is None:
            return False
        payload = {}
        try:
            for prefix, _dst in _BACKUP_MEMBERS:
                src = chosen["files"].get(prefix)
                if src is not None:
                    with open(src, "rb") as f:
                        payload[prefix] = f.read()
        except Exception as e:
            print(f"[backup] restore read error: {e}")
            return False
        try:
            for prefix, dst in _BACKUP_MEMBERS:
                if prefix not in payload:
                    continue
                tmp = dst + ".tmp"
                with open(tmp, "wb") as f:
                    f.write(payload[prefix])
                os.replace(tmp, dst)
        except Exception as e:
            print(f"[backup] restore write error: {e}")
            return False
        self._reload_all_from_disk()
        return True

    def _reload_all_from_disk(self):
        """Tear down live note widgets and reload notes/trash/archive from disk."""
        for n in list(self.notes.values()):
            try:
                n.hide()
                n.deleteLater()
            except RuntimeError:
                pass
        self.notes.clear()
        self.trash_notes = []
        self.archived_notes = []
        self._load_trash_notes()
        self._load_archived_notes()
        self._load_notes()
        self._refresh_manager()

    def _try_read_list(self, path):
        """Return the JSON list at `path`, or None if missing/unreadable/not a list."""
        try:
            with open(path, encoding="utf-8") as f:
                data = json.load(f)
            return data if isinstance(data, list) else None
        except Exception:
            return None

    def _read_json_list(self, path, label):
        """Load a JSON list from `path` with corruption recovery.

        Returns (data, ok). If `path` is unreadable it is moved aside as
        ``<path>.corrupt-<timestamp>``, then the backup generations are tried
        newest→oldest until one parses (cascade); if none do, starts empty. A
        user-facing alert is queued and ok is False on any recovery. Missing
        file → ([], True)."""
        if not os.path.exists(path):
            return [], True
        data = self._try_read_list(path)
        if data is not None:
            return data, True
        # Corrupt: preserve the damaged file so nothing overwrites recoverable data.
        print(f"[load {label}] unreadable — attempting backup recovery")
        name = os.path.basename(path)
        ts = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
        preserved = f"{path}.corrupt-{ts}"
        try:
            os.replace(path, preserved)
            kept = os.path.basename(preserved)
        except Exception as e2:
            print(f"[load {label}] could not set aside corrupt file: {e2}")
            kept = None
        # Cascade through backup generations, newest first, until one is valid.
        prefix = _PREFIX_FOR_PATH.get(path)
        for gen in self.list_backups():
            src = gen["files"].get(prefix)
            if not src:
                continue
            recovered = self._try_read_list(src)
            if recovered is not None:
                self._storage_alerts.append(tr(
                    '"{name}" could not be read and was restored from the backup of {when}.'
                ).format(name=name, when=gen["label"]) + (
                    "\n" + tr('The damaged file was kept as "{kept}".').format(kept=kept)
                    if kept else ""))
                return recovered, False
        # No usable backup anywhere.
        self._storage_alerts.append(tr(
            '"{name}" could not be read and no valid backup was found.'
        ).format(name=name) + (
            "\n" + tr('The damaged file was kept as "{kept}" so no data was overwritten.').format(kept=kept)
            if kept else ""))
        return [], False

    def _load_notes(self):
        data, ok = self._read_json_list(DATA_FILE, "notes")
        self._notes_load_failed = not ok
        for nd in data:
            if not isinstance(nd, dict):
                print("[load] skipping malformed note entry (not an object)")
                continue
            try:
                note = StickyNote(self, nd.get("id"), nd)
                self.notes[note.note_id] = note
                if not note._hidden:      # honour a note the user hid before quitting
                    note.show()
            except Exception as e:
                print(f"[load] skipping unreadable note: {e}")

    def _save_trash_notes(self):
        try:
            tmp = TRASH_FILE + ".tmp"
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(self.trash_notes, f, indent=2, ensure_ascii=False)
            os.replace(tmp, TRASH_FILE)
        except Exception as e:
            print(f"[save trash] error: {e}")

    def _load_trash_notes(self):
        data, _ = self._read_json_list(TRASH_FILE, "trash")
        self.trash_notes = [d for d in data if isinstance(d, dict)]

    def _save_archived_notes(self):
        try:
            tmp = ARCHIVE_FILE + ".tmp"
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(self.archived_notes, f, indent=2, ensure_ascii=False)
            os.replace(tmp, ARCHIVE_FILE)
        except Exception as e:
            print(f"[save archive] error: {e}")

    def _load_archived_notes(self):
        data, _ = self._read_json_list(ARCHIVE_FILE, "archive")
        self.archived_notes = [d for d in data if isinstance(d, dict)]

    def _report_storage_alerts(self):
        """Show a single warning summarising any corrupt-file recovery from
        startup, so silent data problems never pass unnoticed."""
        if not self._storage_alerts:
            return
        msg = QMessageBox()
        msg.setIcon(QMessageBox.Icon.Warning)
        msg.setWindowTitle(tr("Notes recovery"))
        msg.setText(tr("Some data files could not be read."))
        msg.setInformativeText("\n\n".join(self._storage_alerts))
        msg.exec()
        self._storage_alerts.clear()

