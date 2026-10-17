"""Image Upscaler by Jair Lima — interface gráfica principal."""

import json
import os
import subprocess
import sys
import tempfile
import threading
import time
import urllib.request
from pathlib import Path

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from PIL import Image, ImageTk, ImageGrab, ImageDraw

try:
    from tkinterdnd2 import TkinterDnD, DND_ALL
    _DND_AVAILABLE = True
except ImportError:
    _DND_AVAILABLE = False

from upscaler_engine import MODELS, upscale

# ------------------------------------------------------------------ Paleta
BG     = "#1e1e2e"
BG2    = "#2a2a3e"
BG3    = "#11111b"
FG     = "#cdd6f4"
MUTED  = "#6c7086"
ACCENT = "#89b4fa"
GREEN  = "#a6e3a1"
RED    = "#f38ba8"
YELLOW = "#fab387"

EXTS = {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".tiff", ".tif"}
SETTINGS_FILE = Path.home() / ".imageupscaler_settings.json"


# ------------------------------------------------------------------ App
class ImageUpscalerApp(TkinterDnD.Tk if _DND_AVAILABLE else tk.Tk):
    """Image Upscaler by Jair Lima."""

    def __init__(self):
        super().__init__()
        self.title("Image Upscaler by Jair Lima")
        self.geometry("980x700")
        self.minsize(760, 560)
        self.configure(bg=BG)

        # Estado
        self._files: list[str] = []
        self._last_out_folder: str = ""
        self._cancel_event = threading.Event()
        self._processing = False

        # Variáveis de configuração
        self._out_dir = tk.StringVar()
        self._model   = tk.StringVar(value=list(MODELS.keys())[0])
        self._fmt     = tk.StringVar(value="PNG")
        self._quality = tk.IntVar(value=90)
        self._scale   = tk.StringVar(value="4×")

        # Preview (slider)
        self._orig_pil: Image.Image | None = None
        self._result_pil: Image.Image | None = None
        self._divider = 0.5

        self._load_settings()
        self._style_ttk()
        self._build_ui()
        self._load_icon()

        self.bind("<Control-v>", self._paste_clipboard)
        self.bind("<Control-V>", self._paste_clipboard)
        self.protocol("WM_DELETE_WINDOW", self._on_close)

    # ------------------------------------------------------------------ Estilo

    def _style_ttk(self):
        s = ttk.Style(self)
        s.theme_use("clam")
        s.configure("TCombobox", fieldbackground=BG2, background=BG2,
                    foreground=FG, selectbackground=ACCENT, arrowcolor=ACCENT)
        s.configure("TProgressbar", troughcolor=BG2, background=ACCENT, thickness=8)

    def _load_icon(self):
        icon = Path(__file__).parent / "icon.ico"
        if getattr(sys, "frozen", False):
            icon = Path(sys._MEIPASS) / "icon.ico"
        if icon.exists():
            try:
                self.iconbitmap(str(icon))
            except Exception:
                pass

    # ------------------------------------------------------------------ UI

    def _build_ui(self):
        hdr = tk.Frame(self, bg=ACCENT, pady=5)
        hdr.pack(fill="x")
        tk.Label(hdr, text="Image Upscaler by Jair Lima",
                 bg=ACCENT, fg=BG, font=("Segoe UI", 13, "bold")).pack()

        body = tk.Frame(self, bg=BG, padx=12, pady=10)
        body.pack(fill="both", expand=True)

        left = tk.Frame(body, bg=BG)
        left.pack(side="left", fill="both", expand=True)

        right = tk.Frame(body, bg=BG2, width=280, padx=8, pady=8)
        right.pack(side="right", fill="y", padx=(10, 0))
        right.pack_propagate(False)

        self._build_files(left)
        self._build_settings(left)
        self._build_output(left)
        self._build_action(left)
        self._build_preview(right)

    # -- Seção: arquivos
    def _build_files(self, parent):
        fr = self._lframe(parent, "Arquivos  —  arraste, Ctrl+V ou use os botões")

        row = tk.Frame(fr, bg=BG)
        row.pack(fill="x")
        self._btn(row, "Selecionar Imagens", self._select_files).pack(side="left", padx=(0, 6))
        self._btn(row, "Selecionar Pasta",   self._select_folder).pack(side="left")
        self._btn(row, "Limpar", self._clear_files, bg="#585b70").pack(side="right")

        self._listbox = tk.Listbox(
            fr, bg=BG2, fg=FG, selectbackground=ACCENT,
            height=5, font=("Consolas", 8), bd=0,
            highlightthickness=1, highlightbackground="#45475a"
        )
        self._listbox.pack(fill="x", pady=(6, 0))
        self._listbox.bind("<<ListboxSelect>>", self._on_list_select)

        if _DND_AVAILABLE:
            self._listbox.drop_target_register(DND_ALL)
            self._listbox.dnd_bind("<<Drop>>", self._on_drop)

        self._count_lbl = tk.Label(fr, text="0 arquivo(s)", bg=BG, fg=MUTED,
                                   font=("Segoe UI", 8))
        self._count_lbl.pack(anchor="e")

    # -- Seção: configurações
    def _build_settings(self, parent):
        fr = self._lframe(parent, "Configurações")

        self._combo_row(fr, "Modelo:",        self._model,  list(MODELS.keys()), 0)
        self._combo_row(fr, "Formato:",       self._fmt,    ["PNG", "JPEG", "WEBP"], 1,
                        on_select=lambda: self._on_fmt_change())
        scale_cb = self._combo_row(fr, "Escala de saída:", self._scale, ["2×", "4×"], 2)
        scale_cb  # apenas referência; sem callback especial

        # Linha de qualidade JPEG
        self._qual_frame = tk.Frame(fr, bg=BG)
        self._qual_frame.grid(row=3, column=0, columnspan=2, sticky="ew", pady=2)
        tk.Label(self._qual_frame, text="Qualidade JPEG:", bg=BG, fg=FG,
                 font=("Segoe UI", 9), width=16, anchor="w").pack(side="left")
        self._qual_val = tk.Label(self._qual_frame, text=f"{self._quality.get()}%",
                                  bg=BG, fg=ACCENT, font=("Segoe UI", 9, "bold"), width=5)
        self._qual_val.pack(side="right")
        tk.Scale(self._qual_frame, variable=self._quality, from_=50, to=100,
                 orient="horizontal", bg=BG, fg=FG, troughcolor=BG2,
                 highlightthickness=0, bd=0, showvalue=False,
                 command=lambda v: self._qual_val.config(text=f"{int(float(v))}%")
                 ).pack(side="left", fill="x", expand=True, padx=4)
        if self._fmt.get() != "JPEG":
            self._qual_frame.grid_remove()

    # -- Seção: pasta de saída
    def _build_output(self, parent):
        fr = self._lframe(parent, "Pasta de Saída")

        row = tk.Frame(fr, bg=BG)
        row.pack(fill="x")
        tk.Entry(row, textvariable=self._out_dir, bg=BG2, fg=FG,
                 insertbackground=FG, font=("Consolas", 8), bd=0,
                 highlightthickness=1, highlightbackground="#45475a"
                 ).pack(side="left", fill="x", expand=True, padx=(0, 6))
        self._btn(row, "...", self._choose_outdir, width=3).pack(side="left")
        tk.Label(fr, text="Padrão: mesma pasta da imagem, sufixo _upscaled",
                 bg=BG, fg=MUTED, font=("Segoe UI", 8)).pack(anchor="w", pady=(2, 0))

    # -- Seção: ação
    def _build_action(self, parent):
        btn_row = tk.Frame(parent, bg=BG)
        btn_row.pack(fill="x", pady=(8, 0))

        self._start_btn = self._btn(
            btn_row, "Iniciar Upscaling", self._start,
            height=2, font=("Segoe UI", 11, "bold")
        )
        self._start_btn.pack(side="left", fill="x", expand=True)

        self._cancel_btn = self._btn(
            btn_row, "Cancelar", self._cancel,
            bg="#f38ba8", fg="#1e1e2e", height=2, font=("Segoe UI", 10, "bold")
        )
        self._cancel_btn.pack(side="left", padx=(6, 0))
        self._cancel_btn.config(state="disabled")

        self._open_btn = self._btn(
            btn_row, "📂 Abrir Pasta", self._open_output_folder,
            bg="#313244", fg=ACCENT, height=2, font=("Segoe UI", 9)
        )
        self._open_btn.pack(side="left", padx=(6, 0))
        self._open_btn.config(state="disabled")

        self._progress = ttk.Progressbar(parent, mode="determinate")
        self._progress.pack(fill="x", pady=(8, 2))

        self._status_lbl = tk.Label(parent, text="Pronto. Arraste imagens ou use Ctrl+V.",
                                    bg=BG, fg=MUTED, font=("Segoe UI", 8), anchor="w")
        self._status_lbl.pack(fill="x")

    # -- Seção: preview com slider
    def _build_preview(self, parent):
        tk.Label(parent, text="← Antes  |  Depois →", bg=BG2, fg=ACCENT,
                 font=("Segoe UI", 9, "bold")).pack()

        self._preview_canvas = tk.Canvas(
            parent, bg=BG3, highlightthickness=0, cursor="sb_h_double_arrow"
        )
        self._preview_canvas.pack(fill="both", expand=True, pady=(4, 0))

        self._preview_canvas.bind("<ButtonPress-1>", self._on_canvas_press)
        self._preview_canvas.bind("<B1-Motion>",     self._on_canvas_drag)
        self._preview_canvas.bind("<Configure>",     lambda _: self._draw_comparison())

        if _DND_AVAILABLE:
            self._preview_canvas.drop_target_register(DND_ALL)
            self._preview_canvas.dnd_bind("<<Drop>>", self._on_drop)

        self._info_lbl = tk.Label(parent, text="Arraste o divisor para comparar antes/depois",
                                  bg=BG2, fg=MUTED, font=("Segoe UI", 7),
                                  justify="left", anchor="w", wraplength=260)
        self._info_lbl.pack(fill="x", pady=(4, 0))

    # ------------------------------------------------------------------ Helpers UI

    def _lframe(self, parent, text):
        fr = tk.LabelFrame(parent, text=f" {text} ", bg=BG, fg=ACCENT,
                           font=("Segoe UI", 9, "bold"), padx=8, pady=6)
        fr.pack(fill="x", pady=(0, 8))
        return fr

    def _btn(self, parent, text, cmd, bg=ACCENT, fg=BG, height=1,
             font=("Segoe UI", 9), width=None):
        kw = dict(text=text, bg=bg, fg=fg, activebackground=bg, activeforeground=fg,
                  font=font, height=height, bd=0, cursor="hand2",
                  command=cmd, relief="flat", padx=8)
        if width:
            kw["width"] = width
        return tk.Button(parent, **kw)

    def _combo_row(self, parent, label, var, values, row, on_select=None):
        tk.Label(parent, text=label, bg=BG, fg=FG, font=("Segoe UI", 9),
                 width=16, anchor="w").grid(row=row, column=0, sticky="w", pady=3)
        cb = ttk.Combobox(parent, textvariable=var, values=values, state="readonly",
                          font=("Segoe UI", 9))
        cb.grid(row=row, column=1, sticky="ew", pady=3)
        parent.columnconfigure(1, weight=1)
        if on_select:
            cb.bind("<<ComboboxSelected>>", lambda _: on_select())
        return cb

    # ------------------------------------------------------------------ Slider / Preview

    def _on_canvas_press(self, event):
        self._update_divider(event.x)

    def _on_canvas_drag(self, event):
        self._update_divider(event.x)

    def _update_divider(self, x):
        w = self._preview_canvas.winfo_width()
        if w > 1:
            self._divider = max(0.02, min(0.98, x / w))
            self._draw_comparison()

    def _fit_to_canvas(self, img: Image.Image, w: int, h: int) -> Image.Image:
        iw, ih = img.size
        scale = min(w / iw, h / ih)
        nw, nh = int(iw * scale), int(ih * scale)
        resized = img.resize((nw, nh), Image.LANCZOS)
        canvas_img = Image.new("RGB", (w, h), (17, 17, 27))
        canvas_img.paste(resized, ((w - nw) // 2, (h - nh) // 2))
        return canvas_img

    def _draw_comparison(self):
        canvas = self._preview_canvas
        w = canvas.winfo_width()
        h = canvas.winfo_height()
        if w <= 1 or h <= 1:
            return

        div = int(w * self._divider)
        composite = Image.new("RGB", (w, h), (17, 17, 27))

        left_src  = self._orig_pil
        right_src = self._result_pil or self._orig_pil

        if left_src:
            fitted = self._fit_to_canvas(left_src, w, h)
            composite.paste(fitted.crop((0, 0, div, h)), (0, 0))

        if right_src:
            fitted = self._fit_to_canvas(right_src, w, h)
            composite.paste(fitted.crop((div, 0, w, h)), (div, 0))

        draw = ImageDraw.Draw(composite)
        draw.line([(div, 0), (div, h)], fill="#89b4fa", width=2)

        cy, r = h // 2, 11
        draw.ellipse([div - r, cy - r, div + r, cy + r], fill="#89b4fa")
        dark = "#1e1e2e"
        draw.polygon([(div - 7, cy), (div - 3, cy - 4), (div - 3, cy + 4)], fill=dark)
        draw.polygon([(div + 7, cy), (div + 3, cy - 4), (div + 3, cy + 4)], fill=dark)

        photo = ImageTk.PhotoImage(composite)
        canvas.delete("all")
        canvas.create_image(0, 0, anchor="nw", image=photo)
        canvas._img = photo

    def _set_original(self, path: str):
        try:
            self._orig_pil = Image.open(path)
            self._result_pil = None
            self._divider = 0.5
            iw, ih = self._orig_pil.size
            self._info_lbl.config(
                text=f"{Path(path).name}  ({iw}×{ih} px original)",
                fg=FG
            )
            self.after(10, self._draw_comparison)
        except Exception:
            pass

    def _set_result(self, path: str):
        try:
            self._result_pil = Image.open(path)
            rw, rh = self._result_pil.size
            cur = self._info_lbl.cget("text").split("\n")[0]
            self._info_lbl.config(
                text=f"{cur}\n→ {rw}×{rh} px  ·  {path}",
                fg=GREEN
            )
            self.after(10, self._draw_comparison)
        except Exception:
            pass

    # ------------------------------------------------------------------ Drag-and-drop

    def _parse_dnd_paths(self, raw: str) -> list[str]:
        paths, i = [], 0
        while i < len(raw):
            if raw[i] == "{":
                end = raw.index("}", i)
                paths.append(raw[i + 1:end])
                i = end + 2
            else:
                end = raw.find(" ", i)
                chunk = raw[i:] if end == -1 else raw[i:end]
                paths.append(chunk)
                i = len(raw) if end == -1 else end + 1
        return [p.strip() for p in paths if p.strip()]

    def _on_drop(self, event):
        raw = event.data.strip()
        if raw.startswith(("http://", "https://")):
            url = raw.splitlines()[0].strip()
            threading.Thread(target=self._download_url, args=(url,), daemon=True).start()
            return
        for p in self._parse_dnd_paths(raw):
            path = Path(p)
            if path.is_dir():
                for f in sorted(path.iterdir()):
                    if f.suffix.lower() in EXTS and str(f) not in self._files:
                        self._files.append(str(f))
            elif path.suffix.lower() in EXTS and str(path) not in self._files:
                self._files.append(str(path))
        self._refresh_list()

    def _download_url(self, url: str):
        self._set_status("Baixando imagem da URL…", YELLOW)
        try:
            suffix = Path(url.split("?")[0]).suffix or ".jpg"
            if suffix.lower() not in EXTS:
                suffix = ".jpg"
            tmp = tempfile.mktemp(suffix=suffix, prefix="upscaler_url_")
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=30) as resp:
                data = resp.read()
            with open(tmp, "wb") as f:
                f.write(data)
            Image.open(tmp).verify()
            self._files.append(tmp)
            self.after(0, self._refresh_list)
            self._set_status("Imagem da URL adicionada.", GREEN)
        except Exception as e:
            self._set_status(f"Erro ao baixar URL: {e}", RED)

    # ------------------------------------------------------------------ Clipboard

    def _paste_clipboard(self, event=None):
        try:
            clip = ImageGrab.grabclipboard()
        except Exception:
            clip = None

        if clip is None:
            self._set_status("Nada de imagem no clipboard.", MUTED)
            return

        if isinstance(clip, list):
            added = sum(
                1 for p in clip
                if Path(str(p)).suffix.lower() in EXTS
                and str(p) not in self._files
                and not self._files.append(str(p))  # side-effect: adds to list
            )
            if added:
                self._refresh_list()
                self._set_status(f"{added} arquivo(s) colado(s) do clipboard.", GREEN)
            else:
                self._set_status("Nenhuma imagem compatível no clipboard.", MUTED)
            return

        if isinstance(clip, Image.Image):
            tmp = tempfile.mktemp(suffix=".png", prefix="upscaler_paste_")
            clip.save(tmp)
            self._files.append(tmp)
            self._refresh_list()
            self._set_status(f"Imagem colada ({clip.width}×{clip.height} px).", GREEN)

    # ------------------------------------------------------------------ Arquivo actions

    def _select_files(self):
        paths = filedialog.askopenfilenames(
            title="Selecionar imagens",
            filetypes=[("Imagens", "*.jpg *.jpeg *.png *.webp *.bmp *.tiff *.tif"),
                       ("Todos os arquivos", "*.*")]
        )
        for p in paths:
            if p not in self._files:
                self._files.append(p)
        self._refresh_list()

    def _select_folder(self):
        folder = filedialog.askdirectory(title="Selecionar pasta com imagens")
        if not folder:
            return
        for f in sorted(Path(folder).iterdir()):
            if f.suffix.lower() in EXTS and str(f) not in self._files:
                self._files.append(str(f))
        self._refresh_list()

    def _clear_files(self):
        self._files.clear()
        self._orig_pil = None
        self._result_pil = None
        self._refresh_list()
        self._info_lbl.config(text="Arraste o divisor para comparar antes/depois", fg=MUTED)
        self._draw_comparison()

    def _refresh_list(self):
        self._listbox.delete(0, "end")
        for f in self._files:
            self._listbox.insert("end", Path(f).name)
        self._count_lbl.config(text=f"{len(self._files)} arquivo(s)")
        if self._files:
            self._set_original(self._files[0])

    def _on_list_select(self, _):
        sel = self._listbox.curselection()
        if sel:
            self._set_original(self._files[sel[0]])

    def _choose_outdir(self):
        folder = filedialog.askdirectory(title="Pasta de saída")
        if folder:
            self._out_dir.set(folder)

    def _resolve_output(self, input_path: str, fmt: str) -> Path:
        p = Path(input_path)
        ext = ".jpg" if fmt == "JPEG" else f".{fmt.lower()}"
        base = self._out_dir.get().strip()
        folder = Path(base) if base else p.parent
        folder.mkdir(parents=True, exist_ok=True)
        return folder / (p.stem + "_upscaled" + ext)

    def _open_output_folder(self):
        if self._last_out_folder and Path(self._last_out_folder).exists():
            subprocess.Popen(["explorer", self._last_out_folder])

    # ------------------------------------------------------------------ Processamento

    def _start(self):
        if self._processing:
            return
        if not self._files:
            messagebox.showwarning("Sem arquivos",
                                   "Selecione ao menos uma imagem.\n\n"
                                   "Dica: arraste para a lista ou use Ctrl+V.")
            return
        self._cancel_event.clear()
        self._processing = True
        self._start_btn.config(state="disabled", text="Processando…")
        self._cancel_btn.config(state="normal")
        self._open_btn.config(state="disabled")
        threading.Thread(target=self._run_batch, daemon=True).start()

    def _cancel(self):
        if self._processing:
            self._cancel_event.set()
            self._set_status("Cancelando…", YELLOW)
            self._cancel_btn.config(state="disabled")

    def _run_batch(self):
        total   = len(self._files)
        fmt     = self._fmt.get()
        model   = self._model.get()
        quality = self._quality.get()
        scale   = int(self._scale.get().replace("×", ""))
        errors  = []
        last_out = ""

        self.after(0, self._progress.config, {"maximum": total, "value": 0})

        for i, f in enumerate(self._files):
            if self._cancel_event.is_set():
                break

            name = Path(f).name
            self._set_status(f"[{i+1}/{total}] {name}…", YELLOW)

            out_path = self._resolve_output(f, fmt)
            t0 = time.time()
            ok, err = upscale(
                f, out_path, model, fmt, quality,
                output_scale=scale,
                cancel_event=self._cancel_event
            )
            elapsed = time.time() - t0

            if ok and out_path.exists():
                last_out = str(out_path.parent)
                self.after(0, self._set_result, str(out_path))
                self._set_status(f"✓ {name} → {out_path.name}  ({elapsed:.1f}s)", GREEN)
            elif self._cancel_event.is_set():
                break
            else:
                msg = err or f"Arquivo não gerado: {out_path}"
                errors.append(f"{name}: {msg}")
                self._set_status(f"✗ Erro: {name}", RED)

            self.after(0, self._progress.config, {"value": i + 1})

        self._processing = False
        self._last_out_folder = last_out

        self.after(0, self._start_btn.config,  {"state": "normal", "text": "Iniciar Upscaling"})
        self.after(0, self._cancel_btn.config, {"state": "disabled"})
        if last_out:
            self.after(0, self._open_btn.config, {"state": "normal"})

        if self._cancel_event.is_set():
            self._set_status("Processamento cancelado.", MUTED)
        elif errors:
            self._set_status(f"Concluído com {len(errors)} erro(s).", RED)
            self.after(0, messagebox.showerror,
                       "Erros durante o processamento", "\n\n".join(errors))
        else:
            self._set_status(f"✓ {total} imagem(ns) salva(s) em: {last_out}", GREEN)

    def _set_status(self, msg, color=FG):
        self.after(0, self._status_lbl.config, {"text": msg, "fg": color})

    # ------------------------------------------------------------------ Configurações

    def _on_fmt_change(self):
        if self._fmt.get() == "JPEG":
            self._qual_frame.grid()
        else:
            self._qual_frame.grid_remove()

    def _load_settings(self):
        try:
            data = json.loads(SETTINGS_FILE.read_text(encoding="utf-8"))
            models = list(MODELS.keys())
            m = data.get("model", models[0])
            self._model.set(m if m in models else models[0])
            self._fmt.set(data.get("format", "PNG"))
            self._quality.set(int(data.get("quality", 90)))
            s = data.get("scale", 4)
            self._scale.set(f"{s}×")
            self._out_dir.set(data.get("output_dir", ""))
        except Exception:
            pass

    def _save_settings(self):
        try:
            SETTINGS_FILE.write_text(json.dumps({
                "model":      self._model.get(),
                "format":     self._fmt.get(),
                "quality":    self._quality.get(),
                "scale":      int(self._scale.get().replace("×", "")),
                "output_dir": self._out_dir.get(),
            }, indent=2), encoding="utf-8")
        except Exception:
            pass

    def _on_close(self):
        self._save_settings()
        self.destroy()


if __name__ == "__main__":
    app = ImageUpscalerApp()
    app.mainloop()
