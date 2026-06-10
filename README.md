# Flash Reader

A floating, always-on-top macOS widget that flashes words one-by-one so you
can speed-read any text, anywhere on your screen.

---

## Requirements

- macOS 12+
- Python 3.9+ (the system Python 3 on macOS is fine)
- `tkinter` — included with standard Python installs from python.org.
  If missing: `brew install python-tk`

---

## Installation

```bash
# 1 — Clone / copy this folder anywhere permanent (e.g. ~/Apps/flash_reader)
# 2 — Install the macOS Quick Action (one-time):
python3 setup_service.py
```

That's it. The service is now available system-wide.

---

## Usage

### Via right-click (the main flow)
1. Select any text in any app (browser, PDF viewer, Notes, etc.)
2. Right-click → **Services → Flash Reader**
3. The widget appears and starts reading

> If "Flash Reader" doesn't appear in Services the first time, go to
> **System Settings → Privacy & Security → Extensions → Services** and
> make sure it's enabled.

### Via command line / clipboard
```bash
# Pass text directly
python3 main.py "The quick brown fox jumps over the lazy dog"

# Read from clipboard (copy text first, then run)
python3 main.py
```

---

## Widget controls

| Action | Control |
|---|---|
| Play / Pause | `Space` or ▶ button |
| Restart | `R` or ⟳ button |
| Step back one word | `←` |
| Step forward one word | `→` |
| Speed up (+25 wpm) | `↑` or `+` button |
| Slow down (−25 wpm) | `↓` or `−` button |
| Close | `Escape` or ✕ |
| Move widget | Drag the top bar |

Default speed: **250 wpm**. Range: 60 – 800 wpm.

---

## Project structure

```
flash_reader/
├── main.py            # Widget UI & playback engine
├── service_handler.py # Automator stdin bridge
├── setup_service.py   # One-time service installer
└── README.md
```
