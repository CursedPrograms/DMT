"""dmt.py - DMT, the Julia set explorer's window (the Cursed apps' grey and pink, customtkinter).

    run.bat            the window (run.ps1, run.sh the same)
    python dmt.py

A live preview drawn here with numpy (f(z) = z^2 + c, smoothed escape counts, the same colouring as Main.jl): drag
to move, the mouse wheel to zoom, sliders for c and the iterations, a palette, presets. **Animate** walks c round a
slow circle, so the fractal breathes. **Save** renders the full-size picture with Main.jl (the Julia program, when
Julia is installed: the real engine), or here at full size when it isn't.
"""
import glob
import os
import shutil
import subprocess
import threading
import time
import tkinter as tk
import webbrowser
from tkinter import filedialog

import customtkinter as ctk
import numpy as np
from PIL import Image, ImageTk

HERE = os.path.dirname(os.path.abspath(__file__))
NAME = "DMT"
GITHUB = "https://github.com/CursedPrograms/DMT"
KOFI = "https://ko-fi.com/cursedentertainment"
PINK = "#e0408a"

# palettes as colour stops, dark to light (the set itself takes the first colour); cursed is Main.jl's own
PALETTES = {
    "cursed": ["#121217", "#005285", "#e0408a", "#ffffff"],
    "hot": ["#0b0000", "#e60000", "#ffd200", "#ffffff"],
    "inferno": ["#000004", "#57106e", "#bc3754", "#f98e09", "#fcffa4"],
    "magma": ["#000004", "#51127c", "#b73779", "#fc8961", "#fcfdbf"],
    "viridis": ["#440154", "#3b528b", "#21918c", "#5ec962", "#fde725"],
    "neon": ["#020611", "#34a9e3", "#f088e9", "#39ff6a", "#ffffff"],
    "bone": ["#000000", "#545474", "#a7c7c7", "#ffffff"],
}
PRESETS = {                       # name: c
    "Classic": complex(-0.8, 0.156),
    "Dendrite": complex(0.0, 1.0),
    "Douady rabbit": complex(-0.123, 0.745),
    "San Marco": complex(-0.75, 0.0),
    "Siegel disk": complex(-0.391, -0.587),
    "Galaxies": complex(0.285, 0.01),
    "Seahorses": complex(-0.4, 0.6),
    "Lightning": complex(-0.7269, 0.1889),
}


def lut(name, n=1024):
    stops = [tuple(int(h[i:i + 2], 16) for i in (1, 3, 5)) for h in PALETTES[name]]
    xs = np.linspace(0, 1, len(stops))
    t = np.linspace(0, 1, n)
    return np.stack([np.interp(t, xs, [s[k] for s in stops]) for k in range(3)], axis=-1).astype(np.uint8)


def render(width, height, c, center, zoom, max_iter, palette):
    """The picture (H x W x 3 uint8): Main.jl's algorithm in numpy."""
    half_w = 2 / zoom
    half_h = half_w * height / width
    xs = np.linspace(center[0] - half_w, center[0] + half_w, width)
    ys = np.linspace(center[1] + half_h, center[1] - half_h, height)
    z = xs[None, :] + 1j * ys[:, None]
    n = np.full(z.shape, float(max_iter))
    alive = np.ones(z.shape, bool)
    for i in range(max_iter):
        z[alive] = z[alive] * z[alive] + c
        out = alive & (np.abs(z) > 2)
        if out.any():
            n[out] = i + 1 + 1 - np.log2(np.log2(np.abs(z[out])))
            alive &= ~out
        if not alive.any():
            break
    escaped = n < max_iter
    colours = lut(palette)
    img = np.empty(z.shape + (3,), np.uint8)
    img[~escaped] = colours[0]
    if escaped.any():
        v = n[escaped]
        lo, hi = v.min(), v.max()
        t = np.clip((v - lo) / max(hi - lo, 1e-9), 0, 1) ** 0.5
        img[escaped] = colours[(t * (len(colours) - 1)).astype(int)]
    return img


