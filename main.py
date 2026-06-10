#!/usr/bin/env python3
"""
Flash Reader — display words one-by-one in a floating, draggable widget.
Runs as a persistent process. Listens on a socket for new text from the
macOS service. New text loads silently; user presses play to start.

Usage: python3 main.py          (start persistent widget)
       python3 main.py "text"   (start with initial text, for testing)
"""

import sys
import os
import tkinter as tk
from tkinter import font as tkfont
import subprocess
import re
import socket
import threading

# ── Socket config ─────────────────────────────────────────────────────────────
SOCKET_PATH = "/tmp/flash_reader.sock"

# ── Design tokens ─────────────────────────────────────────────────────────────
BG       = "#1A1A1A"
SURFACE  = "#1A1A1A"
ACCENT   = "#E8F4F8"
DIM      = "#3A3A3A"
PROGRESS = "#4A9EBF"
TEXT_MAIN = "#F0F0F0"
TEXT_SUB  = "#606060"
WIDGET_W  = 480
WIDGET_H  = 200


def tokenize(text: str) -> list[str]:
    """Split text into words and punctuation as separate tokens."""
    return [t for t in re.findall(r"[.,!?;:\"'—–]|[\w'-]+", text) if t.strip()]


def get_initial_text() -> str:
    """Return initial text from argv, or empty string."""
    if len(sys.argv) > 1:
        return " ".join(sys.argv[1:])
    return ""


