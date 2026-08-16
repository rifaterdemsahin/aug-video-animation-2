# August Video Animation #2 — Reverse Response Video Production Studio

> **Project:** `aug-video-animation-2`  
> **Author:** Rifat Erdem Sahin / DeliveryPilot  
> **Type:** Multimedia Production Studio & Web Workbench

---

## 🚀 Quickstart

### 1. Launch Local Development Server
```bash
python3 server.py
```
Visit the studio in your browser: **http://127.0.0.1:8765** (or port assigned).

### 2. Run Automation Pipelines
```bash
# Split large videos (>24MB) into Git-compliant binary chunks
python3 split_large_videos.py 3_Simulation/rawexport/sample_raw_master.mp4

# Rejoin split binary chunks with SHA-256 verification
python3 rejoin_large_videos.py

# Extract and AI-rewrite voiceover scripts for high retention
python3 extract_and_rewrite_vo.py --rewrite
```

### 3. Containerized / Fly.io Deployment
```bash
# Build & run Docker container
docker build -t aug-video-studio .
docker run -p 8080:8080 aug-video-studio

# Deploy to Fly.io
fly deploy
```

---

## 🌟 Master Page Catalog (Logical Production Workflow) 🎬

1. [research.html](file:///Users/rifaterdemsahin/projects/aug-video-animation-2/research.html) — 🎬 **1. Research & Master Studio:** Reverse response reference video breakdown, manually triggered Second Brain vault search & note injection, vertical shot cards, and video upload.
2. [script_guru.html](file:///Users/rifaterdemsahin/projects/aug-video-animation-2/script_guru.html) — 🧠 **2. Script Guru:** AI script coach, pacing diagnostics, reading ease, and engagement hooks.
3. [scenes.html](file:///Users/rifaterdemsahin/projects/aug-video-animation-2/scenes.html) — 📑 **3. Scenes:** Scene narrative architecture for 6 main scenes, target word counts, and color themes.
4. [shotlist.html](file:///Users/rifaterdemsahin/projects/aug-video-animation-2/shotlist.html) — 📊 **4. Shotlist:** High-density data grid with sorting, inline editing, and CSV/JSON export.
5. [timeline.html](file:///Users/rifaterdemsahin/projects/aug-video-animation-2/timeline.html) — ⏱️ **5. Timeline:** Gantt-style horizontal visual timeline sequencer and scrubber.
6. [voice_over.html](file:///Users/rifaterdemsahin/projects/aug-video-animation-2/voice_over.html) — 🎙️ **6. Voiceover:** Teleprompter with WPM cadence meter and recording checklist.
7. [gallery.html](file:///Users/rifaterdemsahin/projects/aug-video-animation-2/gallery.html) — 🖼️ **7. Gallery:** Visual asset catalog of 16-stage slide stills and 26 Flow video clips.
8. [tactic.html](file:///Users/rifaterdemsahin/projects/aug-video-animation-2/tactic.html) — ⚔️ **8. Tactics:** Production SOPs, DaVinci Resolve render presets, and quality gates.
9. [analysis.html](file:///Users/rifaterdemsahin/projects/aug-video-animation-2/analysis.html) — 📈 **9. Analytics:** Video production metrics, pacing distribution, and audience retention curve.
10. [index.html](file:///Users/rifaterdemsahin/projects/aug-video-animation-2/index.html) — 🏠 **10. Overview:** Studio landing page, 16-stage pipeline showcase, and stats.

---

## ✍️ Signature Outro ⭐
Designed and engineered with Roger Rabbit style energetic cartoon signature by **Rifat Erdem Sahin**.