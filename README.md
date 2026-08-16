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

## 🌟 Master Page Catalog (10 Views)

1. [index.html](file:///Users/rifaterdemsahin/projects/aug-video-animation-2/index.html) — Landing page, 16-stage pipeline overview cards, and global navigation.
2. [research.html](file:///Users/rifaterdemsahin/projects/aug-video-animation-2/research.html) — Master Shotlist Studio, Second Brain Vault Retrieval, and Video Upload.
3. [timeline.html](file:///Users/rifaterdemsahin/projects/aug-video-animation-2/timeline.html) — Gantt-style horizontal visual timeline sequencer.
4. [shotlist.html](file:///Users/rifaterdemsahin/projects/aug-video-animation-2/shotlist.html) — High-density data grid with sorting and CSV/JSON export.
5. [scenes.html](file:///Users/rifaterdemsahin/projects/aug-video-animation-2/scenes.html) — Scene breakdown and narrative structure editor for 6 main scenes.
6. [voice_over.html](file:///Users/rifaterdemsahin/projects/aug-video-animation-2/voice_over.html) — Voiceover teleprompter with WPM meter and recording checklist.
7. [script_guru.html](file:///Users/rifaterdemsahin/projects/aug-video-animation-2/script_guru.html) — AI script coach, pacing diagnostics, and engagement hooks.
8. [gallery.html](file:///Users/rifaterdemsahin/projects/aug-video-animation-2/gallery.html) — Visual catalog of 16-stage stills and 26 Flow video clips.
9. [tactic.html](file:///Users/rifaterdemsahin/projects/aug-video-animation-2/tactic.html) — Production tactics, SOPs, DaVinci Resolve settings, and quality gates.
10. [analysis.html](file:///Users/rifaterdemsahin/projects/aug-video-animation-2/analysis.html) — Video production analytics and audience retention simulation.

---

## ✍️ Signature Outro
Designed and engineered with Roger Rabbit style signature signoff by **Rifat Erdem Sahin**.