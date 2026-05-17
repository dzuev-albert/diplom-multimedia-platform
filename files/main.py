"""
Multimedia Processor - Кроссплатформенное GUI-приложение для обработки изображений, аудио и видео.

Зависимости: см. requirements.txt
Запуск: python main.py
"""

import sys
import os
# Tell pydub/moviepy exactly where ffmpeg is (Windows fix)
os.environ["PATH"] += r";C:\ffmpeg\bin"
import threading
import traceback
from pathlib import Path
# GUI Framework
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, colorchooser
from tkinter import font as tkfont

# ── Обработка изображений ───────────────────────────────────────────────────
try:
    from PIL import Image, ImageTk, ImageFilter, ImageEnhance, ImageDraw, ImageFont
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False

try:
    import cv2
    CV2_AVAILABLE = True
except ImportError:
    CV2_AVAILABLE = False

# ── Численные вычисления / построение графиков ──────────────────────────────
try:
    import numpy as np
    NUMPY_AVAILABLE = True
except ImportError:
    NUMPY_AVAILABLE = False

try:
    import matplotlib
    matplotlib.use("TkAgg")
    from matplotlib.figure import Figure
    from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
    import matplotlib.pyplot as plt
    MPL_AVAILABLE = True
except ImportError:
    MPL_AVAILABLE = False

# ── Аудио ────────────────────────────────────────────────────────────────────
try:
    from pydub import AudioSegment
    from pydub.playback import play as pydub_play
    PYDUB_AVAILABLE = True
except ImportError:
    PYDUB_AVAILABLE = False

try:
    import sounddevice as sd
    SD_AVAILABLE = True
except ImportError:
    SD_AVAILABLE = False

try:
    import scipy.io.wavfile as wav
    from scipy import signal as scipy_signal
    SCIPY_AVAILABLE = True
except ImportError:
    SCIPY_AVAILABLE = False

# ── Видео ────────────────────────────────────────────────────────────────────
try:
    from moviepy.editor import VideoFileClip, AudioFileClip, concatenate_videoclips
    MOVIEPY_AVAILABLE = True
except ImportError:
    MOVIEPY_AVAILABLE = False

# ─────────────────────────────────────────────────────────────────────────────
# Цветовая палитра и константы стилей
# ─────────────────────────────────────────────────────────────────────────────
COLORS = {
    "bg":        "#1a1a2e",
    "panel":     "#16213e",
    "accent":    "#0f3460",
    "highlight": "#e94560",
    "text":      "#eaeaea",
    "subtext":   "#888ea8",
    "success":   "#00d2a0",
    "warning":   "#ffb347",
    "border":    "#2a2a4a",
}

# ─────────────────────────────────────────────────────────────────────────────
# Вспомогательные функции
# ─────────────────────────────────────────────────────────────────────────────

def show_error(title: str, msg: str):
    messagebox.showerror(title, msg)


def show_info(title: str, msg: str):
    messagebox.showinfo(title, msg)


def run_in_thread(fn, *args, **kwargs):
    """Запускает fn в фоновом потоке, чтобы GUI не зависал."""
    t = threading.Thread(target=fn, args=args, kwargs=kwargs, daemon=True)
    t.start()
    return t


# ─────────────────────────────────────────────────────────────────────────────
# Стилизованные виджеты
# ─────────────────────────────────────────────────────────────────────────────

def styled_button(parent, text, command, accent=False, **kw):
    bg = COLORS["highlight"] if accent else COLORS["accent"]
    btn = tk.Button(
        parent, text=text, command=command,
        bg=bg, fg=COLORS["text"],
        relief=tk.FLAT, padx=10, pady=5,
        activebackground=COLORS["highlight"],
        activeforeground=COLORS["text"],
        cursor="hand2", **kw
    )
    return btn


def styled_label(parent, text, size=10, bold=False, color=None, **kw):
    weight = "bold" if bold else "normal"
    fg = color or COLORS["text"]
    return tk.Label(parent, text=text, bg=COLORS["panel"], fg=fg,
                    font=("Segoe UI", size, weight), **kw)


def styled_frame(parent, **kw):
    return tk.Frame(parent, bg=COLORS["panel"], **kw)


def make_progress(parent):
    style = ttk.Style()
    style.theme_use("clam")
    style.configure("Custom.Horizontal.TProgressbar",
                    troughcolor=COLORS["bg"],
                    background=COLORS["highlight"],
                    darkcolor=COLORS["highlight"],
                    lightcolor=COLORS["highlight"])
    bar = ttk.Progressbar(parent, style="Custom.Horizontal.TProgressbar",
                          orient=tk.HORIZONTAL, mode="determinate")
    return bar


# ═════════════════════════════════════════════════════════════════════════════
# ВКЛАДКА ИЗОБРАЖЕНИЙ
# ═════════════════════════════════════════════════════════════════════════════

