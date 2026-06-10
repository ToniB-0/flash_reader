#!/usr/bin/env python3
"""
macOS Quick Action (Services) entry point.
Receives selected text via stdin (piped by Automator) and launches the widget.

Automator workflow setup:
  1. Open Automator → New → Quick Action
  2. Set "Workflow receives current" → "text" in "any application"
  3. Add action: "Run Shell Script"
     Shell: /bin/bash
     Pass input: as stdin
  4. Paste this one-liner as the script:
       python3 /path/to/flash_reader/service_handler.py
  5. Save as "Flash Reader"
  6. The service will now appear under [App] > Services > Flash Reader
     when you have text selected.
"""

import sys
import os
import subprocess

def main():
    # Automator pipes the selected text to stdin
    text = sys.stdin.read().strip()
    if not text:
        sys.exit(0)

    # Path to main.py (same directory as this script)
    here = os.path.dirname(os.path.abspath(__file__))
    main_py = os.path.join(here, "main.py")

    # Launch the widget as a detached process so Automator doesn't wait for it
    subprocess.Popen(
        [sys.executable, main_py, text],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        start_new_session=True,
    )

if __name__ == "__main__":
    main()
