# Sticky Notes — Installing on Ubuntu

Step-by-step instructions to install and run the app on Ubuntu.
Verified on **Ubuntu 24.04 LTS (GNOME)**.

There is no classic installer — it's a Python program you run once from a
terminal, after which it adds itself to the app menu and starts on login.

---

## Quick path — automatic script (recommended)

If you received a folder/ZIP that contains **`install.sh`** next to `sticky_notes`:

```bash
cd <folder-with-install.sh>
./install.sh
```

The script installs the required packages (asks for your sudo password), copies
the app to a stable location (`~/.local/share/sticky-notes-app`), and runs it
once — registering the launcher, autostart, and shortcuts. Then skip to
**"How to use it"** below.

The rest of this document is the **manual** route (the same thing, step by step).

---

## Prerequisites

- **Ubuntu 24.04** (or newer) with GNOME — a standard Ubuntu install.
- **Python 3** — already included with Ubuntu.
- A few system packages (Step 1).

> **Note:** the app is **intentionally NOT installed via `pip` or a venv.** It
> uses Ubuntu's system packages only — a venv breaks the tray icon and some
> settings because it lacks system GTK integration.

---

## Step 1 — Install the required packages

Open a **Terminal** (`Ctrl+Alt+T`) and paste:

```bash
sudo apt install python3-pyqt6 python3-pyqt6.qtsvg python3-gi gir1.2-ayatanaappindicator3-0.1 fonts-noto-cjk
```

Enter your password and confirm with `Y`.

> **Note:** `fonts-noto-cjk` is required for **Chinese and Japanese** to render correctly — without it, that text shows as empty boxes (tofu). The other languages work without it.

**Optional — reminder sound** (reminders still work without these, just silently):

```bash
sudo apt install libcanberra-gtk3-module sound-theme-freedesktop
```

---

## Step 2 — Get the app

You need a folder named **`sticky_notes`** (contains `__main__.py`, `app.py`, etc.).
Copy it onto your machine — e.g. into a new `~/Applications` folder:

```bash
mkdir -p ~/Applications
```

Put the `sticky_notes` folder inside, so the path is `~/Applications/sticky_notes`.

---

## Step 3 — First run

**Important:** run it from the **parent** folder (the one that *contains*
`sticky_notes`), with `python3 -m sticky_notes` — do not `cd` into `sticky_notes`.

```bash
cd ~/Applications
python3 -m sticky_notes
```

If all is well, an **app icon** appears in the top bar (system tray, near the
clock) and the first note shows on screen. A couple of harmless warnings in the
terminal are not errors.

---

## What happens on first run

The app sets itself up:

- **Adds itself to the app menu** — press `Super` and type "Sticky Notes".
- **Starts automatically on login** (toggle in Settings → "Start automatically on login").
- **Registers three global shortcuts:**

  | Shortcut | Action |
  |---|---|
  | **Super + Alt + N** | New note |
  | **Super + Shift + N** | New note from clipboard |
  | **Super + Shift + F** | Search notes |

  All three can be toggled or rebound in Settings, or in GNOME Settings →
  Keyboard → Custom Shortcuts.

---

## How to use it

- The **tray icon** (top bar) is the main entry point — click it for
  *New Note*, *Show All*, *Settings*, *Manager*.
- **Settings:** theme (light/dark/auto), font, size, opacity, backups,
  language (English/Croatian), and more.
- **Manager:** all notes, archive, trash, search.
- Press **F1** on a note for the full list of keyboard shortcuts.

---

## Where data is stored

- Notes and settings: `~/.local/share/sticky_notes/` and `~/.config/`
- Backups: in the `backups/` subfolder (Settings → Backup — manual or automatic;
  earlier versions can be restored).

Your notes persist across restarts and logins.

---

## Troubleshooting

- **A package is reported missing** → repeat Step 1 (paste the whole line).
- **`python3 -m sticky_notes` says "No module named sticky_notes"** → you're in
  the wrong folder. Be in the *parent* folder (`cd ~/Applications`), not inside
  `sticky_notes`.
- **The tray icon is missing** → on standard Ubuntu the tray works without
  extensions. If it's still missing, run `python3 -m sticky_notes` again —
  existing notes come back, no duplicates.
- **No reminder sound** → install the optional packages from Step 1.

---

## Removing it

1. Turn off "Start automatically on login" in Settings (or delete
   `~/.config/autostart/sticky_notes.desktop`).
2. Delete the app folder (`~/Applications/sticky_notes`).
3. (Optional) delete data: `~/.local/share/sticky_notes/` and the launcher entry
   `~/.local/share/applications/sticky-notes.desktop`.
4. (Optional) remove the three shortcuts in GNOME Settings → Keyboard → Custom Shortcuts.
