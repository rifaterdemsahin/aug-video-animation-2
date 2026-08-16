# August Video Animation #1 — Complete Reverse-Engineered System Specification

> **Document Version:** 1.0.0  
> **Target Project:** `aug-video-animation-2` ("Reverse Response Video" Video Production Studio & Workbench)  
> **Author / Original Creator:** Rifat Erdem Sahin / DeliveryPilot  
> **Output:** Single-document complete technical specification and blueprint to recreate the entire system from scratch.

---

## Table of Contents

1. [Executive Summary & System Purpose](#1-executive-summary--system-purpose)
2. [High-Level Architecture & Tech Stack](#2-high-level-architecture--tech-stack)
3. [Repository Structure & File Topology](#3-repository-structure--file-topology)
4. [Data Models & Manifest Schemas](#4-data-models--manifest-schemas)
   - 4.1. Images Manifest (`stills/images_manifest.json`)
   - 4.2. Video Flow Manifest (`video_flow/video_flow_manifest.json`)
   - 4.3. Shotlist State Schema (localStorage / Azure Blob)
   - 4.4. Script Document Schema (`_script.md`)
5. [Backend Architecture & REST API Specification](#5-backend-architecture--rest-api-specification)
   - 5.1. Server Architecture (`server.py`)
   - 5.2. REST API Endpoints
   - 5.3. Azure Blob & Key Vault HMAC-SHA256 Implementation
   - 5.4. OpenRouter AI & TTS Integration
   - 5.5. Local Vault Fuzzy Search Indexer
6. [Frontend UI & Web Application Specifications](#6-frontend-ui--web-application-specifications)
   - 6.1. Design System & CSS Token Architecture
   - 6.2. Master Page Catalog (10 Views)
   - 6.3. Client-Side State Synchronization & Offline-First Strategy
7. [Auxiliary Automation & Video Pipelines](#7-auxiliary-automation--video-pipelines)
   - 7.1. Video Chunk Splitter (`split_large_videos.py`)
   - 7.2. Video Chunk Rejointer (`rejoin_large_videos.py`)
   - 7.3. Script Extraction & Voiceover Rewriter (`extract_and_rewrite_vo.py`)
8. [Deployment & Containerization Specification](#8-deployment--containerization-specification)
   - 8.1. Docker Configuration (`Dockerfile`)
   - 8.2. Fly.io Configuration (`fly.toml`)
   - 8.3. GitHub Pages Static Deployment (`.nojekyll`)
9. [Step-by-Step Recreation Blueprint](#9-step-by-step-recreation-blueprint)

---

## 1. Executive Summary & System Purpose

`aug-video-animation-2` is an end-to-end multimedia production studio and interactive web workbench designed to produce a **response reverse video**.
- Response reverse video is reverse engineering a popular video and fitting it to our niche. 

The application bridges the gap between raw pre-production assets (Canva slide decks, Obsidian knowledge bases, 26 Google Flow AI-generated video clips, and voiceover scripts) and final video assembly. It delivers:
1. **Interactive Shotlist & Storyboard Editor**: Visual scene-by-scene editing, tagging, timing calculators, and status tracking.
2. **AI-Powered Script & Voiceover Engine**: Automated text refinement, grammar checking, LLM-based voiceover generation, and Text-to-Speech (TTS) synthesis.
3. **Local Vault Knowledge Retrieval**: Fast inverted index and fuzzy search across local Obsidian/markdown files.
4. **Cloud & Local State Synchronization**: Dual-tier persistence across browser `localStorage` and Azure Blob Storage with automated snapshot backups.
5. **Git-Compliant Large Media Management**: Chunking and reassembly pipeline for video assets exceeding Git/GitHub file size limits (>24MB).

---

## 2. High-Level Architecture & Tech Stack

```
+-----------------------------------------------------------------------------------+
|                                  BROWSER CLIENT                                   |
|  +-----------------------------------------------------------------------------+  |
|  | HTML5 + Vanilla CSS3 (Custom Properties Design System) + ES6+ JavaScript   |  |
|  | - index.html (Landing)             - timeline.html (Sequencer)              |  |
|  | - research.html (Master Studio)    - scenes.html (Scene Editor)             |  |
|  | - shotlist.html (Data Grid)        - voice_over.html (Teleprompter)         |  |
|  | - gallery.html (Asset Browser)     - script_guru.html (AI Coach)            |  |
|  | - tactic.html (SOPs & Checklists)  - analysis.html (Metrics & Pacing)       |  |
|  +-----------------------------------------------------------------------------+  |
|                                        |                                          |
|                     localStorage (Offline State Storage)                         |
+----------------------------------------+------------------------------------------+
                                         | HTTP / REST (Port 8765 or 8080)
+----------------------------------------v------------------------------------------+
|                              PYTHON BACKEND (server.py)                           |
|  - Standard Library only (ThreadingHTTPServer, urllib, hmac, hashlib, subprocess) |
|  - Zero Heavy Framework Dependencies                                              |
|                                                                                   |
|  +-------------------+  +--------------------+  +------------------------------+  |
|  | REST API Router   |  | Inverted Indexer   |  | Azure HMAC-SHA256 Client     |  |
|  | /api/state        |  | Vault Search Engine|  | Blob Storage Put/Get/List    |  |
|  | /api/text, /api/ai|  | (Markdown/Assets)  |  | Key Vault Secret Resolution  |  |
|  +-------------------+  +--------------------+  +------------------------------+  |
+------------+-------------------------+-------------------------+-----------------+
             |                         |                         |
             v                         v                         v
+-----------------------+ +-----------------------+ +-----------------------+
|    OpenRouter.ai /    | |      ElevenLabs /     | |   Azure Blob Storage  |
|      OpenAI API       | |    Gemini TTS Engine  | |   & Azure Key Vault   |
+-----------------------+ +-----------------------+ +-----------------------+
```

### Core Technologies
- **Backend**: Python 3.10+ (Standard Library `http.server.ThreadingHTTPServer`, `urllib.request`, `hmac`, `hashlib`, `json`, `subprocess`).
- **Frontend**: Vanilla HTML5, Vanilla CSS3 (CSS Variables, Flexbox, CSS Grid), Vanilla ES6+ JavaScript. No build step or bundler required.
- **Persistence**: Browser `localStorage`, Azure Blob Storage (`projects/aug-video-animation-1/shotlist/`), JSON files (`images_manifest.json`, `video_flow_manifest.json`).
- **Cloud Integrations**:
  - **Azure Key Vault** (`dp-kv-deliverypilot`): Resolves `OPENROUTER-API-KEY` and `AZURE-STORAGE-CONN-STR`.
  - **Azure Blob Storage**: REST API with HMAC-SHA256 shared key signatures (version `2021-08-06`).
  - **OpenRouter AI / OpenAI**: GPT-4o-mini completion for voiceover grammar and script rewriting.
  - **ElevenLabs / Gemini**: Text-to-speech audio synthesis.
- **Hosting & Deployment**: GitHub Pages (Static frontend mode), Docker (`python:3.11-slim`), Fly.io (`lhr` London region).

---

## 3. Repository Structure & File Topology

```
aug-video-animation-2/
├── .dockerignore                            # Excludes git, cache, raw videos from Docker build
├── .gitignore                               # Ignores large raw files, venvs, caches
├── .nojekyll                                # Disables GitHub Pages Jekyll preprocessing
├── Dockerfile                               # Production container definition (Python 3.11-slim)
├── fly.toml                                 # Fly.io deployment manifest
├── README.md                                # Project summary, visual guide, and quickstart
├── SPECIFICATIONS.md                        # This master reverse-engineered specification
├── _script.md                               # Voiceover seed copy (Flagship Part A + Walkthrough Part B)
├── server.py                                # Local development and production API server
├── extract_and_rewrite_vo.py                # Pipeline script: extracts and rewrites VO
├── split_large_videos.py                    # Splits >24MB videos into GitHub-friendly chunks
├── rejoin_large_videos.py                   # Reassembles split chunks into original video files
├── index.html                               # Landing page and showcase
├── research.html                            # Master shotlist studio & vertical editor
├── timeline.html                            # Horizontal interactive sequencing timeline
├── shotlist.html                            # High-density data grid and table view
├── scenes.html                              # Scene breakdown and structural editor
├── voice_over.html                          # Voiceover teleprompter and recording checklist
├── script_guru.html                         # AI script coach and pacing analysis
├── gallery.html                             # Visual asset catalog & gallery viewer
├── tactic.html                              # Production SOPs and execution tactics
├── analysis.html                            # Narrative arc and retention metrics
├── 3_Simulation/                            # Canva raw exports and audio alignment data
│   ├── canva_voiceovers.jpeg                # Source deck voiceover screenshot
│   ├── rawexport/                           # Uncut master media files
│   └── readme.md                            # Simulation documentation
├── stills/                                  # Production stills categorized by pipeline stage
│   ├── images_manifest.json                 # JSON catalog of all 105+ still images
│   ├── 00_index/                            # Stage 00: Framework index
│   ├── 01_architecture/                     # Stage 01: Architecture diagrams
│   ├── 02_plan/                             # Stage 02: Script deck slides (20 slides)
│   ├── 03_assets/                           # Stage 03: Asset references & vault counts
│   ├── 04_cohort/                           # Stage 04: Cohort & community notes
│   ├── 05_gaps/                             # Stage 05: Concept gaps & knowledge maps
│   ├── 06_assembly/                         # Stage 06: Scene assembly stills
│   ├── 07_polish/                           # Stage 07: Polish dividers
│   ├── 08_refinement/                       # Stage 08: Refinement dividers
│   ├── 09_audio/                            # Stage 09: Audio dividers
│   ├── 10_editcolor/                        # Stage 10: Color grading dividers
│   ├── 11_thumbnail/                        # Stage 11: Thumbnail design assets
│   ├── 12_export/                           # Stage 12: Export parameters
│   ├── 13_metadata/                         # Stage 13: Distribution metadata
│   └── 15_tactics/                          # Stage 15: Editor screenshots & tactics
└── video_flow/                              # 26 Google Flow animated MP4 clips
    ├── NN_first-frame-slug.mp4              # Standardized 1080p MP4 clips
    ├── _first_frames/                       # Extracted JPEG posters for video elements
    └── video_flow_manifest.json             # JSON catalog of all 26 video clips
```

---

## 4. Data Models & Manifest Schemas

### 4.1. Images Manifest Schema (`stills/images_manifest.json`)
An array of objects indexing all static visual assets:

```json
[
  {
    "file": "stills/02_plan/02_plan_00_cover-title.png",
    "stage": "02",
    "stageName": "Plan",
    "caption": "Title card: \"\"",
    "voiceoverDefault": true
  }
]
```
- **`file`** *(string, required)*: Relative path to the image file.
- **`stage`** *(string, required)*: 2-digit zero-padded stage identifier (`00` to `15`).
- **`stageName`** *(string, required)*: Human-readable stage title.
- **`caption`** *(string, required)*: Descriptive caption detailing slide content and intent.
- **`voiceoverDefault`** *(boolean, required)*: Whether this slide corresponds to a spoken voiceover beat.

### 4.2. Video Flow Manifest Schema (`video_flow/video_flow_manifest.json`)
Catalog tracking the 26 AI-generated Google Flow video clips:

```json
{
  "folder": "/path/to/source/video_flow",
  "count": 26,
  "naming": "NN_first-frame-slug.mp4 (slug from OpenRouter vision of first frame)",
  "files": [
    {
      "seq": 1,
      "orig_num": 1,
      "from": "2asset.mp4",
      "slug": "colorful-file-icons-background",
      "to": "01_colorful-file-icons-background.mp4",
      "frame": "01_colorful-file-icons-background.jpg",
      "source_index": 26
    }
  ]
}
```

### 4.3. Shotlist State Schema (localStorage / Azure Blob)
The comprehensive document state persisted across client and cloud:

```json
{
  "version": 1,
  "updatedAt": "2026-08-16T18:00:00.000Z",
  "scenes": [
    {
      "id": "scene-1",
      "number": 1,
      "title": "Hook & Problem Setup",
      "timecodeStart": "0:00",
      "timecodeEnd": "0:15",
      "durationSeconds": 15,
      "targetWordCount": 40,
      "color": "#e74c3c",
      "description": "Chaotic workspace overwhelmed with 46,000 unorganized notes.",
      "shots": [
        {
          "id": "shot-1-1",
          "sceneId": "scene-1",
          "shotNumber": 1,
          "duration": 5.0,
          "stillFile": "stills/06_assembly/06_assembly_00_scene1-2-stills.png",
          "videoFlowFile": "video_flow/01_colorful-file-icons-background.mp4",
          "voiceover": "I was drowning in 46,000 notes across Obsidian.",
          "visualNotes": "Chaotic dark workspace, glowing vault icon swirled by note-icons.",
          "status": "completed",
          "tags": ["hook", "problem", "obsidian"]
        }
      ]
    }
  ],
  "script": {
    "markdown": "# Master Voiceover Script...",
    "wordCount": 475,
    "estimatedDuration": 178
  },
  "checklist": {
    "audioRecorded": true,
    "colorGraded": false,
    "finalExport": false
  }
}
```

---

## 5. Backend Architecture & REST API Specification

### 5.1. Server Architecture (`server.py`)
- **HTTP Engine**: `http.server.ThreadingHTTPServer` with custom request handler overriding `SimpleHTTPRequestHandler`.
- **Large Cookie/Header Handling**: Modifies `http.client._MAXLINE = 1048576` (1MB) and `_MAXHEADERS = 400` to prevent HTTP 431 errors on large client payloads.
- **CORS Support**: `Access-Control-Allow-Origin: *`, supporting `GET`, `POST`, `OPTIONS`.
- **Fallback Port Binding**: Scans candidate ports from `8765` to `8774` (or environment `$PORT`).

### 5.2. REST API Endpoints

#### `GET /api/health`
Returns system status, active LLM model, Azure connectivity, and indexed vault metrics.
- **Response `200 OK`**:
```json
{
  "ok": true,
  "model": "openai/gpt-4o-mini",
  "vault": "/path/to/vault",
  "index_size": 1420,
  "openrouter_key_configured": true,
  "azure": {
    "ok": true,
    "account": "deliverypilotstorage",
    "container": "projects",
    "prefix": "aug-video-animation-1/shotlist",
    "secret": "AZURE-STORAGE-CONN-STR",
    "error": ""
  }
}
```

#### `GET /api/state?blob=<blob_name>`
Retrieves the saved shotlist state from Azure Blob Storage.
- **Query Params**: `blob` (optional; defaults to `latest.json`).
- **Response `200 OK`**: Shotlist JSON object.
- **Response `502 Bad Gateway`**: `{"ok": false, "error": "Reason"}`.

#### `POST /api/state`
Saves the shotlist state to Azure Blob Storage and generates a timestamped backup snapshot.
- **Request Body**:
```json
{
  "state": { /* Shotlist JSON state */ },
  "backup": true
}
```
- **Response `200 OK`**:
```json
{
  "ok": true,
  "latest": "aug-video-animation-1/shotlist/latest.json",
  "backup": "aug-video-animation-1/shotlist/2026-08-16T18-00-00Z.json",
  "bytes": 28412
}
```

#### `GET /api/state/list?limit=20`
Lists historical backup snapshots stored in Azure Blob.
- **Response `200 OK`**:
```json
{
  "ok": true,
  "backups": [
    {
      "name": "aug-video-animation-1/shotlist/2026-08-16T18-00-00Z.json",
      "last_modified": "Sun, 16 Aug 2026 18:00:00 GMT",
      "content_length": 28412
    }
  ]
}
```

#### `GET /api/vault-search?q=<query>&limit=20`
Fuzzy sub-string and token search over indexed markdown and media files in the local vault.
- **Response `200 OK`**:
```json
{
  "ok": true,
  "query": "obsidian",
  "results": [
    {"path": "1_Projects/AI_Second_Brain.md", "score": 0.95},
    {"path": "stills/03_assets/03_assets_01_para-vault-counts.png", "score": 0.82}
  ],
  "index_size": 1420
}
```

#### `POST /api/text`
Executes grammar checking or script rewriting via OpenRouter.
- **Request Body**:
```json
{
  "action": "grammar | rewrite",
  "text": "I was drowning in 46000 notes",
  "model": "openai/gpt-4o-mini"
}
```
- **Response `200 OK`**:
```json
{
  "ok": true,
  "action": "rewrite",
  "text": "I found myself overwhelmed by 46,000 notes...",
  "model": "openai/gpt-4o-mini"
}
```

#### `POST /api/ai/tts`
Generates voiceover audio via ElevenLabs or Gemini audio APIs.
- **Request Body**:
```json
{
  "engine": "elevenlabs",
  "text": "I was drowning in 46,000 notes across Obsidian.",
  "voice_id": "JBFqnCBsd6RMkjVDRZzb"
}
```
- **Response `200 OK`**: `{"ok": true, "audio_url": "...", "duration": 3.4}`.

### 5.3. Azure Blob & Key Vault HMAC-SHA256 Engine
`server.py` implements native Azure Blob Storage REST API communication without requiring the `azure-storage-blob` SDK.
- **Authentication**: Canonicalized headers and resource string hashed with `hmac-sha256(base64_decode(AccountKey), string_to_sign)`.
- **Key Resolution**: Automatically falls back to querying the Azure CLI (`az keyvault secret show`) if environment variables are unset.

---

## 6. Frontend UI & Web Application Specifications

### 6.1. Design System & CSS Token Architecture
All 10 HTML views utilize a cohesive CSS custom-property design system with system fonts, dynamic dark/light theme switching, and responsive viewport sizing.

```css
:root {
  --bg-primary: #0f1117;
  --bg-surface: #181b24;
  --bg-surface-elevated: #222634;
  --border-color: rgba(255, 255, 255, 0.08);
  --text-primary: #f0f3f8;
  --text-secondary: #9ba3b4;
  --text-muted: #626a7e;
  --accent-blue: #3b82f6;
  --accent-purple: #8b5cf6;
  --accent-green: #10b981;
  --accent-red: #ef4444;
  --accent-gold: #f59e0b;
  --font-sans: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
  --font-mono: "SF Mono", "Fira Code", monospace;
  --radius-sm: 4px;
  --radius-md: 8px;
  --radius-lg: 12px;
  --transition-fast: 0.15s ease;
}

[data-theme="light"] {
  --bg-primary: #f8fafc;
  --bg-surface: #ffffff;
  --bg-surface-elevated: #f1f5f9;
  --border-color: rgba(0, 0, 0, 0.08);
  --text-primary: #0f172a;
  --text-secondary: #475569;
  --text-muted: #94a3b8;
}
```

### 6.2. Master Page Catalog (Logical Production Order) 🎬

The application navigation is organized in a deterministic, step-by-step production sequence starting with Research and culminating in the overview dashboard:

| Step & File | Page Title | Primary Utility & Functional Specs |
|---|---|---|
| `🎬 1. research.html` | 🎬 Master Research Studio | **Anchor Step:** Benchmark reference video breakdown second-by-second, **manually triggered Second Brain vault search & note injection**, vertical shot cards, and multimedia uploader. |
| `🧠 2. script_guru.html` | 🧠 Script Guru AI Coach | Spoken cadence analysis, reading level diagnostics, retention hooks evaluator, and AI script optimization. |
| `📑 3. scenes.html` | 📑 Scene Breakdown Editor | Macro narrative architecture for 6 main scenes, target word counts, and color-coded scene envelopes. |
| `📊 4. shotlist.html` | 📊 Shotlist Data Grid | High-density sortable/filterable data table, inline editing, batch metadata tagging, and CSV/JSON export. |
| `⏱️ 5. timeline.html` | ⏱️ Visual Timeline Sequencer | Gantt-style horizontal timeline displaying scenes 1–6, shot duration blocks, audio waveforms, and interactive scrubber. |
| `🎙️ 6. voice_over.html` | 🎙️ Voiceover Teleprompter | Large-type teleprompter with adjustable WPM, speaking cadence meter, and sentence-by-sentence recording checklist. |
| `🖼️ 7. gallery.html` | 🖼️ Media Asset Gallery | Visual catalog of 105+ stills and 26 Flow videos, stage filtering (`00`–`15`), and modal media preview. |
| `⚔️ 8. tactic.html` | ⚔️ Production Tactics & SOPs | Standard Operating Procedures, video export presets, DaVinci Resolve render parameters, and quality gates. |
| `📈 9. analysis.html` | 📈 Video Production Analytics | Runtime breakdown, visual vs. spoken pacing metrics, retention drop-off curve, and tag distribution. |
| `🏠 10. index.html` | 🏠 Overview & Showcase | Hero video player, 16-stage pipeline overview cards, dynamic statistics counters, and global navigation. |

### 6.3. Client-Side State Synchronization & Offline-First Strategy
- **Primary Storage**: Browser `localStorage` (`key = "wiganimation_shotlist_state"`).
- **Cloud Backup**: On-demand and auto-sync triggers dispatch `POST /api/state` with snapshot versioning.
- **Conflict Resolution**: Timestamps (`updatedAt`) are evaluated; UI prompts user if remote version is newer than local state.

---

## 7. Auxiliary Automation & Video Pipelines

### 7.1. Video Chunk Splitter (`split_large_videos.py`)
Splits raw master video files exceeding 24MB into 24MB binary chunks to stay within GitHub repository size constraints.
- **Chunk Size**: `24 * 1024 * 1024` bytes (25,165,824 bytes).
- **Manifest Output**: Generates `split_manifest.json` with SHA-256 verification hashes for both the original file and each chunk.

### 7.2. Video Chunk Rejointer (`rejoin_large_videos.py`)
Cross-platform binary assembler that scans `parts_*` directories, concatenates chunks in sequence, and validates the reconstructed file against the source SHA-256 hash.

### 7.3. Script Extraction & Voiceover Rewriter (`extract_and_rewrite_vo.py`)
Automated pipeline that extracts text from Canva slide deck images using OCR/vision models and formats structured voiceover scripts.

---

## 8. Deployment & Containerization Specification

### 8.1. Dual Deployment Strategy Architecture
The application is engineered with a dual deployment architecture:
1. **GitHub Pages (Serverless Static Mode)**: Instant zero-cost distribution for the frontend studio workbench, reading local assets and using browser `localStorage` with Web Speech API audio synthesis.
2. **Fly.io (Full-Stack Container Mode)**: Production containerized Python server running in the London (`lhr`) region with full REST APIs, live Azure HMAC-SHA256 cloud sync, OpenRouter LLM integration, and direct media upload support.

```
                  +--------------------------------------------------+
                  |               DEVELOPER GIT PUSH                 |
                  +-------------------------+------------------------+
                                            |
                    +-----------------------+-----------------------+
                    |                                               |
                    v                                               v
  +------------------------------------+   +------------------------------------+
  | .github/workflows/deploy-pages.yml |   |  .github/workflows/deploy-fly.yml  |
  +-----------------+------------------+   +-----------------+------------------+
                    |                                        |
                    v                                        v
  +------------------------------------+   +------------------------------------+
  |            GITHUB PAGES            |   |               FLY.IO               |
  |     - Static Studio Workbench      |   |   - Python 3.11 ThreadingHTTPServer|
  |     - Client localStorage Engine   |   |   - Azure HMAC-SHA256 Cloud Sync   |
  |     - Web Speech API TTS           |   |   - OpenRouter AI & Media Uploads  |
  |     - .nojekyll Enabled            |   |   - Docker Container Port 8080     |
  +------------------------------------+   +------------------------------------+
```

### 8.2. GitHub Pages Deployment Specification
- **Configuration & Bypass**: An empty `.nojekyll` file sits at the repository root to bypass Jekyll markdown preprocessing.
- **Workflow File**: `.github/workflows/deploy-pages.yml`
- **Permissions**: `contents: read`, `pages: write`, `id-token: write`.
- **Workflow Action Sequence**:
  1. Check out repository code.
  2. Run `python3 generate_assets.py` to ensure all SVGs and manifest images are populated.
  3. Package and upload pages artifact via `actions/upload-pages-artifact@v3`.
  4. Deploy to GitHub Pages environment via `actions/deploy-pages@v4`.
- **Client Offline Mode**: When running on GitHub Pages without a backend, `app.js` gracefully operates via `localStorage`, disabling cloud calls while retaining full storyboard, prompter, timeline, and audio playback capabilities.

### 8.3. Fly.io Deployment Specification
- **Application Manifest (`fly.toml`)**:
  - `app = "aug-video-animation-2"`
  - `primary_region = "lhr"`
  - `internal_port = 8080`
  - `auto_stop_machines = "stop"`, `min_machines_running = 1`
  - Resource VM: `shared-cpu-1x`, `512mb` memory.
- **Production Container (`Dockerfile`)**:
  - Base Image: `python:3.11-slim`
  - Working Directory: `/app`
  - Command: `python3 server.py --host 0.0.0.0 --port 8080`
  - Exposes port `8080`.
- **CI/CD Workflow (`.github/workflows/deploy-fly.yml`)**:
  - Triggers on push to `main` or `master`.
  - Installs `flyctl` via `superfly/flyctl-actions/setup-flyctl@master`.
  - Deploys container with `flyctl deploy --remote-only` using secret `FLY_API_TOKEN`.

---

## 9. Step-by-Step Recreation Blueprint

To reproduce this entire repository from zero:

1. **Initialize Workspace & Directory Structure**:
   ```bash
   mkdir aug-video-animation-2 && cd aug-video-animation-2
   git init
   mkdir -p stills/{00_index,01_architecture,02_plan,03_assets,04_cohort,05_gaps,06_assembly,07_polish,08_refinement,09_audio,10_editcolor,11_thumbnail,12_export,13_metadata,15_tactics}
   mkdir -p video_flow/_first_frames 3_Simulation/rawexport uploads .github/workflows
   touch .nojekyll
   ```

2. **Populate Media Manifests & Assets**:
   - Create `stills/images_manifest.json` mapping all slide stills to stages `00` through `15`.
   - Create `video_flow/video_flow_manifest.json` indexing the 26 Flow video clips and their poster images.
   - Run `python3 generate_assets.py` to render all SVG visuals.

3. **Implement Backend Server (`server.py`)**:
   - Implement the `ThreadingHTTPServer` with custom `SimpleHTTPRequestHandler`.
   - Implement the HMAC-SHA256 Azure Blob client and Key Vault resolver.
   - Implement API routes: `/api/health`, `/api/state`, `/api/state/list`, `/api/vault-search`, `/api/text`, `/api/ai/tts`, `/api/upload`.

4. **Implement Frontend Web Views & Design System**:
   - Build `style.css` and `app.js` with dark/light theme switcher and Roger Rabbit signature footer.
   - Implement the 10 web views (`index.html`, `research.html`, `timeline.html`, `shotlist.html`, `scenes.html`, `voice_over.html`, `script_guru.html`, `gallery.html`, `tactic.html`, `analysis.html`).

5. **Implement Auxiliary Video Pipelines**:
   - Create `split_large_videos.py` and `rejoin_large_videos.py` for large video handling.
   - Create `extract_and_rewrite_vo.py` for automated script processing.

6. **Configure CI/CD & Deployments**:
   - Add `.github/workflows/deploy-pages.yml` for automated GitHub Pages static releases.
   - Add `Dockerfile`, `fly.toml`, and `.github/workflows/deploy-fly.yml` for Fly.io container deployments.
   - Test locally with `python3 server.py --port 8765`.

---

## 10. Reverse Response Video & Second Brain Specification 🎬🧠

### 10.1. Benchmark Reference Video Integration 📹
- **Selected Viral Model**: A proven high-retention video structure serves as the pacing benchmark.
- **Second-by-Second Scrubber**: In `research.html`, the video is dissected second-by-second across key psychological gates:
  - `0:00 - 0:15`: ⚡ Hook & Pain Point Setup ("46,000 notes chaos").
  - `0:15 - 0:45`: 🧩 The Core Problem & Framework Gap (Static PARA vs Active Neural Synthesis).
  - `0:45 - 1:15`: 🚀 Discovery & Reverse Response Architecture.
  - `1:15 - 1:45`: 🛠️ The 16-Stage Workbench & Pacing Guardrails.
  - `1:45 - 2:20`: ⚡ Live Execution, WPM Monitoring & Real-Time Sync.
  - `2:20 - 3:00`: 🏆 The Payoff, Call to Action & Roger Rabbit Outro.

### 10.2. Manually Triggered Second Brain Workflows 🧠
To ensure precision and user control, Second Brain integration is **manually triggered**:
1. **🔍 Manual Vault Query Trigger (`#btn-trigger-vault-search`)**: User types search queries (e.g. `obsidian`, `neural`, `agents`) and manually hits *Trigger Search* to execute an inverted-index fuzzy search across local Obsidian markdown vaults without noisy auto-suggestions.
2. **✍️ Manual Personal Insight Injection (`#manual-note-drawer`)**: A dedicated manual drawer allows the creator to input personal takeaways, anecdotes, or niche-specific knowledge and manually inject them directly into active shot beats.
3. **🔗 Manual Vault Node Linking (`insertVaultReference`)**: Clicking any vault search result directly attaches the source file reference tag (`[Ref: path/to/note.md]`) into the visual notes metadata.

### 10.3. Direct Multimedia Content Upload 📤
- Direct file/video uploader via `POST /api/upload` storing raw master footage, B-roll clips, Canva slide deck exports, and audio recordings in `uploads/` for immediate reference in the storyboard.

---

## 11. Signature Outro ⭐
- All views feature a dynamic **Roger Rabbit style hand-drawn cartoon signature** for **Rifat Erdem Sahin** (`.roger-rabbit-signature`) with animated cartoon stars, cursive typography, and gradient animations.

---
*End of Specification Document.*