class FlashReader:
    def __init__(self, root: tk.Tk, text: str = ""):
        self.root = root
        self.words: list[str] = []
        self.index = 0
        self.running = False
        self.wpm = 350
        self._drag_x = 0
        self._drag_y = 0
        self._after_id = None
        # States: "idle" | "ready" | "playing" | "done"
        self.state = "idle"

        self._build_window()
        self._build_ui()
        self._start_socket_listener()

        if text.strip():
            self._load_text(text)
        else:
            self._set_idle()

    # ── Window ────────────────────────────────────────────────────────────────

    def _build_window(self):
        r = self.root
        r.title("Flash Reader")
        r.overrideredirect(True)
        r.attributes("-topmost", True)
        r.configure(bg=BG)
        r.resizable(False, False)

        try:
            import Quartz
            loc = Quartz.NSEvent.mouseLocation()
            all_screens = Quartz.NSScreen.screens()
            raw_x, raw_y = loc.x, loc.y

            target_screen = all_screens[0]
            for s in all_screens:
                sf = s.frame()
                if (sf.origin.x <= raw_x <= sf.origin.x + sf.size.width and
                        sf.origin.y <= raw_y <= sf.origin.y + sf.size.height):
                    target_screen = s
                    break

            sf = target_screen.frame()
            mx = int(raw_x)
            my = int(sf.origin.y + sf.size.height - (raw_y - sf.origin.y))
            min_x = int(sf.origin.x)
            max_x = int(sf.origin.x + sf.size.width)
            min_y = int(sf.origin.y)
            max_y = int(sf.origin.y + sf.size.height)

        except Exception:
            r.update_idletasks()
            mx = r.winfo_pointerx()
            my = r.winfo_pointery()
            min_x, min_y = 0, 0
            max_x = r.winfo_screenwidth()
            max_y = r.winfo_screenheight()

        x = min(mx - WIDGET_W // 2, max_x - WIDGET_W - 10)
        y = min(my - WIDGET_H - 20, max_y - WIDGET_H - 10)
        x = max(x, min_x + 10)
        y = max(y, min_y + 10)
        r.geometry(f"{WIDGET_W}x{WIDGET_H}+{x}+{y}")

    # ── UI ────────────────────────────────────────────────────────────────────

    def _build_ui(self):
        root = self.root

        self.card = tk.Frame(root, bg=SURFACE, bd=0, highlightthickness=0)
        self.card.place(x=0, y=0, width=WIDGET_W, height=WIDGET_H)

        # Top bar
        top = tk.Frame(self.card, bg=SURFACE, height=32)
        top.pack(fill="x", side="top")
        top.pack_propagate(False)

        title_lbl = tk.Label(
            top, text="FLASH READER", bg=SURFACE,
            fg=TEXT_SUB, font=("SF Mono", 9, "normal"), cursor="fleur"
        )
        title_lbl.pack(side="left", padx=14, pady=8)

        close_btn = tk.Label(
            top, text="✕", bg=SURFACE, fg=TEXT_SUB,
            font=("SF Pro Display", 11), cursor="hand2", padx=10
        )
        close_btn.pack(side="right", pady=4)
        close_btn.bind("<Button-1>", lambda _: self._quit())
        close_btn.bind("<Enter>", lambda _: close_btn.config(fg=TEXT_MAIN))
        close_btn.bind("<Leave>", lambda _: close_btn.config(fg=TEXT_SUB))

        for w in (top, title_lbl):
            w.bind("<ButtonPress-1>", self._drag_start)
            w.bind("<B1-Motion>",     self._drag_motion)

        # Word display area — three labels side by side: left_dot | word | right_dot
        word_area = tk.Frame(self.card, bg=SURFACE)
        word_area.pack(expand=True, fill="both", padx=16)

        word_font = tkfont.Font(family="SF Pro Display", size=34, weight="bold")
        dot_font  = tkfont.Font(family="SF Pro Display", size=54, weight="normal")

        self.left_dot = tk.Label(
            word_area, text="", bg=SURFACE, fg=TEXT_SUB,
            font=dot_font, width=2, anchor="e"
        )
        self.left_dot.pack(side="left")

        self.word_var = tk.StringVar(value="")
        self.word_lbl = tk.Label(
            word_area, textvariable=self.word_var,
            bg=SURFACE, fg=ACCENT, font=word_font, anchor="center"
        )
        self.word_lbl.pack(side="left", expand=True, fill="both")

        self.right_dot = tk.Label(
            word_area, text="", bg=SURFACE, fg=TEXT_SUB,
            font=dot_font, width=2, anchor="w"
        )
        self.right_dot.pack(side="left")

        # Meta label
        self.meta_var = tk.StringVar(value="")
        meta_lbl = tk.Label(
            self.card, textvariable=self.meta_var,
            bg=SURFACE, fg=TEXT_SUB, font=("SF Pro Text", 10)
        )
        meta_lbl.pack(pady=(0, 4))

        # Progress bar
        prog_bg = tk.Frame(self.card, bg=DIM, height=2)
        prog_bg.pack(fill="x", side="bottom")
        self.prog_fill = tk.Frame(prog_bg, bg=PROGRESS, height=2)
        self.prog_fill.place(x=0, y=0, height=2, width=0)
        self._prog_bg = prog_bg

        # Controls bar
        ctrl = tk.Frame(self.card, bg=SURFACE, height=38)
        ctrl.pack(fill="x", side="bottom")
        ctrl.pack_propagate(False)

        self._build_wpm_control(ctrl)

        self.play_btn = tk.Label(
            ctrl, text="▶", bg=SURFACE, fg=TEXT_MAIN,
            font=("SF Pro Display", 14), cursor="hand2", padx=12
        )
        self.play_btn.pack(side="right", padx=(0, 8))
        self.play_btn.bind("<Button-1>", self._toggle_play)

        restart_btn = tk.Label(
            ctrl, text="⟳", bg=SURFACE, fg=TEXT_SUB,
            font=("SF Pro Display", 14), cursor="hand2", padx=8
        )
        restart_btn.pack(side="right")
        restart_btn.bind("<Button-1>", self._restart)
        restart_btn.bind("<Enter>", lambda _: restart_btn.config(fg=TEXT_MAIN))
        restart_btn.bind("<Leave>", lambda _: restart_btn.config(fg=TEXT_SUB))

        # Keyboard shortcuts
        root.bind("<space>",  lambda _: self._toggle_play())
        root.bind("<r>",      lambda _: self._restart())
        root.bind("<Left>",   lambda _: self._step(-1))
        root.bind("<Right>",  lambda _: self._step(1))
        root.bind("<Up>",     lambda _: self._change_wpm(25))
        root.bind("<Down>",   lambda _: self._change_wpm(-25))
        root.bind("<Escape>", lambda _: self._quit())
        root.focus_force()

    def _build_wpm_control(self, parent):
        self.wpm_var = tk.StringVar(value=f"{self.wpm} wpm")

        minus = tk.Label(
            parent, text="−", bg=SURFACE, fg=TEXT_SUB,
            font=("SF Pro Display", 16), cursor="hand2", padx=10
        )
        minus.pack(side="left", padx=(10, 0))
        minus.bind("<Button-1>", lambda _: self._change_wpm(-25))
        minus.bind("<Enter>",    lambda _: minus.config(fg=TEXT_MAIN))
        minus.bind("<Leave>",    lambda _: minus.config(fg=TEXT_SUB))

        wpm_lbl = tk.Label(
            parent, textvariable=self.wpm_var,
            bg=SURFACE, fg=TEXT_SUB, font=("SF Mono", 10), width=7
        )
        wpm_lbl.pack(side="left")

        plus = tk.Label(
            parent, text="+", bg=SURFACE, fg=TEXT_SUB,
            font=("SF Pro Display", 16), cursor="hand2", padx=6
        )
        plus.pack(side="left")
        plus.bind("<Button-1>", lambda _: self._change_wpm(25))
        plus.bind("<Enter>",    lambda _: plus.config(fg=TEXT_MAIN))
        plus.bind("<Leave>",    lambda _: plus.config(fg=TEXT_SUB))

    # ── Socket listener ───────────────────────────────────────────────────────

    def _start_socket_listener(self):
        """Listen for new text from service_handler on a background thread."""
        if os.path.exists(SOCKET_PATH):
            os.remove(SOCKET_PATH)

        server = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        server.bind(SOCKET_PATH)
        server.listen(5)

        def listen():
            while True:
                try:
                    conn, _ = server.accept()
                    data = b""
                    while chunk := conn.recv(4096):
                        data += chunk
                    conn.close()
                    text = data.decode("utf-8").strip()
                    if text:
                        # Schedule on main thread
                        self.root.after(0, lambda t=text: self._load_text(t))
                except Exception:
                    pass

        t = threading.Thread(target=listen, daemon=True)
        t.start()

    # ── Text loading & states ─────────────────────────────────────────────────

    def _load_text(self, text: str):
        """Load new text, stop playback, show first word in ready state."""
        self._pause()
        self.words = tokenize(text)
        self.index = 0
        self.state = "ready"
        self._render_state()

    def _set_idle(self):
        self.state = "idle"
        self.word_var.set("···")
        self.left_dot.config(text="")
        self.right_dot.config(text="")
        self.meta_var.set("waiting for text")
        self._update_progress(0, force_empty=True)

    def _render_state(self):
        if not self.words:
            self._set_idle()
            return

        idx = min(self.index, len(self.words) - 1)
        self.word_var.set(self.words[idx])
        self.meta_var.set(f"{idx + 1} / {len(self.words)}")
        self._update_progress(idx)

        if self.state == "ready":
            self.left_dot.config(text="")
            self.right_dot.config(text="···")
        elif self.state == "playing":
            self.left_dot.config(text="")
            self.right_dot.config(text="")
        elif self.state == "done":
            self.left_dot.config(text="···")
            self.right_dot.config(text="")

    # ── Drag ──────────────────────────────────────────────────────────────────

    def _drag_start(self, e):
        self._drag_x = e.x_root - self.root.winfo_x()
        self._drag_y = e.y_root - self.root.winfo_y()

    def _drag_motion(self, e):
        x = e.x_root - self._drag_x
        y = e.y_root - self._drag_y
        self.root.geometry(f"+{x}+{y}")

    # ── Playback ──────────────────────────────────────────────────────────────

    @property
    def _interval_ms(self) -> int:
        return max(100, int(60_000 / self.wpm))

    def _toggle_play(self, *_):
        if not self.words:
            return
        if self.running:
            self._pause()
        else:
            self._play()

    def _play(self):
        if self.index >= len(self.words):
            self.index = 0
        self.running = True
        self.state = "playing"
        self.play_btn.config(text="⏸")
        self._tick()

    def _pause(self):
        self.running = False
        self.play_btn.config(text="▶")
        if self._after_id:
            self.root.after_cancel(self._after_id)
            self._after_id = None
        if self.state == "playing":
            self.state = "ready"
            self._render_state()

    def _restart(self, *_):
        self._pause()
        self.index = 0
        if self.words:
            self.state = "ready"
        self._render_state()

    def _tick(self):
        if not self.running:
            return
        if self.index >= len(self.words):
            self.running = False
            self.state = "done"
            self.index = len(self.words) - 1
            self.play_btn.config(text="▶")
            self._render_state()
            return
        self.state = "playing"
        self._render_state()
        self.index += 1
        self._after_id = self.root.after(self._interval_ms, self._tick)

    def _step(self, delta: int):
        self._pause()
        self.index = max(0, min(len(self.words) - 1, self.index + delta))
        self.state = "ready"
        self._render_state()

    # ── Display ───────────────────────────────────────────────────────────────

    def _update_progress(self, idx: int, force_empty: bool = False):
        self._prog_bg.update_idletasks()
        total_w = self._prog_bg.winfo_width()
        if force_empty or not self.words:
            self.prog_fill.place(x=0, y=0, height=2, width=0)
            return
        frac = idx / (len(self.words) - 1) if len(self.words) > 1 else 1.0
        self.prog_fill.place(x=0, y=0, height=2, width=int(total_w * frac))

    def _change_wpm(self, delta: int):
        self.wpm = max(60, min(800, self.wpm + delta))
        self.wpm_var.set(f"{self.wpm} wpm")

    def _quit(self):
        if os.path.exists(SOCKET_PATH):
            os.remove(SOCKET_PATH)
        self.root.destroy()


# ── Entry point ───────────────────────────────────────────────────────────────

def main():
    text = get_initial_text()
    root = tk.Tk()
    app = FlashReader(root, text)
    root.mainloop()


if __name__ == "__main__":
    main()