#!/usr/bin/env python3
"""
Flash Reader — display words one-by-one in a floating, draggable widget.
Usage: python3 main.py "Your text goes here"
       python3 main.py  (reads from clipboard)
"""

import sys
import tkinter as tk
from tkinter import font as tkfont
import subprocess


# ── Design tokens ─────────────────────────────────────────────────────────────
BG          = "#0D0D0D"
SURFACE     = "#1A1A1A"
ACCENT      = "#E8F4F8"       # near-white, cold
DIM         = "#3A3A3A"
PROGRESS    = "#4A9EBF"
TEXT_MAIN   = "#F0F0F0"
TEXT_SUB    = "#606060"
BTN_HOVER   = "#2A2A2A"
WIDGET_W    = 480
WIDGET_H    = 200
CORNER_R    = 14


def get_text() -> str:
    """Return the text to read: argv[1], or clipboard content."""
    if len(sys.argv) > 1:
        return " ".join(sys.argv[1:])
    try:
        result = subprocess.run(
            ["pbpaste"], capture_output=True, text=True, timeout=2
        )
        text = result.stdout.strip()
        if text:
            return text
    except Exception:
        pass
    return ""


class FlashReader:
    def __init__(self, root: tk.Tk, text: str):
        self.root = root
        self.words = text.split() if text.strip() else []
        self.index = 0
        self.running = False
        self.wpm = 250          # default words per minute
        self._drag_x = 0
        self._drag_y = 0
        self._after_id = None

        self._build_window()
        self._build_ui()
        self._update_word_display()

        if not self.words:
            self.word_var.set("no text")
            self.meta_var.set("paste text & relaunch, or use the macOS service")

    # ── Window setup ──────────────────────────────────────────────────────────

    def _build_window(self):
        r = self.root
        r.title("Flash Reader")
        r.overrideredirect(True)          # borderless
        r.attributes("-topmost", True)    # always on top
        r.attributes("-alpha", 0.96)
        r.configure(bg=BG)
        r.resizable(False, False)

        # Center on screen
        sw = r.winfo_screenwidth()
        sh = r.winfo_screenheight()
        x = (sw - WIDGET_W) // 2
        y = (sh - WIDGET_H) // 2 - 80
        r.geometry(f"{WIDGET_W}x{WIDGET_H}+{x}+{y}")

        # Rounded corners via a shaped canvas background (macOS supports this)
        r.wm_attributes("-transparent", True)

    # ── UI construction ───────────────────────────────────────────────────────

    def _build_ui(self):
        root = self.root

        # Outer frame (acts as the visible rounded card)
        self.card = tk.Frame(root, bg=SURFACE, bd=0, highlightthickness=0)
        self.card.place(x=0, y=0, width=WIDGET_W, height=WIDGET_H)

        # ── Top bar: drag handle + close ──
        top = tk.Frame(self.card, bg=SURFACE, height=32)
        top.pack(fill="x", side="top")
        top.pack_propagate(False)

        title_lbl = tk.Label(
            top, text="FLASH READER", bg=SURFACE,
            fg=TEXT_SUB, font=("SF Mono", 9, "normal"),
            cursor="fleur"
        )
        title_lbl.pack(side="left", padx=14, pady=8)

        close_btn = tk.Label(
            top, text="✕", bg=SURFACE, fg=TEXT_SUB,
            font=("SF Pro Display", 11), cursor="hand2", padx=10
        )
        close_btn.pack(side="right", pady=4)
        close_btn.bind("<Button-1>", lambda _: root.destroy())
        close_btn.bind("<Enter>", lambda _: close_btn.config(fg=TEXT_MAIN))
        close_btn.bind("<Leave>", lambda _: close_btn.config(fg=TEXT_SUB))

        # Drag bindings on top bar and title
        for w in (top, title_lbl):
            w.bind("<ButtonPress-1>",   self._drag_start)
            w.bind("<B1-Motion>",       self._drag_motion)

        # ── Word display ──
        self.word_var = tk.StringVar(value="")
        self.meta_var = tk.StringVar(value="")

        word_font = tkfont.Font(family="SF Pro Display", size=34, weight="bold")
        self.word_lbl = tk.Label(
            self.card, textvariable=self.word_var,
            bg=SURFACE, fg=ACCENT,
            font=word_font, anchor="center"
        )
        self.word_lbl.pack(expand=True, fill="both", padx=24)

        meta_lbl = tk.Label(
            self.card, textvariable=self.meta_var,
            bg=SURFACE, fg=TEXT_SUB,
            font=("SF Pro Text", 10)
        )
        meta_lbl.pack(pady=(0, 4))

        # ── Progress bar ──
        prog_bg = tk.Frame(self.card, bg=DIM, height=2)
        prog_bg.pack(fill="x", side="bottom", padx=0, pady=0)
        self.prog_fill = tk.Frame(prog_bg, bg=PROGRESS, height=2)
        self.prog_fill.place(x=0, y=0, height=2, width=0)
        self._prog_bg = prog_bg

        # ── Controls bar ──
        ctrl = tk.Frame(self.card, bg=SURFACE, height=38)
        ctrl.pack(fill="x", side="bottom")
        ctrl.pack_propagate(False)

        # WPM − / label / +
        self._build_wpm_control(ctrl)

        # Play / Pause / Restart
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
        root.bind("<space>",   lambda _: self._toggle_play())
        root.bind("<r>",       lambda _: self._restart())
        root.bind("<Left>",    lambda _: self._step(-1))
        root.bind("<Right>",   lambda _: self._step(1))
        root.bind("<Up>",      lambda _: self._change_wpm(25))
        root.bind("<Down>",    lambda _: self._change_wpm(-25))
        root.bind("<Escape>",  lambda _: root.destroy())
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
            bg=SURFACE, fg=TEXT_SUB,
            font=("SF Mono", 10), width=7
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
        self.play_btn.config(text="⏸")
        self._tick()

    def _pause(self):
        self.running = False
        self.play_btn.config(text="▶")
        if self._after_id:
            self.root.after_cancel(self._after_id)
            self._after_id = None

    def _restart(self, *_):
        self._pause()
        self.index = 0
        self._update_word_display()

    def _tick(self):
        if not self.running:
            return
        if self.index >= len(self.words):
            self._pause()
            self.meta_var.set("done  ·  press r to restart")
            return
        self._update_word_display()
        self.index += 1
        self._after_id = self.root.after(self._interval_ms, self._tick)

    def _step(self, delta: int):
        self._pause()
        self.index = max(0, min(len(self.words) - 1, self.index + delta))
        self._update_word_display()

    # ── Display ───────────────────────────────────────────────────────────────

    def _update_word_display(self):
        if not self.words:
            return
        idx = min(self.index, len(self.words) - 1)
        self.word_var.set(self.words[idx])
        self.meta_var.set(f"{idx + 1} / {len(self.words)}")
        self._update_progress(idx)

    def _update_progress(self, idx: int):
        self._prog_bg.update_idletasks()
        total_w = self._prog_bg.winfo_width()
        if len(self.words) > 1:
            frac = idx / (len(self.words) - 1)
        else:
            frac = 1.0
        self.prog_fill.place(x=0, y=0, height=2, width=int(total_w * frac))

    def _change_wpm(self, delta: int):
        self.wpm = max(60, min(800, self.wpm + delta))
        self.wpm_var.set(f"{self.wpm} wpm")


# ── Entry point ───────────────────────────────────────────────────────────────

def main():
    text = get_text()
    root = tk.Tk()
    app = FlashReader(root, text)
    root.mainloop()


if __name__ == "__main__":
    main()
