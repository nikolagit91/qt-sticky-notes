"""Lightweight in-app translation — no external deps, no .qm/.ts toolchain.

Strings are keyed by their English source text. ``tr("Save")`` returns the
translation for the active language, or the English source unchanged when the
language is English or a key is missing. That graceful fallback means a string
that hasn't been translated yet simply stays English instead of breaking.

The active language is set once at startup (from settings, before the UI is
built) so ``tr()`` returns a stable value for the whole run; a change in
Settings is persisted and takes effect on the next launch.
"""

# code -> human-readable name (order = order shown in the Settings dropdown)
LANGUAGES = [
    ("en", "English"),
    ("hr", "Hrvatski"),
    ("de", "Deutsch"),
    ("es", "Español"),
    ("fr", "Français"),
    ("ru", "Русский"),
    ("zh", "简体中文"),
    ("pt", "Português (Brasil)"),
    ("it", "Italiano"),
    ("pl", "Polski"),
    ("ja", "日本語"),
]

_current = "en"


def set_language(code: str) -> None:
    global _current
    _current = code if any(code == c for c, _ in LANGUAGES) else "en"


def get_language() -> str:
    return _current


def language_name(code: str) -> str:
    for c, name in LANGUAGES:
        if c == code:
            return name
    return code


def tr(text: str) -> str:
    """Translate an English source string into the active language."""
    if _current == "en":
        return text
    return _TRANSLATIONS.get(_current, {}).get(text, text)


