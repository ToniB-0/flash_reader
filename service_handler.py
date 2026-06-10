#!/usr/bin/env python3
"""
macOS Quick Action (Services) entry point.
Receives selected text via stdin (piped by Automator).

If Flash Reader is already running (socket exists), sends text to it.
Otherwise, launches a new instance with the text.
"""

import sys
import os
import socket
import subprocess

SOCKET_PATH = "/tmp/flash_reader.sock"

def send_to_running(text: str) -> bool:
    """Try to send text to an already-running Flash Reader. Returns True on success."""
    if not os.path.exists(SOCKET_PATH):
        return False
    try:
        client = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        client.settimeout(2)
        client.connect(SOCKET_PATH)
        client.sendall(text.encode("utf-8"))
        client.close()
        return True
    except Exception:
        return False

def launch_new(text: str):
    """Launch a new Flash Reader instance with the given text."""
    here = os.path.dirname(os.path.abspath(__file__))
    main_py = os.path.join(here, "main.py")
    venv_python = os.path.join(here, "venv", "bin", "python3")
    python = venv_python if os.path.exists(venv_python) else sys.executable

    subprocess.Popen(
        [python, main_py, text],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        start_new_session=True,
    )

def main():
    text = sys.stdin.read().strip()
    if not text:
        sys.exit(0)

    if not send_to_running(text):
        launch_new(text)

if __name__ == "__main__":
    main()