def find_julia():
    found = shutil.which("julia")
    if found:
        return found
    for pattern in (os.path.expandvars(r"%LOCALAPPDATA%\Programs\Julia-*\bin\julia.exe"),
                    os.path.expanduser("~/.juliaup/bin/julia"), "/usr/local/bin/julia"):
        hits = sorted(glob.glob(pattern))
        if hits:
            return hits[-1]
    return None


class Window:
    def __init__(self):
        self.c = PRESETS["Classic"]
        self.center = [0.0, 0.0]
        self.zoom = 1.0
        self.iters = 120
        self.palette = "cursed"
        self.animate = False
        self.angle = 0.0
        self.dirty = True
        self.picture = None
        self.drag = None
        self.julia = find_julia()

        ctk.set_appearance_mode("dark")
        theme = os.path.join(HERE, "theme.json")
        if os.path.exists(theme):
            ctk.set_default_color_theme(theme)
        self.root = ctk.CTk()
        self.root.title(NAME)
        self.root.geometry("1280x800")
        self.root.minsize(960, 600)
        self.root.grid_columnconfigure(0, weight=1)
        self.root.grid_rowconfigure(0, weight=1)
        self._build()
        self.root.bind("<Escape>", lambda e: self.root.destroy())
        self.root.after(50, self.tick)

    # ---- the window
    def _build(self):
        stage = ctk.CTkFrame(self.root, corner_radius=12)
        stage.grid(row=0, column=0, sticky="nsew", padx=(14, 7), pady=14)
        stage.grid_columnconfigure(0, weight=1)
        stage.grid_rowconfigure(0, weight=1)
        self.view = tk.Label(stage, bg="#16161a", bd=0, cursor="fleur")
        self.view.grid(row=0, column=0, sticky="nsew", padx=8, pady=8)
        self.view.bind("<ButtonPress-1>", self._press)
        self.view.bind("<B1-Motion>", self._move)
        self.view.bind("<MouseWheel>", self._wheel)
        self.view.bind("<Button-4>", lambda e: self._zoom_at(e, 1.25))
        self.view.bind("<Button-5>", lambda e: self._zoom_at(e, 0.8))
        self.view.bind("<Configure>", lambda e: self._changed())
        self.status = ctk.CTkLabel(stage, text="", text_color="gray60", anchor="w")
        self.status.grid(row=1, column=0, sticky="ew", padx=12, pady=(0, 8))

        side = ctk.CTkScrollableFrame(self.root, width=300, corner_radius=12)
        side.grid(row=0, column=1, sticky="ns", padx=(7, 14), pady=14)
        ctk.CTkLabel(side, text="CURSED ENTERTAINMENT", text_color="gray55",
                     font=ctk.CTkFont(size=11, weight="bold")).pack(anchor="w", padx=12, pady=(12, 0))
        ctk.CTkLabel(side, text=NAME, font=ctk.CTkFont(size=28, weight="bold"), text_color=PINK).pack(anchor="w", padx=12)
        ctk.CTkLabel(side, text="a Julia set explorer: z² + c, forever", text_color="gray60",
                     wraplength=270, justify="left").pack(anchor="w", padx=12)

        self._section(side, "The set")
        self.preset = ctk.CTkOptionMenu(side, values=list(PRESETS), command=self.pick_preset)
        self.preset.set("Classic")
        self.preset.pack(fill="x", padx=12, pady=4)
        self.c_re = self._slider(side, "c, real", -1.5, 1.5, self.c.real, lambda v: self._set_c(v, None))
        self.c_im = self._slider(side, "c, imaginary", -1.5, 1.5, self.c.imag, lambda v: self._set_c(None, v))
        self.animate_sw = ctk.CTkSwitch(side, text="Animate: c walks a slow circle", command=self.toggle_animate)
        self.animate_sw.pack(anchor="w", padx=12, pady=(6, 2))

        self._section(side, "The look")
        self.palette_pick = ctk.CTkSegmentedButton(side, values=list(PALETTES)[:4], command=self.pick_palette)
        self.palette_pick.set("cursed")
        self.palette_pick.pack(fill="x", padx=12, pady=(4, 2))
        self.palette_more = ctk.CTkSegmentedButton(side, values=list(PALETTES)[4:], command=self.pick_palette)
        self.palette_more.pack(fill="x", padx=12, pady=(2, 4))
        self.iter_s = self._slider(side, "Iterations", 20, 600, self.iters, self._set_iters, fmt="{:.0f}")

        self._section(side, "The view")
        ctk.CTkLabel(side, text="Drag to move, mouse wheel to zoom.", text_color="gray55").pack(anchor="w", padx=12)
        ctk.CTkButton(side, text="Reset the view", command=self.reset_view, fg_color="gray25",
                      hover_color="gray30").pack(fill="x", padx=12, pady=(6, 4))

        self._section(side, "Save")
        self.size = ctk.CTkSegmentedButton(side, values=["1920x1080", "3840x2160", "2048x2048"])
        self.size.set("1920x1080")
        self.size.pack(fill="x", padx=12, pady=4)
        self.save_btn = ctk.CTkButton(side, text="Save the picture", height=40, font=ctk.CTkFont(size=14, weight="bold"),
                                      command=self.save)
        self.save_btn.pack(fill="x", padx=12, pady=(6, 2))
        engine = "Julia (Main.jl)" if self.julia else "Python (Julia isn't installed)"
        self.save_note = ctk.CTkLabel(side, text=f"Full size, rendered by {engine}.", text_color="gray55",
                                      wraplength=270, justify="left")
        self.save_note.pack(anchor="w", padx=12)

        foot = ctk.CTkFrame(side, fg_color="transparent")
        foot.pack(fill="x", padx=12, pady=(18, 6))
        links = ctk.CTkFrame(foot, fg_color="transparent")
        links.pack(anchor="w")
        for text, url in (("GitHub", GITHUB), ("Ko-fi", KOFI)):
            link = ctk.CTkLabel(links, text=text, text_color=("#c2186b", "#f29cc0"), cursor="hand2")
            link.pack(side="left", padx=(0, 14))
            link.bind("<Button-1>", lambda e, u=url: webbrowser.open(u))
        ctk.CTkLabel(foot, text="© Cursed Entertainment 2026", text_color="gray45").pack(anchor="w")

    def _section(self, parent, text):
        ctk.CTkLabel(parent, text=text.upper(), text_color="gray50",
                     font=ctk.CTkFont(size=11, weight="bold")).pack(anchor="w", padx=12, pady=(16, 1))

    def _slider(self, parent, text, lo, hi, value, command, fmt="{:+.3f}"):
        row = ctk.CTkFrame(parent, fg_color="transparent")
        row.pack(fill="x", padx=12, pady=(6, 0))
        ctk.CTkLabel(row, text=text).pack(side="left")
        shown = ctk.CTkLabel(row, text=fmt.format(value), text_color="gray60")
        shown.pack(side="right")

        def moved(v):
            shown.configure(text=fmt.format(v))
            command(v)
        s = ctk.CTkSlider(parent, from_=lo, to=hi, number_of_steps=int((hi - lo) * (1 if fmt == "{:.0f}" else 1000)),
                          command=moved)
        s.set(value)
        s.pack(fill="x", padx=12, pady=(0, 2))
        s.shown, s.fmt = shown, fmt
        return s

    def _setslider(self, s, v):
        s.set(v)
        s.shown.configure(text=s.fmt.format(v))

    # ---- what the controls do
    def _changed(self):
        self.dirty = True

    def _set_c(self, re, im):
        self.c = complex(self.c.real if re is None else re, self.c.imag if im is None else im)
        self._changed()

    def _set_iters(self, v):
        self.iters = int(v)
        self._changed()

    def pick_preset(self, name):
        self.c = PRESETS[name]
        self._setslider(self.c_re, self.c.real)
        self._setslider(self.c_im, self.c.imag)
        self._changed()

    def pick_palette(self, name):
        self.palette = name
        (self.palette_more if name in list(PALETTES)[:4] else self.palette_pick).set("")
        self._changed()

    def toggle_animate(self):
        self.animate = bool(self.animate_sw.get())
        self.radius = abs(self.c)
        self.angle = np.angle(self.c)

    def reset_view(self):
        self.center, self.zoom = [0.0, 0.0], 1.0
        self._changed()

    def _press(self, e):
        self.drag = (e.x, e.y, list(self.center))

    def _move(self, e):
        if not self.drag:
            return
        w = max(self.view.winfo_width(), 1)
        scale = 4 / self.zoom / w
        x0, y0, c0 = self.drag
        self.center = [c0[0] - (e.x - x0) * scale, c0[1] + (e.y - y0) * scale]
        self._changed()

    def _wheel(self, e):
        self._zoom_at(e, 1.25 if e.delta > 0 else 0.8)

    def _zoom_at(self, e, k):
        """Zoom by k, keeping the point under the mouse where it is."""
        w, h = max(self.view.winfo_width(), 1), max(self.view.winfo_height(), 1)
        scale = 4 / self.zoom / w
        px = self.center[0] + (e.x - w / 2) * scale
        py = self.center[1] - (e.y - h / 2) * scale
        self.zoom *= k
        scale2 = 4 / self.zoom / w
        self.center = [px - (e.x - w / 2) * scale2, py + (e.y - h / 2) * scale2]
        self._changed()

    # ---- drawing: a smaller picture while anything moves, then the full window
    def tick(self):
        if self.animate:
            self.angle += 0.012
            r = getattr(self, "radius", 0.78)
            self.c = complex(r * np.cos(self.angle), r * np.sin(self.angle))
            self._setslider(self.c_re, self.c.real)
            self._setslider(self.c_im, self.c.imag)
            self.dirty = True
        if self.dirty:
            self.dirty = False
            w, h = max(self.view.winfo_width(), 64), max(self.view.winfo_height(), 64)
            k = 0.5 if self.animate or self.drag else 1.0
            t0 = time.perf_counter()
            img = render(max(int(w * k), 32), max(int(h * k), 32), self.c, self.center, self.zoom,
                         min(self.iters, 160) if self.animate else self.iters, self.palette)
            pil = Image.fromarray(img).resize((w, h), Image.BILINEAR) if k < 1 else Image.fromarray(img)
            self.picture = ImageTk.PhotoImage(pil)
            self.view.configure(image=self.picture)
            self.status.configure(text=f"c = {self.c.real:+.4f} {self.c.imag:+.4f}i   ·   zoom {self.zoom:.2f}x   ·   "
                                       f"centre {self.center[0]:+.4f}, {self.center[1]:+.4f}   ·   "
                                       f"{(time.perf_counter() - t0) * 1000:.0f} ms")
        self.root.after(30, self.tick)

    # ---- saving at full size
    def save(self):
        w, h = (int(v) for v in self.size.get().split("x"))
        path = filedialog.asksaveasfilename(title="Save the picture", defaultextension=".png",
                                            initialfile=f"dmt_{self.palette}.png", filetypes=[("PNG", "*.png")])
        if not path:
            return
        self.save_btn.configure(state="disabled", text="Rendering ...")
        c, center, zoom, iters, palette = self.c, list(self.center), self.zoom, self.iters, self.palette

        def work():
            message = ""
            try:
                if self.julia and palette in ("cursed", "hot", "inferno", "magma", "viridis", "bone"):
                    cmd = [self.julia, f"--project={HERE}", "-t", "auto", os.path.join(HERE, "Main.jl"),
                           f"--c={c.real}{c.imag:+}im", f"--palette={palette}", f"--zoom={zoom}",
                           f"--center={center[0]},{center[1]}", f"--iter={iters}", f"--size={w}x{h}", f"--out={path}"]
                    r = subprocess.run(cmd, cwd=HERE, capture_output=True, text=True,
                                       creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
                    if r.returncode != 0:
                        raise RuntimeError((r.stderr or r.stdout).strip().splitlines()[-1])
                    message = f"Saved {os.path.basename(path)} (Julia)."
                else:
                    Image.fromarray(render(w, h, c, center, zoom, iters, palette)).save(path)
                    message = f"Saved {os.path.basename(path)}."
            except Exception as e:  # noqa: BLE001 - shown in the window
                message = f"Couldn't save: {e}"
            self.root.after(0, lambda: (self.save_btn.configure(state="normal", text="Save the picture"),
                                        self.save_note.configure(text=message)))
        threading.Thread(target=work, daemon=True).start()

    def run(self):
        self.root.mainloop()


if __name__ == "__main__":
    Window().run()