# ---------------------------------------------------------------------------
# Translations. Keyed by exact English source string (f-string templates keep
# their ``{}`` placeholders so call sites can still ``.format(...)``).
# Product name "Sticky Notes" is intentionally left untranslated (brand).
# ---------------------------------------------------------------------------
_TRANSLATIONS = {
    "de": {
        # ---- generic actions / buttons ----
        "OK": "OK",
        "Cancel": "Abbrechen",
        "Save": "Speichern",
        "Close": "Schließen",
        "Apply": "Übernehmen",
        "Select": "Auswählen",
        "Set": "Festlegen",
        "Refresh": "Aktualisieren",
        "Copy": "Kopieren",
        "Copied": "Kopiert",

        # ---- tray menu ----
        "New Note": "Neue Notiz",
        "Show All": "Alle anzeigen",
        "Hide All": "Alle ausblenden",
        "Lock All": "Alle sperren",
        "Unlock All": "Alle entsperren",
        "Notes Manager": "Notizverwaltung",
        "Settings": "Einstellungen",
        "About": "Über",
        "Toggle theme": "Design wechseln",
        "Quit": "Beenden",

        # ---- note header / toolbar ----
        "Note Options": "Notizoptionen",
        "Toggle Toolbar": "Symbolleiste ein-/ausblenden",
        "Lock / Unlock": "Sperren / Entsperren",
        "Hide Note": "Notiz ausblenden",
        "Always on Top": "Immer im Vordergrund",
        "Favorite": "Favorit",
        "Add to Favorites": "Zu Favoriten hinzufügen",
        "Remove from Favorites": "Aus Favoriten entfernen",
        "Bold (Ctrl+B)": "Fett (Strg+B)",
        "Italic (Ctrl+I)": "Kursiv (Strg+I)",
        "Underline (Ctrl+U)": "Unterstrichen (Strg+U)",
        "Strikethrough (Ctrl+S)": "Durchgestrichen (Strg+S)",
        "Bullet list": "Aufzählungsliste",
        "Checklist": "Checkliste",
        "Checklist — Tab to indent, drag a box or Alt+↑/↓ to reorder":
            "Checkliste — Tab zum Einrücken, Kästchen ziehen oder Alt+↑/↓ zum Umsortieren",
        "Checklist progress (done / total)": "Checklisten-Fortschritt (erledigt / gesamt)",
        "Increase font size": "Schriftgröße erhöhen",
        "Decrease font size": "Schriftgröße verringern",
        "Text Colour": "Textfarbe",
        "Font family": "Schriftart",
        "Click to set exact size": "Klicken für genaue Größe",
        "Click to open colour picker": "Klicken für Farbauswahl",
        "Write your note here…": "Schreib deine Notiz hier…",
        "More fonts…": "Weitere Schriftarten…",

        # ---- note context menu ----
        "Change Colour…": "Farbe ändern…",
        "Copy Note": "Notiz kopieren",
        "Rename…": "Umbenennen…",
        "Rename": "Umbenennen",          # Manager row menu (sits next to "Export")
        "Paste as plain text": "Als reinen Text einfügen",
        "Move to Trash": "In den Papierkorb verschieben",
        "Custom colour:": "Eigene Farbe:",

        # ---- list styles (glyph kept) ----
        "●  Disc": "●  Kreis",
        "▪  Square": "▪  Quadrat",
        "1.  Decimal": "1.  Zahlen",
        "a.  Lower alpha": "a.  Kleinbuchstaben",
        "i.  Lower roman": "i.  Kleine römische Zahlen",
        "✕  Remove list": "✕  Liste entfernen",

        # ---- rename dialog ----
        "Rename note": "Notiz umbenennen",
        "Note name:": "Notizname:",
        "Leave empty to use the automatic name (first line of the note).":
            "Leer lassen für den automatischen Namen (erste Zeile der Notiz).",
        "Untitled": "Unbenannt",

        # ---- reminder dialog ----
        "Reminder": "Erinnerung",
        "Set reminder…": "Erinnerung festlegen…",
        "Reminder: ": "Erinnerung: ",
        "Reminder: {} — change…": "Erinnerung: {} — ändern…",
        "Current: ": "Aktuell: ",
        "Quick options:": "Schnelloptionen:",
        "Or a specific time:": "Oder eine bestimmte Uhrzeit:",
        "Or a specific date and time:": "Oder ein bestimmtes Datum und Uhrzeit:",
        "Date": "Datum",
        "Time": "Uhrzeit",
        "In 1 min": "In 1 Min.",
        "In 5 min": "In 5 Min.",
        "In 10 min": "In 10 Min.",
        "In 30 min": "In 30 Min.",
        "In 1 hour": "In 1 Stunde",
        "In 3 hours": "In 3 Stunden",
        "In 8 hours": "In 8 Stunden",
        "In 24 hours": "In 24 Stunden",
        "Remove reminder": "Erinnerung entfernen",

        # ---- export ----
        "Export Note": "Notiz exportieren",
        "Export Failed": "Export fehlgeschlagen",
        "Plain text (.txt)": "Reiner Text (.txt)",
        "OpenDocument (.odt)": "OpenDocument (.odt)",
        "PDF (.pdf)": "PDF (.pdf)",
        "Text files (*.txt)": "Textdateien (*.txt)",
        "OpenDocument (*.odt)": "OpenDocument (*.odt)",
        "PDF (*.pdf)": "PDF (*.pdf)",
        "(empty note)": "(leere Notiz)",

        # ---- manager ----
        "Restore All": "Alle wiederherstellen",
        "Delete All": "Alle löschen",
        "Search notes…": "Notizen durchsuchen…",
        "Search notes": "Notizen durchsuchen",
        "Search Notes…": "Notizen durchsuchen…",
        "No matching notes": "Keine passenden Notizen",
        "Global shortcut for searching notes": "Globale Tastenkombination zum Durchsuchen von Notizen",
        "Scroll on tray icon to raise/lower notes": "Scrollen auf dem Tray-Symbol hebt/senkt Notizen",
        "Scroll up = bring visible notes to front; scroll down = send them behind other windows. Pinned notes are left alone.":
            "Hochscrollen = sichtbare Notizen nach vorne holen; runterscrollen = hinter andere Fenster schicken. Angepinnte Notizen bleiben unberührt.",
        "Press {} anywhere to open the search palette. Rebind it in GNOME Settings → Keyboard → Custom Shortcuts.":
            "Drücke {} an beliebiger Stelle, um die Suche zu öffnen. Änderbar unter GNOME-Einstellungen → Tastatur → Eigene Tastenkombinationen.",
        "Registers a GNOME shortcut ({}) to open a search box for finding a note from anywhere.":
            "Registriert eine GNOME-Tastenkombination ({}), um von überall aus ein Suchfeld für Notizen zu öffnen.",
        "Restore": "Wiederherstellen",
        "Delete permanently": "Endgültig löschen",
        "Active": "Aktiv",
        "Archive": "Archiv",
        "Trash": "Papierkorb",
        "Active ({})": "Aktiv ({})",
        "Active ({}/{})": "Aktiv ({}/{})",
        "Archive ({})": "Archiv ({})",
        "Archive ({}/{})": "Archiv ({}/{})",
        "Trash ({})": "Papierkorb ({})",
        "Trash ({}/{})": "Papierkorb ({}/{})",
        "{} matches": "{} Treffer",
        "{} active · {} in trash": "{} aktiv · {} im Papierkorb",
        "{} active · {} archived · {} in trash": "{} aktiv · {} archiviert · {} im Papierkorb",
        "Archive Full": "Archiv voll",
        "Active Full": "Aktiv voll",
        "Partly Restored": "Teilweise wiederhergestellt",
        "Archive is full ({} notes).\nRemove something from the Archive first.":
            "Das Archiv ist voll ({} Notizen).\nEntferne zuerst etwas aus dem Archiv.",
        "You already have {} active notes — the maximum.\nArchive or delete one first.":
            "Du hast bereits {} aktive Notizen — das Maximum.\nArchiviere oder lösche zuerst eine.",
        "You already have {} active notes — the maximum.":
            "Du hast bereits {} aktive Notizen — das Maximum.",
        "Restored {} note(s). {} could not be restored — the active limit ({}) was reached.":
            "{} Notiz(en) wiederhergestellt. {} konnten nicht wiederhergestellt werden — das Aktiv-Limit ({}) wurde erreicht.",
        "Permanently delete all {} note(s) in Trash?\nThis cannot be undone.":
            "Alle {} Notiz(en) im Papierkorb endgültig löschen?\nDies kann nicht rückgängig gemacht werden.",

        # ---- settings dialog ----
        "Start automatically on login": "Automatisch bei der Anmeldung starten",
        "Creates an autostart entry in ~/.config/autostart/":
            "Erstellt einen Autostart-Eintrag in ~/.config/autostart/",
        "Requires GNOME (gsettings). Bind a shortcut manually instead.":
            "Erfordert GNOME (gsettings). Lege stattdessen manuell eine Tastenkombination fest.",
        "Global shortcut for new note": "Globale Tastenkombination für neue Notiz",
        "Global shortcut for new note from clipboard":
            "Globale Tastenkombination für Notiz aus Zwischenablage",
        "Press {} anywhere to create a new note. Rebind it in GNOME Settings → Keyboard → Custom Shortcuts.":
            "Drücke {} an beliebiger Stelle, um eine neue Notiz zu erstellen. Änderbar unter GNOME-Einstellungen → Tastatur → Eigene Tastenkombinationen.",
        "Press {} anywhere to create a note from the clipboard. Rebind it in GNOME Settings → Keyboard → Custom Shortcuts.":
            "Drücke {} an beliebiger Stelle, um eine Notiz aus der Zwischenablage zu erstellen. Änderbar unter GNOME-Einstellungen → Tastatur → Eigene Tastenkombinationen.",
        "Registers a GNOME shortcut ({}) to create a new note.":
            "Registriert eine GNOME-Tastenkombination ({}) zum Erstellen einer neuen Notiz.",
        "Registers a GNOME shortcut ({}) to create a note pre-filled with the clipboard contents.":
            "Registriert eine GNOME-Tastenkombination ({}) für eine Notiz, die mit dem Inhalt der Zwischenablage vorausgefüllt ist.",
        "UI Scale": "Oberflächenskalierung",
        "Scales UI text and note content (100%–200%)":
            "Skaliert den Oberflächentext und den Notizinhalt (100%–200%)",
        "Scales the whole interface, text and icons (100%–200%).":
            "Skaliert die gesamte Oberfläche, Text und Symbole (100%–200%).",
        "Restart Sticky Notes to apply the new scale.":
            "Starte Sticky Notes neu, um die neue Skalierung zu übernehmen.",
        "Restart now": "Jetzt neu starten",
        "Default font size": "Standardschriftgröße",
        "Choose Font": "Schriftart wählen",
        "Search fonts…": "Schriftarten durchsuchen…",
        "Apply Font to New Notes": "Schrift auf neue Notizen anwenden",
        "Apply to New Notes": "Auf neue Notizen anwenden",
        "Note": "Notiz",
        "Default size for new notes": "Standardgröße für neue Notizen",
        "Width": "Breite",
        "Height": "Höhe",
        "Background opacity": "Hintergrundtransparenz",
        "Makes the note paper see-through; text stays sharp. Applies to all current and future notes.":
            "Macht das Notizpapier durchscheinend; der Text bleibt scharf. Gilt für alle aktuellen und zukünftigen Notizen.",
        "Auto backup every": "Automatische Sicherung alle",
        "15 minutes": "15 Minuten",
        "30 minutes": "30 Minuten",
        "1 hour": "1 Stunde",
        "2 hours": "2 Stunden",
        "4 hours": "4 Stunden",
        "8 hours": "8 Stunden",
        "12 hours": "12 Stunden",
        "24 hours": "24 Stunden",
        "Backup Now": "Jetzt sichern",
        "Last backup: {}": "Letzte Sicherung: {}",
        "No backup yet": "Noch keine Sicherung",
        "Restore from Backup": "Aus Sicherung wiederherstellen",
        "Notes recovery": "Notizwiederherstellung",
        "Some data files could not be read.": "Einige Datendateien konnten nicht gelesen werden.",
        '"{name}" could not be read and was restored from its backup.':
            '„{name}” konnte nicht gelesen werden und wurde aus der Sicherung wiederhergestellt.',
        '"{name}" could not be read and no valid backup was found.':
            '„{name}” konnte nicht gelesen werden und es wurde keine gültige Sicherung gefunden.',
        'The damaged file was kept as "{kept}".':
            'Die beschädigte Datei wurde als „{kept}” aufbewahrt.',
        'The damaged file was kept as "{kept}" so no data was overwritten.':
            'Die beschädigte Datei wurde als „{kept}” aufbewahrt, damit keine Daten überschrieben wurden.',
        "Restore notes from backup dated:\n{}\n\n⚠  Current notes will be replaced!":
            "Notizen aus der Sicherung vom:\n{}\n\n⚠  wiederherstellen? Aktuelle Notizen werden ersetzt!",
        "EXPORT / IMPORT": "EXPORT / IMPORT",
        "Export to JSON…": "Als JSON exportieren…",
        "Import from JSON…": "Aus JSON importieren…",
        "Language": "Sprache",
        "Language changes apply after restart.": "Sprachänderungen werden nach dem Neustart wirksam.",
        # settings tab labels
        "General": "Allgemein",
        "Backup": "Sicherung",
        # snapping
        "Snapping": "Einrasten",
        "Snapping && Tray": "Einrasten && Tray",
        "Tray": "Tray",
        "Snap to grid": "Am Raster einrasten",
        "Snap to other notes": "An anderen Notizen einrasten",
        "Snap size to grid": "Größe am Raster einrasten",
        "Grid size": "Rastergröße",
        "Notes snap when you drop them or finish resizing. Snap to grid and snap size to grid align a note's position and size to an invisible grid; snap to other notes lines edges up with nearby notes. The grid size below sets the spacing.":
            "Notizen rasten ein, wenn du sie ablegst oder die Größenänderung beendest. Am Raster einrasten und Größe am Raster einrasten richten Position und Größe einer Notiz an einem unsichtbaren Raster aus; an anderen Notizen einrasten richtet Kanten an benachbarten Notizen aus. Die Rastergröße unten legt den Abstand fest.",

        # ---- about dialog ----
        "About Sticky Notes": "Über Sticky Notes",
        "Version {}": "Version {}",
        "A lightweight sticky notes application\nfor Ubuntu desktop.\n\nBuilt with Python & PyQt6":
            "Eine schlanke Anwendung für Haftnotizen\nfür den Ubuntu-Desktop.\n\nErstellt mit Python & PyQt6",
        "View on GitHub": "Auf GitHub ansehen",
        "Made by Nikola Javorina": "Erstellt von Nikola Javorina",
        "For the sharpest result, keep system scaling at 100% and use this.": "Für die schärfste Darstellung: Systemskalierung auf 100% lassen und dies verwenden.",
        "Buy me a coffee": "Spendier mir einen Kaffee",

        # ---- message boxes ----
        "Limit Reached": "Limit erreicht",
        "Maximum of {} active notes reached.\nArchive or move some notes to Trash before creating new ones.":
            "Maximum von {} aktiven Notizen erreicht.\nArchiviere oder verschiebe einige Notizen in den Papierkorb, bevor du neue erstellst.",
        "Maximum of 20 active notes reached.\nMove some notes to Trash before creating new ones.":
            "Maximum von 20 aktiven Notizen erreicht.\nVerschiebe einige Notizen in den Papierkorb, bevor du neue erstellst.",
        "Export Complete": "Export abgeschlossen",
        "Export All": "Alle exportieren",
        "Export": "Exportieren",
        "There are no archived notes to export.": "Es gibt keine archivierten Notizen zum Exportieren.",
        "Export all archived notes to a JSON file.": "Exportiert alle archivierten Notizen in eine JSON-Datei.",
        "Backup saves local “.bak” copies of ALL your notes (active, archived "
        "and trash), kept next to your data on this computer. Restore brings all "
        "three back.":
            "Die Sicherung speichert lokale „.bak”-Kopien ALLER deiner Notizen (aktiv, "
            "archiviert und Papierkorb) neben deinen Daten auf diesem Computer. Die "
            "Wiederherstellung bringt alle drei zurück.",
        "Export writes a portable JSON file of your ACTIVE notes (to move to "
        "another computer or re-import). Import always brings notes in as active. "
        "To export archived notes, use “Export All” in the Manager's Archive tab.":
            "Der Export schreibt eine portable JSON-Datei deiner AKTIVEN Notizen (zum "
            "Verschieben auf einen anderen Computer oder erneuten Import). Der Import "
            "fügt Notizen immer als aktiv hinzu. Um archivierte Notizen zu exportieren, "
            "nutze „Alle exportieren” in der Archiv-Registerkarte der Verwaltung.",
        "Import Complete": "Import abgeschlossen",
        "Import Failed": "Import fehlgeschlagen",
        "Import — Limit Reached": "Import — Limit erreicht",
        "You have {} active note(s). The export file contains {} note(s).\n\nYou can import at most {} note(s).\n\nImport the first {} and skip the rest?":
            "Du hast {} aktive Notiz(en). Die Exportdatei enthält {} Notiz(en).\n\nDu kannst höchstens {} Notiz(en) importieren.\n\nDie ersten {} importieren und den Rest überspringen?",
        "Exported {} note(s) to:\n{}": "{} Notiz(en) exportiert nach:\n{}",
        "Imported {} note(s) successfully.": "{} Notiz(en) erfolgreich importiert.",
        "Could not read export file:\n{}": "Exportdatei konnte nicht gelesen werden:\n{}",
        "You already have {} active notes — the maximum.\nMove some notes to Trash before importing.":
            "Du hast bereits {} aktive Notizen — das Maximum.\nVerschiebe einige Notizen in den Papierkorb, bevor du importierst.",
        "You already have 20 active notes — the maximum.\nMove some notes to Trash before importing.":
            "Du hast bereits 20 aktive Notizen — das Maximum.\nVerschiebe einige Notizen in den Papierkorb, bevor du importierst.",

        # ---- notifications ----
        "Sticky Notes — Reminder": "Sticky Notes — Erinnerung",
        "Snooze 10 min": "10 Min. später erinnern",

        # ---- settings: Note tab (auto-contrast + clean mode) ----
        "Adjust text & icon colour to note background":
            "Text- und Symbolfarbe an den Notizhintergrund anpassen",
        "Dark notes get light icons and text automatically. Turn off to keep the classic dark ink.":
            "Dunkle Notizen erhalten automatisch helle Symbole und Text. Ausschalten, um die klassische dunkle Tinte beizubehalten.",
        "Auto-hide toolbar and header until you hover the note":
            "Symbolleiste und Kopfzeile automatisch ausblenden, bis du mit der Maus über die Notiz fährst",
        "Note border": "Notizrahmen",
        "Off": "Aus",
        "Always": "Immer",
        "Auto (light notes only)": "Automatisch (nur helle Notizen)",
        "Auto shows a border only on light notes, where it helps them stand out from a light background.":
            "Automatisch zeigt einen Rahmen nur bei hellen Notizen, wo er hilft, sich von einem hellen Hintergrund abzuheben.",
        "Notes show only their text at rest; hover the top of a note to bring the controls back. "
        "A single click on the header keeps the controls up and lets you nudge the note with the arrow keys; click elsewhere to hide them again. "
        "Double-click a note's header to keep its controls open while you edit it; "
        "double-click again to hand that note back to auto-hide.":
            "Notizen zeigen im Ruhezustand nur ihren Text; fahre mit der Maus über den oberen Rand einer Notiz, um die Steuerelemente zurückzuholen. "
            "Ein einzelner Klick auf die Kopfzeile hält die Steuerelemente offen und lässt dich die Notiz mit den Pfeiltasten verschieben; ein Klick woanders blendet sie wieder aus. "
            "Doppelklicke auf die Kopfzeile einer Notiz, um ihre Steuerelemente offen zu halten, während du sie bearbeitest; "
            "ein weiterer Doppelklick gibt die Notiz zurück an das automatische Ausblenden.",
        "Code block": "Codeblock",
        "Inline code": "Inline-Code",
        "Enable code blocks": "Codeblöcke aktivieren",
        "Adds code-block { } and inline-code buttons to the toolbar, and enables their shortcuts (Ctrl+M for inline code, Ctrl+Shift+M for a code block). Niche — off by default.":
            "Fügt Codeblock-{ }- und Inline-Code-Schaltflächen zur Symbolleiste hinzu und aktiviert ihre Tastenkombinationen (Strg+M für Inline-Code, Strg+Umschalt+M für einen Codeblock). Nische — standardmäßig aus.",

        # ---- settings: appearance (theme) ----
        "Appearance": "Erscheinungsbild",
        "Window theme": "Fensterdesign",
        "Theme": "Design",
        "Light": "Hell",
        "Dark": "Dunkel",
        "Auto": "Automatisch",
        "Dark from": "Dunkel ab",
        "until": "bis",
        "Auto switches to Dark between these times; the theme changes within a minute of each boundary. The tray's Toggle theme then lasts only until the next boundary.":
            "Automatisch wechselt zwischen diesen Zeiten auf Dunkel; das Design ändert sich innerhalb einer Minute nach jeder Grenze. „Design wechseln” im Tray gilt dann nur bis zur nächsten Grenze.",
        "Sets the look of the app's windows, menus and notes. Switching to Dark gives every note without its own dark colour a dark default; each note keeps separate colours for Light and Dark, so switching back restores the light one. Notes and the main windows recolour instantly; a few helper windows (About, the shortcut list, search) update the next time you open them — no restart needed.":
            "Legt das Aussehen der Fenster, Menüs und Notizen der App fest. Der Wechsel zu Dunkel gibt jeder Notiz ohne eigene dunkle Farbe eine dunkle Standardfarbe; jede Notiz behält getrennte Farben für Hell und Dunkel, sodass der Rückwechsel die helle wiederherstellt. Notizen und die Hauptfenster ändern sofort ihre Farbe; einige Hilfsfenster (Über, die Liste der Tastenkombinationen, Suche) aktualisieren sich beim nächsten Öffnen — kein Neustart nötig.",

        # ---- settings: tray scroll ----
        "Scroll the tray icon to bring notes to front":
            "Über dem Tray-Symbol scrollen, um Notizen nach vorne zu holen",
        "Scroll up on the tray icon to raise your visible notes above "
        "other windows. Pinned notes are unaffected.":
            "Auf dem Tray-Symbol nach oben scrollen, um deine sichtbaren Notizen über andere "
            "Fenster zu heben. Angepinnte Notizen bleiben unberührt.",

        # ---- settings: Backup tab + restore dialogs ----
        "Backups": "Sicherungen",
        "Backups save copies of ALL your notes (active, archived and trash) in a "
        "backups folder on this computer. \"Backup Now\" and the auto-backup "
        "interval each add a new restore point (the 5 most recent are kept); the "
        "daily auto-backup keeps the latest one fresh. \"Restore from Backup…\" "
        "lets you pick which one to go back to (this overwrites your current notes).":
            "Sicherungen speichern Kopien ALLER deiner Notizen (aktiv, archiviert und "
            "Papierkorb) in einem backups-Ordner auf diesem Computer. „Jetzt sichern” und "
            "das Intervall der automatischen Sicherung fügen jeweils einen neuen "
            "Wiederherstellungspunkt hinzu (die 5 neuesten werden aufbewahrt); die tägliche "
            "automatische Sicherung hält die neueste aktuell. „Aus Sicherung "
            "wiederherstellen…” lässt dich auswählen, zu welcher du zurückkehren möchtest "
            "(dies überschreibt deine aktuellen Notizen).",
        "Restore from Backup…": "Aus Sicherung wiederherstellen…",
        "Restore your notes from an earlier backup": "Stelle deine Notizen aus einer früheren Sicherung wieder her",
        "The 5 most recent backups. Restoring overwrites your current "
        "notes and cannot be undone — press \"Backup Now\" first if you "
        "want to keep them.":
            "Die 5 neuesten Sicherungen. Die Wiederherstellung überschreibt deine "
            "aktuellen Notizen und kann nicht rückgängig gemacht werden — drücke zuerst "
            "„Jetzt sichern”, wenn du sie behalten möchtest.",
        "No backups yet.": "Noch keine Sicherungen.",
        "(latest)": "(neueste)",
        "Restore selected": "Auswahl wiederherstellen",
        "Replace your current notes with the backup from {}?\n\n"
        "This overwrites your current notes and cannot be undone. "
        "Use \"Backup Now\" first if you want to keep them.":
            "Deine aktuellen Notizen durch die Sicherung vom {} ersetzen?\n\n"
            "Dies überschreibt deine aktuellen Notizen und kann nicht rückgängig gemacht "
            "werden. Nutze zuerst „Jetzt sichern”, wenn du sie behalten möchtest.",
        "Restore complete": "Wiederherstellung abgeschlossen",
        "Restore failed": "Wiederherstellung fehlgeschlagen",
        "Your notes were restored from the selected backup.":
            "Deine Notizen wurden aus der ausgewählten Sicherung wiederhergestellt.",
        "That backup could not be restored.": "Diese Sicherung konnte nicht wiederhergestellt werden.",
        "\"{name}\" could not be read and was restored from the backup of {when}.":
            "„{name}” konnte nicht gelesen werden und wurde aus der Sicherung vom {when} wiederhergestellt.",

        # ---- keyboard shortcuts (tray + cheat-sheet) ----
        "Keyboard shortcuts…": "Tastenkombinationen…",
        "Keyboard shortcuts": "Tastenkombinationen",
        "Turn these on or off in Settings.": "In den Einstellungen ein- oder ausschalten.",
        # ---- cheat-sheet tabs + section notes (translated via tr(title), so the
        # AST scan in test_i18n_hr_complete can't see them — that test checks the
        # shortcuts catalog explicitly instead) ----
        "Global": "Global",
        "Text & lists": "Text & Listen",
        "Code": "Code",
        "Windows": "Fenster",
        "These act on the note you are using right now.":
            "Diese wirken sich auf die Notiz aus, die du gerade verwendest.",
        "These only do anything while \"Enable code blocks\" is on (Settings → Note).":
            "Diese wirken nur, wenn „Codeblöcke aktivieren” eingeschaltet ist (Einstellungen → Notiz).",

        # ---- export: PNG ----
        "Image (.png)": "Bild (.png)",
        "PNG image (*.png)": "PNG-Bild (*.png)",
    },
    "es": {
        # ---- generic actions / buttons ----
        "OK": "Aceptar",
        "Cancel": "Cancelar",
        "Save": "Guardar",
        "Close": "Cerrar",
        "Apply": "Aplicar",
        "Select": "Seleccionar",
        "Set": "Establecer",
        "Refresh": "Actualizar",
        "Copy": "Copiar",
        "Copied": "Copiado",

        # ---- tray menu ----
        "New Note": "Nueva nota",
        "Show All": "Mostrar todo",
        "Hide All": "Ocultar todo",
        "Lock All": "Bloquear todo",
        "Unlock All": "Desbloquear todo",
        "Notes Manager": "Administrador de notas",
        "Settings": "Ajustes",
        "About": "Acerca de",
        "Toggle theme": "Cambiar tema",
        "Quit": "Salir",

        # ---- note header / toolbar ----
        "Note Options": "Opciones de la nota",
        "Toggle Toolbar": "Mostrar/ocultar barra de herramientas",
        "Lock / Unlock": "Bloquear / desbloquear",
        "Hide Note": "Ocultar nota",
        "Always on Top": "Siempre visible",
        "Favorite": "Favorito",
        "Add to Favorites": "Añadir a favoritos",
        "Remove from Favorites": "Quitar de favoritos",
        "Bold (Ctrl+B)": "Negrita (Ctrl+B)",
        "Italic (Ctrl+I)": "Cursiva (Ctrl+I)",
        "Underline (Ctrl+U)": "Subrayado (Ctrl+U)",
        "Strikethrough (Ctrl+S)": "Tachado (Ctrl+S)",
        "Bullet list": "Lista con viñetas",
        "Checklist": "Lista de tareas",
        "Checklist — Tab to indent, drag a box or Alt+↑/↓ to reorder":
            "Lista de tareas — Tab para sangrar, arrastra una casilla o Alt+↑/↓ para reordenar",
        "Checklist progress (done / total)": "Progreso de la lista (hechas / total)",
        "Increase font size": "Aumentar tamaño de fuente",
        "Decrease font size": "Reducir tamaño de fuente",
        "Text Colour": "Color del texto",
        "Font family": "Tipo de fuente",
        "Click to set exact size": "Haz clic para fijar el tamaño exacto",
        "Click to open colour picker": "Haz clic para abrir el selector de color",
        "Write your note here…": "Escribe tu nota aquí…",
        "More fonts…": "Más fuentes…",

        # ---- note context menu ----
        "Change Colour…": "Cambiar color…",
        "Copy Note": "Copiar nota",
        "Rename…": "Renombrar…",
        "Rename": "Renombrar",          # Manager row menu (sits next to "Export")
        "Paste as plain text": "Pegar como texto sin formato",
        "Move to Trash": "Mover a la papelera",
        "Custom colour:": "Color personalizado:",

        # ---- list styles (glyph kept) ----
        "●  Disc": "●  Círculo",
        "▪  Square": "▪  Cuadrado",
        "1.  Decimal": "1.  Números",
        "a.  Lower alpha": "a.  Minúsculas",
        "i.  Lower roman": "i.  Romanos minúsculos",
        "✕  Remove list": "✕  Quitar lista",

        # ---- rename dialog ----
        "Rename note": "Renombrar nota",
        "Note name:": "Nombre de la nota:",
        "Leave empty to use the automatic name (first line of the note).":
            "Déjalo vacío para usar el nombre automático (primera línea de la nota).",
        "Untitled": "Sin título",

        # ---- reminder dialog ----
        "Reminder": "Recordatorio",
        "Set reminder…": "Establecer recordatorio…",
        "Reminder: ": "Recordatorio: ",
        "Reminder: {} — change…": "Recordatorio: {} — cambiar…",
        "Current: ": "Actual: ",
        "Quick options:": "Opciones rápidas:",
        "Or a specific time:": "O una hora específica:",
        "Or a specific date and time:": "O una fecha y hora específicas:",
        "Date": "Fecha",
        "Time": "Hora",
        "In 1 min": "En 1 min",
        "In 5 min": "En 5 min",
        "In 10 min": "En 10 min",
        "In 30 min": "En 30 min",
        "In 1 hour": "En 1 hora",
        "In 3 hours": "En 3 horas",
        "In 8 hours": "En 8 horas",
        "In 24 hours": "En 24 horas",
        "Remove reminder": "Quitar recordatorio",

        # ---- export ----
        "Export Note": "Exportar nota",
        "Export Failed": "Error al exportar",
        "Plain text (.txt)": "Texto sin formato (.txt)",
        "OpenDocument (.odt)": "OpenDocument (.odt)",
        "PDF (.pdf)": "PDF (.pdf)",
        "Text files (*.txt)": "Archivos de texto (*.txt)",
        "OpenDocument (*.odt)": "OpenDocument (*.odt)",
        "PDF (*.pdf)": "PDF (*.pdf)",
        "(empty note)": "(nota vacía)",

        # ---- manager ----
        "Restore All": "Restaurar todo",
        "Delete All": "Eliminar todo",
        "Search notes…": "Buscar notas…",
        "Search notes": "Buscar notas",
        "Search Notes…": "Buscar notas…",
        "No matching notes": "No hay notas coincidentes",
        "Global shortcut for searching notes": "Atajo global para buscar notas",
        "Scroll on tray icon to raise/lower notes": "Desplaza sobre el icono de la bandeja para subir/bajar notas",
        "Scroll up = bring visible notes to front; scroll down = send them behind other windows. Pinned notes are left alone.":
            "Desplazar hacia arriba = trae las notas visibles al frente; hacia abajo = las envía detrás de otras ventanas. Las notas fijadas no se ven afectadas.",
        "Press {} anywhere to open the search palette. Rebind it in GNOME Settings → Keyboard → Custom Shortcuts.":
            "Pulsa {} en cualquier lugar para abrir la paleta de búsqueda. Cámbialo en Configuración de GNOME → Teclado → Atajos personalizados.",
        "Registers a GNOME shortcut ({}) to open a search box for finding a note from anywhere.":
            "Registra un atajo de GNOME ({}) para abrir un cuadro de búsqueda y encontrar una nota desde cualquier lugar.",
        "Restore": "Restaurar",
        "Delete permanently": "Eliminar permanentemente",
        "Active": "Activas",
        "Archive": "Archivo",
        "Trash": "Papelera",
        "Active ({})": "Activas ({})",
        "Active ({}/{})": "Activas ({}/{})",
        "Archive ({})": "Archivo ({})",
        "Archive ({}/{})": "Archivo ({}/{})",
        "Trash ({})": "Papelera ({})",
        "Trash ({}/{})": "Papelera ({}/{})",
        "{} matches": "{} coincidencias",
        "{} active · {} in trash": "{} activas · {} en la papelera",
        "{} active · {} archived · {} in trash": "{} activas · {} archivadas · {} en la papelera",
        "Archive Full": "Archivo lleno",
        "Active Full": "Activas al máximo",
        "Partly Restored": "Restaurado parcialmente",
        "Archive is full ({} notes).\nRemove something from the Archive first.":
            "El archivo está lleno ({} notas).\nQuita algo del archivo primero.",
        "You already have {} active notes — the maximum.\nArchive or delete one first.":
            "Ya tienes {} notas activas — el máximo.\nArchiva o elimina una primero.",
        "You already have {} active notes — the maximum.":
            "Ya tienes {} notas activas — el máximo.",
        "Restored {} note(s). {} could not be restored — the active limit ({}) was reached.":
            "Se restauraron {} nota(s). {} no se pudieron restaurar — se alcanzó el límite activo ({}).",
        "Permanently delete all {} note(s) in Trash?\nThis cannot be undone.":
            "¿Eliminar permanentemente las {} nota(s) de la papelera?\nEsto no se puede deshacer.",

        # ---- settings dialog ----
        "Start automatically on login": "Iniciar automáticamente al iniciar sesión",
        "Creates an autostart entry in ~/.config/autostart/":
            "Crea una entrada de inicio automático en ~/.config/autostart/",
        "Requires GNOME (gsettings). Bind a shortcut manually instead.":
            "Requiere GNOME (gsettings). Asigna un atajo manualmente en su lugar.",
        "Global shortcut for new note": "Atajo global para nueva nota",
        "Global shortcut for new note from clipboard":
            "Atajo global para nota desde el portapapeles",
        "Press {} anywhere to create a new note. Rebind it in GNOME Settings → Keyboard → Custom Shortcuts.":
            "Pulsa {} en cualquier lugar para crear una nueva nota. Cámbialo en Configuración de GNOME → Teclado → Atajos personalizados.",
        "Press {} anywhere to create a note from the clipboard. Rebind it in GNOME Settings → Keyboard → Custom Shortcuts.":
            "Pulsa {} en cualquier lugar para crear una nota desde el portapapeles. Cámbialo en Configuración de GNOME → Teclado → Atajos personalizados.",
        "Registers a GNOME shortcut ({}) to create a new note.":
            "Registra un atajo de GNOME ({}) para crear una nueva nota.",
        "Registers a GNOME shortcut ({}) to create a note pre-filled with the clipboard contents.":
            "Registra un atajo de GNOME ({}) para crear una nota con el contenido del portapapeles ya incluido.",
        "UI Scale": "Escala de la interfaz",
        "Scales UI text and note content (100%–200%)":
            "Escala el texto de la interfaz y el contenido de las notas (100%–200%)",
        "Scales the whole interface, text and icons (100%–200%).":
            "Escala toda la interfaz, texto e iconos (100%–200%).",
        "Restart Sticky Notes to apply the new scale.":
            "Reinicia Sticky Notes para aplicar la nueva escala.",
        "Restart now": "Reiniciar ahora",
        "Default font size": "Tamaño de fuente predeterminado",
        "Choose Font": "Elegir fuente",
        "Search fonts…": "Buscar fuentes…",
        "Apply Font to New Notes": "Aplicar fuente a las notas nuevas",
        "Apply to New Notes": "Aplicar a notas nuevas",
        "Note": "Nota",
        "Default size for new notes": "Tamaño predeterminado de las notas nuevas",
        "Width": "Ancho",
        "Height": "Alto",
        "Background opacity": "Opacidad del fondo",
        "Makes the note paper see-through; text stays sharp. Applies to all current and future notes.":
            "Hace transparente el papel de la nota; el texto se mantiene nítido. Se aplica a todas las notas actuales y futuras.",
        "Auto backup every": "Copia de seguridad automática cada",
        "15 minutes": "15 minutos",
        "30 minutes": "30 minutos",
        "1 hour": "1 hora",
        "2 hours": "2 horas",
        "4 hours": "4 horas",
        "8 hours": "8 horas",
        "12 hours": "12 horas",
        "24 hours": "24 horas",
        "Backup Now": "Hacer copia ahora",
        "Last backup: {}": "Última copia: {}",
        "No backup yet": "Todavía no hay copia",
        "Restore from Backup": "Restaurar desde copia de seguridad",
        "Notes recovery": "Recuperación de notas",
        "Some data files could not be read.": "Algunos archivos de datos no se pudieron leer.",
        '"{name}" could not be read and was restored from its backup.':
            '"{name}" no se pudo leer y se restauró desde su copia de seguridad.',
        '"{name}" could not be read and no valid backup was found.':
            '"{name}" no se pudo leer y no se encontró ninguna copia de seguridad válida.',
        'The damaged file was kept as "{kept}".':
            'El archivo dañado se conservó como "{kept}".',
        'The damaged file was kept as "{kept}" so no data was overwritten.':
            'El archivo dañado se conservó como "{kept}" para no sobrescribir ningún dato.',
        "Restore notes from backup dated:\n{}\n\n⚠  Current notes will be replaced!":
            "Restaurar notas desde la copia de seguridad del:\n{}\n\n⚠  ¡Las notas actuales serán reemplazadas!",
        "EXPORT / IMPORT": "EXPORTAR / IMPORTAR",
        "Export to JSON…": "Exportar a JSON…",
        "Import from JSON…": "Importar desde JSON…",
        "Language": "Idioma",
        "Language changes apply after restart.": "Los cambios de idioma se aplican tras reiniciar.",
        # settings tab labels
        "General": "General",
        "Backup": "Copia de seguridad",
        # snapping
        "Snapping": "Ajuste",
        "Snapping && Tray": "Ajuste && bandeja",
        "Tray": "Bandeja",
        "Snap to grid": "Ajustar a la cuadrícula",
        "Snap to other notes": "Ajustar a otras notas",
        "Snap size to grid": "Ajustar tamaño a la cuadrícula",
        "Grid size": "Tamaño de la cuadrícula",
        "Notes snap when you drop them or finish resizing. Snap to grid and snap size to grid align a note's position and size to an invisible grid; snap to other notes lines edges up with nearby notes. The grid size below sets the spacing.":
            "Las notas se ajustan al soltarlas o al terminar de cambiar su tamaño. Ajustar a la cuadrícula y ajustar tamaño a la cuadrícula alinean la posición y el tamaño de una nota a una cuadrícula invisible; ajustar a otras notas alinea los bordes con las notas cercanas. El tamaño de la cuadrícula de abajo define el espaciado.",

        # ---- about dialog ----
        "About Sticky Notes": "Acerca de Sticky Notes",
        "Version {}": "Versión {}",
        "A lightweight sticky notes application\nfor Ubuntu desktop.\n\nBuilt with Python & PyQt6":
            "Una aplicación ligera de notas adhesivas\npara el escritorio de Ubuntu.\n\nCreado con Python y PyQt6",
        "View on GitHub": "Ver en GitHub",
        "Made by Nikola Javorina": "Creado por Nikola Javorina",
        "For the sharpest result, keep system scaling at 100% and use this.": "Para máxima nitidez, deja el escalado del sistema al 100% y usa esto.",
        "Buy me a coffee": "Invítame a un café",

        # ---- message boxes ----
        "Limit Reached": "Límite alcanzado",
        "Maximum of {} active notes reached.\nArchive or move some notes to Trash before creating new ones.":
            "Se alcanzó el máximo de {} notas activas.\nArchiva o mueve algunas notas a la papelera antes de crear otras nuevas.",
        "Maximum of 20 active notes reached.\nMove some notes to Trash before creating new ones.":
            "Se alcanzó el máximo de 20 notas activas.\nMueve algunas notas a la papelera antes de crear otras nuevas.",
        "Export Complete": "Exportación completada",
        "Export All": "Exportar todo",
        "Export": "Exportar",
        "There are no archived notes to export.": "No hay notas archivadas para exportar.",
        "Export all archived notes to a JSON file.": "Exporta todas las notas archivadas a un archivo JSON.",
        "Backup saves local “.bak” copies of ALL your notes (active, archived "
        "and trash), kept next to your data on this computer. Restore brings all "
        "three back.":
            "La copia de seguridad guarda copias locales “.bak” de TODAS tus notas "
            "(activas, archivadas y en la papelera), junto a tus datos en este "
            "ordenador. Restaurar las recupera todas.",
        "Export writes a portable JSON file of your ACTIVE notes (to move to "
        "another computer or re-import). Import always brings notes in as active. "
        "To export archived notes, use “Export All” in the Manager's Archive tab.":
            "La exportación escribe un archivo JSON portátil de tus notas ACTIVAS "
            "(para moverlas a otro ordenador o reimportarlas). La importación siempre "
            "añade las notas como activas. Para exportar las archivadas, usa “Exportar "
            "todo” en la pestaña Archivo del Administrador.",
        "Import Complete": "Importación completada",
        "Import Failed": "Error al importar",
        "Import — Limit Reached": "Importar — límite alcanzado",
        "You have {} active note(s). The export file contains {} note(s).\n\nYou can import at most {} note(s).\n\nImport the first {} and skip the rest?":
            "Tienes {} nota(s) activa(s). El archivo de exportación contiene {} nota(s).\n\nPuedes importar como máximo {} nota(s).\n\n¿Importar las primeras {} y omitir el resto?",
        "Exported {} note(s) to:\n{}": "Se exportaron {} nota(s) a:\n{}",
        "Imported {} note(s) successfully.": "Se importaron {} nota(s) correctamente.",
        "Could not read export file:\n{}": "No se pudo leer el archivo de exportación:\n{}",
        "You already have {} active notes — the maximum.\nMove some notes to Trash before importing.":
            "Ya tienes {} notas activas — el máximo.\nMueve algunas notas a la papelera antes de importar.",
        "You already have 20 active notes — the maximum.\nMove some notes to Trash before importing.":
            "Ya tienes 20 notas activas — el máximo.\nMueve algunas notas a la papelera antes de importar.",

        # ---- notifications ----
        "Sticky Notes — Reminder": "Sticky Notes — Recordatorio",
        "Snooze 10 min": "Posponer 10 min",

        # ---- settings: Note tab (auto-contrast + clean mode) ----
        "Adjust text & icon colour to note background":
            "Ajustar el color del texto e iconos al fondo de la nota",
        "Dark notes get light icons and text automatically. Turn off to keep the classic dark ink.":
            "Las notas oscuras reciben iconos y texto claros automáticamente. Desactívalo para mantener la tinta oscura clásica.",
        "Auto-hide toolbar and header until you hover the note":
            "Ocultar automáticamente la barra de herramientas y el encabezado hasta pasar el ratón sobre la nota",
        "Note border": "Borde de la nota",
        "Off": "Desactivado",
        "Always": "Siempre",
        "Auto (light notes only)": "Automático (solo notas claras)",
        "Auto shows a border only on light notes, where it helps them stand out from a light background.":
            "Automático muestra un borde solo en notas claras, donde ayuda a que destaquen sobre un fondo claro.",
        "Notes show only their text at rest; hover the top of a note to bring the controls back. "
        "A single click on the header keeps the controls up and lets you nudge the note with the arrow keys; click elsewhere to hide them again. "
        "Double-click a note's header to keep its controls open while you edit it; "
        "double-click again to hand that note back to auto-hide.":
            "En reposo, las notas muestran solo su texto; pasa el ratón por la parte superior de una nota para que "
            "vuelvan los controles. Un clic en el encabezado mantiene los controles visibles y permite mover la "
            "nota con las flechas del teclado; haz clic en otro lugar para volver a ocultarlos. "
            "Haz doble clic en el encabezado de una nota para mantener sus controles abiertos mientras la editas; "
            "doble clic de nuevo para devolverla al ocultamiento automático.",
        "Code block": "Bloque de código",
        "Inline code": "Código en línea",
        "Enable code blocks": "Habilitar bloques de código",
        "Adds code-block { } and inline-code buttons to the toolbar, and enables their shortcuts (Ctrl+M for inline code, Ctrl+Shift+M for a code block). Niche — off by default.":
            "Añade botones de bloque de código { } y código en línea a la barra de herramientas, y habilita sus atajos (Ctrl+M para código en línea, Ctrl+Shift+M para un bloque de código). Función específica — desactivada por defecto.",

        # ---- settings: appearance (theme) ----
        "Appearance": "Apariencia",
        "Window theme": "Tema de la ventana",
        "Theme": "Tema",
        "Light": "Claro",
        "Dark": "Oscuro",
        "Auto": "Automático",
        "Dark from": "Oscuro desde",
        "until": "hasta",
        "Auto switches to Dark between these times; the theme changes within a minute of each boundary. The tray's Toggle theme then lasts only until the next boundary.":
            "Automático cambia a Oscuro entre estas horas; el tema cambia dentro del minuto siguiente a cada límite. El «Cambiar tema» de la bandeja solo dura hasta el siguiente límite.",
        "Sets the look of the app's windows, menus and notes. Switching to Dark gives every note without its own dark colour a dark default; each note keeps separate colours for Light and Dark, so switching back restores the light one. Notes and the main windows recolour instantly; a few helper windows (About, the shortcut list, search) update the next time you open them — no restart needed.":
            "Define el aspecto de las ventanas, menús y notas de la aplicación. Cambiar a Oscuro asigna un color oscuro predeterminado a cada nota sin color oscuro propio; cada nota conserva colores separados para Claro y Oscuro, así que volver atrás restaura el claro. Las notas y las ventanas principales cambian de color al instante; algunas ventanas auxiliares (Acerca de, la lista de atajos, la búsqueda) se actualizan la próxima vez que se abren — sin necesidad de reiniciar.",

        # ---- settings: tray scroll ----
        "Scroll the tray icon to bring notes to front":
            "Desplaza sobre el icono de la bandeja para traer las notas al frente",
        "Scroll up on the tray icon to raise your visible notes above "
        "other windows. Pinned notes are unaffected.":
            "Desplaza hacia arriba sobre el icono de la bandeja para elevar tus notas visibles por "
            "encima de otras ventanas. Las notas fijadas no se ven afectadas.",

        # ---- settings: Backup tab + restore dialogs ----
        "Backups": "Copias de seguridad",
        "Backups save copies of ALL your notes (active, archived and trash) in a "
        "backups folder on this computer. \"Backup Now\" and the auto-backup "
        "interval each add a new restore point (the 5 most recent are kept); the "
        "daily auto-backup keeps the latest one fresh. \"Restore from Backup…\" "
        "lets you pick which one to go back to (this overwrites your current notes).":
            "Las copias de seguridad guardan copias de TODAS tus notas (activas, archivadas y "
            "en la papelera) en una carpeta de copias de seguridad en este ordenador. «Hacer "
            "copia ahora» y el intervalo de copia automática añaden cada uno un nuevo punto de "
            "restauración (se conservan las 5 más recientes); la copia automática diaria mantiene "
            "actualizada la más reciente. «Restaurar desde copia de seguridad…» te permite elegir "
            "a cuál volver (esto sobrescribe tus notas actuales).",
        "Restore from Backup…": "Restaurar desde copia de seguridad…",
        "Restore your notes from an earlier backup": "Restaura tus notas desde una copia de seguridad anterior",
        "The 5 most recent backups. Restoring overwrites your current "
        "notes and cannot be undone — press \"Backup Now\" first if you "
        "want to keep them.":
            "Las 5 copias de seguridad más recientes. Restaurar sobrescribe tus notas actuales y "
            "no se puede deshacer — pulsa «Hacer copia ahora» primero si quieres conservarlas.",
        "No backups yet.": "Todavía no hay copias de seguridad.",
        "(latest)": "(más reciente)",
        "Restore selected": "Restaurar seleccionada",
        "Replace your current notes with the backup from {}?\n\n"
        "This overwrites your current notes and cannot be undone. "
        "Use \"Backup Now\" first if you want to keep them.":
            "¿Reemplazar tus notas actuales con la copia de seguridad de {}?\n\n"
            "Esto sobrescribe tus notas actuales y no se puede deshacer. "
            "Usa «Hacer copia ahora» primero si quieres conservarlas.",
        "Restore complete": "Restauración completada",
        "Restore failed": "Error al restaurar",
        "Your notes were restored from the selected backup.":
            "Tus notas se restauraron desde la copia de seguridad seleccionada.",
        "That backup could not be restored.": "Esa copia de seguridad no se pudo restaurar.",
        "\"{name}\" could not be read and was restored from the backup of {when}.":
            "«{name}» no se pudo leer y se restauró desde la copia de seguridad de {when}.",

        # ---- keyboard shortcuts (tray + cheat-sheet) ----
        "Keyboard shortcuts…": "Atajos de teclado…",
        "Keyboard shortcuts": "Atajos de teclado",
        "Turn these on or off in Settings.": "Actívalos o desactívalos en Ajustes.",
        # ---- cheat-sheet tabs + section notes (translated via tr(title), so the
        # AST scan in test_i18n_hr_complete can't see them — that test checks the
        # shortcuts catalog explicitly instead) ----
        "Global": "Global",
        "Text & lists": "Texto y listas",
        "Code": "Código",
        "Windows": "Ventanas",
        "These act on the note you are using right now.":
            "Estos actúan sobre la nota que estás usando ahora mismo.",
        "These only do anything while \"Enable code blocks\" is on (Settings → Note).":
            "Estos solo hacen algo mientras «Habilitar bloques de código» está activado (Ajustes → Nota).",

        # ---- export: PNG ----
        "Image (.png)": "Imagen (.png)",
        "PNG image (*.png)": "Imagen PNG (*.png)",
    },
    "fr": {
        'OK': 'OK',
        'Cancel': 'Annuler',
        'Save': 'Enregistrer',
        'Close': 'Fermer',
        'Apply': 'Appliquer',
        'Select': 'Sélectionner',
        'Set': 'Définir',
        'Refresh': 'Actualiser',
        'Copy': 'Copier',
        'Copied': 'Copié',
        'New Note': 'Nouvelle note',
        'Show All': 'Tout afficher',
        'Hide All': 'Tout masquer',
        'Lock All': 'Tout verrouiller',
        'Unlock All': 'Tout déverrouiller',
        'Notes Manager': 'Gestionnaire de notes',
        'Settings': 'Paramètres',
        'About': 'À propos',
        'Toggle theme': 'Changer de thème',
        'Quit': 'Quitter',
        'Note Options': 'Options de la note',
        'Toggle Toolbar': "Afficher/masquer la barre d'outils",
        'Lock / Unlock': 'Verrouiller / déverrouiller',
        'Hide Note': 'Masquer la note',
        'Always on Top': 'Toujours au premier plan',
        'Favorite': 'Favori',
        'Add to Favorites': 'Ajouter aux favoris',
        'Remove from Favorites': 'Retirer des favoris',
        'Bold (Ctrl+B)': 'Gras (Ctrl+B)',
        'Italic (Ctrl+I)': 'Italique (Ctrl+I)',
        'Underline (Ctrl+U)': 'Souligné (Ctrl+U)',
        'Strikethrough (Ctrl+S)': 'Barré (Ctrl+S)',
        'Bullet list': 'Liste à puces',
        'Checklist': 'Liste de tâches',
        'Checklist — Tab to indent, drag a box or Alt+↑/↓ to reorder': 'Liste de tâches — Tab pour indenter, faites glisser une case ou Alt+↑/↓ pour réorganiser',
        'Checklist progress (done / total)': 'Progression de la liste (faites / total)',
        'Increase font size': 'Augmenter la taille de la police',
        'Decrease font size': 'Réduire la taille de la police',
        'Text Colour': 'Couleur du texte',
        'Font family': 'Police',
        'Click to set exact size': 'Cliquez pour définir la taille exacte',
        'Click to open colour picker': 'Cliquez pour ouvrir le sélecteur de couleur',
        'Write your note here…': 'Écrivez votre note ici…',
        'More fonts…': 'Plus de polices…',
        'Change Colour…': 'Changer la couleur…',
        'Copy Note': 'Copier la note',
        'Rename…': 'Renommer…',
        'Rename': 'Renommer',
        'Paste as plain text': 'Coller comme texte brut',
        'Move to Trash': 'Déplacer vers la corbeille',
        'Custom colour:': 'Couleur personnalisée :',
        '●  Disc': '●  Disque',
        '▪  Square': '▪  Carré',
        '1.  Decimal': '1.  Chiffres',
        'a.  Lower alpha': 'a.  Minuscules',
        'i.  Lower roman': 'i.  Chiffres romains',
        '✕  Remove list': '✕  Supprimer la liste',
        'Rename note': 'Renommer la note',
        'Note name:': 'Nom de la note :',
        'Leave empty to use the automatic name (first line of the note).': 'Laissez vide pour utiliser le nom automatique (première ligne de la note).',
        'Untitled': 'Sans titre',
        'Reminder': 'Rappel',
        'Set reminder…': 'Définir un rappel…',
        'Reminder: ': 'Rappel : ',
        'Reminder: {} — change…': 'Rappel : {} — modifier…',
        'Current: ': 'Actuel : ',
        'Quick options:': 'Options rapides :',
        'Or a specific time:': 'Ou une heure précise :',
        'Or a specific date and time:': 'Ou une date et heure précises :',
        'Date': 'Date',
        'Time': 'Heure',
        'In 1 min': 'Dans 1 min',
        'In 5 min': 'Dans 5 min',
        'In 10 min': 'Dans 10 min',
        'In 30 min': 'Dans 30 min',
        'In 1 hour': 'Dans 1 heure',
        'In 3 hours': 'Dans 3 heures',
        'In 8 hours': 'Dans 8 heures',
        'In 24 hours': 'Dans 24 heures',
        'Remove reminder': 'Supprimer le rappel',
        'Export Note': 'Exporter la note',
        'Export Failed': "Échec de l'export",
        'Plain text (.txt)': 'Texte brut (.txt)',
        'OpenDocument (.odt)': 'OpenDocument (.odt)',
        'PDF (.pdf)': 'PDF (.pdf)',
        'Text files (*.txt)': 'Fichiers texte (*.txt)',
        'OpenDocument (*.odt)': 'OpenDocument (*.odt)',
        'PDF (*.pdf)': 'PDF (*.pdf)',
        '(empty note)': '(note vide)',
        'Restore All': 'Tout restaurer',
        'Delete All': 'Tout supprimer',
        'Search notes…': 'Rechercher des notes…',
        'Search notes': 'Rechercher des notes',
        'Search Notes…': 'Rechercher des notes…',
        'No matching notes': 'Aucune note correspondante',
        'Global shortcut for searching notes': 'Raccourci global pour rechercher des notes',
        'Scroll on tray icon to raise/lower notes': "Défiler sur l'icône de la zone de notification pour lever/abaisser les notes",
        'Scroll up = bring visible notes to front; scroll down = send them behind other windows. Pinned notes are left alone.': 'Défiler vers le haut = amène les notes visibles au premier plan ; défiler vers le bas = les envoie derrière les autres fenêtres. Les notes épinglées ne sont pas affectées.',
        'Press {} anywhere to open the search palette. Rebind it in GNOME Settings → Keyboard → Custom Shortcuts.': "Appuyez sur {} n'importe où pour ouvrir la palette de recherche. Modifiable dans Paramètres GNOME → Clavier → Raccourcis personnalisés.",
        'Registers a GNOME shortcut ({}) to open a search box for finding a note from anywhere.': "Enregistre un raccourci GNOME ({}) pour ouvrir un champ de recherche permettant de trouver une note depuis n'importe où.",
        'Restore': 'Restaurer',
        'Delete permanently': 'Supprimer définitivement',
        'Active': 'Actives',
        'Archive': 'Archive',
        'Trash': 'Corbeille',
        'Active ({})': 'Actives ({})',
        'Active ({}/{})': 'Actives ({}/{})',
        'Archive ({})': 'Archive ({})',
        'Archive ({}/{})': 'Archive ({}/{})',
        'Trash ({})': 'Corbeille ({})',
        'Trash ({}/{})': 'Corbeille ({}/{})',
        '{} matches': '{} résultats',
        '{} active · {} in trash': '{} actives · {} dans la corbeille',
        '{} active · {} archived · {} in trash': '{} actives · {} archivées · {} dans la corbeille',
        'Archive Full': 'Archive pleine',
        'Active Full': 'Actives au maximum',
        'Partly Restored': 'Partiellement restauré',
        'Archive is full ({} notes).\nRemove something from the Archive first.': "L'archive est pleine ({} notes).\nSupprimez d'abord quelque chose de l'archive.",
        'You already have {} active notes — the maximum.\nArchive or delete one first.': "Vous avez déjà {} notes actives — le maximum.\nArchivez ou supprimez-en une d'abord.",
        'You already have {} active notes — the maximum.': 'Vous avez déjà {} notes actives — le maximum.',
        'Restored {} note(s). {} could not be restored — the active limit ({}) was reached.': "{} note(s) restaurée(s). {} n'a/n'ont pas pu être restaurée(s) — la limite active ({}) a été atteinte.",
        'Permanently delete all {} note(s) in Trash?\nThis cannot be undone.': 'Supprimer définitivement les {} note(s) de la corbeille ?\nCette action est irréversible.',
        'Start automatically on login': 'Démarrer automatiquement à la connexion',
        'Creates an autostart entry in ~/.config/autostart/': 'Crée une entrée de démarrage automatique dans ~/.config/autostart/',
        'Requires GNOME (gsettings). Bind a shortcut manually instead.': 'Nécessite GNOME (gsettings). Définissez plutôt un raccourci manuellement.',
        'Global shortcut for new note': 'Raccourci global pour une nouvelle note',
        'Global shortcut for new note from clipboard': 'Raccourci global pour une note depuis le presse-papiers',
        'Press {} anywhere to create a new note. Rebind it in GNOME Settings → Keyboard → Custom Shortcuts.': "Appuyez sur {} n'importe où pour créer une nouvelle note. Modifiable dans Paramètres GNOME → Clavier → Raccourcis personnalisés.",
        'Press {} anywhere to create a note from the clipboard. Rebind it in GNOME Settings → Keyboard → Custom Shortcuts.': "Appuyez sur {} n'importe où pour créer une note à partir du presse-papiers. Modifiable dans Paramètres GNOME → Clavier → Raccourcis personnalisés.",
        'Registers a GNOME shortcut ({}) to create a new note.': 'Enregistre un raccourci GNOME ({}) pour créer une nouvelle note.',
        'Registers a GNOME shortcut ({}) to create a note pre-filled with the clipboard contents.': 'Enregistre un raccourci GNOME ({}) pour créer une note pré-remplie avec le contenu du presse-papiers.',
        'UI Scale': "Échelle de l'interface",
        'Scales UI text and note content (100%–200%)': "Redimensionne le texte de l'interface et le contenu des notes (100 %–200 %)",
        'Scales the whole interface, text and icons (100%–200%).': "Redimensionne toute l'interface, le texte et les icônes (100 %–200 %).",
        'Restart Sticky Notes to apply the new scale.': 'Redémarrez Sticky Notes pour appliquer la nouvelle échelle.',
        'Restart now': 'Redémarrer maintenant',
        'Default font size': 'Taille de police par défaut',
        'Choose Font': 'Choisir une police',
        'Search fonts…': 'Rechercher des polices…',
        'Apply Font to New Notes': 'Appliquer la police aux nouvelles notes',
        'Apply to New Notes': 'Appliquer aux nouvelles notes',
        'Note': 'Note',
        'Default size for new notes': 'Taille par défaut des nouvelles notes',
        'Width': 'Largeur',
        'Height': 'Hauteur',
        'Background opacity': "Opacité de l'arrière-plan",
        'Makes the note paper see-through; text stays sharp. Applies to all current and future notes.': "Rend le papier de la note transparent ; le texte reste net. S'applique à toutes les notes actuelles et futures.",
        'Auto backup every': 'Sauvegarde automatique toutes les',
        '15 minutes': '15 minutes',
        '30 minutes': '30 minutes',
        '1 hour': '1 heure',
        '2 hours': '2 heures',
        '4 hours': '4 heures',
        '8 hours': '8 heures',
        '12 hours': '12 heures',
        '24 hours': '24 heures',
        'Backup Now': 'Sauvegarder maintenant',
        'Last backup: {}': 'Dernière sauvegarde : {}',
        'No backup yet': "Aucune sauvegarde pour l'instant",
        'Restore from Backup': 'Restaurer depuis une sauvegarde',
        'Notes recovery': 'Récupération des notes',
        'Some data files could not be read.': "Certains fichiers de données n'ont pas pu être lus.",
        '"{name}" could not be read and was restored from its backup.': "« {name} » n'a pas pu être lu et a été restauré à partir de sa sauvegarde.",
        '"{name}" could not be read and no valid backup was found.': "« {name} » n'a pas pu être lu et aucune sauvegarde valide n'a été trouvée.",
        'The damaged file was kept as "{kept}".': 'Le fichier endommagé a été conservé sous le nom « {kept} ».',
        'The damaged file was kept as "{kept}" so no data was overwritten.': "Le fichier endommagé a été conservé sous le nom « {kept} » afin qu'aucune donnée ne soit écrasée.",
        'Restore notes from backup dated:\n{}\n\n⚠  Current notes will be replaced!': 'Restaurer les notes à partir de la sauvegarde datée du :\n{}\n\n⚠  Les notes actuelles seront remplacées !',
        'EXPORT / IMPORT': 'EXPORT / IMPORT',
        'Export to JSON…': 'Exporter en JSON…',
        'Import from JSON…': 'Importer depuis JSON…',
        'Language': 'Langue',
        'Language changes apply after restart.': "Les changements de langue s'appliquent après redémarrage.",
        'General': 'Général',
        'Backup': 'Sauvegarde',
        'Snapping': 'Alignement',
        'Snapping && Tray': 'Alignement && Zone de notification',
        'Tray': 'Zone de notification',
        'Snap to grid': 'Aligner sur la grille',
        'Snap to other notes': 'Aligner sur les autres notes',
        'Snap size to grid': 'Aligner la taille sur la grille',
        'Grid size': 'Taille de la grille',
        "Notes snap when you drop them or finish resizing. Snap to grid and snap size to grid align a note's position and size to an invisible grid; snap to other notes lines edges up with nearby notes. The grid size below sets the spacing.": "Les notes s'alignent lorsque vous les déposez ou terminez leur redimensionnement. Aligner sur la grille et aligner la taille sur la grille alignent la position et la taille d'une note sur une grille invisible ; aligner sur les autres notes fait correspondre les bords avec les notes voisines. La taille de la grille ci-dessous définit l'espacement.",
        'About Sticky Notes': 'À propos de Sticky Notes',
        'Version {}': 'Version {}',
        'A lightweight sticky notes application\nfor Ubuntu desktop.\n\nBuilt with Python & PyQt6':
            'Une application légère de notes autocollantes\npour le bureau Ubuntu.\n\nCréé avec Python et PyQt6',
        'View on GitHub': 'Voir sur GitHub',
        'Made by Nikola Javorina': 'Créé par Nikola Javorina',
        'For the sharpest result, keep system scaling at 100% and use this.': 'Pour une image nette, réglez le zoom du système à 100% et utilisez ceci.',
        'Buy me a coffee': 'Offrez-moi un café',
        'Limit Reached': 'Limite atteinte',
        'Maximum of {} active notes reached.\nArchive or move some notes to Trash before creating new ones.': "Maximum de {} notes actives atteint.\nArchivez ou déplacez des notes vers la corbeille avant d'en créer de nouvelles.",
        'Maximum of 20 active notes reached.\nMove some notes to Trash before creating new ones.': "Maximum de 20 notes actives atteint.\nDéplacez des notes vers la corbeille avant d'en créer de nouvelles.",
        'Export Complete': 'Export terminé',
        'Export All': 'Tout exporter',
        'Export': 'Exporter',
        'There are no archived notes to export.': "Il n'y a aucune note archivée à exporter.",
        'Export all archived notes to a JSON file.': 'Exporte toutes les notes archivées dans un fichier JSON.',
        'Backup saves local “.bak” copies of ALL your notes (active, archived and trash), kept next to your data on this computer. Restore brings all three back.': 'La sauvegarde enregistre des copies locales « .bak » de TOUTES vos notes (actives, archivées et corbeille), conservées à côté de vos données sur cet ordinateur. La restauration ramène les trois.',
        "Export writes a portable JSON file of your ACTIVE notes (to move to another computer or re-import). Import always brings notes in as active. To export archived notes, use “Export All” in the Manager's Archive tab.": "L'export écrit un fichier JSON portable de vos notes ACTIVES (pour les transférer sur un autre ordinateur ou les réimporter). L'import ajoute toujours les notes comme actives. Pour exporter les notes archivées, utilisez « Tout exporter » dans l'onglet Archive du Gestionnaire.",
        'Import Complete': 'Import terminé',
        'Import Failed': "Échec de l'import",
        'Import — Limit Reached': 'Import — limite atteinte',
        'You have {} active note(s). The export file contains {} note(s).\n\nYou can import at most {} note(s).\n\nImport the first {} and skip the rest?': "Vous avez {} note(s) active(s). Le fichier d'export contient {} note(s).\n\nVous pouvez importer au maximum {} note(s).\n\nImporter les {} premières et ignorer le reste ?",
        'Exported {} note(s) to:\n{}': '{} note(s) exportée(s) vers :\n{}',
        'Imported {} note(s) successfully.': '{} note(s) importée(s) avec succès.',
        'Could not read export file:\n{}': "Impossible de lire le fichier d'export :\n{}",
        'You already have {} active notes — the maximum.\nMove some notes to Trash before importing.': "Vous avez déjà {} notes actives — le maximum.\nDéplacez des notes vers la corbeille avant d'importer.",
        'You already have 20 active notes — the maximum.\nMove some notes to Trash before importing.': "Vous avez déjà 20 notes actives — le maximum.\nDéplacez des notes vers la corbeille avant d'importer.",
        'Sticky Notes — Reminder': 'Sticky Notes — Rappel',
        'Snooze 10 min': 'Reporter de 10 min',
        'Adjust text & icon colour to note background': "Adapter la couleur du texte et des icônes à l'arrière-plan de la note",
        'Dark notes get light icons and text automatically. Turn off to keep the classic dark ink.': "Les notes sombres reçoivent automatiquement des icônes et du texte clairs. Désactivez pour conserver l'encre sombre classique.",
        'Auto-hide toolbar and header until you hover the note': "Masquer automatiquement la barre d'outils et l'en-tête jusqu'à ce que vous survoliez la note",
        'Note border': 'Bordure de la note',
        'Off': 'Désactivée',
        'Always': 'Toujours',
        'Auto (light notes only)': 'Automatique (notes claires uniquement)',
        'Auto shows a border only on light notes, where it helps them stand out from a light background.': "Automatique affiche une bordure uniquement sur les notes claires, où elle les aide à se détacher d'un arrière-plan clair.",
        "Notes show only their text at rest; hover the top of a note to bring the controls back. A single click on the header keeps the controls up and lets you nudge the note with the arrow keys; click elsewhere to hide them again. Double-click a note's header to keep its controls open while you edit it; double-click again to hand that note back to auto-hide.": "Au repos, les notes n'affichent que leur texte ; survolez le haut d'une note pour faire réapparaître les commandes. Un simple clic sur l'en-tête garde les commandes visibles et permet de déplacer la note avec les touches fléchées ; cliquez ailleurs pour les masquer à nouveau. Double-cliquez sur l'en-tête d'une note pour garder ses commandes ouvertes pendant que vous la modifiez ; double-cliquez à nouveau pour rendre cette note au masquage automatique.",
        'Code block': 'Bloc de code',
        'Inline code': 'Code en ligne',
        'Enable code blocks': 'Activer les blocs de code',
        'Adds code-block { } and inline-code buttons to the toolbar, and enables their shortcuts (Ctrl+M for inline code, Ctrl+Shift+M for a code block). Niche — off by default.': "Ajoute des boutons bloc de code { } et code en ligne à la barre d'outils, et active leurs raccourcis (Ctrl+M pour le code en ligne, Ctrl+Maj+M pour un bloc de code). Fonctionnalité de niche — désactivée par défaut.",
        'Appearance': 'Apparence',
        'Window theme': 'Thème de la fenêtre',
        'Theme': 'Thème',
        'Light': 'Clair',
        'Dark': 'Sombre',
        'Auto': 'Automatique',
        'Dark from': 'Sombre à partir de',
        'until': "jusqu'à",
        "Auto switches to Dark between these times; the theme changes within a minute of each boundary. The tray's Toggle theme then lasts only until the next boundary.": "Automatique passe au thème Sombre entre ces horaires ; le thème change dans la minute suivant chaque limite. Le « Changer de thème » de la zone de notification ne dure alors que jusqu'à la limite suivante.",
        "Sets the look of the app's windows, menus and notes. Switching to Dark gives every note without its own dark colour a dark default; each note keeps separate colours for Light and Dark, so switching back restores the light one. Notes and the main windows recolour instantly; a few helper windows (About, the shortcut list, search) update the next time you open them — no restart needed.": "Définit l'apparence des fenêtres, menus et notes de l'application. Passer au thème Sombre donne à chaque note sans couleur sombre propre une couleur sombre par défaut ; chaque note conserve des couleurs distinctes pour Clair et Sombre, donc revenir en arrière restaure la couleur claire. Les notes et les fenêtres principales changent de couleur instantanément ; quelques fenêtres auxiliaires (À propos, la liste des raccourcis, la recherche) se mettent à jour à la prochaine ouverture — aucun redémarrage requis.",
        'Scroll the tray icon to bring notes to front': "Défiler sur l'icône de la zone de notification pour amener les notes au premier plan",
        'Scroll up on the tray icon to raise your visible notes above other windows. Pinned notes are unaffected.': "Défilez vers le haut sur l'icône de la zone de notification pour faire passer vos notes visibles au-dessus des autres fenêtres. Les notes épinglées ne sont pas affectées.",
        'Backups': 'Sauvegardes',
        'Backups save copies of ALL your notes (active, archived and trash) in a backups folder on this computer. "Backup Now" and the auto-backup interval each add a new restore point (the 5 most recent are kept); the daily auto-backup keeps the latest one fresh. "Restore from Backup…" lets you pick which one to go back to (this overwrites your current notes).': "Les sauvegardes enregistrent des copies de TOUTES vos notes (actives, archivées et corbeille) dans un dossier de sauvegardes sur cet ordinateur. « Sauvegarder maintenant » et l'intervalle de sauvegarde automatique ajoutent chacun un nouveau point de restauration (les 5 plus récents sont conservés) ; la sauvegarde automatique quotidienne maintient le plus récent à jour. « Restaurer depuis une sauvegarde… » vous permet de choisir celle vers laquelle revenir (cela écrase vos notes actuelles).",
        'Restore from Backup…': 'Restaurer depuis une sauvegarde…',
        'Restore your notes from an earlier backup': "Restaurez vos notes à partir d'une sauvegarde antérieure",
        'The 5 most recent backups. Restoring overwrites your current notes and cannot be undone — press "Backup Now" first if you want to keep them.': "Les 5 sauvegardes les plus récentes. La restauration écrase vos notes actuelles et ne peut pas être annulée — appuyez d'abord sur « Sauvegarder maintenant » si vous souhaitez les conserver.",
        'No backups yet.': "Aucune sauvegarde pour l'instant.",
        '(latest)': '(la plus récente)',
        'Restore selected': 'Restaurer la sélection',
        'Replace your current notes with the backup from {}?\n\nThis overwrites your current notes and cannot be undone. Use "Backup Now" first if you want to keep them.': "Remplacer vos notes actuelles par la sauvegarde du {} ?\n\nCela écrase vos notes actuelles et ne peut pas être annulé. Utilisez d'abord « Sauvegarder maintenant » si vous souhaitez les conserver.",
        'Restore complete': 'Restauration terminée',
        'Restore failed': 'Échec de la restauration',
        'Your notes were restored from the selected backup.': 'Vos notes ont été restaurées à partir de la sauvegarde sélectionnée.',
        'That backup could not be restored.': "Cette sauvegarde n'a pas pu être restaurée.",
        '"{name}" could not be read and was restored from the backup of {when}.': "« {name} » n'a pas pu être lu et a été restauré à partir de la sauvegarde du {when}.",
        'Keyboard shortcuts…': 'Raccourcis clavier…',
        'Keyboard shortcuts': 'Raccourcis clavier',
        'Turn these on or off in Settings.': 'Activez-les ou désactivez-les dans les Paramètres.',
        'Global': 'Global',
        'Text & lists': 'Texte et listes',
        'Code': 'Code',
        'Windows': 'Fenêtres',
        'These act on the note you are using right now.': 'Ceux-ci agissent sur la note que vous utilisez actuellement.',
        'These only do anything while "Enable code blocks" is on (Settings → Note).': "Ceux-ci n'ont d'effet que lorsque « Activer les blocs de code » est activé (Paramètres → Note).",
        'Image (.png)': 'Image (.png)',
        'PNG image (*.png)': 'Image PNG (*.png)',
    },
    "hr": {
        # ---- generic actions / buttons ----
        "OK": "U redu",
        "Cancel": "Odustani",
        "Save": "Spremi",
        "Close": "Zatvori",
        "Apply": "Primijeni",
        "Select": "Odaberi",
        "Set": "Postavi",
        "Refresh": "Osvježi",
        "Copy": "Kopiraj",
        "Copied": "Kopirano",

        # ---- tray menu ----
        "New Note": "Nova bilješka",
        "Show All": "Prikaži sve",
        "Hide All": "Sakrij sve",
        "Lock All": "Zaključaj sve",
        "Unlock All": "Otključaj sve",
        "Notes Manager": "Upravitelj bilješki",
        "Settings": "Postavke",
        "About": "O programu",
        "Toggle theme": "Prebaci temu",
        "Quit": "Izlaz",

        # ---- note header / toolbar ----
        "Note Options": "Opcije bilješke",
        "Toggle Toolbar": "Prikaži/sakrij alatnu traku",
        "Lock / Unlock": "Zaključaj / otključaj",
        "Hide Note": "Sakrij bilješku",
        "Always on Top": "Uvijek na vrhu",
        "Favorite": "Favorit",
        "Add to Favorites": "Dodaj u favorite",
        "Remove from Favorites": "Ukloni iz favorita",
        "Bold (Ctrl+B)": "Podebljano (Ctrl+B)",
        "Italic (Ctrl+I)": "Kurziv (Ctrl+I)",
        "Underline (Ctrl+U)": "Podcrtano (Ctrl+U)",
        "Strikethrough (Ctrl+S)": "Precrtano (Ctrl+S)",
        "Bullet list": "Lista s oznakama",
        "Checklist": "Lista zadataka",
        "Checklist — Tab to indent, drag a box or Alt+↑/↓ to reorder":
            "Lista zadataka — Tab za uvlačenje, povuci okvir ili Alt+↑/↓ za presloživanje",
        "Checklist progress (done / total)": "Napredak liste (gotovo / ukupno)",
        "Increase font size": "Povećaj veličinu fonta",
        "Decrease font size": "Smanji veličinu fonta",
        "Text Colour": "Boja teksta",
        "Font family": "Vrsta fonta",
        "Click to set exact size": "Kliknite za točnu veličinu",
        "Click to open colour picker": "Kliknite za birač boja",
        "Write your note here…": "Napišite bilješku ovdje…",
        "More fonts…": "Više fontova…",

        # ---- note context menu ----
        "Change Colour…": "Promijeni boju…",
        "Copy Note": "Kopiraj bilješku",
        "Rename…": "Preimenuj…",
        "Rename": "Preimenuj",          # Manager row menu (sits next to "Export")
        "Paste as plain text": "Zalijepi kao čisti tekst",
        "Move to Trash": "Premjesti u smeće",
        "Custom colour:": "Prilagođena boja:",

        # ---- list styles (glyph kept) ----
        "●  Disc": "●  Krug",
        "▪  Square": "▪  Kvadrat",
        "1.  Decimal": "1.  Brojevi",
        "a.  Lower alpha": "a.  Mala slova",
        "i.  Lower roman": "i.  Mali rimski",
        "✕  Remove list": "✕  Ukloni listu",

        # ---- rename dialog ----
        "Rename note": "Preimenuj bilješku",
        "Note name:": "Naziv bilješke:",
        "Leave empty to use the automatic name (first line of the note).":
            "Ostavite prazno za automatski naziv (prvi red bilješke).",
        "Untitled": "Bez naziva",

        # ---- reminder dialog ----
        "Reminder": "Podsjetnik",
        "Set reminder…": "Postavi podsjetnik…",
        "Reminder: ": "Podsjetnik: ",
        "Reminder: {} — change…": "Podsjetnik: {} — promijeni…",
        "Current: ": "Trenutno: ",
        "Quick options:": "Brze opcije:",
        "Or a specific time:": "Ili točno vrijeme:",
        "Or a specific date and time:": "Ili određeni datum i vrijeme:",
        "Date": "Datum",
        "Time": "Vrijeme",
        "In 1 min": "Za 1 min",
        "In 5 min": "Za 5 min",
        "In 10 min": "Za 10 min",
        "In 30 min": "Za 30 min",
        "In 1 hour": "Za 1 sat",
        "In 3 hours": "Za 3 sata",
        "In 8 hours": "Za 8 sati",
        "In 24 hours": "Za 24 sata",
        "Remove reminder": "Ukloni podsjetnik",

        # ---- export ----
        "Export Note": "Izvoz bilješke",
        "Export Failed": "Izvoz nije uspio",
        "Plain text (.txt)": "Obični tekst (.txt)",
        "OpenDocument (.odt)": "OpenDocument (.odt)",
        "PDF (.pdf)": "PDF (.pdf)",
        "Text files (*.txt)": "Tekstualne datoteke (*.txt)",
        "OpenDocument (*.odt)": "OpenDocument (*.odt)",
        "PDF (*.pdf)": "PDF (*.pdf)",
        "(empty note)": "(prazna bilješka)",

        # ---- manager ----
        "Restore All": "Vrati sve",
        "Delete All": "Izbriši sve",
        "Search notes…": "Pretraži bilješke…",
        "Search notes": "Pretraži bilješke",
        "Search Notes…": "Pretraži bilješke…",
        "No matching notes": "Nema podudarnih bilješki",
        "Global shortcut for searching notes": "Globalni prečac za pretragu bilješki",
        "Scroll on tray icon to raise/lower notes": "Scroll na tray ikoni za dizanje/spuštanje bilješki",
        "Scroll up = bring visible notes to front; scroll down = send them behind other windows. Pinned notes are left alone.":
            "Scroll gore = vidljive bilješke naprijed; scroll dolje = iza ostalih prozora. Pinane se ne diraju.",
        "Press {} anywhere to open the search palette. Rebind it in GNOME Settings → Keyboard → Custom Shortcuts.":
            "Pritisni {} bilo gdje za otvaranje pretrage. Promijeni prečac u GNOME Settings → Keyboard → Custom Shortcuts.",
        "Registers a GNOME shortcut ({}) to open a search box for finding a note from anywhere.":
            "Registrira GNOME prečac ({}) za otvaranje pretrage bilješki s bilo kojeg mjesta.",
        "Restore": "Vrati",
        "Delete permanently": "Trajno izbriši",
        "Active": "Aktivne",
        "Archive": "Arhiva",
        "Trash": "Smeće",
        "Active ({})": "Aktivne ({})",
        "Active ({}/{})": "Aktivne ({}/{})",
        "Archive ({})": "Arhiva ({})",
        "Archive ({}/{})": "Arhiva ({}/{})",
        "Trash ({})": "Smeće ({})",
        "Trash ({}/{})": "Smeće ({}/{})",
        "{} matches": "{} podudaranja",
        "{} active · {} in trash": "{} aktivnih · {} u smeću",
        "{} active · {} archived · {} in trash": "{} aktivnih · {} arhiviranih · {} u smeću",
        "Archive Full": "Arhiva puna",
        "Active Full": "Aktivne pune",
        "Partly Restored": "Djelomično vraćeno",
        "Archive is full ({} notes).\nRemove something from the Archive first.":
            "Arhiva je puna ({} bilješki).\nPrvo uklonite nešto iz arhive.",
        "You already have {} active notes — the maximum.\nArchive or delete one first.":
            "Već imate {} aktivnih bilješki — maksimum.\nPrvo neku arhivirajte ili izbrišite.",
        "You already have {} active notes — the maximum.":
            "Već imate {} aktivnih bilješki — maksimum.",
        "Restored {} note(s). {} could not be restored — the active limit ({}) was reached.":
            "Vraćeno {} bilješki. {} nije moguće vratiti — dosegnut je limit aktivnih ({}).",
        "Permanently delete all {} note(s) in Trash?\nThis cannot be undone.":
            "Trajno izbrisati svih {} bilješki u smeću?\nOvo se ne može poništiti.",

        # ---- settings dialog ----
        "Start automatically on login": "Automatski pokreni pri prijavi",
        "Creates an autostart entry in ~/.config/autostart/":
            "Stvara stavku automatskog pokretanja u ~/.config/autostart/",
        "Requires GNOME (gsettings). Bind a shortcut manually instead.":
            "Zahtijeva GNOME (gsettings). Umjesto toga ručno postavite prečicu.",
        "Global shortcut for new note": "Globalna prečica za novu bilješku",
        "Global shortcut for new note from clipboard":
            "Globalna prečica za bilješku iz međuspremnika",
        "Press {} anywhere to create a new note. Rebind it in GNOME Settings → Keyboard → Custom Shortcuts.":
            "Pritisnite {} bilo gdje za novu bilješku. Promijenite je u GNOME Postavke → Tipkovnica → Prilagođene prečice.",
        "Press {} anywhere to create a note from the clipboard. Rebind it in GNOME Settings → Keyboard → Custom Shortcuts.":
            "Pritisnite {} bilo gdje za bilješku iz međuspremnika. Promijenite je u GNOME Postavke → Tipkovnica → Prilagođene prečice.",
        "Registers a GNOME shortcut ({}) to create a new note.":
            "Registrira GNOME prečicu ({}) za stvaranje nove bilješke.",
        "Registers a GNOME shortcut ({}) to create a note pre-filled with the clipboard contents.":
            "Registrira GNOME prečicu ({}) za bilješku ispunjenu sadržajem međuspremnika.",
        "UI Scale": "Veličina sučelja",
        "Scales UI text and note content (100%–200%)":
            "Skalira tekst sučelja i sadržaj bilješki (100%–200%)",
        "Scales the whole interface, text and icons (100%–200%).":
            "Skalira cijelo sučelje, tekst i ikone (100%–200%).",
        "Restart Sticky Notes to apply the new scale.":
            "Ponovno pokrenite Sticky Notes za primjenu novog mjerila.",
        "Restart now": "Ponovo pokreni sada",
        "Default font size": "Zadana veličina fonta",
        "Choose Font": "Odaberi font",
        "Search fonts…": "Pretraži fontove…",
        "Apply Font to New Notes": "Primijeni font na nove bilješke",
        "Apply to New Notes": "Primijeni na nove bilješke",
        "Note": "Bilješka",
        "Default size for new notes": "Zadana veličina novih bilješki",
        "Width": "Širina",
        "Height": "Visina",
        "Background opacity": "Prozirnost pozadine",
        "Makes the note paper see-through; text stays sharp. Applies to all current and future notes.":
            "Čini podlogu bilješke prozirnom; tekst ostaje oštar. Vrijedi za sve trenutne i buduće bilješke.",
        "Auto backup every": "Automatska kopija svakih",
        "15 minutes": "15 minuta",
        "30 minutes": "30 minuta",
        "1 hour": "1 sat",
        "2 hours": "2 sata",
        "4 hours": "4 sata",
        "8 hours": "8 sati",
        "12 hours": "12 sati",
        "24 hours": "24 sata",
        "Backup Now": "Napravi kopiju sada",
        "Last backup: {}": "Zadnja kopija: {}",
        "No backup yet": "Još nema kopije",
        "Restore from Backup": "Vrati iz kopije",
        "Notes recovery": "Oporavak bilješki",
        "Some data files could not be read.": "Neke datoteke s podacima nije bilo moguće pročitati.",
        '"{name}" could not be read and was restored from its backup.':
            '"{name}" nije bilo moguće pročitati i vraćena je iz sigurnosne kopije.',
        '"{name}" could not be read and no valid backup was found.':
            '"{name}" nije bilo moguće pročitati i nije nađena valjana sigurnosna kopija.',
        'The damaged file was kept as "{kept}".':
            'Oštećena datoteka sačuvana je kao "{kept}".',
        'The damaged file was kept as "{kept}" so no data was overwritten.':
            'Oštećena datoteka sačuvana je kao "{kept}" pa ništa nije prepisano.',
        "Restore notes from backup dated:\n{}\n\n⚠  Current notes will be replaced!":
            "Vratiti bilješke iz kopije od:\n{}\n\n⚠  Trenutne bilješke bit će zamijenjene!",
        "EXPORT / IMPORT": "IZVOZ / UVOZ",
        "Export to JSON…": "Izvezi u JSON…",
        "Import from JSON…": "Uvezi iz JSON…",
        "Language": "Jezik",
        "Language changes apply after restart.": "Promjena jezika primjenjuje se nakon ponovnog pokretanja.",
        # settings tab labels
        "General": "Općenito",
        "Backup": "Sigurnosne kopije",
        # snapping
        "Snapping": "Prianjanje",
        "Snapping && Tray": "Prianjanje && traka",
        "Tray": "Traka",
        "Snap to grid": "Prianjanje uz mrežu",
        "Snap to other notes": "Prianjanje uz druge bilješke",
        "Snap size to grid": "Prianjanje veličine uz mrežu",
        "Grid size": "Veličina mreže",
        "Notes snap when you drop them or finish resizing. Snap to grid and snap size to grid align a note's position and size to an invisible grid; snap to other notes lines edges up with nearby notes. The grid size below sets the spacing.":
            "Bilješke prianjaju kad ih pustite ili završite promjenu veličine. Prianjanje uz mrežu i prianjanje veličine uz mrežu poravnavaju položaj i veličinu bilješke uz nevidljivu mrežu; prianjanje uz druge bilješke poravnava rubove sa susjednim bilješkama. Veličina mreže ispod određuje razmak.",

        # ---- about dialog ----
        "About Sticky Notes": "O programu Sticky Notes",
        "Version {}": "Verzija {}",
        "A lightweight sticky notes application\nfor Ubuntu desktop.\n\nBuilt with Python & PyQt6":
            "Lagana aplikacija za ljepljive bilješke\nza Ubuntu radnu površinu.\n\nIzrađeno s Python i PyQt6",
        "View on GitHub": "Pogledaj na GitHubu",
        "Made by Nikola Javorina": "Izradio Nikola Javorina",
        "For the sharpest result, keep system scaling at 100% and use this.": "Za najoštriju sliku ostavite sistemsko skaliranje na 100% i koristite ovo.",
        "Buy me a coffee": "Časti me kavom",

        # ---- message boxes ----
        "Limit Reached": "Dosegnuto ograničenje",
        "Maximum of {} active notes reached.\nArchive or move some notes to Trash before creating new ones.":
            "Dosegnut je maksimum od {} aktivnih bilješki.\nArhivirajte ili premjestite neke u smeće prije stvaranja novih.",
        "Maximum of 20 active notes reached.\nMove some notes to Trash before creating new ones.":
            "Dosegnut je maksimum od 20 aktivnih bilješki.\nPremjestite neke u smeće prije stvaranja novih.",
        "Export Complete": "Izvoz dovršen",
        "Export All": "Izvezi sve",
        "Export": "Izvezi",
        "There are no archived notes to export.": "Nema arhiviranih bilješki za izvoz.",
        "Export all archived notes to a JSON file.": "Izvezi sve arhivirane bilješke u JSON datoteku.",
        "Backup saves local “.bak” copies of ALL your notes (active, archived "
        "and trash), kept next to your data on this computer. Restore brings all "
        "three back.":
            "Sigurnosna kopija sprema lokalne „.bak” kopije SVIH bilješki (aktivne, "
            "arhivirane i smeće), pored tvojih podataka na ovom računalu. Vraćanje "
            "vraća sve tri.",
        "Export writes a portable JSON file of your ACTIVE notes (to move to "
        "another computer or re-import). Import always brings notes in as active. "
        "To export archived notes, use “Export All” in the Manager's Archive tab.":
            "Izvoz zapisuje prenosivu JSON datoteku tvojih AKTIVNIH bilješki (za "
            "prijenos na drugo računalo ili ponovni uvoz). Uvoz uvijek dodaje bilješke "
            "kao aktivne. Za izvoz arhiviranih koristi „Izvezi sve” u kartici Arhiva u Pregledniku.",
        "Import Complete": "Uvoz dovršen",
        "Import Failed": "Uvoz nije uspio",
        "Import — Limit Reached": "Uvoz — dosegnuto ograničenje",
        "You have {} active note(s). The export file contains {} note(s).\n\nYou can import at most {} note(s).\n\nImport the first {} and skip the rest?":
            "Imate {} aktivnih bilješki. Datoteka izvoza sadrži {} bilješki.\n\nMožete uvesti najviše {} bilješki.\n\nUvesti prvih {} i preskočiti ostatak?",
        "Exported {} note(s) to:\n{}": "Izvezeno {} bilješki u:\n{}",
        "Imported {} note(s) successfully.": "Uvezeno {} bilješki.",
        "Could not read export file:\n{}": "Datoteku izvoza nije moguće pročitati:\n{}",
        "You already have {} active notes — the maximum.\nMove some notes to Trash before importing.":
            "Već imate {} aktivnih bilješki — maksimum.\nPremjestite neke u smeće prije uvoza.",
        "You already have 20 active notes — the maximum.\nMove some notes to Trash before importing.":
            "Već imate 20 aktivnih bilješki — to je maksimum.\nPremjestite neke u smeće prije uvoza.",

        # ---- notifications ----
        "Sticky Notes — Reminder": "Sticky Notes — Podsjetnik",
        "Snooze 10 min": "Odgodi 10 min",

        # ---- settings: Note tab (auto-contrast + clean mode) ----
        "Adjust text & icon colour to note background":
            "Prilagodi boju teksta i ikona pozadini bilješke",
        "Dark notes get light icons and text automatically. Turn off to keep the classic dark ink.":
            "Tamne bilješke automatski dobivaju svijetle ikone i tekst. Isključi za klasičnu tamnu tintu.",
        "Auto-hide toolbar and header until you hover the note":
            "Sakrij alatnu traku i zaglavlje dok ne pređeš mišem preko bilješke",
        "Note border": "Obrub bilješke",
        "Off": "Isključeno",
        "Always": "Uvijek",
        "Auto (light notes only)": "Automatski (samo svijetle bilješke)",
        "Auto shows a border only on light notes, where it helps them stand out from a light background.":
            "Automatski prikazuje obrub samo na svijetlim bilješkama, gdje pomaže da se odvoje od svijetle pozadine.",
        "Notes show only their text at rest; hover the top of a note to bring the controls back. "
        "A single click on the header keeps the controls up and lets you nudge the note with the arrow keys; click elsewhere to hide them again. "
        "Double-click a note's header to keep its controls open while you edit it; "
        "double-click again to hand that note back to auto-hide.":
            "Bilješke u mirovanju prikazuju samo tekst; pređi mišem preko vrha bilješke da vratiš kontrole. "
            "Jedan klik na zaglavlje drži kontrole otvorenima i omogućuje pomicanje bilješke strelicama; klik drugdje ih ponovno skrije. "
            "Dvoklik na zaglavlje bilješke drži njezine kontrole otvorenima dok je uređuješ; "
            "dvoklik ponovo vraća tu bilješku na automatsko skrivanje.",
        "Code block": "Blok koda",
        "Inline code": "Inline kod",
        "Enable code blocks": "Omogući blokove koda",
        "Adds code-block { } and inline-code buttons to the toolbar, and enables their shortcuts (Ctrl+M for inline code, Ctrl+Shift+M for a code block). Niche — off by default.":
            "Dodaje gumbe za blok koda { } i inline kod u alatnu traku te uključuje njihove prečice (Ctrl+M za inline kod, Ctrl+Shift+M za blok koda). Niche — isključeno po zadanom.",

        # ---- settings: appearance (theme) ----
        "Appearance": "Izgled",
        "Window theme": "Tema prozora",
        "Theme": "Tema",
        "Light": "Svijetla",
        "Dark": "Tamna",
        "Auto": "Automatski",
        "Dark from": "Tamna od",
        "until": "do",
        "Auto switches to Dark between these times; the theme changes within a minute of each boundary. The tray's Toggle theme then lasts only until the next boundary.":
            "Automatski prelazi na tamnu između ovih vremena; tema se mijenja unutar minute od granice. Toggle theme iz traya tada vrijedi samo do iduće granice.",
        "Sets the look of the app's windows, menus and notes. Switching to Dark gives every note without its own dark colour a dark default; each note keeps separate colours for Light and Dark, so switching back restores the light one. Notes and the main windows recolour instantly; a few helper windows (About, the shortcut list, search) update the next time you open them — no restart needed.":
            "Postavlja izgled prozora, izbornika i bilješki aplikacije. Prebacivanje na Tamnu daje svakoj bilješci bez vlastite tamne boje tamni default; svaka bilješka pamti zasebne boje za Svijetlu i Tamnu, pa povratak vraća svijetlu. Bilješke i glavni prozori preboje se odmah; nekoliko pomoćnih prozora (O aplikaciji, popis prečica, pretraga) osvježi se kad ih idući put otvoriš — bez ponovnog pokretanja.",

        # ---- settings: tray scroll ----
        "Scroll the tray icon to bring notes to front":
            "Scroll na tray ikoni za bilješke naprijed",
        "Scroll up on the tray icon to raise your visible notes above "
        "other windows. Pinned notes are unaffected.":
            "Scroll gore na tray ikoni diže vidljive bilješke iznad ostalih "
            "prozora. Pinane bilješke ostaju netaknute.",

        # ---- settings: Backup tab + restore dialogs ----
        "Backups": "Sigurnosne kopije",
        "Backups save copies of ALL your notes (active, archived and trash) in a "
        "backups folder on this computer. \"Backup Now\" and the auto-backup "
        "interval each add a new restore point (the 5 most recent are kept); the "
        "daily auto-backup keeps the latest one fresh. \"Restore from Backup…\" "
        "lets you pick which one to go back to (this overwrites your current notes).":
            "Sigurnosne kopije spremaju kopije SVIH bilješki (aktivne, arhivirane i "
            "smeće) u backups mapu na ovom računalu. „Napravi kopiju sada” i interval "
            "automatske kopije svaki dodaju novu točku vraćanja (čuva se 5 najnovijih); "
            "dnevna automatska kopija drži najnoviju svježom. „Vrati iz sigurnosne "
            "kopije…” omogućuje odabir na koju se vratiti (ovo prepisuje trenutne bilješke).",
        "Restore from Backup…": "Vrati iz sigurnosne kopije…",
        "Restore your notes from an earlier backup": "Vrati bilješke iz ranije sigurnosne kopije",
        "The 5 most recent backups. Restoring overwrites your current "
        "notes and cannot be undone — press \"Backup Now\" first if you "
        "want to keep them.":
            "5 najnovijih sigurnosnih kopija. Vraćanje prepisuje trenutne bilješke i "
            "ne može se poništiti — prvo pritisni „Napravi kopiju sada” ako ih želiš zadržati.",
        "No backups yet.": "Još nema sigurnosnih kopija.",
        "(latest)": "(najnovija)",
        "Restore selected": "Vrati odabrano",
        "Replace your current notes with the backup from {}?\n\n"
        "This overwrites your current notes and cannot be undone. "
        "Use \"Backup Now\" first if you want to keep them.":
            "Zamijeniti trenutne bilješke kopijom od {}?\n\n"
            "Ovo prepisuje trenutne bilješke i ne može se poništiti. "
            "Prvo koristi „Napravi kopiju sada” ako ih želiš zadržati.",
        "Restore complete": "Vraćanje dovršeno",
        "Restore failed": "Vraćanje nije uspjelo",
        "Your notes were restored from the selected backup.":
            "Bilješke su vraćene iz odabrane sigurnosne kopije.",
        "That backup could not be restored.": "Tu sigurnosnu kopiju nije bilo moguće vratiti.",
        "\"{name}\" could not be read and was restored from the backup of {when}.":
            "„{name}” nije bilo moguće pročitati i vraćena je iz sigurnosne kopije od {when}.",

        # ---- keyboard shortcuts (tray + cheat-sheet) ----
        "Keyboard shortcuts…": "Tipkovnički prečaci…",
        "Keyboard shortcuts": "Tipkovnički prečaci",
        "Turn these on or off in Settings.": "Uključi ili isključi u Postavkama.",
        # ---- cheat-sheet tabs + section notes (translated via tr(title), so the
        # AST scan in test_i18n_hr_complete can't see them — that test checks the
        # shortcuts catalog explicitly instead) ----
        "Global": "Globalno",
        "Text & lists": "Tekst i liste",
        "Code": "Kod",
        "Windows": "Prozori",
        "These act on the note you are using right now.":
            "Ovo djeluje na bilješku koju trenutno koristiš.",
        "These only do anything while \"Enable code blocks\" is on (Settings → Note).":
            "Ovo radi samo kad je uključeno „Enable code blocks\" (Postavke → Bilješka).",

        # ---- export: PNG ----
        "Image (.png)": "Slika (.png)",
        "PNG image (*.png)": "PNG slika (*.png)",
    },
    "ru": {
        'OK': 'ОК',
        'Cancel': 'Отмена',
        'Save': 'Сохранить',
        'Close': 'Закрыть',
        'Apply': 'Применить',
        'Select': 'Выбрать',
        'Set': 'Установить',
        'Refresh': 'Обновить',
        'Copy': 'Копировать',
        'Copied': 'Скопировано',
        'New Note': 'Новая заметка',
        'Show All': 'Показать все',
        'Hide All': 'Скрыть все',
        'Lock All': 'Заблокировать все',
        'Unlock All': 'Разблокировать все',
        'Notes Manager': 'Менеджер заметок',
        'Settings': 'Настройки',
        'About': 'О программе',
        'Toggle theme': 'Переключить тему',
        'Quit': 'Выход',
        'Note Options': 'Параметры заметки',
        'Toggle Toolbar': 'Показать/скрыть панель инструментов',
        'Lock / Unlock': 'Заблокировать / разблокировать',
        'Hide Note': 'Скрыть заметку',
        'Always on Top': 'Поверх всех окон',
        'Favorite': 'Избранное',
        'Add to Favorites': 'Добавить в избранное',
        'Remove from Favorites': 'Удалить из избранного',
        'Bold (Ctrl+B)': 'Жирный (Ctrl+B)',
        'Italic (Ctrl+I)': 'Курсив (Ctrl+I)',
        'Underline (Ctrl+U)': 'Подчёркнутый (Ctrl+U)',
        'Strikethrough (Ctrl+S)': 'Зачёркнутый (Ctrl+S)',
        'Bullet list': 'Маркированный список',
        'Checklist': 'Список задач',
        'Checklist — Tab to indent, drag a box or Alt+↑/↓ to reorder': 'Список задач — Tab для отступа, перетащите флажок или Alt+↑/↓ для изменения порядка',
        'Checklist progress (done / total)': 'Прогресс списка (выполнено / всего)',
        'Increase font size': 'Увеличить размер шрифта',
        'Decrease font size': 'Уменьшить размер шрифта',
        'Text Colour': 'Цвет текста',
        'Font family': 'Семейство шрифтов',
        'Click to set exact size': 'Нажмите, чтобы задать точный размер',
        'Click to open colour picker': 'Нажмите, чтобы открыть выбор цвета',
        'Write your note here…': 'Напишите заметку здесь…',
        'More fonts…': 'Больше шрифтов…',
        'Change Colour…': 'Изменить цвет…',
        'Copy Note': 'Копировать заметку',
        'Rename…': 'Переименовать…',
        'Rename': 'Переименовать',
        'Paste as plain text': 'Вставить как обычный текст',
        'Move to Trash': 'Переместить в корзину',
        'Custom colour:': 'Свой цвет:',
        '●  Disc': '●  Круг',
        '▪  Square': '▪  Квадрат',
        '1.  Decimal': '1.  Числа',
        'a.  Lower alpha': 'a.  Строчные буквы',
        'i.  Lower roman': 'i.  Строчные римские',
        '✕  Remove list': '✕  Удалить список',
        'Rename note': 'Переименовать заметку',
        'Note name:': 'Название заметки:',
        'Leave empty to use the automatic name (first line of the note).': 'Оставьте пустым для автоматического названия (первая строка заметки).',
        'Untitled': 'Без названия',
        'Reminder': 'Напоминание',
        'Set reminder…': 'Установить напоминание…',
        'Reminder: ': 'Напоминание: ',
        'Reminder: {} — change…': 'Напоминание: {} — изменить…',
        'Current: ': 'Текущее: ',
        'Quick options:': 'Быстрые варианты:',
        'Or a specific time:': 'Или конкретное время:',
        'Or a specific date and time:': 'Или конкретная дата и время:',
        'Date': 'Дата',
        'Time': 'Время',
        'In 1 min': 'Через 1 мин',
        'In 5 min': 'Через 5 мин',
        'In 10 min': 'Через 10 мин',
        'In 30 min': 'Через 30 мин',
        'In 1 hour': 'Через 1 час',
        'In 3 hours': 'Через 3 часа',
        'In 8 hours': 'Через 8 часов',
        'In 24 hours': 'Через 24 часа',
        'Remove reminder': 'Удалить напоминание',
        'Export Note': 'Экспорт заметки',
        'Export Failed': 'Экспорт не удался',
        'Plain text (.txt)': 'Обычный текст (.txt)',
        'OpenDocument (.odt)': 'OpenDocument (.odt)',
        'PDF (.pdf)': 'PDF (.pdf)',
        'Text files (*.txt)': 'Текстовые файлы (*.txt)',
        'OpenDocument (*.odt)': 'OpenDocument (*.odt)',
        'PDF (*.pdf)': 'PDF (*.pdf)',
        '(empty note)': '(пустая заметка)',
        'Restore All': 'Восстановить все',
        'Delete All': 'Удалить все',
        'Search notes…': 'Поиск заметок…',
        'Search notes': 'Поиск заметок',
        'Search Notes…': 'Поиск заметок…',
        'No matching notes': 'Нет подходящих заметок',
        'Global shortcut for searching notes': 'Глобальное сочетание клавиш для поиска заметок',
        'Scroll on tray icon to raise/lower notes': 'Прокрутка на значке в трее поднимает/опускает заметки',
        'Scroll up = bring visible notes to front; scroll down = send them behind other windows. Pinned notes are left alone.': 'Прокрутка вверх = вывести видимые заметки на передний план; прокрутка вниз = отправить их за другие окна. Закреплённые заметки не затрагиваются.',
        'Press {} anywhere to open the search palette. Rebind it in GNOME Settings → Keyboard → Custom Shortcuts.': 'Нажмите {} в любом месте, чтобы открыть панель поиска. Измените сочетание в GNOME Settings → Keyboard → Custom Shortcuts.',
        'Registers a GNOME shortcut ({}) to open a search box for finding a note from anywhere.': 'Регистрирует сочетание клавиш GNOME ({}) для открытия поля поиска заметок из любого места.',
        'Restore': 'Восстановить',
        'Delete permanently': 'Удалить навсегда',
        'Active': 'Активные',
        'Archive': 'Архив',
        'Trash': 'Корзина',
        'Active ({})': 'Активные ({})',
        'Active ({}/{})': 'Активные ({}/{})',
        'Archive ({})': 'Архив ({})',
        'Archive ({}/{})': 'Архив ({}/{})',
        'Trash ({})': 'Корзина ({})',
        'Trash ({}/{})': 'Корзина ({}/{})',
        '{} matches': '{} совпадений',
        '{} active · {} in trash': '{} активных · {} в корзине',
        '{} active · {} archived · {} in trash': '{} активных · {} в архиве · {} в корзине',
        'Archive Full': 'Архив заполнен',
        'Active Full': 'Активные заполнены',
        'Partly Restored': 'Частично восстановлено',
        'Archive is full ({} notes).\nRemove something from the Archive first.': 'Архив заполнен ({} заметок).\nСначала удалите что-нибудь из архива.',
        'You already have {} active notes — the maximum.\nArchive or delete one first.': 'У вас уже есть {} активных заметок — это максимум.\nСначала архивируйте или удалите одну.',
        'You already have {} active notes — the maximum.': 'У вас уже есть {} активных заметок — это максимум.',
        'Restored {} note(s). {} could not be restored — the active limit ({}) was reached.': 'Восстановлено {} заметок. {} не удалось восстановить — достигнут лимит активных ({}).',
        'Permanently delete all {} note(s) in Trash?\nThis cannot be undone.': 'Безвозвратно удалить все {} заметок в корзине?\nЭто действие нельзя отменить.',
        'Start automatically on login': 'Запускать автоматически при входе',
        'Creates an autostart entry in ~/.config/autostart/': 'Создаёт запись автозапуска в ~/.config/autostart/',
        'Requires GNOME (gsettings). Bind a shortcut manually instead.': 'Требуется GNOME (gsettings). Вместо этого назначьте сочетание клавиш вручную.',
        'Global shortcut for new note': 'Глобальное сочетание клавиш для новой заметки',
        'Global shortcut for new note from clipboard': 'Глобальное сочетание клавиш для заметки из буфера обмена',
        'Press {} anywhere to create a new note. Rebind it in GNOME Settings → Keyboard → Custom Shortcuts.': 'Нажмите {} в любом месте, чтобы создать новую заметку. Измените сочетание в GNOME Settings → Keyboard → Custom Shortcuts.',
        'Press {} anywhere to create a note from the clipboard. Rebind it in GNOME Settings → Keyboard → Custom Shortcuts.': 'Нажмите {} в любом месте, чтобы создать заметку из буфера обмена. Измените сочетание в GNOME Settings → Keyboard → Custom Shortcuts.',
        'Registers a GNOME shortcut ({}) to create a new note.': 'Регистрирует сочетание клавиш GNOME ({}) для создания новой заметки.',
        'Registers a GNOME shortcut ({}) to create a note pre-filled with the clipboard contents.': 'Регистрирует сочетание клавиш GNOME ({}) для создания заметки с содержимым буфера обмена.',
        'UI Scale': 'Масштаб интерфейса',
        'Scales UI text and note content (100%–200%)': 'Масштабирует текст интерфейса и содержимое заметок (100%–200%)',
        'Scales the whole interface, text and icons (100%–200%).': 'Масштабирует весь интерфейс, текст и значки (100%–200%).',
        'Restart Sticky Notes to apply the new scale.': 'Перезапустите Sticky Notes, чтобы применить новый масштаб.',
        'Restart now': 'Перезапустить сейчас',
        'Default font size': 'Размер шрифта по умолчанию',
        'Choose Font': 'Выбрать шрифт',
        'Search fonts…': 'Поиск шрифтов…',
        'Apply Font to New Notes': 'Применить шрифт к новым заметкам',
        'Apply to New Notes': 'Применить к новым заметкам',
        'Note': 'Заметка',
        'Default size for new notes': 'Размер новых заметок по умолчанию',
        'Width': 'Ширина',
        'Height': 'Высота',
        'Background opacity': 'Прозрачность фона',
        'Makes the note paper see-through; text stays sharp. Applies to all current and future notes.': 'Делает бумагу заметки прозрачной; текст остаётся чётким. Применяется ко всем текущим и будущим заметкам.',
        'Auto backup every': 'Автосохранение копии каждые',
        '15 minutes': '15 минут',
        '30 minutes': '30 минут',
        '1 hour': '1 час',
        '2 hours': '2 часа',
        '4 hours': '4 часа',
        '8 hours': '8 часов',
        '12 hours': '12 часов',
        '24 hours': '24 часа',
        'Backup Now': 'Создать копию сейчас',
        'Last backup: {}': 'Последняя копия: {}',
        'No backup yet': 'Копий ещё нет',
        'Restore from Backup': 'Восстановить из копии',
        'Notes recovery': 'Восстановление заметок',
        'Some data files could not be read.': 'Некоторые файлы данных не удалось прочитать.',
        '"{name}" could not be read and was restored from its backup.': '«{name}» не удалось прочитать, и она восстановлена из резервной копии.',
        '"{name}" could not be read and no valid backup was found.': '«{name}» не удалось прочитать, и подходящая резервная копия не найдена.',
        'The damaged file was kept as "{kept}".': 'Повреждённый файл сохранён как «{kept}».',
        'The damaged file was kept as "{kept}" so no data was overwritten.': 'Повреждённый файл сохранён как «{kept}», поэтому данные не были перезаписаны.',
        'Restore notes from backup dated:\n{}\n\n⚠  Current notes will be replaced!': 'Восстановить заметки из копии от:\n{}\n\n⚠  Текущие заметки будут заменены!',
        'EXPORT / IMPORT': 'ЭКСПОРТ / ИМПОРТ',
        'Export to JSON…': 'Экспорт в JSON…',
        'Import from JSON…': 'Импорт из JSON…',
        'Language': 'Язык',
        'Language changes apply after restart.': 'Изменение языка применяется после перезапуска.',
        'General': 'Общие',
        'Backup': 'Резервные копии',
        'Snapping': 'Привязка',
        'Snapping && Tray': 'Привязка && трей',
        'Tray': 'Трей',
        'Snap to grid': 'Привязка к сетке',
        'Snap to other notes': 'Привязка к другим заметкам',
        'Snap size to grid': 'Привязка размера к сетке',
        'Grid size': 'Размер сетки',
        "Notes snap when you drop them or finish resizing. Snap to grid and snap size to grid align a note's position and size to an invisible grid; snap to other notes lines edges up with nearby notes. The grid size below sets the spacing.": 'Заметки привязываются при отпускании или после изменения размера. Привязка к сетке и привязка размера к сетке выравнивают положение и размер заметки по невидимой сетке; привязка к другим заметкам выравнивает края по соседним заметкам. Размер сетки ниже задаёт шаг.',
        'About Sticky Notes': 'О программе Sticky Notes',
        'Version {}': 'Версия {}',
        'A lightweight sticky notes application\nfor Ubuntu desktop.\n\nBuilt with Python & PyQt6':
            'Лёгкое приложение для стикеров\nдля рабочего стола Ubuntu.\n\nСоздано с помощью Python и PyQt6',
        'View on GitHub': 'Открыть на GitHub',
        'Made by Nikola Javorina': 'Автор: Никола Яворина',
        'For the sharpest result, keep system scaling at 100% and use this.': 'Для максимальной чёткости оставьте системное масштабирование на 100% и используйте это.',
        'Buy me a coffee': 'Угостить меня кофе',
        'Limit Reached': 'Достигнут лимит',
        'Maximum of {} active notes reached.\nArchive or move some notes to Trash before creating new ones.': 'Достигнут максимум в {} активных заметок.\nАрхивируйте или переместите некоторые в корзину перед созданием новых.',
        'Maximum of 20 active notes reached.\nMove some notes to Trash before creating new ones.': 'Достигнут максимум в 20 активных заметок.\nПереместите некоторые в корзину перед созданием новых.',
        'Export Complete': 'Экспорт завершён',
        'Export All': 'Экспортировать все',
        'Export': 'Экспорт',
        'There are no archived notes to export.': 'Нет архивных заметок для экспорта.',
        'Export all archived notes to a JSON file.': 'Экспортировать все архивные заметки в файл JSON.',
        'Backup saves local “.bak” copies of ALL your notes (active, archived and trash), kept next to your data on this computer. Restore brings all three back.': 'Резервное копирование сохраняет локальные копии «.bak» ВСЕХ ваших заметок (активные, архивные и корзина) рядом с вашими данными на этом компьютере. Восстановление возвращает все три категории.',
        "Export writes a portable JSON file of your ACTIVE notes (to move to another computer or re-import). Import always brings notes in as active. To export archived notes, use “Export All” in the Manager's Archive tab.": 'Экспорт создаёт переносимый файл JSON с вашими АКТИВНЫМИ заметками (для переноса на другой компьютер или повторного импорта). Импорт всегда добавляет заметки как активные. Чтобы экспортировать архивные заметки, используйте «Экспортировать все» на вкладке «Архив» в менеджере.',
        'Import Complete': 'Импорт завершён',
        'Import Failed': 'Импорт не удался',
        'Import — Limit Reached': 'Импорт — достигнут лимит',
        'You have {} active note(s). The export file contains {} note(s).\n\nYou can import at most {} note(s).\n\nImport the first {} and skip the rest?': 'У вас {} активных заметок. Файл экспорта содержит {} заметок.\n\nВы можете импортировать не более {} заметок.\n\nИмпортировать первые {} и пропустить остальные?',
        'Exported {} note(s) to:\n{}': 'Экспортировано {} заметок в:\n{}',
        'Imported {} note(s) successfully.': 'Успешно импортировано {} заметок.',
        'Could not read export file:\n{}': 'Не удалось прочитать файл экспорта:\n{}',
        'You already have {} active notes — the maximum.\nMove some notes to Trash before importing.': 'У вас уже есть {} активных заметок — это максимум.\nПеред импортом переместите некоторые в корзину.',
        'You already have 20 active notes — the maximum.\nMove some notes to Trash before importing.': 'У вас уже есть 20 активных заметок — это максимум.\nПеред импортом переместите некоторые в корзину.',
        'Sticky Notes — Reminder': 'Sticky Notes — Напоминание',
        'Snooze 10 min': 'Отложить на 10 мин',
        'Adjust text & icon colour to note background': 'Подстраивать цвет текста и значков под фон заметки',
        'Dark notes get light icons and text automatically. Turn off to keep the classic dark ink.': 'Тёмные заметки автоматически получают светлые значки и текст. Отключите, чтобы сохранить классические тёмные чернила.',
        'Auto-hide toolbar and header until you hover the note': 'Автоматически скрывать панель инструментов и заголовок, пока курсор не наведён на заметку',
        'Note border': 'Рамка заметки',
        'Off': 'Выключено',
        'Always': 'Всегда',
        'Auto (light notes only)': 'Автоматически (только светлые заметки)',
        'Auto shows a border only on light notes, where it helps them stand out from a light background.': 'Автоматический режим показывает рамку только на светлых заметках, где она помогает выделить их на светлом фоне.',
        "Notes show only their text at rest; hover the top of a note to bring the controls back. A single click on the header keeps the controls up and lets you nudge the note with the arrow keys; click elsewhere to hide them again. Double-click a note's header to keep its controls open while you edit it; double-click again to hand that note back to auto-hide.": 'В состоянии покоя заметки показывают только текст; наведите курсор на верх заметки, чтобы вернуть элементы управления. Один щелчок по заголовку удерживает элементы управления открытыми и позволяет перемещать заметку клавишами со стрелками; щелчок в другом месте снова скрывает их. Двойной щелчок по заголовку заметки удерживает её элементы управления открытыми во время редактирования; повторный двойной щелчок возвращает заметку в режим автоскрытия.',
        'Code block': 'Блок кода',
        'Inline code': 'Встроенный код',
        'Enable code blocks': 'Включить блоки кода',
        'Adds code-block { } and inline-code buttons to the toolbar, and enables their shortcuts (Ctrl+M for inline code, Ctrl+Shift+M for a code block). Niche — off by default.': 'Добавляет кнопки блока кода { } и встроенного кода на панель инструментов, а также включает их сочетания клавиш (Ctrl+M для встроенного кода, Ctrl+Shift+M для блока кода). Редко используется — по умолчанию выключено.',
        'Appearance': 'Внешний вид',
        'Window theme': 'Тема окон',
        'Theme': 'Тема',
        'Light': 'Светлая',
        'Dark': 'Тёмная',
        'Auto': 'Автоматически',
        'Dark from': 'Тёмная с',
        'until': 'до',
        "Auto switches to Dark between these times; the theme changes within a minute of each boundary. The tray's Toggle theme then lasts only until the next boundary.": 'Автоматический режим переключается на тёмную тему между этими временами; тема меняется в течение минуты после каждой границы. Переключение темы из трея действует только до следующей границы.',
        "Sets the look of the app's windows, menus and notes. Switching to Dark gives every note without its own dark colour a dark default; each note keeps separate colours for Light and Dark, so switching back restores the light one. Notes and the main windows recolour instantly; a few helper windows (About, the shortcut list, search) update the next time you open them — no restart needed.": 'Задаёт внешний вид окон, меню и заметок приложения. Переключение на тёмную тему даёт каждой заметке без собственного тёмного цвета тёмный цвет по умолчанию; каждая заметка хранит отдельные цвета для светлой и тёмной темы, поэтому обратное переключение восстанавливает светлый цвет. Заметки и главные окна перекрашиваются мгновенно; несколько вспомогательных окон (О программе, список сочетаний клавиш, поиск) обновляются при следующем открытии — перезапуск не требуется.',
        'Scroll the tray icon to bring notes to front': 'Прокрутка на значке в трее выводит заметки на передний план',
        'Scroll up on the tray icon to raise your visible notes above other windows. Pinned notes are unaffected.': 'Прокрутите вверх на значке в трее, чтобы поднять видимые заметки над другими окнами. Закреплённые заметки не затрагиваются.',
        'Backups': 'Резервные копии',
        'Backups save copies of ALL your notes (active, archived and trash) in a backups folder on this computer. "Backup Now" and the auto-backup interval each add a new restore point (the 5 most recent are kept); the daily auto-backup keeps the latest one fresh. "Restore from Backup…" lets you pick which one to go back to (this overwrites your current notes).': 'Резервные копии сохраняют копии ВСЕХ ваших заметок (активные, архивные и корзина) в папке backups на этом компьютере. «Создать копию сейчас» и интервал автосохранения каждый раз добавляют новую точку восстановления (хранятся 5 последних); ежедневное автосохранение поддерживает актуальность последней копии. «Восстановить из копии…» позволяет выбрать, к какой точке вернуться (это перезапишет текущие заметки).',
        'Restore from Backup…': 'Восстановить из копии…',
        'Restore your notes from an earlier backup': 'Восстановить заметки из более ранней резервной копии',
        'The 5 most recent backups. Restoring overwrites your current notes and cannot be undone — press "Backup Now" first if you want to keep them.': '5 последних резервных копий. Восстановление перезаписывает текущие заметки и не может быть отменено — сначала нажмите «Создать копию сейчас», если хотите их сохранить.',
        'No backups yet.': 'Резервных копий ещё нет.',
        '(latest)': '(последняя)',
        'Restore selected': 'Восстановить выбранное',
        'Replace your current notes with the backup from {}?\n\nThis overwrites your current notes and cannot be undone. Use "Backup Now" first if you want to keep them.': 'Заменить текущие заметки резервной копией от {}?\n\nЭто перезапишет текущие заметки и не может быть отменено. Сначала используйте «Создать копию сейчас», если хотите их сохранить.',
        'Restore complete': 'Восстановление завершено',
        'Restore failed': 'Восстановление не удалось',
        'Your notes were restored from the selected backup.': 'Ваши заметки восстановлены из выбранной резервной копии.',
        'That backup could not be restored.': 'Эту резервную копию не удалось восстановить.',
        '"{name}" could not be read and was restored from the backup of {when}.': '«{name}» не удалось прочитать, и она восстановлена из резервной копии от {when}.',
        'Keyboard shortcuts…': 'Сочетания клавиш…',
        'Keyboard shortcuts': 'Сочетания клавиш',
        'Turn these on or off in Settings.': 'Включите или отключите их в настройках.',
        'Global': 'Общие',
        'Text & lists': 'Текст и списки',
        'Code': 'Код',
        'Windows': 'Окна',
        'These act on the note you are using right now.': 'Эти действия относятся к заметке, с которой вы сейчас работаете.',
        'These only do anything while "Enable code blocks" is on (Settings → Note).': 'Эти действия работают только при включённой опции «Включить блоки кода» (Настройки → Заметка).',
        'Image (.png)': 'Изображение (.png)',
        'PNG image (*.png)': 'Изображение PNG (*.png)',
    },

    "zh": {
        'OK': '确定',
        'Cancel': '取消',
        'Save': '保存',
        'Close': '关闭',
        'Apply': '应用',
        'Select': '选择',
        'Set': '设置',
        'Refresh': '刷新',
        'Copy': '复制',
        'Copied': '已复制',
        'New Note': '新建便签',
        'Show All': '显示全部',
        'Hide All': '隐藏全部',
        'Lock All': '全部锁定',
        'Unlock All': '全部解锁',
        'Notes Manager': '便签管理器',
        'Settings': '设置',
        'About': '关于',
        'Toggle theme': '切换主题',
        'Quit': '退出',
        'Note Options': '便签选项',
        'Toggle Toolbar': '显示/隐藏工具栏',
        'Lock / Unlock': '锁定 / 解锁',
        'Hide Note': '隐藏便签',
        'Always on Top': '始终置顶',
        'Favorite': '收藏',
        'Add to Favorites': '添加到收藏',
        'Remove from Favorites': '从收藏中移除',
        'Bold (Ctrl+B)': '粗体 (Ctrl+B)',
        'Italic (Ctrl+I)': '斜体 (Ctrl+I)',
        'Underline (Ctrl+U)': '下划线 (Ctrl+U)',
        'Strikethrough (Ctrl+S)': '删除线 (Ctrl+S)',
        'Bullet list': '项目符号列表',
        'Checklist': '清单列表',
        'Checklist — Tab to indent, drag a box or Alt+↑/↓ to reorder': '清单列表 — 按 Tab 缩进，拖动方框或按 Alt+↑/↓ 重新排序',
        'Checklist progress (done / total)': '清单进度（已完成 / 总数）',
        'Increase font size': '增大字号',
        'Decrease font size': '减小字号',
        'Text Colour': '文字颜色',
        'Font family': '字体',
        'Click to set exact size': '点击设置精确大小',
        'Click to open colour picker': '点击打开颜色选择器',
        'Write your note here…': '在此处输入便签内容…',
        'More fonts…': '更多字体…',
        'Change Colour…': '更改颜色…',
        'Copy Note': '复制便签',
        'Rename…': '重命名…',
        'Rename': '重命名',
        'Paste as plain text': '粘贴为纯文本',
        'Move to Trash': '移到回收站',
        'Custom colour:': '自定义颜色：',
        '●  Disc': '●  圆点',
        '▪  Square': '▪  方块',
        '1.  Decimal': '1.  数字',
        'a.  Lower alpha': 'a.  小写字母',
        'i.  Lower roman': 'i.  小写罗马数字',
        '✕  Remove list': '✕  移除列表',
        'Rename note': '重命名便签',
        'Note name:': '便签名称：',
        'Leave empty to use the automatic name (first line of the note).': '留空则使用自动名称（便签的第一行）。',
        'Untitled': '无标题',
        'Reminder': '提醒',
        'Set reminder…': '设置提醒…',
        'Reminder: ': '提醒：',
        'Reminder: {} — change…': '提醒：{} — 更改…',
        'Current: ': '当前：',
        'Quick options:': '快捷选项：',
        'Or a specific time:': '或指定时间：',
        'Or a specific date and time:': '或指定日期和时间：',
        'Date': '日期',
        'Time': '时间',
        'In 1 min': '1 分钟后',
        'In 5 min': '5 分钟后',
        'In 10 min': '10 分钟后',
        'In 30 min': '30 分钟后',
        'In 1 hour': '1 小时后',
        'In 3 hours': '3 小时后',
        'In 8 hours': '8 小时后',
        'In 24 hours': '24 小时后',
        'Remove reminder': '移除提醒',
        'Export Note': '导出便签',
        'Export Failed': '导出失败',
        'Plain text (.txt)': '纯文本 (.txt)',
        'OpenDocument (.odt)': 'OpenDocument (.odt)',
        'PDF (.pdf)': 'PDF (.pdf)',
        'Text files (*.txt)': '文本文件 (*.txt)',
        'OpenDocument (*.odt)': 'OpenDocument (*.odt)',
        'PDF (*.pdf)': 'PDF (*.pdf)',
        '(empty note)': '(空便签)',
        'Restore All': '全部恢复',
        'Delete All': '全部删除',
        'Search notes…': '搜索便签…',
        'Search notes': '搜索便签',
        'Search Notes…': '搜索便签…',
        'No matching notes': '没有匹配的便签',
        'Global shortcut for searching notes': '搜索便签的全局快捷键',
        'Scroll on tray icon to raise/lower notes': '在托盘图标上滚动以置顶/置后便签',
        'Scroll up = bring visible notes to front; scroll down = send them behind other windows. Pinned notes are left alone.': '向上滚动会将可见便签置于最前；向下滚动会将其移到其他窗口后面。置顶便签不受影响。',
        'Press {} anywhere to open the search palette. Rebind it in GNOME Settings → Keyboard → Custom Shortcuts.': '在任意位置按 {} 即可打开搜索面板。可在 GNOME 设置 → 键盘 → 自定义快捷键中重新绑定。',
        'Registers a GNOME shortcut ({}) to open a search box for finding a note from anywhere.': '注册一个 GNOME 快捷键（{}），可在任意位置打开搜索框查找便签。',
        'Restore': '恢复',
        'Delete permanently': '永久删除',
        'Active': '活动',
        'Archive': '归档',
        'Trash': '回收站',
        'Active ({})': '活动 ({})',
        'Active ({}/{})': '活动 ({}/{})',
        'Archive ({})': '归档 ({})',
        'Archive ({}/{})': '归档 ({}/{})',
        'Trash ({})': '回收站 ({})',
        'Trash ({}/{})': '回收站 ({}/{})',
        '{} matches': '{} 个匹配项',
        '{} active · {} in trash': '{} 个活动 · {} 个在回收站',
        '{} active · {} archived · {} in trash': '{} 个活动 · {} 个已归档 · {} 个在回收站',
        'Archive Full': '归档已满',
        'Active Full': '活动已满',
        'Partly Restored': '部分已恢复',
        'Archive is full ({} notes).\nRemove something from the Archive first.': '归档已满（{} 条便签）。\n请先从归档中移除一些内容。',
        'You already have {} active notes — the maximum.\nArchive or delete one first.': '你已经有 {} 条活动便签——已达上限。\n请先归档或删除一条。',
        'You already have {} active notes — the maximum.': '你已经有 {} 条活动便签——已达上限。',
        'Restored {} note(s). {} could not be restored — the active limit ({}) was reached.': '已恢复 {} 条便签。{} 条无法恢复——已达到活动上限（{}）。',
        'Permanently delete all {} note(s) in Trash?\nThis cannot be undone.': '永久删除回收站中的全部 {} 条便签？\n此操作无法撤销。',
        'Start automatically on login': '登录时自动启动',
        'Creates an autostart entry in ~/.config/autostart/': '在 ~/.config/autostart/ 中创建自动启动项',
        'Requires GNOME (gsettings). Bind a shortcut manually instead.': '需要 GNOME（gsettings）。请改为手动绑定快捷键。',
        'Global shortcut for new note': '新建便签的全局快捷键',
        'Global shortcut for new note from clipboard': '从剪贴板新建便签的全局快捷键',
        'Press {} anywhere to create a new note. Rebind it in GNOME Settings → Keyboard → Custom Shortcuts.': '在任意位置按 {} 即可新建便签。可在 GNOME 设置 → 键盘 → 自定义快捷键中重新绑定。',
        'Press {} anywhere to create a note from the clipboard. Rebind it in GNOME Settings → Keyboard → Custom Shortcuts.': '在任意位置按 {} 即可从剪贴板内容新建便签。可在 GNOME 设置 → 键盘 → 自定义快捷键中重新绑定。',
        'Registers a GNOME shortcut ({}) to create a new note.': '注册一个 GNOME 快捷键（{}）用于新建便签。',
        'Registers a GNOME shortcut ({}) to create a note pre-filled with the clipboard contents.': '注册一个 GNOME 快捷键（{}），用于创建预填剪贴板内容的便签。',
        'UI Scale': '界面缩放',
        'Scales UI text and note content (100%–200%)': '缩放界面文字和便签内容（100%–200%）',
        'Scales the whole interface, text and icons (100%–200%).': '缩放整个界面、文字和图标（100%–200%）。',
        'Restart Sticky Notes to apply the new scale.': '重启 Sticky Notes 以应用新的缩放比例。',
        'Restart now': '立即重启',
        'Default font size': '默认字号',
        'Choose Font': '选择字体',
        'Search fonts…': '搜索字体…',
        'Apply Font to New Notes': '将字体应用到新便签',
        'Apply to New Notes': '应用到新便签',
        'Note': '便签',
        'Default size for new notes': '新便签的默认大小',
        'Width': '宽度',
        'Height': '高度',
        'Background opacity': '背景不透明度',
        'Makes the note paper see-through; text stays sharp. Applies to all current and future notes.': '使便签纸张变得透明；文字仍保持清晰。适用于所有当前及以后的便签。',
        'Auto backup every': '自动备份间隔',
        '15 minutes': '15 分钟',
        '30 minutes': '30 分钟',
        '1 hour': '1 小时',
        '2 hours': '2 小时',
        '4 hours': '4 小时',
        '8 hours': '8 小时',
        '12 hours': '12 小时',
        '24 hours': '24 小时',
        'Backup Now': '立即备份',
        'Last backup: {}': '上次备份：{}',
        'No backup yet': '尚无备份',
        'Restore from Backup': '从备份恢复',
        'Notes recovery': '便签恢复',
        'Some data files could not be read.': '部分数据文件无法读取。',
        '"{name}" could not be read and was restored from its backup.': '“{name}” 无法读取，已从其备份中恢复。',
        '"{name}" could not be read and no valid backup was found.': '“{name}” 无法读取，且未找到有效备份。',
        'The damaged file was kept as "{kept}".': '损坏的文件已保留为 “{kept}”。',
        'The damaged file was kept as "{kept}" so no data was overwritten.': '损坏的文件已保留为 “{kept}”，因此没有数据被覆盖。',
        'Restore notes from backup dated:\n{}\n\n⚠  Current notes will be replaced!': '从以下日期的备份恢复便签：\n{}\n\n⚠  当前便签将被替换！',
        'EXPORT / IMPORT': '导出 / 导入',
        'Export to JSON…': '导出为 JSON…',
        'Import from JSON…': '从 JSON 导入…',
        'Language': '语言',
        'Language changes apply after restart.': '语言更改将在重启后生效。',
        'General': '常规',
        'Backup': '备份',
        'Snapping': '吸附',
        'Snapping && Tray': '吸附 && 托盘',
        'Tray': '托盘',
        'Snap to grid': '吸附到网格',
        'Snap to other notes': '吸附到其他便签',
        'Snap size to grid': '尺寸吸附到网格',
        'Grid size': '网格大小',
        "Notes snap when you drop them or finish resizing. Snap to grid and snap size to grid align a note's position and size to an invisible grid; snap to other notes lines edges up with nearby notes. The grid size below sets the spacing.": '释放便签或完成调整大小时会发生吸附。“吸附到网格”和“尺寸吸附到网格”会将便签的位置和大小对齐到隐形网格；“吸附到其他便签”会将边缘与附近的便签对齐。下方的网格大小用于设置间距。',
        'About Sticky Notes': '关于 Sticky Notes',
        'Version {}': '版本 {}',
        'A lightweight sticky notes application\nfor Ubuntu desktop.\n\nBuilt with Python & PyQt6':
            '一款适用于 Ubuntu 桌面的\n轻量级便签应用。\n\n使用 Python 和 PyQt6 构建',
        'View on GitHub': '在 GitHub 上查看',
        'Made by Nikola Javorina': '作者：Nikola Javorina',
        'For the sharpest result, keep system scaling at 100% and use this.': '为获得最清晰的效果，请将系统缩放保持为 100% 并使用此选项。',
        'Buy me a coffee': '请我喝杯咖啡',
        'Limit Reached': '已达上限',
        'Maximum of {} active notes reached.\nArchive or move some notes to Trash before creating new ones.': '已达到最多 {} 条活动便签的上限。\n请先归档或将部分便签移至回收站，再创建新便签。',
        'Maximum of 20 active notes reached.\nMove some notes to Trash before creating new ones.': '已达到最多 20 条活动便签的上限。\n请先将部分便签移至回收站，再创建新便签。',
        'Export Complete': '导出完成',
        'Export All': '导出全部',
        'Export': '导出',
        'There are no archived notes to export.': '没有可导出的归档便签。',
        'Export all archived notes to a JSON file.': '将所有归档便签导出为 JSON 文件。',
        'Backup saves local “.bak” copies of ALL your notes (active, archived and trash), kept next to your data on this computer. Restore brings all three back.': '备份会在本机数据旁保存所有便签（活动、归档和回收站）的本地“.bak”副本。恢复会将这三类便签全部找回。',
        "Export writes a portable JSON file of your ACTIVE notes (to move to another computer or re-import). Import always brings notes in as active. To export archived notes, use “Export All” in the Manager's Archive tab.": '导出会为你的活动便签生成一个可移植的 JSON 文件（用于转移到其他电脑或重新导入）。导入时始终会将便签作为活动便签导入。要导出归档便签，请使用管理器归档标签页中的“导出全部”。',
        'Import Complete': '导入完成',
        'Import Failed': '导入失败',
        'Import — Limit Reached': '导入 — 已达上限',
        'You have {} active note(s). The export file contains {} note(s).\n\nYou can import at most {} note(s).\n\nImport the first {} and skip the rest?': '你目前有 {} 条活动便签。导出文件包含 {} 条便签。\n\n最多可导入 {} 条便签。\n\n是否导入前 {} 条并跳过其余部分？',
        'Exported {} note(s) to:\n{}': '已将 {} 条便签导出到：\n{}',
        'Imported {} note(s) successfully.': '已成功导入 {} 条便签。',
        'Could not read export file:\n{}': '无法读取导出文件：\n{}',
        'You already have {} active notes — the maximum.\nMove some notes to Trash before importing.': '你已经有 {} 条活动便签——已达上限。\n请先将部分便签移至回收站，再导入。',
        'You already have 20 active notes — the maximum.\nMove some notes to Trash before importing.': '你已经有 20 条活动便签——已达上限。\n请先将部分便签移至回收站，再导入。',
        'Sticky Notes — Reminder': 'Sticky Notes — 提醒',
        'Snooze 10 min': '延迟 10 分钟',
        'Adjust text & icon colour to note background': '根据便签背景调整文字和图标颜色',
        'Dark notes get light icons and text automatically. Turn off to keep the classic dark ink.': '深色便签会自动获得浅色图标和文字。关闭此选项可保留经典的深色墨迹。',
        'Auto-hide toolbar and header until you hover the note': '自动隐藏工具栏和标题栏，直到鼠标悬停在便签上',
        'Note border': '便签边框',
        'Off': '关闭',
        'Always': '始终',
        'Auto (light notes only)': '自动（仅浅色便签）',
        'Auto shows a border only on light notes, where it helps them stand out from a light background.': '自动模式仅在浅色便签上显示边框，帮助它们从浅色背景中凸显出来。',
        "Notes show only their text at rest; hover the top of a note to bring the controls back. A single click on the header keeps the controls up and lets you nudge the note with the arrow keys; click elsewhere to hide them again. Double-click a note's header to keep its controls open while you edit it; double-click again to hand that note back to auto-hide.": '便签在静止状态下只显示文字；将鼠标悬停在便签顶部即可唤出控件。单击标题栏可让控件保持显示，并可用方向键微调便签位置；点击其他位置会再次隐藏控件。双击便签的标题栏可在编辑时保持控件常开；再次双击可让该便签恢复自动隐藏。',
        'Code block': '代码块',
        'Inline code': '行内代码',
        'Enable code blocks': '启用代码块',
        'Adds code-block { } and inline-code buttons to the toolbar, and enables their shortcuts (Ctrl+M for inline code, Ctrl+Shift+M for a code block). Niche — off by default.': '在工具栏中添加代码块 { } 和行内代码按钮，并启用相应快捷键（Ctrl+M 用于行内代码，Ctrl+Shift+M 用于代码块）。小众功能——默认关闭。',
        'Appearance': '外观',
        'Window theme': '窗口主题',
        'Theme': '主题',
        'Light': '浅色',
        'Dark': '深色',
        'Auto': '自动',
        'Dark from': '深色开始于',
        'until': '至',
        "Auto switches to Dark between these times; the theme changes within a minute of each boundary. The tray's Toggle theme then lasts only until the next boundary.": '自动模式会在这段时间内切换为深色主题；主题会在每个边界时间的一分钟内变化。此后托盘的“切换主题”仅在下一个边界前有效。',
        "Sets the look of the app's windows, menus and notes. Switching to Dark gives every note without its own dark colour a dark default; each note keeps separate colours for Light and Dark, so switching back restores the light one. Notes and the main windows recolour instantly; a few helper windows (About, the shortcut list, search) update the next time you open them — no restart needed.": '设置应用窗口、菜单和便签的外观。切换到深色主题时，没有自定义深色的便签会使用默认深色；每张便签会分别保存浅色和深色两种颜色，因此切换回来会恢复浅色。便签和主窗口会立即变色；少数辅助窗口（关于、快捷键列表、搜索）会在下次打开时更新——无需重启。',
        'Scroll the tray icon to bring notes to front': '在托盘图标上滚动以将便签置于最前',
        'Scroll up on the tray icon to raise your visible notes above other windows. Pinned notes are unaffected.': '在托盘图标上向上滚动，可将可见便签提升到其他窗口之上。置顶便签不受影响。',
        'Backups': '备份',
        'Backups save copies of ALL your notes (active, archived and trash) in a backups folder on this computer. "Backup Now" and the auto-backup interval each add a new restore point (the 5 most recent are kept); the daily auto-backup keeps the latest one fresh. "Restore from Backup…" lets you pick which one to go back to (this overwrites your current notes).': '备份会将你所有便签（活动、归档和回收站）的副本保存在本机的 backups 文件夹中。“立即备份”和自动备份间隔每次都会新增一个还原点（保留最近 5 个）；每日自动备份会持续更新最新的一份。“从备份恢复…”可让你选择要还原到哪一个（这会覆盖当前便签）。',
        'Restore from Backup…': '从备份恢复…',
        'Restore your notes from an earlier backup': '从较早的备份恢复便签',
        'The 5 most recent backups. Restoring overwrites your current notes and cannot be undone — press "Backup Now" first if you want to keep them.': '最近的 5 个备份。恢复会覆盖当前便签且无法撤销——如果想保留当前便签，请先点击“立即备份”。',
        'No backups yet.': '尚无备份。',
        '(latest)': '(最新)',
        'Restore selected': '恢复所选',
        'Replace your current notes with the backup from {}?\n\nThis overwrites your current notes and cannot be undone. Use "Backup Now" first if you want to keep them.': '要用来自 {} 的备份替换当前便签吗？\n\n此操作会覆盖当前便签且无法撤销。如果想保留当前便签，请先使用“立即备份”。',
        'Restore complete': '恢复完成',
        'Restore failed': '恢复失败',
        'Your notes were restored from the selected backup.': '你的便签已从所选备份中恢复。',
        'That backup could not be restored.': '无法恢复该备份。',
        '"{name}" could not be read and was restored from the backup of {when}.': '“{name}” 无法读取，已从 {when} 的备份中恢复。',
        'Keyboard shortcuts…': '键盘快捷键…',
        'Keyboard shortcuts': '键盘快捷键',
        'Turn these on or off in Settings.': '可在设置中开启或关闭这些功能。',
        'Global': '全局',
        'Text & lists': '文本与列表',
        'Code': '代码',
        'Windows': '窗口',
        'These act on the note you are using right now.': '这些操作作用于你当前正在使用的便签。',
        'These only do anything while "Enable code blocks" is on (Settings → Note).': '这些操作仅在开启“启用代码块”时才有效（设置 → 便签）。',
        'Image (.png)': 'Image (.png)',
        'PNG image (*.png)': 'PNG 图片 (*.png)',
    },
    "pt": {
        # ---- generic actions / buttons ----
        "OK": "OK",
        "Cancel": "Cancelar",
        "Save": "Salvar",
        "Close": "Fechar",
        "Apply": "Aplicar",
        "Select": "Selecionar",
        "Set": "Definir",
        "Refresh": "Atualizar",
        "Copy": "Copiar",
        "Copied": "Copiado",

        # ---- tray menu ----
        "New Note": "Nova nota",
        "Show All": "Mostrar todas",
        "Hide All": "Ocultar todas",
        "Lock All": "Bloquear todas",
        "Unlock All": "Desbloquear todas",
        "Notes Manager": "Gerenciador de notas",
        "Settings": "Configurações",
        "About": "Sobre",
        "Toggle theme": "Alternar tema",
        "Quit": "Sair",

        # ---- note header / toolbar ----
        "Note Options": "Opções da nota",
        "Toggle Toolbar": "Mostrar/ocultar barra de ferramentas",
        "Lock / Unlock": "Bloquear / desbloquear",
        "Hide Note": "Ocultar nota",
        "Always on Top": "Sempre no topo",
        "Favorite": "Favorito",
        "Add to Favorites": "Adicionar aos favoritos",
        "Remove from Favorites": "Remover dos favoritos",
        "Bold (Ctrl+B)": "Negrito (Ctrl+B)",
        "Italic (Ctrl+I)": "Itálico (Ctrl+I)",
        "Underline (Ctrl+U)": "Sublinhado (Ctrl+U)",
        "Strikethrough (Ctrl+S)": "Tachado (Ctrl+S)",
        "Bullet list": "Lista com marcadores",
        "Checklist": "Lista de tarefas",
        "Checklist — Tab to indent, drag a box or Alt+↑/↓ to reorder":
            "Lista de tarefas — Tab para recuar, arraste uma caixa ou Alt+↑/↓ para reordenar",
        "Checklist progress (done / total)": "Progresso da lista (concluído / total)",
        "Increase font size": "Aumentar tamanho da fonte",
        "Decrease font size": "Diminuir tamanho da fonte",
        "Text Colour": "Cor do texto",
        "Font family": "Tipo de fonte",
        "Click to set exact size": "Clique para definir o tamanho exato",
        "Click to open colour picker": "Clique para abrir o seletor de cores",
        "Write your note here…": "Escreva sua nota aqui…",
        "More fonts…": "Mais fontes…",

        # ---- note context menu ----
        "Change Colour…": "Mudar cor…",
        "Copy Note": "Copiar nota",
        "Rename…": "Renomear…",
        "Rename": "Renomear",
        "Paste as plain text": "Colar como texto simples",
        "Move to Trash": "Mover para a lixeira",
        "Custom colour:": "Cor personalizada:",

        # ---- list styles (glyph kept) ----
        "●  Disc": "●  Círculo",
        "▪  Square": "▪  Quadrado",
        "1.  Decimal": "1.  Números",
        "a.  Lower alpha": "a.  Letras minúsculas",
        "i.  Lower roman": "i.  Romanos minúsculos",
        "✕  Remove list": "✕  Remover lista",

        # ---- rename dialog ----
        "Rename note": "Renomear nota",
        "Note name:": "Nome da nota:",
        "Leave empty to use the automatic name (first line of the note).":
            "Deixe em branco para usar o nome automático (primeira linha da nota).",
        "Untitled": "Sem título",

        # ---- reminder dialog ----
        "Reminder": "Lembrete",
        "Set reminder…": "Definir lembrete…",
        "Reminder: ": "Lembrete: ",
        "Reminder: {} — change…": "Lembrete: {} — alterar…",
        "Current: ": "Atual: ",
        "Quick options:": "Opções rápidas:",
        "Or a specific time:": "Ou um horário específico:",
        "Or a specific date and time:": "Ou uma data e horário específicos:",
        "Date": "Data",
        "Time": "Hora",
        "In 1 min": "Em 1 min",
        "In 5 min": "Em 5 min",
        "In 10 min": "Em 10 min",
        "In 30 min": "Em 30 min",
        "In 1 hour": "Em 1 hora",
        "In 3 hours": "Em 3 horas",
        "In 8 hours": "Em 8 horas",
        "In 24 hours": "Em 24 horas",
        "Remove reminder": "Remover lembrete",

        # ---- export ----
        "Export Note": "Exportar nota",
        "Export Failed": "Falha na exportação",
        "Plain text (.txt)": "Texto simples (.txt)",
        "OpenDocument (.odt)": "OpenDocument (.odt)",
        "PDF (.pdf)": "PDF (.pdf)",
        "Text files (*.txt)": "Arquivos de texto (*.txt)",
        "OpenDocument (*.odt)": "OpenDocument (*.odt)",
        "PDF (*.pdf)": "PDF (*.pdf)",
        "(empty note)": "(nota vazia)",

        # ---- manager ----
        "Restore All": "Restaurar todas",
        "Delete All": "Excluir todas",
        "Search notes…": "Buscar notas…",
        "Search notes": "Buscar notas",
        "Search Notes…": "Buscar notas…",
        "No matching notes": "Nenhuma nota encontrada",
        "Global shortcut for searching notes": "Atalho global para buscar notas",
        "Scroll on tray icon to raise/lower notes":
            "Rolar sobre o ícone da bandeja para trazer/enviar notas",
        "Scroll up = bring visible notes to front; scroll down = send them behind other windows. Pinned notes are left alone.":
            "Rolar para cima = traz as notas visíveis para frente; rolar para baixo = envia-as para trás de outras janelas. Notas fixadas não são afetadas.",
        "Press {} anywhere to open the search palette. Rebind it in GNOME Settings → Keyboard → Custom Shortcuts.":
            "Pressione {} em qualquer lugar para abrir a busca. Altere o atalho em Configurações do GNOME → Teclado → Atalhos personalizados.",
        "Registers a GNOME shortcut ({}) to open a search box for finding a note from anywhere.":
            "Registra um atalho do GNOME ({}) para abrir uma caixa de busca de notas de qualquer lugar.",
        "Restore": "Restaurar",
        "Delete permanently": "Excluir permanentemente",
        "Active": "Ativas",
        "Archive": "Arquivo",
        "Trash": "Lixeira",
        "Active ({})": "Ativas ({})",
        "Active ({}/{})": "Ativas ({}/{})",
        "Archive ({})": "Arquivo ({})",
        "Archive ({}/{})": "Arquivo ({}/{})",
        "Trash ({})": "Lixeira ({})",
        "Trash ({}/{})": "Lixeira ({}/{})",
        "{} matches": "{} correspondências",
        "{} active · {} in trash": "{} ativas · {} na lixeira",
        "{} active · {} archived · {} in trash": "{} ativas · {} arquivadas · {} na lixeira",
        "Archive Full": "Arquivo cheio",
        "Active Full": "Ativas no limite",
        "Partly Restored": "Restaurado parcialmente",
        "Archive is full ({} notes).\nRemove something from the Archive first.":
            "O arquivo está cheio ({} notas).\nRemova algo do arquivo primeiro.",
        "You already have {} active notes — the maximum.\nArchive or delete one first.":
            "Você já tem {} notas ativas — o máximo.\nArquive ou exclua uma primeiro.",
        "You already have {} active notes — the maximum.":
            "Você já tem {} notas ativas — o máximo.",
        "Restored {} note(s). {} could not be restored — the active limit ({}) was reached.":
            "{} nota(s) restaurada(s). {} não puderam ser restauradas — o limite de ativas ({}) foi atingido.",
        "Permanently delete all {} note(s) in Trash?\nThis cannot be undone.":
            "Excluir permanentemente todas as {} nota(s) na lixeira?\nEsta ação não pode ser desfeita.",

        # ---- settings dialog ----
        "Start automatically on login": "Iniciar automaticamente ao entrar",
        "Creates an autostart entry in ~/.config/autostart/":
            "Cria uma entrada de inicialização automática em ~/.config/autostart/",
        "Requires GNOME (gsettings). Bind a shortcut manually instead.":
            "Requer GNOME (gsettings). Defina um atalho manualmente.",
        "Global shortcut for new note": "Atalho global para nova nota",
        "Global shortcut for new note from clipboard":
            "Atalho global para nota a partir da área de transferência",
        "Press {} anywhere to create a new note. Rebind it in GNOME Settings → Keyboard → Custom Shortcuts.":
            "Pressione {} em qualquer lugar para criar uma nova nota. Altere o atalho em Configurações do GNOME → Teclado → Atalhos personalizados.",
        "Press {} anywhere to create a note from the clipboard. Rebind it in GNOME Settings → Keyboard → Custom Shortcuts.":
            "Pressione {} em qualquer lugar para criar uma nota a partir da área de transferência. Altere o atalho em Configurações do GNOME → Teclado → Atalhos personalizados.",
        "Registers a GNOME shortcut ({}) to create a new note.":
            "Registra um atalho do GNOME ({}) para criar uma nova nota.",
        "Registers a GNOME shortcut ({}) to create a note pre-filled with the clipboard contents.":
            "Registra um atalho do GNOME ({}) para criar uma nota preenchida com o conteúdo da área de transferência.",
        "UI Scale": "Escala da interface",
        "Scales UI text and note content (100%–200%)":
            "Redimensiona o texto da interface e o conteúdo das notas (100%–200%)",
        "Scales the whole interface, text and icons (100%–200%).":
            "Redimensiona toda a interface, texto e ícones (100%–200%).",
        "Restart Sticky Notes to apply the new scale.":
            "Reinicie o Sticky Notes para aplicar a nova escala.",
        "Restart now": "Reiniciar agora",
        "Default font size": "Tamanho padrão da fonte",
        "Choose Font": "Escolher fonte",
        "Search fonts…": "Buscar fontes…",
        "Apply Font to New Notes": "Aplicar fonte às novas notas",
        "Apply to New Notes": "Aplicar às novas notas",
        "Note": "Nota",
        "Default size for new notes": "Tamanho padrão das novas notas",
        "Width": "Largura",
        "Height": "Altura",
        "Background opacity": "Opacidade do fundo",
        "Makes the note paper see-through; text stays sharp. Applies to all current and future notes.":
            "Torna o papel da nota transparente; o texto permanece nítido. Aplica-se a todas as notas atuais e futuras.",
        "Auto backup every": "Cópia de segurança automática a cada",
        "15 minutes": "15 minutos",
        "30 minutes": "30 minutos",
        "1 hour": "1 hora",
        "2 hours": "2 horas",
        "4 hours": "4 horas",
        "8 hours": "8 horas",
        "12 hours": "12 horas",
        "24 hours": "24 horas",
        "Backup Now": "Fazer cópia agora",
        "Last backup: {}": "Última cópia: {}",
        "No backup yet": "Ainda não há cópia",
        "Restore from Backup": "Restaurar de uma cópia",
        "Notes recovery": "Recuperação de notas",
        "Some data files could not be read.": "Alguns arquivos de dados não puderam ser lidos.",
        '"{name}" could not be read and was restored from its backup.':
            '"{name}" não pôde ser lida e foi restaurada a partir da cópia de segurança.',
        '"{name}" could not be read and no valid backup was found.':
            '"{name}" não pôde ser lida e nenhuma cópia de segurança válida foi encontrada.',
        'The damaged file was kept as "{kept}".': 'O arquivo danificado foi mantido como "{kept}".',
        'The damaged file was kept as "{kept}" so no data was overwritten.':
            'O arquivo danificado foi mantido como "{kept}" para que nenhum dado fosse sobrescrito.',
        "Restore notes from backup dated:\n{}\n\n⚠  Current notes will be replaced!":
            "Restaurar notas da cópia de segurança de:\n{}\n\n⚠  As notas atuais serão substituídas!",
        "EXPORT / IMPORT": "EXPORTAR / IMPORTAR",
        "Export to JSON…": "Exportar para JSON…",
        "Import from JSON…": "Importar de JSON…",
        "Language": "Idioma",
        "Language changes apply after restart.":
            "As alterações de idioma se aplicam após reiniciar.",
        # settings tab labels
        "General": "Geral",
        "Backup": "Cópia de segurança",
        # snapping
        "Snapping": "Alinhamento",
        "Snapping && Tray": "Alinhamento && bandeja",
        "Tray": "Bandeja",
        "Snap to grid": "Alinhar à grade",
        "Snap to other notes": "Alinhar a outras notas",
        "Snap size to grid": "Alinhar tamanho à grade",
        "Grid size": "Tamanho da grade",
        "Notes snap when you drop them or finish resizing. Snap to grid and snap size to grid align a note's position and size to an invisible grid; snap to other notes lines edges up with nearby notes. The grid size below sets the spacing.":
            "As notas se alinham ao soltá-las ou ao terminar de redimensioná-las. Alinhar à grade e alinhar tamanho à grade ajustam a posição e o tamanho da nota a uma grade invisível; alinhar a outras notas alinha as bordas com notas próximas. O tamanho da grade abaixo define o espaçamento.",

        # ---- about dialog ----
        "About Sticky Notes": "Sobre o Sticky Notes",
        "Version {}": "Versão {}",
        "A lightweight sticky notes application\nfor Ubuntu desktop.\n\nBuilt with Python & PyQt6":
            "Um aplicativo leve de notas adesivas\npara o desktop Ubuntu.\n\nDesenvolvido com Python e PyQt6",
        "View on GitHub": "Ver no GitHub",
        "Made by Nikola Javorina": "Feito por Nikola Javorina",
        "For the sharpest result, keep system scaling at 100% and use this.": "Para máxima nitidez, mantenha o dimensionamento do sistema em 100% e use isto.",
        "Buy me a coffee": "Pague-me um café",

        # ---- message boxes ----
        "Limit Reached": "Limite atingido",
        "Maximum of {} active notes reached.\nArchive or move some notes to Trash before creating new ones.":
            "Máximo de {} notas ativas atingido.\nArquive ou mova algumas notas para a lixeira antes de criar novas.",
        "Maximum of 20 active notes reached.\nMove some notes to Trash before creating new ones.":
            "Máximo de 20 notas ativas atingido.\nMova algumas notas para a lixeira antes de criar novas.",
        "Export Complete": "Exportação concluída",
        "Export All": "Exportar tudo",
        "Export": "Exportar",
        "There are no archived notes to export.": "Não há notas arquivadas para exportar.",
        "Export all archived notes to a JSON file.":
            "Exporta todas as notas arquivadas para um arquivo JSON.",
        "Backup saves local “.bak” copies of ALL your notes (active, archived and trash), kept next to your data on this computer. Restore brings all three back.":
            "A cópia de segurança salva cópias locais “.bak” de TODAS as suas notas (ativas, arquivadas e na lixeira), guardadas junto aos seus dados neste computador. Restaurar traz as três de volta.",
        "Export writes a portable JSON file of your ACTIVE notes (to move to another computer or re-import). Import always brings notes in as active. To export archived notes, use “Export All” in the Manager's Archive tab.":
            "A exportação grava um arquivo JSON portátil das suas notas ATIVAS (para mover para outro computador ou reimportar). A importação sempre traz as notas como ativas. Para exportar notas arquivadas, use “Exportar tudo” na aba Arquivo do Gerenciador.",
        "Import Complete": "Importação concluída",
        "Import Failed": "Falha na importação",
        "Import — Limit Reached": "Importação — limite atingido",
        "You have {} active note(s). The export file contains {} note(s).\n\nYou can import at most {} note(s).\n\nImport the first {} and skip the rest?":
            "Você tem {} nota(s) ativa(s). O arquivo de exportação contém {} nota(s).\n\nVocê pode importar no máximo {} nota(s).\n\nImportar as primeiras {} e ignorar o resto?",
        "Exported {} note(s) to:\n{}": "Exportadas {} nota(s) para:\n{}",
        "Imported {} note(s) successfully.": "Importadas {} nota(s) com sucesso.",
        "Could not read export file:\n{}": "Não foi possível ler o arquivo de exportação:\n{}",
        "You already have {} active notes — the maximum.\nMove some notes to Trash before importing.":
            "Você já tem {} notas ativas — o máximo.\nMova algumas notas para a lixeira antes de importar.",
        "You already have 20 active notes — the maximum.\nMove some notes to Trash before importing.":
            "Você já tem 20 notas ativas — o máximo.\nMova algumas notas para a lixeira antes de importar.",

        # ---- notifications ----
        "Sticky Notes — Reminder": "Sticky Notes — Lembrete",
        "Snooze 10 min": "Adiar 10 min",

        # ---- settings: Note tab (auto-contrast + clean mode) ----
        "Adjust text & icon colour to note background":
            "Ajustar cor do texto e dos ícones ao fundo da nota",
        "Dark notes get light icons and text automatically. Turn off to keep the classic dark ink.":
            "Notas escuras recebem ícones e texto claros automaticamente. Desative para manter a tinta escura clássica.",
        "Auto-hide toolbar and header until you hover the note":
            "Ocultar automaticamente a barra de ferramentas e o cabeçalho até passar o mouse sobre a nota",
        "Note border": "Borda da nota",
        "Off": "Desativado",
        "Always": "Sempre",
        "Auto (light notes only)": "Automático (apenas notas claras)",
        "Auto shows a border only on light notes, where it helps them stand out from a light background.":
            "O modo automático mostra a borda apenas em notas claras, onde ajuda a destacá-las de um fundo claro.",
        "Notes show only their text at rest; hover the top of a note to bring the controls back. A single click on the header keeps the controls up and lets you nudge the note with the arrow keys; click elsewhere to hide them again. Double-click a note's header to keep its controls open while you edit it; double-click again to hand that note back to auto-hide.":
            "Em repouso, as notas mostram apenas o texto; passe o mouse sobre o topo da nota para trazer os controles de volta. Um único clique no cabeçalho mantém os controles visíveis e permite mover a nota com as teclas de seta; clicar em outro lugar os oculta novamente. Duplo clique no cabeçalho de uma nota mantém seus controles abertos enquanto você a edita; duplo clique novamente devolve a nota ao modo de ocultação automática.",
        "Code block": "Bloco de código",
        "Inline code": "Código em linha",
        "Enable code blocks": "Ativar blocos de código",
        "Adds code-block { } and inline-code buttons to the toolbar, and enables their shortcuts (Ctrl+M for inline code, Ctrl+Shift+M for a code block). Niche — off by default.":
            "Adiciona os botões de bloco de código { } e código em linha à barra de ferramentas e ativa seus atalhos (Ctrl+M para código em linha, Ctrl+Shift+M para bloco de código). Recurso específico — desativado por padrão.",

        # ---- settings: appearance (theme) ----
        "Appearance": "Aparência",
        "Window theme": "Tema da janela",
        "Theme": "Tema",
        "Light": "Claro",
        "Dark": "Escuro",
        "Auto": "Automático",
        "Dark from": "Escuro a partir das",
        "until": "até",
        "Auto switches to Dark between these times; the theme changes within a minute of each boundary. The tray's Toggle theme then lasts only until the next boundary.":
            "O modo automático muda para escuro entre esses horários; o tema muda em até um minuto de cada limite. O alternar tema da bandeja então dura apenas até o próximo limite.",
        "Sets the look of the app's windows, menus and notes. Switching to Dark gives every note without its own dark colour a dark default; each note keeps separate colours for Light and Dark, so switching back restores the light one. Notes and the main windows recolour instantly; a few helper windows (About, the shortcut list, search) update the next time you open them — no restart needed.":
            "Define a aparência das janelas, menus e notas do aplicativo. Mudar para escuro dá a cada nota sem cor escura própria uma cor escura padrão; cada nota mantém cores separadas para claro e escuro, então voltar restaura a clara. As notas e as janelas principais mudam de cor instantaneamente; algumas janelas auxiliares (Sobre, lista de atalhos, busca) são atualizadas na próxima vez que você as abrir — sem necessidade de reiniciar.",

        # ---- settings: tray scroll ----
        "Scroll the tray icon to bring notes to front":
            "Role o ícone da bandeja para trazer as notas para frente",
        "Scroll up on the tray icon to raise your visible notes above other windows. Pinned notes are unaffected.":
            "Role para cima no ícone da bandeja para elevar suas notas visíveis acima de outras janelas. Notas fixadas não são afetadas.",

        # ---- settings: Backup tab + restore dialogs ----
        "Backups": "Cópias de segurança",
        'Backups save copies of ALL your notes (active, archived and trash) in a backups folder on this computer. "Backup Now" and the auto-backup interval each add a new restore point (the 5 most recent are kept); the daily auto-backup keeps the latest one fresh. "Restore from Backup…" lets you pick which one to go back to (this overwrites your current notes).':
            'As cópias de segurança salvam cópias de TODAS as suas notas (ativas, arquivadas e na lixeira) em uma pasta backups neste computador. "Fazer cópia agora" e o intervalo de cópia automática adicionam um novo ponto de restauração (as 5 mais recentes são mantidas); a cópia automática diária mantém a mais recente atualizada. "Restaurar de uma cópia…" permite escolher para qual voltar (isso sobrescreve suas notas atuais).',
        "Restore from Backup…": "Restaurar de uma cópia…",
        "Restore your notes from an earlier backup":
            "Restaure suas notas a partir de uma cópia anterior",
        'The 5 most recent backups. Restoring overwrites your current notes and cannot be undone — press "Backup Now" first if you want to keep them.':
            'As 5 cópias de segurança mais recentes. Restaurar sobrescreve suas notas atuais e não pode ser desfeito — pressione "Fazer cópia agora" primeiro se quiser mantê-las.',
        "No backups yet.": "Ainda não há cópias de segurança.",
        "(latest)": "(mais recente)",
        "Restore selected": "Restaurar selecionada",
        'Replace your current notes with the backup from {}?\n\nThis overwrites your current notes and cannot be undone. Use "Backup Now" first if you want to keep them.':
            'Substituir suas notas atuais pela cópia de segurança de {}?\n\nIsso sobrescreve suas notas atuais e não pode ser desfeito. Use "Fazer cópia agora" primeiro se quiser mantê-las.',
        "Restore complete": "Restauração concluída",
        "Restore failed": "Falha na restauração",
        "Your notes were restored from the selected backup.":
            "Suas notas foram restauradas a partir da cópia de segurança selecionada.",
        "That backup could not be restored.": "Não foi possível restaurar essa cópia de segurança.",
        '"{name}" could not be read and was restored from the backup of {when}.':
            '"{name}" não pôde ser lida e foi restaurada a partir da cópia de segurança de {when}.',

        # ---- keyboard shortcuts (tray + cheat-sheet) ----
        "Keyboard shortcuts…": "Atalhos de teclado…",
        "Keyboard shortcuts": "Atalhos de teclado",
        "Turn these on or off in Settings.": "Ative ou desative isso nas Configurações.",
        # ---- cheat-sheet tabs + section notes (translated via tr(title), so the
        # AST scan in test_i18n_hr_complete can't see them — that test checks the
        # shortcuts catalog explicitly instead) ----
        "Global": "Global",
        "Text & lists": "Texto e listas",
        "Code": "Código",
        "Windows": "Janelas",
        "These act on the note you are using right now.":
            "Eles agem sobre a nota que você está usando agora.",
        'These only do anything while "Enable code blocks" is on (Settings → Note).':
            'Eles só têm efeito enquanto "Ativar blocos de código" estiver ativado (Configurações → Nota).',

        # ---- export: PNG ----
        "Image (.png)": "Imagem (.png)",
        "PNG image (*.png)": "Imagem PNG (*.png)",
    },
    "it": {
        # ---- generic actions / buttons ----
        "OK": "OK",
        "Cancel": "Annulla",
        "Save": "Salva",
        "Close": "Chiudi",
        "Apply": "Applica",
        "Select": "Seleziona",
        "Set": "Imposta",
        "Refresh": "Aggiorna",
        "Copy": "Copia",
        "Copied": "Copiato",

        # ---- tray menu ----
        "New Note": "Nuova nota",
        "Show All": "Mostra tutte",
        "Hide All": "Nascondi tutte",
        "Lock All": "Blocca tutte",
        "Unlock All": "Sblocca tutte",
        "Notes Manager": "Gestione note",
        "Settings": "Impostazioni",
        "About": "Informazioni",
        "Toggle theme": "Cambia tema",
        "Quit": "Esci",

        # ---- note header / toolbar ----
        "Note Options": "Opzioni nota",
        "Toggle Toolbar": "Mostra/nascondi barra degli strumenti",
        "Lock / Unlock": "Blocca / sblocca",
        "Hide Note": "Nascondi nota",
        "Always on Top": "Sempre in primo piano",
        "Favorite": "Preferita",
        "Add to Favorites": "Aggiungi ai preferiti",
        "Remove from Favorites": "Rimuovi dai preferiti",
        "Bold (Ctrl+B)": "Grassetto (Ctrl+B)",
        "Italic (Ctrl+I)": "Corsivo (Ctrl+I)",
        "Underline (Ctrl+U)": "Sottolineato (Ctrl+U)",
        "Strikethrough (Ctrl+S)": "Barrato (Ctrl+S)",
        "Bullet list": "Elenco puntato",
        "Checklist": "Lista di controllo",
        "Checklist — Tab to indent, drag a box or Alt+↑/↓ to reorder":
            "Lista di controllo — Tab per rientrare, trascina una casella oppure Alt+↑/↓ per riordinare",
        "Checklist progress (done / total)": "Avanzamento lista (fatte / totali)",
        "Increase font size": "Aumenta dimensione carattere",
        "Decrease font size": "Riduci dimensione carattere",
        "Text Colour": "Colore testo",
        "Font family": "Tipo di carattere",
        "Click to set exact size": "Clicca per impostare la dimensione esatta",
        "Click to open colour picker": "Clicca per aprire il selettore colori",
        "Write your note here…": "Scrivi qui la tua nota…",
        "More fonts…": "Altri caratteri…",

        # ---- note context menu ----
        "Change Colour…": "Cambia colore…",
        "Copy Note": "Copia nota",
        "Rename…": "Rinomina…",
        "Rename": "Rinomina",          # Manager row menu (sits next to "Export")
        "Paste as plain text": "Incolla come testo semplice",
        "Move to Trash": "Sposta nel cestino",
        "Custom colour:": "Colore personalizzato:",

        # ---- list styles (glyph kept) ----
        "●  Disc": "●  Cerchio",
        "▪  Square": "▪  Quadrato",
        "1.  Decimal": "1.  Numeri",
        "a.  Lower alpha": "a.  Lettere minuscole",
        "i.  Lower roman": "i.  Numeri romani minuscoli",
        "✕  Remove list": "✕  Rimuovi elenco",

        # ---- rename dialog ----
        "Rename note": "Rinomina nota",
        "Note name:": "Nome nota:",
        "Leave empty to use the automatic name (first line of the note).":
            "Lascia vuoto per usare il nome automatico (prima riga della nota).",
        "Untitled": "Senza titolo",

        # ---- reminder dialog ----
        "Reminder": "Promemoria",
        "Set reminder…": "Imposta promemoria…",
        "Reminder: ": "Promemoria: ",
        "Reminder: {} — change…": "Promemoria: {} — modifica…",
        "Current: ": "Attuale: ",
        "Quick options:": "Opzioni rapide:",
        "Or a specific time:": "Oppure un orario specifico:",
        "Or a specific date and time:": "Oppure una data e ora specifiche:",
        "Date": "Data",
        "Time": "Ora",
        "In 1 min": "Tra 1 min",
        "In 5 min": "Tra 5 min",
        "In 10 min": "Tra 10 min",
        "In 30 min": "Tra 30 min",
        "In 1 hour": "Tra 1 ora",
        "In 3 hours": "Tra 3 ore",
        "In 8 hours": "Tra 8 ore",
        "In 24 hours": "Tra 24 ore",
        "Remove reminder": "Rimuovi promemoria",

        # ---- export ----
        "Export Note": "Esporta nota",
        "Export Failed": "Esportazione non riuscita",
        "Plain text (.txt)": "Testo semplice (.txt)",
        "OpenDocument (.odt)": "OpenDocument (.odt)",
        "PDF (.pdf)": "PDF (.pdf)",
        "Text files (*.txt)": "File di testo (*.txt)",
        "OpenDocument (*.odt)": "OpenDocument (*.odt)",
        "PDF (*.pdf)": "PDF (*.pdf)",
        "(empty note)": "(nota vuota)",

        # ---- manager ----
        "Restore All": "Ripristina tutte",
        "Delete All": "Elimina tutte",
        "Search notes…": "Cerca nelle note…",
        "Search notes": "Cerca nelle note",
        "Search Notes…": "Cerca nelle note…",
        "No matching notes": "Nessuna nota corrispondente",
        "Global shortcut for searching notes": "Scorciatoia globale per cercare le note",
        "Scroll on tray icon to raise/lower notes": "Scorri sull'icona nella barra per alzare/abbassare le note",
        "Scroll up = bring visible notes to front; scroll down = send them behind other windows. Pinned notes are left alone.":
            "Scorri su = porta le note visibili in primo piano; scorri giù = mandale dietro le altre finestre. Le note fissate non vengono toccate.",
        "Press {} anywhere to open the search palette. Rebind it in GNOME Settings → Keyboard → Custom Shortcuts.":
            "Premi {} ovunque per aprire la ricerca. Modifica la scorciatoia in GNOME Impostazioni → Tastiera → Scorciatoie personalizzate.",
        "Registers a GNOME shortcut ({}) to open a search box for finding a note from anywhere.":
            "Registra una scorciatoia GNOME ({}) per aprire la ricerca delle note da qualsiasi punto.",
        "Restore": "Ripristina",
        "Delete permanently": "Elimina definitivamente",
        "Active": "Attive",
        "Archive": "Archivio",
        "Trash": "Cestino",
        "Active ({})": "Attive ({})",
        "Active ({}/{})": "Attive ({}/{})",
        "Archive ({})": "Archivio ({})",
        "Archive ({}/{})": "Archivio ({}/{})",
        "Trash ({})": "Cestino ({})",
        "Trash ({}/{})": "Cestino ({}/{})",
        "{} matches": "{} risultati",
        "{} active · {} in trash": "{} attive · {} nel cestino",
        "{} active · {} archived · {} in trash": "{} attive · {} archiviate · {} nel cestino",
        "Archive Full": "Archivio pieno",
        "Active Full": "Attive al completo",
        "Partly Restored": "Ripristino parziale",
        "Archive is full ({} notes).\nRemove something from the Archive first.":
            "L'archivio è pieno ({} note).\nRimuovi prima qualcosa dall'archivio.",
        "You already have {} active notes — the maximum.\nArchive or delete one first.":
            "Hai già {} note attive — il massimo consentito.\nArchivia o elimina prima una nota.",
        "You already have {} active notes — the maximum.":
            "Hai già {} note attive — il massimo consentito.",
        "Restored {} note(s). {} could not be restored — the active limit ({}) was reached.":
            "Ripristinate {} note. {} non è stato possibile ripristinarle — raggiunto il limite di note attive ({}).",
        "Permanently delete all {} note(s) in Trash?\nThis cannot be undone.":
            "Eliminare definitivamente tutte le {} note nel cestino?\nL'operazione non può essere annullata.",

        # ---- settings dialog ----
        "Start automatically on login": "Avvia automaticamente all'accesso",
        "Creates an autostart entry in ~/.config/autostart/":
            "Crea una voce di avvio automatico in ~/.config/autostart/",
        "Requires GNOME (gsettings). Bind a shortcut manually instead.":
            "Richiede GNOME (gsettings). Associa invece una scorciatoia manualmente.",
        "Global shortcut for new note": "Scorciatoia globale per una nuova nota",
        "Global shortcut for new note from clipboard":
            "Scorciatoia globale per una nota dagli appunti",
        "Press {} anywhere to create a new note. Rebind it in GNOME Settings → Keyboard → Custom Shortcuts.":
            "Premi {} ovunque per creare una nuova nota. Modifica la scorciatoia in GNOME Impostazioni → Tastiera → Scorciatoie personalizzate.",
        "Press {} anywhere to create a note from the clipboard. Rebind it in GNOME Settings → Keyboard → Custom Shortcuts.":
            "Premi {} ovunque per creare una nota dagli appunti. Modifica la scorciatoia in GNOME Impostazioni → Tastiera → Scorciatoie personalizzate.",
        "Registers a GNOME shortcut ({}) to create a new note.":
            "Registra una scorciatoia GNOME ({}) per creare una nuova nota.",
        "Registers a GNOME shortcut ({}) to create a note pre-filled with the clipboard contents.":
            "Registra una scorciatoia GNOME ({}) per creare una nota precompilata con il contenuto degli appunti.",
        "UI Scale": "Scala interfaccia",
        "Scales UI text and note content (100%–200%)":
            "Ridimensiona il testo dell'interfaccia e il contenuto delle note (100%–200%)",
        "Scales the whole interface, text and icons (100%–200%).":
            "Ridimensiona l'intera interfaccia, testo e icone (100%–200%).",
        "Restart Sticky Notes to apply the new scale.":
            "Riavvia Sticky Notes per applicare la nuova scala.",
        "Restart now": "Riavvia ora",
        "Default font size": "Dimensione carattere predefinita",
        "Choose Font": "Scegli carattere",
        "Search fonts…": "Cerca caratteri…",
        "Apply Font to New Notes": "Applica carattere alle nuove note",
        "Apply to New Notes": "Applica alle nuove note",
        "Note": "Nota",
        "Default size for new notes": "Dimensione predefinita delle nuove note",
        "Width": "Larghezza",
        "Height": "Altezza",
        "Background opacity": "Opacità dello sfondo",
        "Makes the note paper see-through; text stays sharp. Applies to all current and future notes.":
            "Rende trasparente il foglio della nota; il testo resta nitido. Si applica a tutte le note attuali e future.",
        "Auto backup every": "Copia di sicurezza automatica ogni",
        "15 minutes": "15 minuti",
        "30 minutes": "30 minuti",
        "1 hour": "1 ora",
        "2 hours": "2 ore",
        "4 hours": "4 ore",
        "8 hours": "8 ore",
        "12 hours": "12 ore",
        "24 hours": "24 ore",
        "Backup Now": "Crea copia ora",
        "Last backup: {}": "Ultima copia: {}",
        "No backup yet": "Nessuna copia ancora",
        "Restore from Backup": "Ripristina da copia di sicurezza",
        "Notes recovery": "Recupero note",
        "Some data files could not be read.": "Alcuni file di dati non è stato possibile leggerli.",
        '"{name}" could not be read and was restored from its backup.':
            '"{name}" non è stato possibile leggerla ed è stata ripristinata dalla sua copia di sicurezza.',
        '"{name}" could not be read and no valid backup was found.':
            '"{name}" non è stato possibile leggerla e non è stata trovata alcuna copia di sicurezza valida.',
        'The damaged file was kept as "{kept}".':
            'Il file danneggiato è stato conservato come "{kept}".',
        'The damaged file was kept as "{kept}" so no data was overwritten.':
            'Il file danneggiato è stato conservato come "{kept}" così nessun dato è stato sovrascritto.',
        "Restore notes from backup dated:\n{}\n\n⚠  Current notes will be replaced!":
            "Ripristinare le note dalla copia del:\n{}\n\n⚠  Le note attuali verranno sostituite!",
        "EXPORT / IMPORT": "ESPORTA / IMPORTA",
        "Export to JSON…": "Esporta in JSON…",
        "Import from JSON…": "Importa da JSON…",
        "Language": "Lingua",
        "Language changes apply after restart.": "Le modifiche alla lingua si applicano dopo il riavvio.",
        # settings tab labels
        "General": "Generali",
        "Backup": "Copie di sicurezza",
        # snapping
        "Snapping": "Aggancio",
        "Snapping && Tray": "Aggancio && barra",
        "Tray": "Barra",
        "Snap to grid": "Aggancia alla griglia",
        "Snap to other notes": "Aggancia alle altre note",
        "Snap size to grid": "Aggancia dimensione alla griglia",
        "Grid size": "Dimensione griglia",
        "Notes snap when you drop them or finish resizing. Snap to grid and snap size to grid align a note's position and size to an invisible grid; snap to other notes lines edges up with nearby notes. The grid size below sets the spacing.":
            "Le note si agganciano quando le rilasci o finisci di ridimensionarle. Aggancia alla griglia e aggancia dimensione alla griglia allineano posizione e dimensione di una nota a una griglia invisibile; aggancia alle altre note allinea i bordi con le note vicine. La dimensione della griglia sotto imposta la spaziatura.",

        # ---- about dialog ----
        "About Sticky Notes": "Informazioni su Sticky Notes",
        "Version {}": "Versione {}",
        "A lightweight sticky notes application\nfor Ubuntu desktop.\n\nBuilt with Python & PyQt6":
            "Un'applicazione leggera per note adesive\nper il desktop Ubuntu.\n\nRealizzata con Python e PyQt6",
        "View on GitHub": "Vedi su GitHub",
        "Made by Nikola Javorina": "Realizzato da Nikola Javorina",
        "For the sharpest result, keep system scaling at 100% and use this.": "Per la massima nitidezza, mantieni il ridimensionamento di sistema al 100% e usa questo.",
        "Buy me a coffee": "Offrimi un caffè",

        # ---- message boxes ----
        "Limit Reached": "Limite raggiunto",
        "Maximum of {} active notes reached.\nArchive or move some notes to Trash before creating new ones.":
            "Raggiunto il massimo di {} note attive.\nArchivia o sposta alcune note nel cestino prima di crearne di nuove.",
        "Maximum of 20 active notes reached.\nMove some notes to Trash before creating new ones.":
            "Raggiunto il massimo di 20 note attive.\nSposta alcune note nel cestino prima di crearne di nuove.",
        "Export Complete": "Esportazione completata",
        "Export All": "Esporta tutte",
        "Export": "Esporta",
        "There are no archived notes to export.": "Non ci sono note archiviate da esportare.",
        "Export all archived notes to a JSON file.": "Esporta tutte le note archiviate in un file JSON.",
        "Backup saves local “.bak” copies of ALL your notes (active, archived "
        "and trash), kept next to your data on this computer. Restore brings all "
        "three back.":
            "La copia di sicurezza salva copie locali “.bak” di TUTTE le tue note "
            "(attive, archiviate e cestino), conservate accanto ai tuoi dati su questo "
            "computer. Il ripristino riporta indietro tutte e tre.",
        "Export writes a portable JSON file of your ACTIVE notes (to move to "
        "another computer or re-import). Import always brings notes in as active. "
        "To export archived notes, use “Export All” in the Manager's Archive tab.":
            "L'esportazione crea un file JSON portatile delle tue note ATTIVE (per "
            "spostarle su un altro computer o reimportarle). L'importazione aggiunge "
            "sempre le note come attive. Per esportare le note archiviate, usa "
            "„Esporta tutte” nella scheda Archivio di Gestione note.",
        "Import Complete": "Importazione completata",
        "Import Failed": "Importazione non riuscita",
        "Import — Limit Reached": "Importazione — limite raggiunto",
        "You have {} active note(s). The export file contains {} note(s).\n\nYou can import at most {} note(s).\n\nImport the first {} and skip the rest?":
            "Hai {} note attive. Il file di esportazione contiene {} note.\n\nPuoi importarne al massimo {}.\n\nImportare le prime {} e saltare le restanti?",
        "Exported {} note(s) to:\n{}": "Esportate {} note in:\n{}",
        "Imported {} note(s) successfully.": "Importate con successo {} note.",
        "Could not read export file:\n{}": "Impossibile leggere il file di esportazione:\n{}",
        "You already have {} active notes — the maximum.\nMove some notes to Trash before importing.":
            "Hai già {} note attive — il massimo consentito.\nSposta alcune note nel cestino prima di importare.",
        "You already have 20 active notes — the maximum.\nMove some notes to Trash before importing.":
            "Hai già 20 note attive — il massimo consentito.\nSposta alcune note nel cestino prima di importare.",

        # ---- notifications ----
        "Sticky Notes — Reminder": "Sticky Notes — Promemoria",
        "Snooze 10 min": "Rimanda 10 min",

        # ---- settings: Note tab (auto-contrast + clean mode) ----
        "Adjust text & icon colour to note background":
            "Adatta il colore di testo e icone allo sfondo della nota",
        "Dark notes get light icons and text automatically. Turn off to keep the classic dark ink.":
            "Le note scure ottengono automaticamente icone e testo chiari. Disattiva per mantenere il classico inchiostro scuro.",
        "Auto-hide toolbar and header until you hover the note":
            "Nascondi automaticamente barra degli strumenti e intestazione finché non passi sopra la nota",
        "Note border": "Bordo nota",
        "Off": "Disattivato",
        "Always": "Sempre",
        "Auto (light notes only)": "Automatico (solo note chiare)",
        "Auto shows a border only on light notes, where it helps them stand out from a light background.":
            "Automatico mostra un bordo solo sulle note chiare, dove aiuta a distinguerle da uno sfondo chiaro.",
        "Notes show only their text at rest; hover the top of a note to bring the controls back. "
        "A single click on the header keeps the controls up and lets you nudge the note with the arrow keys; click elsewhere to hide them again. "
        "Double-click a note's header to keep its controls open while you edit it; "
        "double-click again to hand that note back to auto-hide.":
            "A riposo le note mostrano solo il testo; passa il mouse sulla parte superiore per far ricomparire i controlli. "
            "Un singolo clic sull'intestazione mantiene i controlli visibili e permette di spostare la nota con i tasti freccia; un clic altrove li nasconde di nuovo. "
            "Doppio clic sull'intestazione di una nota per mantenere i suoi controlli aperti mentre la modifichi; "
            "un altro doppio clic riporta quella nota all'auto-nascondimento.",
        "Code block": "Blocco di codice",
        "Inline code": "Codice in linea",
        "Enable code blocks": "Abilita blocchi di codice",
        "Adds code-block { } and inline-code buttons to the toolbar, and enables their shortcuts (Ctrl+M for inline code, Ctrl+Shift+M for a code block). Niche — off by default.":
            "Aggiunge i pulsanti per blocco di codice { } e codice in linea alla barra degli strumenti e abilita le relative scorciatoie (Ctrl+M per il codice in linea, Ctrl+Shift+M per un blocco di codice). Di nicchia — disattivato per impostazione predefinita.",

        # ---- settings: appearance (theme) ----
        "Appearance": "Aspetto",
        "Window theme": "Tema finestra",
        "Theme": "Tema",
        "Light": "Chiaro",
        "Dark": "Scuro",
        "Auto": "Automatico",
        "Dark from": "Scuro dalle",
        "until": "alle",
        "Auto switches to Dark between these times; the theme changes within a minute of each boundary. The tray's Toggle theme then lasts only until the next boundary.":
            "Automatico passa allo scuro tra questi orari; il tema cambia entro un minuto da ogni limite. Il Cambia tema della barra vale allora solo fino al limite successivo.",
        "Sets the look of the app's windows, menus and notes. Switching to Dark gives every note without its own dark colour a dark default; each note keeps separate colours for Light and Dark, so switching back restores the light one. Notes and the main windows recolour instantly; a few helper windows (About, the shortcut list, search) update the next time you open them — no restart needed.":
            "Imposta l'aspetto di finestre, menu e note dell'applicazione. Passare allo scuro assegna un colore scuro predefinito a ogni nota priva di un proprio colore scuro; ogni nota mantiene colori separati per chiaro e scuro, quindi tornando indietro si ripristina quello chiaro. Le note e le finestre principali cambiano colore all'istante; alcune finestre secondarie (Informazioni, l'elenco scorciatoie, la ricerca) si aggiornano la prossima volta che le apri — nessun riavvio necessario.",

        # ---- settings: tray scroll ----
        "Scroll the tray icon to bring notes to front":
            "Scorri sull'icona nella barra per portare le note in primo piano",
        "Scroll up on the tray icon to raise your visible notes above "
        "other windows. Pinned notes are unaffected.":
            "Scorri verso l'alto sull'icona nella barra per alzare le note visibili "
            "sopra le altre finestre. Le note fissate non sono interessate.",

        # ---- settings: Backup tab + restore dialogs ----
        "Backups": "Copie di sicurezza",
        "Backups save copies of ALL your notes (active, archived and trash) in a "
        "backups folder on this computer. \"Backup Now\" and the auto-backup "
        "interval each add a new restore point (the 5 most recent are kept); the "
        "daily auto-backup keeps the latest one fresh. \"Restore from Backup…\" "
        "lets you pick which one to go back to (this overwrites your current notes).":
            "Le copie di sicurezza salvano copie di TUTTE le tue note (attive, archiviate "
            "e cestino) in una cartella backups su questo computer. „Crea copia ora” e "
            "l'intervallo della copia automatica aggiungono ciascuno un nuovo punto di "
            "ripristino (si conservano le 5 più recenti); la copia automatica giornaliera "
            "mantiene aggiornata quella più recente. „Ripristina da copia di sicurezza…” "
            "permette di scegliere a quale tornare (questo sovrascrive le note attuali).",
        "Restore from Backup…": "Ripristina da copia di sicurezza…",
        "Restore your notes from an earlier backup": "Ripristina le tue note da una copia precedente",
        "The 5 most recent backups. Restoring overwrites your current "
        "notes and cannot be undone — press \"Backup Now\" first if you "
        "want to keep them.":
            "Le 5 copie di sicurezza più recenti. Il ripristino sovrascrive le note "
            "attuali e non può essere annullato — premi prima „Crea copia ora” se "
            "vuoi conservarle.",
        "No backups yet.": "Ancora nessuna copia di sicurezza.",
        "(latest)": "(più recente)",
        "Restore selected": "Ripristina selezionata",
        "Replace your current notes with the backup from {}?\n\n"
        "This overwrites your current notes and cannot be undone. "
        "Use \"Backup Now\" first if you want to keep them.":
            "Sostituire le note attuali con la copia del {}?\n\n"
            "Questo sovrascrive le note attuali e non può essere annullato. "
            "Usa prima „Crea copia ora” se vuoi conservarle.",
        "Restore complete": "Ripristino completato",
        "Restore failed": "Ripristino non riuscito",
        "Your notes were restored from the selected backup.":
            "Le tue note sono state ripristinate dalla copia di sicurezza selezionata.",
        "That backup could not be restored.": "Non è stato possibile ripristinare quella copia di sicurezza.",
        "\"{name}\" could not be read and was restored from the backup of {when}.":
            "„{name}” non è stato possibile leggerla ed è stata ripristinata dalla copia di sicurezza del {when}.",

        # ---- keyboard shortcuts (tray + cheat-sheet) ----
        "Keyboard shortcuts…": "Scorciatoie da tastiera…",
        "Keyboard shortcuts": "Scorciatoie da tastiera",
        "Turn these on or off in Settings.": "Attivale o disattivale nelle Impostazioni.",
        # ---- cheat-sheet tabs + section notes (translated via tr(title), so the
        # AST scan in test_i18n_hr_complete can't see them — that test checks the
        # shortcuts catalog explicitly instead) ----
        "Global": "Globali",
        "Text & lists": "Testo ed elenchi",
        "Code": "Codice",
        "Windows": "Finestre",
        "These act on the note you are using right now.":
            "Agiscono sulla nota che stai usando in questo momento.",
        "These only do anything while \"Enable code blocks\" is on (Settings → Note).":
            "Funzionano solo quando „Abilita blocchi di codice” è attivo (Impostazioni → Nota).",

        # ---- export: PNG ----
        "Image (.png)": "Immagine (.png)",
        "PNG image (*.png)": "Immagine PNG (*.png)",
    },
    "pl": {
        # ---- generic actions / buttons ----
        "OK": "OK",
        "Cancel": "Anuluj",
        "Save": "Zapisz",
        "Close": "Zamknij",
        "Apply": "Zastosuj",
        "Select": "Wybierz",
        "Set": "Ustaw",
        "Refresh": "Odśwież",
        "Copy": "Kopiuj",
        "Copied": "Skopiowano",

        # ---- tray menu ----
        "New Note": "Nowa notatka",
        "Show All": "Pokaż wszystkie",
        "Hide All": "Ukryj wszystkie",
        "Lock All": "Zablokuj wszystkie",
        "Unlock All": "Odblokuj wszystkie",
        "Notes Manager": "Menedżer notatek",
        "Settings": "Ustawienia",
        "About": "O programie",
        "Toggle theme": "Przełącz motyw",
        "Quit": "Zakończ",

        # ---- note header / toolbar ----
        "Note Options": "Opcje notatki",
        "Toggle Toolbar": "Pokaż/ukryj pasek narzędzi",
        "Lock / Unlock": "Zablokuj / odblokuj",
        "Hide Note": "Ukryj notatkę",
        "Always on Top": "Zawsze na wierzchu",
        "Favorite": "Ulubione",
        "Add to Favorites": "Dodaj do ulubionych",
        "Remove from Favorites": "Usuń z ulubionych",
        "Bold (Ctrl+B)": "Pogrubienie (Ctrl+B)",
        "Italic (Ctrl+I)": "Kursywa (Ctrl+I)",
        "Underline (Ctrl+U)": "Podkreślenie (Ctrl+U)",
        "Strikethrough (Ctrl+S)": "Przekreślenie (Ctrl+S)",
        "Bullet list": "Lista punktowana",
        "Checklist": "Lista zadań",
        "Checklist — Tab to indent, drag a box or Alt+↑/↓ to reorder":
            "Lista zadań — Tab, aby wciąć, przeciągnij pole lub Alt+↑/↓, aby zmienić kolejność",
        "Checklist progress (done / total)": "Postęp listy (zrobione / razem)",
        "Increase font size": "Zwiększ rozmiar czcionki",
        "Decrease font size": "Zmniejsz rozmiar czcionki",
        "Text Colour": "Kolor tekstu",
        "Font family": "Rodzaj czcionki",
        "Click to set exact size": "Kliknij, aby ustawić dokładny rozmiar",
        "Click to open colour picker": "Kliknij, aby otworzyć wybór koloru",
        "Write your note here…": "Napisz notatkę tutaj…",
        "More fonts…": "Więcej czcionek…",

        # ---- note context menu ----
        "Change Colour…": "Zmień kolor…",
        "Copy Note": "Kopiuj notatkę",
        "Rename…": "Zmień nazwę…",
        "Rename": "Zmień nazwę",          # Manager row menu (sits next to "Export")
        "Paste as plain text": "Wklej jako zwykły tekst",
        "Move to Trash": "Przenieś do kosza",
        "Custom colour:": "Własny kolor:",

        # ---- list styles (glyph kept) ----
        "●  Disc": "●  Kółko",
        "▪  Square": "▪  Kwadrat",
        "1.  Decimal": "1.  Liczby",
        "a.  Lower alpha": "a.  Małe litery",
        "i.  Lower roman": "i.  Małe rzymskie",
        "✕  Remove list": "✕  Usuń listę",

        # ---- rename dialog ----
        "Rename note": "Zmień nazwę notatki",
        "Note name:": "Nazwa notatki:",
        "Leave empty to use the automatic name (first line of the note).":
            "Pozostaw puste, aby użyć automatycznej nazwy (pierwszy wiersz notatki).",
        "Untitled": "Bez nazwy",

        # ---- reminder dialog ----
        "Reminder": "Przypomnienie",
        "Set reminder…": "Ustaw przypomnienie…",
        "Reminder: ": "Przypomnienie: ",
        "Reminder: {} — change…": "Przypomnienie: {} — zmień…",
        "Current: ": "Obecnie: ",
        "Quick options:": "Szybkie opcje:",
        "Or a specific time:": "Lub konkretna godzina:",
        "Or a specific date and time:": "Lub konkretna data i godzina:",
        "Date": "Data",
        "Time": "Godzina",
        "In 1 min": "Za 1 min",
        "In 5 min": "Za 5 min",
        "In 10 min": "Za 10 min",
        "In 30 min": "Za 30 min",
        "In 1 hour": "Za 1 godzinę",
        "In 3 hours": "Za 3 godziny",
        "In 8 hours": "Za 8 godzin",
        "In 24 hours": "Za 24 godziny",
        "Remove reminder": "Usuń przypomnienie",

        # ---- export ----
        "Export Note": "Eksportuj notatkę",
        "Export Failed": "Eksport nie powiódł się",
        "Plain text (.txt)": "Zwykły tekst (.txt)",
        "OpenDocument (.odt)": "OpenDocument (.odt)",
        "PDF (.pdf)": "PDF (.pdf)",
        "Text files (*.txt)": "Pliki tekstowe (*.txt)",
        "OpenDocument (*.odt)": "OpenDocument (*.odt)",
        "PDF (*.pdf)": "PDF (*.pdf)",
        "(empty note)": "(pusta notatka)",

        # ---- manager ----
        "Restore All": "Przywróć wszystkie",
        "Delete All": "Usuń wszystkie",
        "Search notes…": "Szukaj notatek…",
        "Search notes": "Szukaj notatek",
        "Search Notes…": "Szukaj notatek…",
        "No matching notes": "Brak pasujących notatek",
        "Global shortcut for searching notes": "Globalny skrót do wyszukiwania notatek",
        "Scroll on tray icon to raise/lower notes": "Przewiń na ikonie w zasobniku, aby podnieść/obniżyć notatki",
        "Scroll up = bring visible notes to front; scroll down = send them behind other windows. Pinned notes are left alone.":
            "Przewiń w górę = widoczne notatki na wierzch; przewiń w dół = za inne okna. Przypięte notatki pozostają bez zmian.",
        "Press {} anywhere to open the search palette. Rebind it in GNOME Settings → Keyboard → Custom Shortcuts.":
            "Naciśnij {} w dowolnym miejscu, aby otworzyć wyszukiwanie. Zmień skrót w GNOME Ustawienia → Klawiatura → Niestandardowe skróty.",
        "Registers a GNOME shortcut ({}) to open a search box for finding a note from anywhere.":
            "Rejestruje skrót GNOME ({}) do otwierania wyszukiwania notatek z dowolnego miejsca.",
        "Restore": "Przywróć",
        "Delete permanently": "Usuń trwale",
        "Active": "Aktywne",
        "Archive": "Archiwum",
        "Trash": "Kosz",
        "Active ({})": "Aktywne ({})",
        "Active ({}/{})": "Aktywne ({}/{})",
        "Archive ({})": "Archiwum ({})",
        "Archive ({}/{})": "Archiwum ({}/{})",
        "Trash ({})": "Kosz ({})",
        "Trash ({}/{})": "Kosz ({}/{})",
        "{} matches": "{} wyników",
        "{} active · {} in trash": "{} aktywnych · {} w koszu",
        "{} active · {} archived · {} in trash": "{} aktywnych · {} zarchiwizowanych · {} w koszu",
        "Archive Full": "Archiwum pełne",
        "Active Full": "Aktywne pełne",
        "Partly Restored": "Częściowo przywrócone",
        "Archive is full ({} notes).\nRemove something from the Archive first.":
            "Archiwum jest pełne ({} notatek).\nNajpierw usuń coś z archiwum.",
        "You already have {} active notes — the maximum.\nArchive or delete one first.":
            "Masz już {} aktywnych notatek — to maksimum.\nNajpierw zarchiwizuj lub usuń jedną.",
        "You already have {} active notes — the maximum.":
            "Masz już {} aktywnych notatek — to maksimum.",
        "Restored {} note(s). {} could not be restored — the active limit ({}) was reached.":
            "Przywrócono {} notatek. {} nie można przywrócić — osiągnięto limit aktywnych ({}).",
        "Permanently delete all {} note(s) in Trash?\nThis cannot be undone.":
            "Trwale usunąć wszystkie {} notatek w koszu?\nTej operacji nie można cofnąć.",

        # ---- settings dialog ----
        "Start automatically on login": "Uruchamiaj automatycznie przy logowaniu",
        "Creates an autostart entry in ~/.config/autostart/":
            "Tworzy wpis autostartu w ~/.config/autostart/",
        "Requires GNOME (gsettings). Bind a shortcut manually instead.":
            "Wymaga GNOME (gsettings). Zamiast tego ustaw skrót ręcznie.",
        "Global shortcut for new note": "Globalny skrót do nowej notatki",
        "Global shortcut for new note from clipboard":
            "Globalny skrót do notatki ze schowka",
        "Press {} anywhere to create a new note. Rebind it in GNOME Settings → Keyboard → Custom Shortcuts.":
            "Naciśnij {} w dowolnym miejscu, aby utworzyć nową notatkę. Zmień skrót w GNOME Ustawienia → Klawiatura → Niestandardowe skróty.",
        "Press {} anywhere to create a note from the clipboard. Rebind it in GNOME Settings → Keyboard → Custom Shortcuts.":
            "Naciśnij {} w dowolnym miejscu, aby utworzyć notatkę ze schowka. Zmień skrót w GNOME Ustawienia → Klawiatura → Niestandardowe skróty.",
        "Registers a GNOME shortcut ({}) to create a new note.":
            "Rejestruje skrót GNOME ({}) do tworzenia nowej notatki.",
        "Registers a GNOME shortcut ({}) to create a note pre-filled with the clipboard contents.":
            "Rejestruje skrót GNOME ({}) do tworzenia notatki wypełnionej zawartością schowka.",
        "UI Scale": "Skala interfejsu",
        "Scales UI text and note content (100%–200%)":
            "Skaluje tekst interfejsu i treść notatek (100%–200%)",
        "Scales the whole interface, text and icons (100%–200%).":
            "Skaluje cały interfejs, tekst i ikony (100%–200%).",
        "Restart Sticky Notes to apply the new scale.":
            "Uruchom ponownie Sticky Notes, aby zastosować nową skalę.",
        "Restart now": "Uruchom ponownie teraz",
        "Default font size": "Domyślny rozmiar czcionki",
        "Choose Font": "Wybierz czcionkę",
        "Search fonts…": "Szukaj czcionek…",
        "Apply Font to New Notes": "Zastosuj czcionkę do nowych notatek",
        "Apply to New Notes": "Zastosuj do nowych notatek",
        "Note": "Notatka",
        "Default size for new notes": "Domyślny rozmiar nowych notatek",
        "Width": "Szerokość",
        "Height": "Wysokość",
        "Background opacity": "Przezroczystość tła",
        "Makes the note paper see-through; text stays sharp. Applies to all current and future notes.":
            "Sprawia, że kartka notatki jest przezroczysta; tekst pozostaje ostry. Dotyczy wszystkich obecnych i przyszłych notatek.",
        "Auto backup every": "Automatyczna kopia co",
        "15 minutes": "15 minut",
        "30 minutes": "30 minut",
        "1 hour": "1 godzinę",
        "2 hours": "2 godziny",
        "4 hours": "4 godziny",
        "8 hours": "8 godzin",
        "12 hours": "12 godzin",
        "24 hours": "24 godziny",
        "Backup Now": "Utwórz kopię teraz",
        "Last backup: {}": "Ostatnia kopia: {}",
        "No backup yet": "Jeszcze brak kopii",
        "Restore from Backup": "Przywróć z kopii zapasowej",
        "Notes recovery": "Odzyskiwanie notatek",
        "Some data files could not be read.": "Niektórych plików danych nie udało się odczytać.",
        '"{name}" could not be read and was restored from its backup.':
            '"{name}" nie udało się odczytać i przywrócono ją z kopii zapasowej.',
        '"{name}" could not be read and no valid backup was found.':
            '"{name}" nie udało się odczytać i nie znaleziono prawidłowej kopii zapasowej.',
        'The damaged file was kept as "{kept}".':
            'Uszkodzony plik zachowano jako "{kept}".',
        'The damaged file was kept as "{kept}" so no data was overwritten.':
            'Uszkodzony plik zachowano jako "{kept}", więc żadne dane nie zostały nadpisane.',
        "Restore notes from backup dated:\n{}\n\n⚠  Current notes will be replaced!":
            "Przywrócić notatki z kopii z dnia:\n{}\n\n⚠  Obecne notatki zostaną zastąpione!",
        "EXPORT / IMPORT": "EKSPORT / IMPORT",
        "Export to JSON…": "Eksportuj do JSON…",
        "Import from JSON…": "Importuj z JSON…",
        "Language": "Język",
        "Language changes apply after restart.": "Zmiana języka zacznie obowiązywać po ponownym uruchomieniu.",
        # settings tab labels
        "General": "Ogólne",
        "Backup": "Kopia zapasowa",
        # snapping
        "Snapping": "Przyciąganie",
        "Snapping && Tray": "Przyciąganie && zasobnik",
        "Tray": "Zasobnik",
        "Snap to grid": "Przyciągaj do siatki",
        "Snap to other notes": "Przyciągaj do innych notatek",
        "Snap size to grid": "Przyciągaj rozmiar do siatki",
        "Grid size": "Rozmiar siatki",
        "Notes snap when you drop them or finish resizing. Snap to grid and snap size to grid align a note's position and size to an invisible grid; snap to other notes lines edges up with nearby notes. The grid size below sets the spacing.":
            "Notatki przyciągają się, gdy je upuścisz lub zakończysz zmianę rozmiaru. Przyciąganie do siatki i przyciąganie rozmiaru do siatki wyrównują pozycję i rozmiar notatki do niewidocznej siatki; przyciąganie do innych notatek wyrównuje krawędzie z sąsiednimi notatkami. Rozmiar siatki poniżej ustala odstęp.",

        # ---- about dialog ----
        "About Sticky Notes": "O programie Sticky Notes",
        "Version {}": "Wersja {}",
        "A lightweight sticky notes application\nfor Ubuntu desktop.\n\nBuilt with Python & PyQt6":
            "Lekka aplikacja z karteczkami\ndla pulpitu Ubuntu.\n\nStworzone z Python i PyQt6",
        "View on GitHub": "Zobacz na GitHubie",
        "Made by Nikola Javorina": "Stworzone przez Nikola Javorina",
        "For the sharpest result, keep system scaling at 100% and use this.": "Aby uzyskać najostrzejszy obraz, ustaw skalowanie systemu na 100% i użyj tego.",
        "Buy me a coffee": "Postaw mi kawę",

        # ---- message boxes ----
        "Limit Reached": "Osiągnięto limit",
        "Maximum of {} active notes reached.\nArchive or move some notes to Trash before creating new ones.":
            "Osiągnięto maksimum {} aktywnych notatek.\nZarchiwizuj lub przenieś niektóre do kosza przed utworzeniem nowych.",
        "Maximum of 20 active notes reached.\nMove some notes to Trash before creating new ones.":
            "Osiągnięto maksimum 20 aktywnych notatek.\nPrzenieś niektóre do kosza przed utworzeniem nowych.",
        "Export Complete": "Eksport zakończony",
        "Export All": "Eksportuj wszystkie",
        "Export": "Eksportuj",
        "There are no archived notes to export.": "Brak zarchiwizowanych notatek do eksportu.",
        "Export all archived notes to a JSON file.": "Eksportuj wszystkie zarchiwizowane notatki do pliku JSON.",
        "Backup saves local “.bak” copies of ALL your notes (active, archived "
        "and trash), kept next to your data on this computer. Restore brings all "
        "three back.":
            "Kopia zapasowa zapisuje lokalne kopie „.bak” WSZYSTKICH notatek (aktywnych, "
            "zarchiwizowanych i w koszu), przechowywane obok danych na tym komputerze. "
            "Przywracanie zwraca wszystkie trzy.",
        "Export writes a portable JSON file of your ACTIVE notes (to move to "
        "another computer or re-import). Import always brings notes in as active. "
        "To export archived notes, use “Export All” in the Manager's Archive tab.":
            "Eksport zapisuje przenośny plik JSON z AKTYWNYMI notatkami (do "
            "przeniesienia na inny komputer lub ponownego importu). Import zawsze dodaje "
            "notatki jako aktywne. Aby wyeksportować zarchiwizowane notatki, użyj „Eksportuj "
            "wszystkie” w karcie Archiwum w Menedżerze.",
        "Import Complete": "Import zakończony",
        "Import Failed": "Import nie powiódł się",
        "Import — Limit Reached": "Import — osiągnięto limit",
        "You have {} active note(s). The export file contains {} note(s).\n\nYou can import at most {} note(s).\n\nImport the first {} and skip the rest?":
            "Masz {} aktywnych notatek. Plik eksportu zawiera {} notatek.\n\nMożesz zaimportować maksymalnie {} notatek.\n\nZaimportować pierwsze {} i pominąć resztę?",
        "Exported {} note(s) to:\n{}": "Wyeksportowano {} notatek do:\n{}",
        "Imported {} note(s) successfully.": "Pomyślnie zaimportowano {} notatek.",
        "Could not read export file:\n{}": "Nie udało się odczytać pliku eksportu:\n{}",
        "You already have {} active notes — the maximum.\nMove some notes to Trash before importing.":
            "Masz już {} aktywnych notatek — to maksimum.\nPrzenieś niektóre do kosza przed importem.",
        "You already have 20 active notes — the maximum.\nMove some notes to Trash before importing.":
            "Masz już 20 aktywnych notatek — to maksimum.\nPrzenieś niektóre do kosza przed importem.",

        # ---- notifications ----
        "Sticky Notes — Reminder": "Sticky Notes — Przypomnienie",
        "Snooze 10 min": "Drzemka 10 min",

        # ---- settings: Note tab (auto-contrast + clean mode) ----
        "Adjust text & icon colour to note background":
            "Dostosuj kolor tekstu i ikon do tła notatki",
        "Dark notes get light icons and text automatically. Turn off to keep the classic dark ink.":
            "Ciemne notatki automatycznie otrzymują jasne ikony i tekst. Wyłącz, aby zachować klasyczny ciemny atrament.",
        "Auto-hide toolbar and header until you hover the note":
            "Automatycznie ukrywaj pasek narzędzi i nagłówek, dopóki nie najedziesz na notatkę",
        "Note border": "Obramowanie notatki",
        "Off": "Wyłączone",
        "Always": "Zawsze",
        "Auto (light notes only)": "Automatycznie (tylko jasne notatki)",
        "Auto shows a border only on light notes, where it helps them stand out from a light background.":
            "Tryb automatyczny pokazuje obramowanie tylko na jasnych notatkach, gdzie pomaga im wyróżnić się na jasnym tle.",
        "Notes show only their text at rest; hover the top of a note to bring the controls back. "
        "A single click on the header keeps the controls up and lets you nudge the note with the arrow keys; click elsewhere to hide them again. "
        "Double-click a note's header to keep its controls open while you edit it; "
        "double-click again to hand that note back to auto-hide.":
            "W spoczynku notatki pokazują tylko tekst; najedź na górę notatki, aby przywrócić kontrolki. "
            "Pojedyncze kliknięcie w nagłówek utrzymuje kontrolki widoczne i pozwala przesuwać notatkę strzałkami; "
            "kliknięcie gdzie indziej ponownie je ukrywa. "
            "Dwuklik na nagłówku notatki utrzymuje jej kontrolki otwarte podczas edycji; "
            "kolejny dwuklik oddaje tę notatkę z powrotem automatycznemu ukrywaniu.",
        "Code block": "Blok kodu",
        "Inline code": "Kod w linii",
        "Enable code blocks": "Włącz bloki kodu",
        "Adds code-block { } and inline-code buttons to the toolbar, and enables their shortcuts (Ctrl+M for inline code, Ctrl+Shift+M for a code block). Niche — off by default.":
            "Dodaje przyciski bloku kodu { } i kodu w linii do paska narzędzi oraz włącza ich skróty (Ctrl+M dla kodu w linii, Ctrl+Shift+M dla bloku kodu). Funkcja niszowa — domyślnie wyłączona.",

        # ---- settings: appearance (theme) ----
        "Appearance": "Wygląd",
        "Window theme": "Motyw okna",
        "Theme": "Motyw",
        "Light": "Jasny",
        "Dark": "Ciemny",
        "Auto": "Automatyczny",
        "Dark from": "Ciemny od",
        "until": "do",
        "Auto switches to Dark between these times; the theme changes within a minute of each boundary. The tray's Toggle theme then lasts only until the next boundary.":
            "Tryb automatyczny przełącza na ciemny między tymi godzinami; motyw zmienia się w ciągu minuty od każdej granicy. Przełącznik motywu w zasobniku obowiązuje wtedy tylko do następnej granicy.",
        "Sets the look of the app's windows, menus and notes. Switching to Dark gives every note without its own dark colour a dark default; each note keeps separate colours for Light and Dark, so switching back restores the light one. Notes and the main windows recolour instantly; a few helper windows (About, the shortcut list, search) update the next time you open them — no restart needed.":
            "Ustala wygląd okien, menu i notatek aplikacji. Przełączenie na ciemny nadaje każdej notatce bez własnego "
            "ciemnego koloru domyślny ciemny kolor; każda notatka zachowuje osobne kolory dla jasnego i ciemnego, więc "
            "powrót przywraca jasny. Notatki i główne okna zmieniają kolor natychmiast; kilka okien pomocniczych "
            "(O programie, lista skrótów, wyszukiwanie) aktualizuje się przy następnym otwarciu — bez potrzeby "
            "ponownego uruchamiania.",

        # ---- settings: tray scroll ----
        "Scroll the tray icon to bring notes to front":
            "Przewiń ikonę w zasobniku, aby przenieść notatki na wierzch",
        "Scroll up on the tray icon to raise your visible notes above "
        "other windows. Pinned notes are unaffected.":
            "Przewiń w górę na ikonie w zasobniku, aby podnieść widoczne notatki nad "
            "inne okna. Przypięte notatki pozostają bez zmian.",

        # ---- settings: Backup tab + restore dialogs ----
        "Backups": "Kopie zapasowe",
        "Backups save copies of ALL your notes (active, archived and trash) in a "
        "backups folder on this computer. \"Backup Now\" and the auto-backup "
        "interval each add a new restore point (the 5 most recent are kept); the "
        "daily auto-backup keeps the latest one fresh. \"Restore from Backup…\" "
        "lets you pick which one to go back to (this overwrites your current notes).":
            "Kopie zapasowe zapisują kopie WSZYSTKICH notatek (aktywnych, zarchiwizowanych i w "
            "koszu) w folderze backups na tym komputerze. „Utwórz kopię teraz” i interwał "
            "automatycznej kopii dodają nowy punkt przywracania (przechowywanych jest 5 "
            "najnowszych); codzienna automatyczna kopia utrzymuje najnowszą aktualną. „Przywróć "
            "z kopii zapasowej…” pozwala wybrać, do której wrócić (to nadpisuje obecne notatki).",
        "Restore from Backup…": "Przywróć z kopii zapasowej…",
        "Restore your notes from an earlier backup": "Przywróć notatki z wcześniejszej kopii zapasowej",
        "The 5 most recent backups. Restoring overwrites your current "
        "notes and cannot be undone — press \"Backup Now\" first if you "
        "want to keep them.":
            "5 najnowszych kopii zapasowych. Przywracanie nadpisuje obecne notatki i "
            "nie można tego cofnąć — najpierw naciśnij „Utwórz kopię teraz”, jeśli chcesz je zachować.",
        "No backups yet.": "Jeszcze brak kopii zapasowych.",
        "(latest)": "(najnowsza)",
        "Restore selected": "Przywróć wybraną",
        "Replace your current notes with the backup from {}?\n\n"
        "This overwrites your current notes and cannot be undone. "
        "Use \"Backup Now\" first if you want to keep them.":
            "Zastąpić obecne notatki kopią z {}?\n\n"
            "To nadpisuje obecne notatki i nie można tego cofnąć. "
            "Najpierw użyj „Utwórz kopię teraz”, jeśli chcesz je zachować.",
        "Restore complete": "Przywracanie zakończone",
        "Restore failed": "Przywracanie nie powiodło się",
        "Your notes were restored from the selected backup.":
            "Notatki zostały przywrócone z wybranej kopii zapasowej.",
        "That backup could not be restored.": "Nie udało się przywrócić tej kopii zapasowej.",
        "\"{name}\" could not be read and was restored from the backup of {when}.":
            "„{name}” nie udało się odczytać i przywrócono ją z kopii zapasowej z {when}.",

        # ---- keyboard shortcuts (tray + cheat-sheet) ----
        "Keyboard shortcuts…": "Skróty klawiszowe…",
        "Keyboard shortcuts": "Skróty klawiszowe",
        "Turn these on or off in Settings.": "Włącz lub wyłącz w Ustawieniach.",
        # ---- cheat-sheet tabs + section notes (translated via tr(title), so the
        # AST scan in test_i18n_hr_complete can't see them — that test checks the
        # shortcuts catalog explicitly instead) ----
        "Global": "Globalne",
        "Text & lists": "Tekst i listy",
        "Code": "Kod",
        "Windows": "Okna",
        "These act on the note you are using right now.":
            "Dotyczą notatki, której obecnie używasz.",
        "These only do anything while \"Enable code blocks\" is on (Settings → Note).":
            "Działają tylko, gdy włączona jest opcja „Enable code blocks” (Ustawienia → Notatka).",

        # ---- export: PNG ----
        "Image (.png)": "Obraz (.png)",
        "PNG image (*.png)": "Obraz PNG (*.png)",
    },

    "ja": {
        # ---- generic actions / buttons ----
        "OK": "OK",
        "Cancel": "キャンセル",
        "Save": "保存",
        "Close": "閉じる",
        "Apply": "適用",
        "Select": "選択",
        "Set": "設定",
        "Refresh": "更新",
        "Copy": "コピー",
        "Copied": "コピーしました",

        # ---- tray menu ----
        "New Note": "新しいメモ",
        "Show All": "すべて表示",
        "Hide All": "すべて非表示",
        "Lock All": "すべてロック",
        "Unlock All": "すべてロック解除",
        "Notes Manager": "メモマネージャー",
        "Settings": "設定",
        "About": "このアプリについて",
        "Toggle theme": "テーマを切り替え",
        "Quit": "終了",

        # ---- note header / toolbar ----
        "Note Options": "メモのオプション",
        "Toggle Toolbar": "ツールバーの表示切替",
        "Lock / Unlock": "ロック / ロック解除",
        "Hide Note": "メモを非表示",
        "Always on Top": "常に最前面",
        "Favorite": "お気に入り",
        "Add to Favorites": "お気に入りに追加",
        "Remove from Favorites": "お気に入りから削除",
        "Bold (Ctrl+B)": "太字 (Ctrl+B)",
        "Italic (Ctrl+I)": "斜体 (Ctrl+I)",
        "Underline (Ctrl+U)": "下線 (Ctrl+U)",
        "Strikethrough (Ctrl+S)": "取り消し線 (Ctrl+S)",
        "Bullet list": "箇条書きリスト",
        "Checklist": "チェックリスト",
        "Checklist — Tab to indent, drag a box or Alt+↑/↓ to reorder":
            "チェックリスト — Tab でインデント、ボックスをドラッグまたは Alt+↑/↓ で並べ替え",
        "Checklist progress (done / total)": "チェックリストの進捗（完了 / 合計）",
        "Increase font size": "フォントサイズを大きくする",
        "Decrease font size": "フォントサイズを小さくする",
        "Text Colour": "文字の色",
        "Font family": "フォントの種類",
        "Click to set exact size": "クリックして正確なサイズを設定",
        "Click to open colour picker": "クリックしてカラーピッカーを開く",
        "Write your note here…": "ここにメモを書いてください…",
        "More fonts…": "フォントをもっと見る…",

        # ---- note context menu ----
        "Change Colour…": "色を変更…",
        "Copy Note": "メモをコピー",
        "Rename…": "名前を変更…",
        "Rename": "名前を変更",          # Manager row menu (sits next to "Export")
        "Paste as plain text": "プレーンテキストとして貼り付け",
        "Move to Trash": "ゴミ箱に移動",
        "Custom colour:": "カスタムカラー:",

        # ---- list styles (glyph kept) ----
        "●  Disc": "●  黒丸",
        "▪  Square": "▪  四角",
        "1.  Decimal": "1.  数字",
        "a.  Lower alpha": "a.  小文字アルファベット",
        "i.  Lower roman": "i.  小文字ローマ数字",
        "✕  Remove list": "✕  リストを削除",

        # ---- rename dialog ----
        "Rename note": "メモの名前を変更",
        "Note name:": "メモ名:",
        "Leave empty to use the automatic name (first line of the note).":
            "空欄のままにすると自動的に名前が付きます（メモの最初の行）。",
        "Untitled": "無題",

        # ---- reminder dialog ----
        "Reminder": "リマインダー",
        "Set reminder…": "リマインダーを設定…",
        "Reminder: ": "リマインダー: ",
        "Reminder: {} — change…": "リマインダー: {} — 変更…",
        "Current: ": "現在: ",
        "Quick options:": "クイックオプション:",
        "Or a specific time:": "または特定の時刻:",
        "Or a specific date and time:": "または特定の日付と時刻:",
        "Date": "日付",
        "Time": "時刻",
        "In 1 min": "1分後",
        "In 5 min": "5分後",
        "In 10 min": "10分後",
        "In 30 min": "30分後",
        "In 1 hour": "1時間後",
        "In 3 hours": "3時間後",
        "In 8 hours": "8時間後",
        "In 24 hours": "24時間後",
        "Remove reminder": "リマインダーを削除",

        # ---- export ----
        "Export Note": "メモを書き出す",
        "Export Failed": "書き出しに失敗しました",
        "Plain text (.txt)": "プレーンテキスト (.txt)",
        "OpenDocument (.odt)": "OpenDocument (.odt)",
        "PDF (.pdf)": "PDF (.pdf)",
        "Text files (*.txt)": "テキストファイル (*.txt)",
        "OpenDocument (*.odt)": "OpenDocument (*.odt)",
        "PDF (*.pdf)": "PDF (*.pdf)",
        "(empty note)": "（空のメモ）",

        # ---- manager ----
        "Restore All": "すべて復元",
        "Delete All": "すべて削除",
        "Search notes…": "メモを検索…",
        "Search notes": "メモを検索",
        "Search Notes…": "メモを検索…",
        "No matching notes": "一致するメモがありません",
        "Global shortcut for searching notes": "メモ検索のグローバルショートカット",
        "Scroll on tray icon to raise/lower notes": "トレイアイコンをスクロールしてメモを前後に移動",
        "Scroll up = bring visible notes to front; scroll down = send them behind other windows. Pinned notes are left alone.":
            "上にスクロール = 表示中のメモを前面に、下にスクロール = 他のウィンドウの後ろに送ります。ピン留めされたメモは対象外です。",
        "Press {} anywhere to open the search palette. Rebind it in GNOME Settings → Keyboard → Custom Shortcuts.":
            "どこでも {} を押すと検索パレットが開きます。GNOME の設定 → キーボード → カスタムショートカットで変更できます。",
        "Registers a GNOME shortcut ({}) to open a search box for finding a note from anywhere.":
            "どこからでもメモを検索できるように、GNOME ショートカット（{}）を登録します。",
        "Restore": "復元",
        "Delete permanently": "完全に削除",
        "Active": "アクティブ",
        "Archive": "アーカイブ",
        "Trash": "ゴミ箱",
        "Active ({})": "アクティブ ({})",
        "Active ({}/{})": "アクティブ ({}/{})",
        "Archive ({})": "アーカイブ ({})",
        "Archive ({}/{})": "アーカイブ ({}/{})",
        "Trash ({})": "ゴミ箱 ({})",
        "Trash ({}/{})": "ゴミ箱 ({}/{})",
        "{} matches": "{} 件一致",
        "{} active · {} in trash": "アクティブ {} 件・ゴミ箱 {} 件",
        "{} active · {} archived · {} in trash": "アクティブ {} 件・アーカイブ {} 件・ゴミ箱 {} 件",
        "Archive Full": "アーカイブが満杯です",
        "Active Full": "アクティブが満杯です",
        "Partly Restored": "一部復元されました",
        "Archive is full ({} notes).\nRemove something from the Archive first.":
            "アーカイブが満杯です（{} 件）。\n先にアーカイブから何かを削除してください。",
        "You already have {} active notes — the maximum.\nArchive or delete one first.":
            "すでにアクティブなメモが {} 件あります — これが上限です。\n先にどれかをアーカイブまたは削除してください。",
        "You already have {} active notes — the maximum.":
            "すでにアクティブなメモが {} 件あります — これが上限です。",
        "Restored {} note(s). {} could not be restored — the active limit ({}) was reached.":
            "{} 件のメモを復元しました。{} 件は復元できませんでした — アクティブの上限（{}）に達しています。",
        "Permanently delete all {} note(s) in Trash?\nThis cannot be undone.":
            "ゴミ箱にある {} 件のメモをすべて完全に削除しますか？\nこの操作は取り消せません。",

        # ---- settings dialog ----
        "Start automatically on login": "ログイン時に自動的に起動",
        "Creates an autostart entry in ~/.config/autostart/":
            "~/.config/autostart/ に自動起動エントリを作成します",
        "Requires GNOME (gsettings). Bind a shortcut manually instead.":
            "GNOME（gsettings）が必要です。代わりに手動でショートカットを設定してください。",
        "Global shortcut for new note": "新規メモのグローバルショートカット",
        "Global shortcut for new note from clipboard":
            "クリップボードから新規メモを作成するグローバルショートカット",
        "Press {} anywhere to create a new note. Rebind it in GNOME Settings → Keyboard → Custom Shortcuts.":
            "どこでも {} を押すと新しいメモを作成します。GNOME の設定 → キーボード → カスタムショートカットで変更できます。",
        "Press {} anywhere to create a note from the clipboard. Rebind it in GNOME Settings → Keyboard → Custom Shortcuts.":
            "どこでも {} を押すとクリップボードの内容からメモを作成します。GNOME の設定 → キーボード → カスタムショートカットで変更できます。",
        "Registers a GNOME shortcut ({}) to create a new note.":
            "新しいメモを作成する GNOME ショートカット（{}）を登録します。",
        "Registers a GNOME shortcut ({}) to create a note pre-filled with the clipboard contents.":
            "クリップボードの内容があらかじめ入力されたメモを作成する GNOME ショートカット（{}）を登録します。",
        "UI Scale": "UIの拡大率",
        "Scales UI text and note content (100%–200%)":
            "UIのテキストとメモの内容を拡大縮小します（70%～200%）",
        "Scales the whole interface, text and icons (100%–200%).":
            "インターフェース全体、テキスト、アイコンを拡大縮小します（70%～200%）。",
        "Restart Sticky Notes to apply the new scale.":
            "新しい拡大率を適用するには Sticky Notes を再起動してください。",
        "Restart now": "今すぐ再起動",
        "Default font size": "デフォルトのフォントサイズ",
        "Choose Font": "フォントを選択",
        "Search fonts…": "フォントを検索…",
        "Apply Font to New Notes": "新しいメモにフォントを適用",
        "Apply to New Notes": "新しいメモに適用",
        "Note": "メモ",
        "Default size for new notes": "新しいメモのデフォルトサイズ",
        "Width": "幅",
        "Height": "高さ",
        "Background opacity": "背景の不透明度",
        "Makes the note paper see-through; text stays sharp. Applies to all current and future notes.":
            "メモの用紙を透明にします。文字はくっきりしたままです。現在と今後のすべてのメモに適用されます。",
        "Auto backup every": "自動バックアップの間隔",
        "15 minutes": "15分",
        "30 minutes": "30分",
        "1 hour": "1時間",
        "2 hours": "2時間",
        "4 hours": "4時間",
        "8 hours": "8時間",
        "12 hours": "12時間",
        "24 hours": "24時間",
        "Backup Now": "今すぐバックアップ",
        "Last backup: {}": "前回のバックアップ: {}",
        "No backup yet": "まだバックアップがありません",
        "Restore from Backup": "バックアップから復元",
        "Notes recovery": "メモの復旧",
        "Some data files could not be read.": "一部のデータファイルを読み込めませんでした。",
        '"{name}" could not be read and was restored from its backup.':
            '「{name}」を読み込めなかったため、バックアップから復元しました。',
        '"{name}" could not be read and no valid backup was found.':
            '「{name}」を読み込めず、有効なバックアップも見つかりませんでした。',
        'The damaged file was kept as "{kept}".':
            '破損したファイルは「{kept}」として保存されました。',
        'The damaged file was kept as "{kept}" so no data was overwritten.':
            '破損したファイルは「{kept}」として保存されたため、データは上書きされませんでした。',
        "Restore notes from backup dated:\n{}\n\n⚠  Current notes will be replaced!":
            "次の日付のバックアップからメモを復元します:\n{}\n\n⚠  現在のメモは置き換えられます！",
        "EXPORT / IMPORT": "書き出し / 読み込み",
        "Export to JSON…": "JSONに書き出す…",
        "Import from JSON…": "JSONから読み込む…",
        "Language": "言語",
        "Language changes apply after restart.": "言語の変更は再起動後に適用されます。",
        # settings tab labels
        "General": "一般",
        "Backup": "バックアップ",
        # snapping
        "Snapping": "スナップ",
        "Snapping && Tray": "スナップ && トレイ",
        "Tray": "トレイ",
        "Snap to grid": "グリッドにスナップ",
        "Snap to other notes": "他のメモにスナップ",
        "Snap size to grid": "サイズをグリッドにスナップ",
        "Grid size": "グリッドサイズ",
        "Notes snap when you drop them or finish resizing. Snap to grid and snap size to grid align a note's position and size to an invisible grid; snap to other notes lines edges up with nearby notes. The grid size below sets the spacing.":
            "メモはドロップ時やサイズ変更完了時にスナップします。「グリッドにスナップ」と「サイズをグリッドにスナップ」はメモの位置とサイズを見えないグリッドに合わせます。「他のメモにスナップ」は近くのメモと端をそろえます。以下のグリッドサイズが間隔を設定します。",

        # ---- about dialog ----
        "About Sticky Notes": "Sticky Notes について",
        "Version {}": "バージョン {}",
        "A lightweight sticky notes application\nfor Ubuntu desktop.\n\nBuilt with Python & PyQt6":
            "Ubuntuデスクトップ向けの\n軽量な付箋アプリです。\n\nPythonとPyQt6で作成",
        "View on GitHub": "GitHub で見る",
        "Made by Nikola Javorina": "制作: Nikola Javorina",
        "For the sharpest result, keep system scaling at 100% and use this.": "最も鮮明にするには、システムのスケーリングを 100% のままにして、これを使用してください。",
        "Buy me a coffee": "コーヒーをおごる",

        # ---- message boxes ----
        "Limit Reached": "上限に達しました",
        "Maximum of {} active notes reached.\nArchive or move some notes to Trash before creating new ones.":
            "アクティブなメモの上限（{} 件）に達しました。\n新しいメモを作成する前に、いくつかをアーカイブまたはゴミ箱に移動してください。",
        "Maximum of 20 active notes reached.\nMove some notes to Trash before creating new ones.":
            "アクティブなメモの上限（20件）に達しました。\n新しいメモを作成する前に、いくつかをゴミ箱に移動してください。",
        "Export Complete": "書き出し完了",
        "Export All": "すべて書き出す",
        "Export": "書き出す",
        "There are no archived notes to export.": "書き出せるアーカイブ済みのメモがありません。",
        "Export all archived notes to a JSON file.": "アーカイブ済みのメモをすべてJSONファイルに書き出します。",
        "Backup saves local “.bak” copies of ALL your notes (active, archived "
        "and trash), kept next to your data on this computer. Restore brings all "
        "three back.":
            "バックアップはすべてのメモ（アクティブ、アーカイブ、ゴミ箱）の"
            "ローカルな「.bak」コピーを、このコンピューター上のデータの隣に"
            "保存します。復元するとこの3つすべてが元に戻ります。",
        "Export writes a portable JSON file of your ACTIVE notes (to move to "
        "another computer or re-import). Import always brings notes in as active. "
        "To export archived notes, use “Export All” in the Manager's Archive tab.":
            "書き出しはアクティブなメモの持ち運び可能なJSONファイルを作成します"
            "（他のコンピューターへの移動や再読み込み用）。読み込みでは常に"
            "メモがアクティブとして追加されます。アーカイブ済みのメモを書き出す"
            "には、マネージャーのアーカイブタブにある「すべて書き出す」を"
            "使用してください。",
        "Import Complete": "読み込み完了",
        "Import Failed": "読み込みに失敗しました",
        "Import — Limit Reached": "読み込み — 上限に達しました",
        "You have {} active note(s). The export file contains {} note(s).\n\nYou can import at most {} note(s).\n\nImport the first {} and skip the rest?":
            "現在アクティブなメモが {} 件あります。書き出しファイルには {} 件のメモが含まれています。\n\n読み込めるのは最大 {} 件までです。\n\n最初の {} 件を読み込み、残りをスキップしますか？",
        "Exported {} note(s) to:\n{}": "{} 件のメモを次の場所に書き出しました:\n{}",
        "Imported {} note(s) successfully.": "{} 件のメモを正常に読み込みました。",
        "Could not read export file:\n{}": "書き出しファイルを読み込めませんでした:\n{}",
        "You already have {} active notes — the maximum.\nMove some notes to Trash before importing.":
            "すでにアクティブなメモが {} 件あります — これが上限です。\n読み込む前にいくつかをゴミ箱に移動してください。",
        "You already have 20 active notes — the maximum.\nMove some notes to Trash before importing.":
            "すでにアクティブなメモが20件あります — これが上限です。\n読み込む前にいくつかをゴミ箱に移動してください。",

        # ---- notifications ----
        "Sticky Notes — Reminder": "Sticky Notes — リマインダー",
        "Snooze 10 min": "10分スヌーズ",

        # ---- settings: Note tab (auto-contrast + clean mode) ----
        "Adjust text & icon colour to note background":
            "メモの背景に合わせて文字とアイコンの色を調整",
        "Dark notes get light icons and text automatically. Turn off to keep the classic dark ink.":
            "暗い色のメモには自動的に明るいアイコンと文字が使われます。オフにすると従来の暗いインクのままになります。",
        "Auto-hide toolbar and header until you hover the note":
            "メモにカーソルを合わせるまでツールバーとヘッダーを自動的に非表示",
        "Note border": "メモの枠線",
        "Off": "オフ",
        "Always": "常に",
        "Auto (light notes only)": "自動（明るいメモのみ）",
        "Auto shows a border only on light notes, where it helps them stand out from a light background.":
            "自動は明るいメモにのみ枠線を表示し、明るい背景から目立たせるのに役立ちます。",
        "Notes show only their text at rest; hover the top of a note to bring the controls back. "
        "A single click on the header keeps the controls up and lets you nudge the note with the arrow keys; click elsewhere to hide them again. "
        "Double-click a note's header to keep its controls open while you edit it; "
        "double-click again to hand that note back to auto-hide.":
            "メモは通常時には文字のみを表示します。メモの上部にカーソルを合わせるとコントロールが戻ります。"
            "ヘッダーを一度クリックするとコントロールが表示されたままになり、矢印キーでメモを動かせます。"
            "他の場所をクリックすると再び非表示になります。"
            "メモのヘッダーをダブルクリックすると編集中はコントロールが開いたままになり、"
            "もう一度ダブルクリックすると自動非表示に戻ります。",
        "Code block": "コードブロック",
        "Inline code": "インラインコード",
        "Enable code blocks": "コードブロックを有効化",
        "Adds code-block { } and inline-code buttons to the toolbar, and enables their shortcuts (Ctrl+M for inline code, Ctrl+Shift+M for a code block). Niche — off by default.":
            "ツールバーにコードブロック { } とインラインコードのボタンを追加し、そのショートカット"
            "（インラインコードは Ctrl+M、コードブロックは Ctrl+Shift+M）を有効にします。"
            "ニッチな機能のため、デフォルトではオフです。",

        # ---- settings: appearance (theme) ----
        "Appearance": "外観",
        "Window theme": "ウィンドウのテーマ",
        "Theme": "テーマ",
        "Light": "ライト",
        "Dark": "ダーク",
        "Auto": "自動",
        "Dark from": "ダーク開始",
        "until": "終了",
        "Auto switches to Dark between these times; the theme changes within a minute of each boundary. The tray's Toggle theme then lasts only until the next boundary.":
            "自動はこの時間帯にダークへ切り替わります。テーマは各境界から1分以内に変わります。"
            "トレイの「テーマを切り替え」はその場合、次の境界までのみ有効です。",
        "Sets the look of the app's windows, menus and notes. Switching to Dark gives every note without its own dark colour a dark default; each note keeps separate colours for Light and Dark, so switching back restores the light one. Notes and the main windows recolour instantly; a few helper windows (About, the shortcut list, search) update the next time you open them — no restart needed.":
            "アプリのウィンドウ、メニュー、メモの見た目を設定します。ダークに切り替えると、"
            "独自のダーク色を持たないメモにはデフォルトのダーク色が適用されます。"
            "各メモはライトとダークで別々の色を保持するため、戻すとライトの色に戻ります。"
            "メモと主要なウィンドウは即座に配色が変わり、一部の補助ウィンドウ"
            "（このアプリについて、ショートカット一覧、検索）は次回開いたときに更新されます"
            " — 再起動は不要です。",

        # ---- settings: tray scroll ----
        "Scroll the tray icon to bring notes to front":
            "トレイアイコンをスクロールしてメモを前面に",
        "Scroll up on the tray icon to raise your visible notes above "
        "other windows. Pinned notes are unaffected.":
            "トレイアイコンを上にスクロールすると、表示中のメモが他のウィンドウより"
            "前面に上がります。ピン留めされたメモには影響しません。",

        # ---- settings: Backup tab + restore dialogs ----
        "Backups": "バックアップ",
        "Backups save copies of ALL your notes (active, archived and trash) in a "
        "backups folder on this computer. \"Backup Now\" and the auto-backup "
        "interval each add a new restore point (the 5 most recent are kept); the "
        "daily auto-backup keeps the latest one fresh. \"Restore from Backup…\" "
        "lets you pick which one to go back to (this overwrites your current notes).":
            "バックアップは、すべてのメモ（アクティブ、アーカイブ、ゴミ箱）のコピーを、"
            "このコンピューター上の backups フォルダーに保存します。「今すぐバックアップ」と"
            "自動バックアップの間隔は、それぞれ新しい復元ポイントを追加します"
            "（直近5件が保持されます）。毎日の自動バックアップは最新の状態を保ちます。"
            "「バックアップから復元…」では戻す先を選べます（現在のメモは上書きされます）。",
        "Restore from Backup…": "バックアップから復元…",
        "Restore your notes from an earlier backup": "以前のバックアップからメモを復元",
        "The 5 most recent backups. Restoring overwrites your current "
        "notes and cannot be undone — press \"Backup Now\" first if you "
        "want to keep them.":
            "直近5件のバックアップです。復元すると現在のメモが上書きされ、元に戻せません "
            "— 保持したい場合は先に「今すぐバックアップ」を押してください。",
        "No backups yet.": "まだバックアップがありません。",
        "(latest)": "（最新）",
        "Restore selected": "選択項目を復元",
        "Replace your current notes with the backup from {}?\n\n"
        "This overwrites your current notes and cannot be undone. "
        "Use \"Backup Now\" first if you want to keep them.":
            "現在のメモを {} のバックアップに置き換えますか？\n\n"
            "この操作は現在のメモを上書きし、元に戻せません。"
            "保持したい場合は先に「今すぐバックアップ」を使用してください。",
        "Restore complete": "復元完了",
        "Restore failed": "復元に失敗しました",
        "Your notes were restored from the selected backup.":
            "選択したバックアップからメモが復元されました。",
        "That backup could not be restored.": "そのバックアップを復元できませんでした。",
        "\"{name}\" could not be read and was restored from the backup of {when}.":
            "「{name}」を読み込めなかったため、{when} のバックアップから復元しました。",

        # ---- keyboard shortcuts (tray + cheat-sheet) ----
        "Keyboard shortcuts…": "キーボードショートカット…",
        "Keyboard shortcuts": "キーボードショートカット",
        "Turn these on or off in Settings.": "設定でオン・オフを切り替えられます。",
        # ---- cheat-sheet tabs + section notes (translated via tr(title), so the
        # AST scan in test_i18n_hr_complete can't see them — that test checks the
        # shortcuts catalog explicitly instead) ----
        "Global": "全般",
        "Text & lists": "テキストとリスト",
        "Code": "コード",
        "Windows": "ウィンドウ",
        "These act on the note you are using right now.":
            "現在使用しているメモに対して機能します。",
        "These only do anything while \"Enable code blocks\" is on (Settings → Note).":
            "これらは「コードブロックを有効化」がオンのときのみ機能します（設定 → メモ）。",

        # ---- export: PNG ----
        "Image (.png)": "画像 (.png)",
        "PNG image (*.png)": "PNG画像 (*.png)",
    },
}
