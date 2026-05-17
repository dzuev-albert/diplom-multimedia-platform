# Multimedia Processor

A cross-platform desktop application for image, audio, and video processing built with Python + Tkinter.

---

## Quick Start

### 1 — Clone / download the files
```
multimedia_processor/
├── main.py
├── requirements.txt
└── README.md
```

### 2 — Create a virtual environment (recommended)
```bash
python -m venv venv

# Activate
# Windows:
venv\Scripts\activate
# macOS / Linux:
source venv/bin/activate
```

### 3 — Install Python dependencies
```bash
pip install -r requirements.txt
```

### 4 — Install ffmpeg (required for audio & video)
| Platform | Command |
|----------|---------|
| macOS    | `brew install ffmpeg` |
| Ubuntu   | `sudo apt install ffmpeg` |
| Windows  | Download from https://ffmpeg.org and add `bin/` to PATH |

### 5 — Run
```bash
python main.py
```

Or in **PyCharm**: open the project folder, right-click `main.py` → *Run 'main'*.

---

## Features

### 🖼 Images
- Load / save JPEG, PNG, BMP
- Filters: grayscale, blur, edge detection, sharpen
- Brightness & contrast sliders (live preview)
- Rotate 90°, flip horizontal / vertical
- Resize to custom dimensions
- Drawing tools: rectangle, circle, text overlay with colour picker
- Full undo / redo stack

### 🎵 Audio
- Load MP3, WAV, OGG, FLAC
- Play / stop with volume (dB) and speed controls
- Waveform and spectrogram visualisation
- Trim by start/end second
- Export to WAV / MP3 / OGG

### 🎬 Video
- Load MP4, AVI, MOV, MKV
- Frame scrubber with live preview
- Extract any frame as PNG/JPEG
- Apply grayscale / blur / edge-detection to all frames on export
- Trim by start/end second
- Playback speed multiplier
- Replace / add audio track
- Export to MP4 (H.264 + AAC)

---

## Dependency notes

| Library      | Purpose                          | Required? |
|--------------|----------------------------------|-----------|
| Pillow       | Image I/O, filters, drawing      | Yes (images) |
| opencv-python| Frame filters for video          | Recommended |
| numpy        | Audio sample arrays              | Yes (audio viz) |
| matplotlib   | Waveform + spectrogram plots     | Yes (audio viz) |
| scipy        | WAV reading, signal processing   | Yes (audio viz) |
| pydub        | Audio load, edit, export         | Yes (audio) |
| sounddevice  | Stop playback                    | Optional |
| moviepy      | Video load, edit, export         | Yes (video) |

The app starts even if some libraries are missing — a ✓/✗ status row is shown in the header so you know which features are active.

---

## Troubleshooting

**`No module named 'tkinter'` on Linux**
```bash
sudo apt install python3-tk
```

**Audio won't play / export**
Make sure `ffmpeg` is installed and on your PATH (`ffmpeg -version` in a terminal).

**moviepy import warning about imageio**
```bash
pip install imageio[ffmpeg]
```

**Windows: `sounddevice` install fails**
Install the Microsoft C++ Build Tools or use the pre-built wheel:
```bash
pip install sounddevice --only-binary=:all:
```