class ImageTab(tk.Frame):
    """Вся функциональность обработки изображений."""

    def __init__(self, parent):
        super().__init__(parent, bg=COLORS["bg"])
        self.image_path: str | None = None
        self.original_image: "Image.Image | None" = None
        self.current_image: "Image.Image | None" = None
        self.display_photo = None
        self.undo_stack: list = []
        self.redo_stack: list = []

        # Состояние рисования
        self.draw_mode: str | None = None
        self.draw_start = None
        self.draw_color = "#ff0000"

        self._build_ui()

    def _build_ui(self):
        # Левая панель управления
        ctrl = styled_frame(self, width=240)
        ctrl.pack(side=tk.LEFT, fill=tk.Y, padx=(10, 5), pady=10)
        ctrl.pack_propagate(False)

        styled_label(ctrl, "ОБРАБОТКА ИЗОБРАЖЕНИЙ", size=11, bold=True,
                     color=COLORS["highlight"]).pack(pady=(10, 5))

        # Загрузка / сохранение
        btn_frame = styled_frame(ctrl)
        btn_frame.pack(fill=tk.X, padx=8, pady=4)
        styled_button(btn_frame, "📂 Загрузить изображение", self._load_image, accent=True).pack(fill=tk.X, pady=2)
        styled_button(btn_frame, "💾 Сохранить изображение", self._save_image).pack(fill=tk.X, pady=2)

        ttk.Separator(ctrl, orient=tk.HORIZONTAL).pack(fill=tk.X, padx=8, pady=8)

        # Фильтры
        styled_label(ctrl, "Фильтры", bold=True).pack(anchor=tk.W, padx=10)
        filters = [
            ("Оттенки серого",   self._apply_grayscale),
            ("Размытие",         self._apply_blur),
            ("Выделение границ", self._apply_edges),
            ("Резкость",         self._apply_sharpen),
        ]
        for label, cmd in filters:
            styled_button(ctrl, label, cmd).pack(fill=tk.X, padx=8, pady=2)

        ttk.Separator(ctrl, orient=tk.HORIZONTAL).pack(fill=tk.X, padx=8, pady=8)

        # Яркость / контраст
        styled_label(ctrl, "Яркость", bold=True).pack(anchor=tk.W, padx=10)
        self.brightness_var = tk.DoubleVar(value=1.0)
        tk.Scale(ctrl, from_=0.1, to=3.0, resolution=0.05,
                 orient=tk.HORIZONTAL, variable=self.brightness_var,
                 bg=COLORS["panel"], fg=COLORS["text"],
                 highlightbackground=COLORS["panel"],
                 troughcolor=COLORS["bg"],
                 command=lambda _: self._apply_brightness_contrast()
                 ).pack(fill=tk.X, padx=8)

        styled_label(ctrl, "Контраст", bold=True).pack(anchor=tk.W, padx=10)
        self.contrast_var = tk.DoubleVar(value=1.0)
        tk.Scale(ctrl, from_=0.1, to=3.0, resolution=0.05,
                 orient=tk.HORIZONTAL, variable=self.contrast_var,
                 bg=COLORS["panel"], fg=COLORS["text"],
                 highlightbackground=COLORS["panel"],
                 troughcolor=COLORS["bg"],
                 command=lambda _: self._apply_brightness_contrast()
                 ).pack(fill=tk.X, padx=8)

        ttk.Separator(ctrl, orient=tk.HORIZONTAL).pack(fill=tk.X, padx=8, pady=8)

        # Трансформация
        styled_label(ctrl, "Трансформация", bold=True).pack(anchor=tk.W, padx=10)
        for label, cmd in [("Повернуть на 90°", self._rotate), ("Отразить по горизонтали", self._flip_h),
                            ("Отразить по вертикали", self._flip_v)]:
            styled_button(ctrl, label, cmd).pack(fill=tk.X, padx=8, pady=2)

        # Изменение размера
        resize_frame = styled_frame(ctrl)
        resize_frame.pack(fill=tk.X, padx=8, pady=4)
        styled_label(resize_frame, "Ш:", size=9).pack(side=tk.LEFT)
        self.resize_w = tk.Entry(resize_frame, width=5, bg=COLORS["bg"], fg=COLORS["text"],
                                 insertbackground=COLORS["text"])
        self.resize_w.pack(side=tk.LEFT, padx=2)
        styled_label(resize_frame, "В:", size=9).pack(side=tk.LEFT)
        self.resize_h = tk.Entry(resize_frame, width=5, bg=COLORS["bg"], fg=COLORS["text"],
                                 insertbackground=COLORS["text"])
        self.resize_h.pack(side=tk.LEFT, padx=2)
        styled_button(resize_frame, "Применить", self._resize).pack(side=tk.LEFT, padx=4)

        ttk.Separator(ctrl, orient=tk.HORIZONTAL).pack(fill=tk.X, padx=8, pady=8)

        # Инструменты рисования
        styled_label(ctrl, "Инструменты рисования", bold=True).pack(anchor=tk.W, padx=10)
        for label, mode in [("Прямоугольник", "rect"), ("Круг", "circle"), ("Текст", "text")]:
            styled_button(ctrl, label, lambda m=mode: self._set_draw_mode(m)).pack(fill=tk.X, padx=8, pady=2)
        styled_button(ctrl, "🎨 Выбрать цвет", self._pick_color).pack(fill=tk.X, padx=8, pady=2)

        ttk.Separator(ctrl, orient=tk.HORIZONTAL).pack(fill=tk.X, padx=8, pady=8)

        # Отмена / повтор
        undo_frame = styled_frame(ctrl)
        undo_frame.pack(fill=tk.X, padx=8, pady=4)
        styled_button(undo_frame, "↩ Отменить", self._undo).pack(side=tk.LEFT, expand=True, fill=tk.X, padx=2)
        styled_button(undo_frame, "↪ Повторить", self._redo).pack(side=tk.LEFT, expand=True, fill=tk.X, padx=2)

        # Правая область — холст
        canvas_frame = tk.Frame(self, bg=COLORS["bg"])
        canvas_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(5, 10), pady=10)

        self.canvas = tk.Canvas(canvas_frame, bg=COLORS["bg"],
                                highlightbackground=COLORS["border"], highlightthickness=1)
        self.canvas.pack(fill=tk.BOTH, expand=True)

        self.status_var = tk.StringVar(value="Загрузите изображение")
        tk.Label(canvas_frame, textvariable=self.status_var,
                 bg=COLORS["bg"], fg=COLORS["subtext"], font=("Segoe UI", 9)).pack(pady=(4, 0))

        # События мыши для рисования
        self.canvas.bind("<ButtonPress-1>", self._on_canvas_press)
        self.canvas.bind("<ButtonRelease-1>", self._on_canvas_release)

        # Drag-and-drop (поддержка на Linux/macOS с TkDND; если нет — пропускаем)
        try:
            self.canvas.drop_target_register("DND_Files")
            self.canvas.dnd_bind("<<Drop>>", self._on_drop)
        except Exception:
            pass

    # ── Ввод/вывод файлов ───────────────────────────────────────────────────────

    def _load_image(self, path: str | None = None):
        if not PIL_AVAILABLE:
            show_error("Отсутствует библиотека", "Требуется Pillow.\nУстановите: pip install Pillow")
            return
        if path is None:
            path = filedialog.askopenfilename(
                title="Открыть изображение",
                filetypes=[("Изображения", "*.jpg *.jpeg *.png *.bmp *.gif *.tiff"), ("Все файлы", "*.*")]
            )
        if not path:
            return
        try:
            self.image_path = path
            self.original_image = Image.open(path).convert("RGBA")
            self.current_image = self.original_image.copy()
            self.undo_stack.clear()
            self.redo_stack.clear()
            self._refresh_canvas()
            self.status_var.set(f"Загружено: {Path(path).name}  [{self.current_image.size[0]}×{self.current_image.size[1]}]")
        except Exception as e:
            show_error("Ошибка загрузки", str(e))

    def _on_drop(self, event):
        path = event.data.strip().strip("{}")
        self._load_image(path)

    def _save_image(self):
        if self.current_image is None:
            return show_error("Нет изображения", "Сначала загрузите изображение.")
        path = filedialog.asksaveasfilename(
            defaultextension=".png",
            filetypes=[("PNG", "*.png"), ("JPEG", "*.jpg"), ("BMP", "*.bmp")]
        )
        if not path:
            return
        try:
            img = self.current_image
            if path.lower().endswith((".jpg", ".jpeg")):
                img = img.convert("RGB")
            img.save(path)
            show_info("Сохранено", f"Изображение сохранено в:\n{path}")
        except Exception as e:
            show_error("Ошибка сохранения", str(e))

    # ── Отображение на холсте ─────────────────────────────────────────────────────

    def _refresh_canvas(self):
        if self.current_image is None:
            return
        cw = self.canvas.winfo_width() or 800
        ch = self.canvas.winfo_height() or 600
        img = self.current_image.copy()
        img.thumbnail((cw, ch), Image.LANCZOS)
        self.display_photo = ImageTk.PhotoImage(img)
        self.canvas.delete("all")
        self.canvas.create_image(cw // 2, ch // 2, anchor=tk.CENTER, image=self.display_photo)

    # ── Отмена / повтор ───────────────────────────────────────────────────────────

    def _push_undo(self):
        if self.current_image:
            self.undo_stack.append(self.current_image.copy())
            self.redo_stack.clear()

    def _undo(self):
        if self.undo_stack:
            self.redo_stack.append(self.current_image.copy())
            self.current_image = self.undo_stack.pop()
            self._refresh_canvas()

    def _redo(self):
        if self.redo_stack:
            self.undo_stack.append(self.current_image.copy())
            self.current_image = self.redo_stack.pop()
            self._refresh_canvas()

    # ── Фильтры ───────────────────────────────────────────────────────────────────

    def _apply_grayscale(self):
        if not self.current_image:
            return
        self._push_undo()
        gray = self.current_image.convert("L").convert("RGBA")
        self.current_image = gray
        self._refresh_canvas()

    def _apply_blur(self):
        if not self.current_image:
            return
        self._push_undo()
        self.current_image = self.current_image.filter(ImageFilter.GaussianBlur(radius=2))
        self._refresh_canvas()

    def _apply_edges(self):
        if not self.current_image:
            return
        self._push_undo()
        rgb = self.current_image.convert("RGB")
        edges = rgb.filter(ImageFilter.FIND_EDGES).convert("RGBA")
        self.current_image = edges
        self._refresh_canvas()

    def _apply_sharpen(self):
        if not self.current_image:
            return
        self._push_undo()
        self.current_image = self.current_image.filter(ImageFilter.SHARPEN)
        self._refresh_canvas()

    def _apply_brightness_contrast(self):
        if not self.original_image:
            return
        b = self.brightness_var.get()
        c = self.contrast_var.get()
        img = self.original_image.copy()
        img = ImageEnhance.Brightness(img).enhance(b)
        img = ImageEnhance.Contrast(img).enhance(c)
        self.current_image = img
        self._refresh_canvas()

    # ── Трансформации ────────────────────────────────────────────────────────────

    def _rotate(self):
        if not self.current_image:
            return
        self._push_undo()
        self.current_image = self.current_image.rotate(-90, expand=True)
        self._refresh_canvas()

    def _flip_h(self):
        if not self.current_image:
            return
        self._push_undo()
        self.current_image = self.current_image.transpose(Image.FLIP_LEFT_RIGHT)
        self._refresh_canvas()

    def _flip_v(self):
        if not self.current_image:
            return
        self._push_undo()
        self.current_image = self.current_image.transpose(Image.FLIP_TOP_BOTTOM)
        self._refresh_canvas()

    def _resize(self):
        if not self.current_image:
            return
        try:
            w = int(self.resize_w.get())
            h = int(self.resize_h.get())
        except ValueError:
            show_error("Некорректный ввод", "Введите целые значения ширины и высоты.")
            return
        self._push_undo()
        self.current_image = self.current_image.resize((w, h), Image.LANCZOS)
        self._refresh_canvas()

    # ── Инструменты рисования ─────────────────────────────────────────────────────

    def _set_draw_mode(self, mode: str):
        self.draw_mode = mode
        self.status_var.set(f"Режим рисования: {mode}  |  Щёлкните на изображении")

    def _pick_color(self):
        color = colorchooser.askcolor(self.draw_color)[1]
        if color:
            self.draw_color = color

    def _on_canvas_press(self, event):
        self.draw_start = (event.x, event.y)

    def _on_canvas_release(self, event):
        if not self.draw_mode or self.current_image is None or self.draw_start is None:
            return
        x0, y0 = self.draw_start
        x1, y1 = event.x, event.y

        # Пересчёт координат холста → координаты изображения
        cw = self.canvas.winfo_width()
        ch = self.canvas.winfo_height()
        iw, ih = self.current_image.size
        scale = min(cw / iw, ch / ih)
        off_x = (cw - iw * scale) / 2
        off_y = (ch - ih * scale) / 2
        ix0 = int((x0 - off_x) / scale)
        iy0 = int((y0 - off_y) / scale)
        ix1 = int((x1 - off_x) / scale)
        iy1 = int((y1 - off_y) / scale)

        self._push_undo()
        draw = ImageDraw.Draw(self.current_image)
        color = self.draw_color

        if self.draw_mode == "rect":
            draw.rectangle([ix0, iy0, ix1, iy1], outline=color, width=3)
        elif self.draw_mode == "circle":
            draw.ellipse([ix0, iy0, ix1, iy1], outline=color, width=3)
        elif self.draw_mode == "text":
            draw.text((ix0, iy0), "Пример текста", fill=color)

        self._refresh_canvas()


# ═════════════════════════════════════════════════════════════════════════════
# ВКЛАДКА АУДИО
# ═════════════════════════════════════════════════════════════════════════════

class AudioTab(tk.Frame):
    """Загрузка аудио, воспроизведение, визуализация и редактирование."""

    def __init__(self, parent):
        super().__init__(parent, bg=COLORS["bg"])
        self.audio_path: str | None = None
        self.audio_segment: "AudioSegment | None" = None
        self.playing_thread = None
        self._build_ui()

    def _build_ui(self):
        # Левая панель управления
        ctrl = styled_frame(self, width=220)
        ctrl.pack(side=tk.LEFT, fill=tk.Y, padx=(10, 5), pady=10)
        ctrl.pack_propagate(False)

        styled_label(ctrl, "ОБРАБОТКА АУДИО", size=11, bold=True,
                     color=COLORS["highlight"]).pack(pady=(10, 5))

        styled_button(ctrl, "📂 Загрузить аудио", self._load_audio, accent=True).pack(fill=tk.X, padx=8, pady=2)

        ttk.Separator(ctrl, orient=tk.HORIZONTAL).pack(fill=tk.X, padx=8, pady=8)

        styled_label(ctrl, "Воспроизведение", bold=True).pack(anchor=tk.W, padx=10)
        styled_button(ctrl, "▶ Воспроизвести", self._play_audio).pack(fill=tk.X, padx=8, pady=2)
        styled_button(ctrl, "⏹ Остановить", self._stop_audio).pack(fill=tk.X, padx=8, pady=2)

        ttk.Separator(ctrl, orient=tk.HORIZONTAL).pack(fill=tk.X, padx=8, pady=8)

        styled_label(ctrl, "Громкость (смещение в дБ)", bold=True).pack(anchor=tk.W, padx=10)
        self.volume_var = tk.DoubleVar(value=0)
        tk.Scale(ctrl, from_=-20, to=20, resolution=1, orient=tk.HORIZONTAL,
                 variable=self.volume_var,
                 bg=COLORS["panel"], fg=COLORS["text"],
                 highlightbackground=COLORS["panel"], troughcolor=COLORS["bg"]
                 ).pack(fill=tk.X, padx=8)

        styled_label(ctrl, "Множитель скорости", bold=True).pack(anchor=tk.W, padx=10)
        self.speed_var = tk.DoubleVar(value=1.0)
        tk.Scale(ctrl, from_=0.5, to=3.0, resolution=0.1, orient=tk.HORIZONTAL,
                 variable=self.speed_var,
                 bg=COLORS["panel"], fg=COLORS["text"],
                 highlightbackground=COLORS["panel"], troughcolor=COLORS["bg"]
                 ).pack(fill=tk.X, padx=8)

        ttk.Separator(ctrl, orient=tk.HORIZONTAL).pack(fill=tk.X, padx=8, pady=8)

        # Обрезка
        styled_label(ctrl, "Обрезка (секунды)", bold=True).pack(anchor=tk.W, padx=10)
        trim_frame = styled_frame(ctrl)
        trim_frame.pack(fill=tk.X, padx=8, pady=4)
        styled_label(trim_frame, "Начало:", size=9).pack(side=tk.LEFT)
        self.trim_start = tk.Entry(trim_frame, width=5, bg=COLORS["bg"], fg=COLORS["text"],
                                   insertbackground=COLORS["text"])
        self.trim_start.insert(0, "0")
        self.trim_start.pack(side=tk.LEFT, padx=2)
        styled_label(trim_frame, "Конец:", size=9).pack(side=tk.LEFT)
        self.trim_end = tk.Entry(trim_frame, width=5, bg=COLORS["bg"], fg=COLORS["text"],
                                 insertbackground=COLORS["text"])
        self.trim_end.insert(0, "10")
        self.trim_end.pack(side=tk.LEFT, padx=2)
        styled_button(ctrl, "✂ Обрезать", self._trim_audio).pack(fill=tk.X, padx=8, pady=2)

        ttk.Separator(ctrl, orient=tk.HORIZONTAL).pack(fill=tk.X, padx=8, pady=8)

        # Экспорт
        styled_label(ctrl, "Формат экспорта", bold=True).pack(anchor=tk.W, padx=10)
        self.export_fmt = tk.StringVar(value="wav")
        for fmt in ("wav", "mp3", "ogg"):
            tk.Radiobutton(ctrl, text=fmt.upper(), variable=self.export_fmt, value=fmt,
                           bg=COLORS["panel"], fg=COLORS["text"],
                           activebackground=COLORS["panel"], selectcolor=COLORS["accent"]
                           ).pack(anchor=tk.W, padx=20)
        styled_button(ctrl, "📤 Экспортировать", self._export_audio, accent=True).pack(fill=tk.X, padx=8, pady=4)

        # Прогресс
        self.progress = make_progress(ctrl)
        self.progress.pack(fill=tk.X, padx=8, pady=4)

        # Правая область — визуализация
        viz_frame = tk.Frame(self, bg=COLORS["bg"])
        viz_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(5, 10), pady=10)

        self.status_var = tk.StringVar(value="Загрузите аудиофайл")
        tk.Label(viz_frame, textvariable=self.status_var,
                 bg=COLORS["bg"], fg=COLORS["subtext"], font=("Segoe UI", 9)).pack(pady=(0, 4))

        if MPL_AVAILABLE:
            self.fig = Figure(figsize=(8, 5), facecolor=COLORS["bg"])
            self.ax_wave = self.fig.add_subplot(211)
            self.ax_spec = self.fig.add_subplot(212)
            for ax in (self.ax_wave, self.ax_spec):
                ax.set_facecolor(COLORS["panel"])
                for spine in ax.spines.values():
                    spine.set_color(COLORS["border"])
                ax.tick_params(colors=COLORS["subtext"])
            self.canvas_mpl = FigureCanvasTkAgg(self.fig, master=viz_frame)
            self.canvas_mpl.get_tk_widget().pack(fill=tk.BOTH, expand=True)
        else:
            tk.Label(viz_frame, text="matplotlib не установлена — визуализация недоступна",
                     bg=COLORS["bg"], fg=COLORS["warning"]).pack(expand=True)

    # ── Вспомогательные методы ───────────────────────────────────────────────────

    def _load_audio(self, path: str | None = None):
        if not PYDUB_AVAILABLE:
            show_error("Отсутствует библиотека", "Требуется pydub.\nУстановите: pip install pydub")
            return
        if path is None:
            path = filedialog.askopenfilename(
                title="Открыть аудио",
                filetypes=[("Аудио", "*.mp3 *.wav *.ogg *.flac *.aac"), ("Все файлы", "*.*")]
            )
        if not path:
            return
        try:
            self.audio_path = path
            self.audio_segment = AudioSegment.from_file(path)
            dur = len(self.audio_segment) / 1000
            self.status_var.set(
                f"{Path(path).name}  |  {self.audio_segment.channels} канала  "
                f"|  {self.audio_segment.frame_rate} Гц  |  {dur:.1f} с"
            )
            self.trim_end.delete(0, tk.END)
            self.trim_end.insert(0, str(int(dur)))
            self._visualize()
        except Exception as e:
            show_error("Ошибка загрузки", str(e))

    def _visualize(self):
        if not (MPL_AVAILABLE and NUMPY_AVAILABLE and self.audio_segment):
            return
        try:
            samples = np.array(self.audio_segment.get_array_of_samples(), dtype=float)
            if self.audio_segment.channels == 2:
                samples = samples[::2]  # берём левый канал
            sr = self.audio_segment.frame_rate
            t = np.linspace(0, len(samples) / sr, len(samples))

            self.ax_wave.clear()
            self.ax_wave.plot(t, samples, color=COLORS["highlight"], linewidth=0.4)
            self.ax_wave.set_title("Форма волны", color=COLORS["text"])
            self.ax_wave.set_xlabel("Время (с)", color=COLORS["subtext"])
            self.ax_wave.set_facecolor(COLORS["panel"])

            # Спектрограмма
            self.ax_spec.clear()
            ds = samples[::4]  # прореживание для скорости
            self.ax_spec.specgram(ds, Fs=sr // 4, cmap="plasma")
            self.ax_spec.set_title("Спектрограмма", color=COLORS["text"])
            self.ax_spec.set_xlabel("Время (с)", color=COLORS["subtext"])
            self.ax_spec.set_ylabel("Частота (Гц)", color=COLORS["subtext"])
            self.ax_spec.set_facecolor(COLORS["panel"])

            for ax in (self.ax_wave, self.ax_spec):
                ax.tick_params(colors=COLORS["subtext"])
                for sp in ax.spines.values():
                    sp.set_color(COLORS["border"])

            self.fig.tight_layout()
            self.canvas_mpl.draw()
        except Exception as e:
            print(f"Ошибка визуализации: {e}")

    def _play_audio(self):
        if not self.audio_segment:
            return show_error("Нет аудио", "Сначала загрузите аудиофайл.")
        def _worker():
            try:
                seg = self.audio_segment + self.volume_var.get()
                speed = self.speed_var.get()
                if speed != 1.0:
                    seg = seg._spawn(seg.raw_data, overrides={
                        "frame_rate": int(seg.frame_rate * speed)
                    }).set_frame_rate(seg.frame_rate)
                pydub_play(seg)
            except Exception as e:
                print(f"Ошибка воспроизведения: {e}")
        self.playing_thread = run_in_thread(_worker)

    def _stop_audio(self):
        if SD_AVAILABLE:
            sd.stop()

    def _trim_audio(self):
        if not self.audio_segment:
            return
        try:
            start = float(self.trim_start.get()) * 1000
            end = float(self.trim_end.get()) * 1000
            self.audio_segment = self.audio_segment[start:end]
            self.status_var.set(f"Обрезано до {(end-start)/1000:.1f} с")
            self._visualize()
        except ValueError:
            show_error("Некорректный ввод", "Введите числовые значения начала и конца.")

    def _export_audio(self):
        if not self.audio_segment:
            return show_error("Нет аудио", "Сначала загрузите аудиофайл.")
        fmt = self.export_fmt.get()
        path = filedialog.asksaveasfilename(defaultextension=f".{fmt}",
                                            filetypes=[(fmt.upper(), f"*.{fmt}")])
        if not path:
            return
        def _worker():
            try:
                self.progress["value"] = 30
                seg = self.audio_segment + self.volume_var.get()
                self.progress["value"] = 70
                seg.export(path, format=fmt)
                self.progress["value"] = 100
                self.status_var.set(f"Экспортировано → {Path(path).name}")
            except Exception as e:
                show_error("Ошибка экспорта", str(e))
            finally:
                self.after(2000, lambda: self.progress.configure(value=0))
        run_in_thread(_worker)


# ═════════════════════════════════════════════════════════════════════════════
# ВКЛАДКА ВИДЕО
# ═════════════════════════════════════════════════════════════════════════════

class VideoTab(tk.Frame):
    """Загрузка видео, извлечение кадров, фильтрация, обрезка и экспорт."""

    def __init__(self, parent):
        super().__init__(parent, bg=COLORS["bg"])
        self.video_path: str | None = None
        self.clip = None          # moviepy VideoFileClip
        self.current_frame = None # PIL Image текущего кадра для предпросмотра
        self.display_photo = None
        self._build_ui()

    def _build_ui(self):
        ctrl = styled_frame(self, width=230)
        ctrl.pack(side=tk.LEFT, fill=tk.Y, padx=(10, 5), pady=10)
        ctrl.pack_propagate(False)

        styled_label(ctrl, "ОБРАБОТКА ВИДЕО", size=11, bold=True,
                     color=COLORS["highlight"]).pack(pady=(10, 5))

        styled_button(ctrl, "📂 Загрузить видео", self._load_video, accent=True).pack(fill=tk.X, padx=8, pady=2)

        ttk.Separator(ctrl, orient=tk.HORIZONTAL).pack(fill=tk.X, padx=8, pady=8)

        # Предпросмотр кадра
        styled_label(ctrl, "Предпросмотр кадра (секунда)", bold=True).pack(anchor=tk.W, padx=10)
        self.seek_var = tk.DoubleVar(value=0)
        self.seek_scale = tk.Scale(ctrl, from_=0, to=100, resolution=0.1, orient=tk.HORIZONTAL,
                                   variable=self.seek_var,
                                   bg=COLORS["panel"], fg=COLORS["text"],
                                   highlightbackground=COLORS["panel"], troughcolor=COLORS["bg"],
                                   command=self._preview_frame)
        self.seek_scale.pack(fill=tk.X, padx=8)
        styled_button(ctrl, "📷 Извлечь кадр", self._extract_frame).pack(fill=tk.X, padx=8, pady=2)

        ttk.Separator(ctrl, orient=tk.HORIZONTAL).pack(fill=tk.X, padx=8, pady=8)

        # Фильтры
        styled_label(ctrl, "Применить фильтр ко всем кадрам", bold=True).pack(anchor=tk.W, padx=10)
        self.filter_var = tk.StringVar(value="none")
        filters = [("нет", "none"), ("оттенки серого", "grayscale"), ("размытие", "blur"), ("границы", "edges")]
        for text, val in filters:
            tk.Radiobutton(ctrl, text=text, variable=self.filter_var, value=val,
                           bg=COLORS["panel"], fg=COLORS["text"],
                           activebackground=COLORS["panel"], selectcolor=COLORS["accent"]
                           ).pack(anchor=tk.W, padx=20)

        ttk.Separator(ctrl, orient=tk.HORIZONTAL).pack(fill=tk.X, padx=8, pady=8)

        # Обрезка
        styled_label(ctrl, "Обрезка (секунды)", bold=True).pack(anchor=tk.W, padx=10)
        tf = styled_frame(ctrl)
        tf.pack(fill=tk.X, padx=8, pady=4)
        styled_label(tf, "Начало:", size=9).pack(side=tk.LEFT)
        self.v_start = tk.Entry(tf, width=5, bg=COLORS["bg"], fg=COLORS["text"],
                                insertbackground=COLORS["text"])
        self.v_start.insert(0, "0")
        self.v_start.pack(side=tk.LEFT, padx=2)
        styled_label(tf, "Конец:", size=9).pack(side=tk.LEFT)
        self.v_end = tk.Entry(tf, width=5, bg=COLORS["bg"], fg=COLORS["text"],
                              insertbackground=COLORS["text"])
        self.v_end.insert(0, "10")
        self.v_end.pack(side=tk.LEFT, padx=2)

        # Скорость
        styled_label(ctrl, "Множитель скорости", bold=True).pack(anchor=tk.W, padx=10)
        self.vspeed_var = tk.DoubleVar(value=1.0)
        tk.Scale(ctrl, from_=0.25, to=4.0, resolution=0.25, orient=tk.HORIZONTAL,
                 variable=self.vspeed_var,
                 bg=COLORS["panel"], fg=COLORS["text"],
                 highlightbackground=COLORS["panel"], troughcolor=COLORS["bg"]
                 ).pack(fill=tk.X, padx=8)

        # Аудиодорожка
        styled_label(ctrl, "Добавить аудиодорожку (опционально)", bold=True).pack(anchor=tk.W, padx=10)
        af = styled_frame(ctrl)
        af.pack(fill=tk.X, padx=8, pady=2)
        self.audio_track_path = tk.StringVar(value="")
        tk.Entry(af, textvariable=self.audio_track_path, bg=COLORS["bg"], fg=COLORS["text"],
                 insertbackground=COLORS["text"], width=14).pack(side=tk.LEFT)
        styled_button(af, "…", self._pick_audio_track).pack(side=tk.LEFT, padx=2)

        ttk.Separator(ctrl, orient=tk.HORIZONTAL).pack(fill=tk.X, padx=8, pady=8)

        styled_button(ctrl, "📤 Экспортировать MP4", self._export_video, accent=True).pack(fill=tk.X, padx=8, pady=2)

        self.progress = make_progress(ctrl)
        self.progress.pack(fill=tk.X, padx=8, pady=4)

        # Правая область — холст
        right = tk.Frame(self, bg=COLORS["bg"])
        right.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(5, 10), pady=10)

        self.status_var = tk.StringVar(value="Загрузите видеофайл")
        tk.Label(right, textvariable=self.status_var,
                 bg=COLORS["bg"], fg=COLORS["subtext"], font=("Segoe UI", 9)).pack(pady=(0, 4))

        self.canvas = tk.Canvas(right, bg=COLORS["bg"],
                                highlightbackground=COLORS["border"], highlightthickness=1)
        self.canvas.pack(fill=tk.BOTH, expand=True)

    # ── Ввод/вывод файлов ───────────────────────────────────────────────────────

    def _load_video(self):
        if not MOVIEPY_AVAILABLE:
            show_error("Отсутствует библиотека", "Требуется moviepy.\nУстановите: pip install moviepy")
            return
        path = filedialog.askopenfilename(
            title="Открыть видео",
            filetypes=[("Видео", "*.mp4 *.avi *.mov *.mkv *.webm"), ("Все файлы", "*.*")]
        )
        if not path:
            return
        try:
            if self.clip:
                self.clip.close()
            self.video_path = path
            self.clip = VideoFileClip(path)
            dur = self.clip.duration
            self.seek_scale.configure(to=dur)
            self.v_end.delete(0, tk.END)
            self.v_end.insert(0, str(int(dur)))
            self.status_var.set(
                f"{Path(path).name}  |  {self.clip.w}×{self.clip.h}  "
                f"|  {self.clip.fps:.1f} к/с  |  {dur:.1f} с"
            )
            self._preview_frame(0)
        except Exception as e:
            show_error("Ошибка загрузки", str(e))

    def _preview_frame(self, t=None):
        if not (self.clip and PIL_AVAILABLE):
            return
        try:
            t = float(self.seek_var.get()) if t is None else float(t)
            t = min(t, self.clip.duration - 0.01)
            frame_np = self.clip.get_frame(t)
            pil_img = Image.fromarray(frame_np)
            cw = self.canvas.winfo_width() or 800
            ch = self.canvas.winfo_height() or 500
            pil_img.thumbnail((cw, ch), Image.LANCZOS)
            self.current_frame = pil_img
            self.display_photo = ImageTk.PhotoImage(pil_img)
            self.canvas.delete("all")
            self.canvas.create_image(cw // 2, ch // 2, anchor=tk.CENTER, image=self.display_photo)
        except Exception as e:
            print(f"Ошибка предпросмотра кадра: {e}")

    def _extract_frame(self):
        if not self.current_frame:
            return show_error("Нет кадра", "Сначала загрузите видео и выберите кадр.")
        path = filedialog.asksaveasfilename(defaultextension=".png",
                                            filetypes=[("PNG", "*.png"), ("JPEG", "*.jpg")])
        if path:
            self.current_frame.save(path)
            show_info("Сохранено", f"Кадр сохранён в:\n{path}")

    def _pick_audio_track(self):
        path = filedialog.askopenfilename(
            filetypes=[("Аудио", "*.mp3 *.wav *.ogg *.aac"), ("Все файлы", "*.*")]
        )
        if path:
            self.audio_track_path.set(path)

    def _apply_frame_filter(self, frame_np):
        """Применяет выбранный фильтр к кадру (numpy массив H×W×3)."""
        flt = self.filter_var.get()
        if flt == "none":
            return frame_np
        if not CV2_AVAILABLE:
            return frame_np
        if flt == "grayscale":
            gray = cv2.cvtColor(frame_np, cv2.COLOR_RGB2GRAY)
            return cv2.cvtColor(gray, cv2.COLOR_GRAY2RGB)
        if flt == "blur":
            return cv2.GaussianBlur(frame_np, (15, 15), 0)
        if flt == "edges":
            gray = cv2.cvtColor(frame_np, cv2.COLOR_RGB2GRAY)
            edges = cv2.Canny(gray, 100, 200)
            return cv2.cvtColor(edges, cv2.COLOR_GRAY2RGB)
        return frame_np

    def _export_video(self):
        if not self.clip:
            return show_error("Нет видео", "Сначала загрузите видео.")
        if not MOVIEPY_AVAILABLE:
            return show_error("Отсутствует библиотека", "Требуется moviepy.")
        path = filedialog.asksaveasfilename(defaultextension=".mp4",
                                            filetypes=[("MP4", "*.mp4")])
        if not path:
            return

        def _worker():
            try:
                self.progress["value"] = 10
                start = float(self.v_start.get())
                end = float(self.v_end.get())
                speed = self.vspeed_var.get()

                sub = self.clip.subclip(start, end)
                if speed != 1.0:
                    sub = sub.speedx(speed)

                # Применяем фильтр к кадрам
                flt = self.filter_var.get()
                if flt != "none" and CV2_AVAILABLE:
                    sub = sub.fl_image(self._apply_frame_filter)

                self.progress["value"] = 40

                # Опционально заменяем аудиодорожку
                audio_path = self.audio_track_path.get().strip()
                if audio_path and os.path.isfile(audio_path):
                    new_audio = AudioFileClip(audio_path).subclip(0, sub.duration)
                    sub = sub.set_audio(new_audio)

                self.progress["value"] = 60
                sub.write_videofile(path, codec="libx264", audio_codec="aac",
                                    logger=None)
                self.progress["value"] = 100
                self.status_var.set(f"Экспортировано → {Path(path).name}")
                show_info("Готово", f"Видео сохранено в:\n{path}")
            except Exception as e:
                show_error("Ошибка экспорта", traceback.format_exc())
            finally:
                self.after(3000, lambda: self.progress.configure(value=0))

        run_in_thread(_worker)


# ═════════════════════════════════════════════════════════════════════════════
# ГЛАВНОЕ ОКНО ПРИЛОЖЕНИЯ
# ═════════════════════════════════════════════════════════════════════════════

class MultimediaApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Мультимедиа Процессор")
        self.geometry("1200x750")
        self.minsize(900, 600)
        self.configure(bg=COLORS["bg"])

        self._apply_style()
        self._build_header()
        self._build_tabs()

    def _apply_style(self):
        style = ttk.Style(self)
        style.theme_use("clam")
        style.configure("TNotebook", background=COLORS["bg"], borderwidth=0)
        style.configure("TNotebook.Tab",
                        background=COLORS["accent"], foreground=COLORS["text"],
                        padding=[16, 8], font=("Segoe UI", 10, "bold"))
        style.map("TNotebook.Tab",
                  background=[("selected", COLORS["highlight"])],
                  foreground=[("selected", COLORS["text"])])
        style.configure("TSeparator", background=COLORS["border"])

    def _build_header(self):
        hdr = tk.Frame(self, bg=COLORS["panel"], height=50)
        hdr.pack(fill=tk.X)
        hdr.pack_propagate(False)
        tk.Label(hdr, text="🎬  МУЛЬТИМЕДИА ПРОЦЕССОР",
                 bg=COLORS["panel"], fg=COLORS["highlight"],
                 font=("Segoe UI", 14, "bold")).pack(side=tk.LEFT, padx=20)
        tk.Label(hdr, text="Изображения · Аудио · Видео",
                 bg=COLORS["panel"], fg=COLORS["subtext"],
                 font=("Segoe UI", 10)).pack(side=tk.LEFT)

        # Индикаторы наличия библиотек
        deps = [
            ("Pillow", PIL_AVAILABLE),
            ("OpenCV", CV2_AVAILABLE),
            ("pydub", PYDUB_AVAILABLE),
            ("moviepy", MOVIEPY_AVAILABLE),
            ("matplotlib", MPL_AVAILABLE),
            ("numpy", NUMPY_AVAILABLE),
        ]
        for name, ok in deps:
            color = COLORS["success"] if ok else COLORS["warning"]
            symbol = "✓" if ok else "✗"
            tk.Label(hdr, text=f" {symbol} {name} ",
                     bg=COLORS["panel"], fg=color,
                     font=("Segoe UI", 8)).pack(side=tk.RIGHT, padx=2)

    def _build_tabs(self):
        nb = ttk.Notebook(self)
        nb.pack(fill=tk.BOTH, expand=True, padx=10, pady=(5, 10))

        self.img_tab = ImageTab(nb)
        self.aud_tab = AudioTab(nb)
        self.vid_tab = VideoTab(nb)

        nb.add(self.img_tab, text="🖼  Изображения")
        nb.add(self.aud_tab, text="🎵  Аудио")
        nb.add(self.vid_tab, text="🎬  Видео")


# ─────────────────────────────────────────────────────────────────────────────

def main():
    app = MultimediaApp()
    app.mainloop()


if __name__ == "__main__":
    main()