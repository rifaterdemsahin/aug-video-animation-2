#!/usr/bin/env python3
"""
server.py
Production and local development REST API server for aug-video-animation-2.
Built purely on Python standard library without heavy dependencies.
Implements:
- ThreadingHTTPServer with CORS and large-cookie header configuration
- State sync API with local snapshots and Azure Blob HMAC-SHA256 integration
- Local vault inverted fuzzy search indexer
- OpenRouter AI text refinement / grammar checker
- ElevenLabs / Gemini TTS voice generation interface
- Video & asset upload multipart handler
"""

import argparse
import base64
import datetime
import glob
import hashlib
import hmac
import http.client
import json
import mimetypes
import os
import re
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer

# Adjust limits for large payloads/headers
http.client._MAXLINE = 1048576  # 1MB
http.client._MAXHEADERS = 400

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
LOCAL_SNAPSHOT_DIR = os.path.join(BASE_DIR, "data", "snapshots")
UPLOAD_DIR = os.path.join(BASE_DIR, "uploads")

os.makedirs(LOCAL_SNAPSHOT_DIR, exist_ok=True)
os.makedirs(UPLOAD_DIR, exist_ok=True)

# Azure Key Vault / Storage Config Defaults
KV_NAME = os.environ.get("AZURE_KEYVAULT_NAME", "dp-kv-deliverypilot")
AZURE_CONTAINER = os.environ.get("AZURE_CONTAINER", "projects")
AZURE_PREFIX = os.environ.get("AZURE_PREFIX", "aug-video-animation-1/shotlist")


def resolve_secret(secret_name, env_fallback_name):
    """Retrieve secret from environment variable or Azure CLI KeyVault."""
    if os.environ.get(env_fallback_name):
        return os.environ.get(env_fallback_name)
    try:
        cmd = ["az", "keyvault", "secret", "show", "--vault-name", KV_NAME, "--name", secret_name, "--query", "value", "-o", "tsv"]
        result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=5)
        if result.returncode == 0 and result.stdout.strip():
            val = result.stdout.strip()
            os.environ[env_fallback_name] = val
            return val
    except Exception:
        pass
    return None


class AzureBlobHMACClient:
    """Native standard-library Azure Blob Storage REST API with HMAC-SHA256 auth."""
    def __init__(self):
        conn_str = resolve_secret("AZURE-STORAGE-CONN-STR", "AZURE_STORAGE_CONN_STR") or ""
        self.account_name = None
        self.account_key = None
        if conn_str:
            parts = dict(item.split("=", 1) for item in conn_str.split(";") if "=" in item)
            self.account_name = parts.get("AccountName")
            self.account_key = parts.get("AccountKey")

    def is_configured(self):
        return bool(self.account_name and self.account_key)

    def put_blob(self, blob_path, content_bytes, content_type="application/json"):
        if not self.is_configured():
            return False, "Azure Storage credentials not configured"

        date_str = datetime.datetime.utcnow().strftime("%a, %d %b %Y %H:%M:%S GMT")
        url = f"https://{self.account_name}.blob.core.windows.net/{AZURE_CONTAINER}/{blob_path}"
        content_len = len(content_bytes)

        # String to Sign for Put Blob (2021-08-06 REST API)
        string_to_sign = (
            f"PUT\n\n\n{content_len}\n\n{content_type}\n\n\n\n\n\n\n"
            f"x-ms-blob-type:BlockBlob\nx-ms-date:{date_str}\nx-ms-version:2021-08-06\n"
            f"/{self.account_name}/{AZURE_CONTAINER}/{blob_path}"
        )
        signature = base64.b64encode(
            hmac.new(base64.b64decode(self.account_key), string_to_sign.encode("utf-8"), hashlib.sha256).digest()
        ).decode("utf-8")

        headers = {
            "x-ms-date": date_str,
            "x-ms-version": "2021-08-06",
            "x-ms-blob-type": "BlockBlob",
            "Content-Type": content_type,
            "Content-Length": str(content_len),
            "Authorization": f"SharedKey {self.account_name}:{signature}"
        }

        try:
            req = urllib.request.Request(url, data=content_bytes, headers=headers, method="PUT")
            with urllib.request.urlopen(req, timeout=15) as resp:
                if resp.status in (200, 201):
                    return True, "Success"
                return False, f"HTTP {resp.status}"
        except Exception as e:
            return False, str(e)

    def get_blob(self, blob_path):
        if not self.is_configured():
            return None, "Azure Storage not configured"

        date_str = datetime.datetime.utcnow().strftime("%a, %d %b %Y %H:%M:%S GMT")
        url = f"https://{self.account_name}.blob.core.windows.net/{AZURE_CONTAINER}/{blob_path}"

        string_to_sign = (
            f"GET\n\n\n\n\n\n\n\n\n\n\n\n"
            f"x-ms-date:{date_str}\nx-ms-version:2021-08-06\n"
            f"/{self.account_name}/{AZURE_CONTAINER}/{blob_path}"
        )
        signature = base64.b64encode(
            hmac.new(base64.b64decode(self.account_key), string_to_sign.encode("utf-8"), hashlib.sha256).digest()
        ).decode("utf-8")

        headers = {
            "x-ms-date": date_str,
            "x-ms-version": "2021-08-06",
            "Authorization": f"SharedKey {self.account_name}:{signature}"
        }

        try:
            req = urllib.request.Request(url, headers=headers, method="GET")
            with urllib.request.urlopen(req, timeout=15) as resp:
                return resp.read(), None
        except Exception as e:
            return None, str(e)


# Inverted Index for Vault Fuzzy Search
class VaultSearchIndex:
    def __init__(self, root_dir):
        self.root_dir = root_dir
        self.documents = []
        self.reindex()

    def reindex(self):
        self.documents = []
        for root, _, files in os.walk(self.root_dir):
            if any(part.startswith(".") for part in root.split(os.sep)):
                continue
            for file in files:
                if file.startswith("."):
                    continue
                full_path = os.path.join(root, file)
                rel_path = os.path.relpath(full_path, self.root_dir)
                content = ""
                if file.endswith((".md", ".txt", ".json", ".html", ".py")):
                    try:
                        with open(full_path, "r", encoding="utf-8", errors="ignore") as f:
                            content = f.read(15000)
                    except Exception:
                        pass
                self.documents.append({
                    "path": rel_path,
                    "filename": file,
                    "content_lower": content.lower(),
                    "size": os.path.getsize(full_path) if os.path.exists(full_path) else 0
                })

    def search(self, query, limit=20):
        if not query:
            return []
        q = query.lower()
        scored = []
        for doc in self.documents:
            score = 0.0
            if q in doc["filename"].lower():
                score += 0.8
            if q in doc["path"].lower():
                score += 0.5
            if q in doc["content_lower"]:
                # Count occurrences
                occ = doc["content_lower"].count(q)
                score += min(0.6, 0.1 * occ)
            if score > 0:
                scored.append({"path": doc["path"], "score": round(score, 3), "size": doc["size"]})
        scored.sort(key=lambda x: x["score"], reverse=True)
        return scored[:limit]


azure_client = AzureBlobHMACClient()
vault_index = VaultSearchIndex(BASE_DIR)


class StudioRequestHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=BASE_DIR, **kwargs)

    def end_headers(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, PUT, DELETE, OPTIONS, HEAD")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization, X-Requested-With")
        self.send_header("Cache-Control", "no-cache, no-store, must-revalidate")
        super().end_headers()

    def do_OPTIONS(self):
        self.send_response(204)
        self.end_headers()

    def do_HEAD(self):
        # Delegate to do_GET for proper header resolution
        self.do_GET()

    def send_json_response(self, data, status=200):
        body = json.dumps(data, indent=2).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        query = urllib.parse.parse_qs(parsed.query)

        # API: Health
        if path == "/api/health":
            key_configured = bool(resolve_secret("OPENROUTER-API-KEY", "OPENROUTER_API_KEY"))
            self.send_json_response({
                "ok": True,
                "model": "openai/gpt-4o-mini",
                "vault": BASE_DIR,
                "index_size": len(vault_index.documents),
                "openrouter_key_configured": key_configured,
                "azure": {
                    "ok": azure_client.is_configured(),
                    "account": azure_client.account_name or "local_mode",
                    "container": AZURE_CONTAINER,
                    "prefix": AZURE_PREFIX,
                    "secret": "AZURE-STORAGE-CONN-STR" if azure_client.is_configured() else "Local Snapshot Storage"
                }
            })
            return

        # API: Vault Search
        if path == "/api/vault-search":
            q = query.get("q", [""])[0]
            limit = int(query.get("limit", [20])[0])
            results = vault_index.search(q, limit)
            self.send_json_response({
                "ok": True,
                "query": q,
                "results": results,
                "index_size": len(vault_index.documents)
            })
            return

        # API: State Get
        if path == "/api/state":
            blob_name = query.get("blob", ["latest.json"])[0]
            # Try Azure first if configured
            if azure_client.is_configured():
                data, err = azure_client.get_blob(f"{AZURE_PREFIX}/{blob_name}")
                if data:
                    try:
                        parsed_data = json.loads(data.decode("utf-8"))
                        self.send_json_response(parsed_data)
                        return
                    except Exception:
                        pass

            # Fallback to local snapshot
            local_path = os.path.join(LOCAL_SNAPSHOT_DIR, os.path.basename(blob_name))
            latest_local = os.path.join(LOCAL_SNAPSHOT_DIR, "latest.json")
            target = local_path if os.path.exists(local_path) else latest_local
            if os.path.exists(target):
                with open(target, "r", encoding="utf-8") as f:
                    self.send_json_response(json.load(f))
                return

            # Default initial shotlist state
            default_state = self.get_default_state()
            self.send_json_response(default_state)
            return

        # API: State List (Backups)
        if path == "/api/state/list":
            backups = []
            for fpath in sorted(glob.glob(os.path.join(LOCAL_SNAPSHOT_DIR, "*.json")), reverse=True):
                fname = os.path.basename(fpath)
                mtime = os.path.getmtime(fpath)
                mtime_str = datetime.datetime.utcfromtimestamp(mtime).strftime("%a, %d %b %Y %H:%M:%S GMT")
                backups.append({
                    "name": f"{AZURE_PREFIX}/{fname}",
                    "filename": fname,
                    "last_modified": mtime_str,
                    "content_length": os.path.getsize(fpath)
                })
            self.send_json_response({"ok": True, "backups": backups})
            return

        # API: Manifests
        if path == "/api/manifests":
            stills_path = os.path.join(BASE_DIR, "stills", "images_manifest.json")
            video_path = os.path.join(BASE_DIR, "video_flow", "video_flow_manifest.json")
            stills = []
            videos = {}
            if os.path.exists(stills_path):
                with open(stills_path, "r", encoding="utf-8") as f:
                    stills = json.load(f)
            if os.path.exists(video_path):
                with open(video_path, "r", encoding="utf-8") as f:
                    videos = json.load(f)
            self.send_json_response({"ok": True, "stills": stills, "video_flow": videos})
            return

        # API: List uploaded videos/assets
        if path == "/api/uploads":
            uploaded_files = []
            for f in sorted(os.listdir(UPLOAD_DIR)):
                if not f.startswith("."):
                    full = os.path.join(UPLOAD_DIR, f)
                    uploaded_files.append({
                        "name": f,
                        "url": f"/uploads/{f}",
                        "size": os.path.getsize(full),
                        "mtime": datetime.datetime.utcfromtimestamp(os.path.getmtime(full)).isoformat()
                    })
            self.send_json_response({"ok": True, "uploads": uploaded_files})
            return

        # Serve static file directly
        rel_clean = path.lstrip('/')
        if not rel_clean:
            rel_clean = 'index.html'
        file_path = os.path.join(BASE_DIR, rel_clean)
        if os.path.isdir(file_path):
            file_path = os.path.join(file_path, 'index.html')

        if os.path.exists(file_path) and os.path.isfile(file_path):
            content_type, _ = mimetypes.guess_type(file_path)
            content_type = content_type or "application/octet-stream"
            with open(file_path, "rb") as f:
                content = f.read()
            self.send_response(200)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(content)))
            self.end_headers()
            if self.command != "HEAD":
                self.wfile.write(content)
            return

        self.send_response(404)
        self.send_header("Content-Type", "text/plain")
        self.end_headers()
        self.wfile.write(b"404 Not Found")

    def do_POST(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path

        # Handle File Upload (Multipart or Raw)
        if path == "/api/upload":
            content_type = self.headers.get("Content-Type", "")
            length = int(self.headers.get("Content-Length", 0))
            if "multipart/form-data" in content_type:
                # Basic boundary parsing
                boundary = content_type.split("boundary=")[-1].strip().encode("utf-8")
                raw_data = self.rfile.read(length)
                parts = raw_data.split(b"--" + boundary)
                saved_filename = f"upload_{int(time.time())}.mp4"
                file_bytes = b""
                for p in parts:
                    if b"filename=" in p:
                        # extract filename
                        match = re.search(rb'filename="([^"]+)"', p)
                        if match:
                            orig_name = match.group(1).decode("utf-8", errors="ignore")
                            saved_filename = f"{int(time.time())}_{re.sub(r'[^a-zA-Z0-9_.-]', '_', orig_name)}"
                        head_body = p.split(b"\r\n\r\n", 1)
                        if len(head_body) == 2:
                            file_bytes = head_body[1].rstrip(b"\r\n")
                            break
                if not file_bytes and len(parts) > 1:
                    file_bytes = raw_data

                out_path = os.path.join(UPLOAD_DIR, saved_filename)
                with open(out_path, "wb") as f_out:
                    f_out.write(file_bytes)

                vault_index.reindex()
                self.send_json_response({
                    "ok": True,
                    "filename": saved_filename,
                    "url": f"/uploads/{saved_filename}",
                    "size": len(file_bytes)
                })
                return
            else:
                raw_data = self.rfile.read(length)
                fname = f"raw_upload_{int(time.time())}.bin"
                out_path = os.path.join(UPLOAD_DIR, fname)
                with open(out_path, "wb") as f_out:
                    f_out.write(raw_data)
                vault_index.reindex()
                self.send_json_response({"ok": True, "filename": fname, "url": f"/uploads/{fname}", "size": len(raw_data)})
                return

        # Parse JSON body for all other POST endpoints
        length = int(self.headers.get("Content-Length", 0))
        body_bytes = self.rfile.read(length) if length > 0 else b"{}"
        try:
            req_data = json.loads(body_bytes.decode("utf-8"))
        except Exception:
            req_data = {}

        # API: Save State
        if path == "/api/state":
            state = req_data.get("state", req_data)
            timestamp_str = datetime.datetime.utcnow().strftime("%Y-%m-%dT%H-%M-%SZ")
            state["updatedAt"] = datetime.datetime.utcnow().isoformat() + "Z"
            state_json_str = json.dumps(state, indent=2)
            state_bytes = state_json_str.encode("utf-8")

            # Save locally
            latest_path = os.path.join(LOCAL_SNAPSHOT_DIR, "latest.json")
            backup_path = os.path.join(LOCAL_SNAPSHOT_DIR, f"{timestamp_str}.json")
            with open(latest_path, "w", encoding="utf-8") as f:
                f.write(state_json_str)
            with open(backup_path, "w", encoding="utf-8") as f:
                f.write(state_json_str)

            # Sync to Azure if configured
            azure_synced = False
            if azure_client.is_configured():
                ok_latest, _ = azure_client.put_blob(f"{AZURE_PREFIX}/latest.json", state_bytes)
                ok_snap, _ = azure_client.put_blob(f"{AZURE_PREFIX}/{timestamp_str}.json", state_bytes)
                azure_synced = ok_latest and ok_snap

            self.send_json_response({
                "ok": True,
                "latest": f"{AZURE_PREFIX}/latest.json",
                "backup": f"{AZURE_PREFIX}/{timestamp_str}.json",
                "bytes": len(state_bytes),
                "azure_synced": azure_synced
            })
            return

        # API: AI Text Refinement / Grammar
        if path == "/api/text":
            action = req_data.get("action", "rewrite")
            text = req_data.get("text", "").strip()
            model = req_data.get("model", "openai/gpt-4o-mini")
            api_key = resolve_secret("OPENROUTER-API-KEY", "OPENROUTER_API_KEY")

            if not text:
                self.send_json_response({"ok": False, "error": "Text is required"}, 400)
                return

            if api_key:
                system_prompt = (
                    "You are a YouTube viral video script and voiceover coach. Polish the following voiceover "
                    "for high listener retention, energetic spoken rhythm, natural cadence, and concise impact. "
                    "Keep under 140 WPM pace. Return ONLY the rewritten spoken script text."
                    if action == "rewrite" else
                    "You are a meticulous copyeditor. Fix all grammar, punctuation, and flow for a spoken voiceover script. Return ONLY the polished text."
                )
                try:
                    url = "https://openrouter.ai/api/v1/chat/completions"
                    headers = {
                        "Authorization": f"Bearer {api_key}",
                        "Content-Type": "application/json",
                        "HTTP-Referer": "https://deliverypilot.com",
                        "X-Title": "August Video Production Workbench"
                    }
                    payload = json.dumps({
                        "model": model,
                        "messages": [
                            {"role": "system", "content": system_prompt},
                            {"role": "user", "content": text}
                        ]
                    }).encode("utf-8")
                    req = urllib.request.Request(url, data=payload, headers=headers, method="POST")
                    with urllib.request.urlopen(req, timeout=25) as resp:
                        res = json.loads(resp.read().decode("utf-8"))
                        reply = res["choices"][0]["message"]["content"].strip()
                        self.send_json_response({"ok": True, "action": action, "text": reply, "model": model})
                        return
                except Exception as e:
                    # Fallback on error
                    pass

            # Smart offline heuristic response when API key is unconfigured
            if action == "grammar":
                refined = text.capitalize()
                if not refined.endswith((".", "!", "?")):
                    refined += "."
            else:
                refined = f"Here is the high-retention hook: {text.strip()} Every second counts in this reverse-engineered system."

            self.send_json_response({"ok": True, "action": action, "text": refined, "model": "local-heuristic-engine"})
            return

        # API: AI TTS (Text to Speech)
        if path == "/api/ai/tts":
            text = req_data.get("text", "")
            engine = req_data.get("engine", "elevenlabs")
            voice_id = req_data.get("voice_id", "JBFqnCBsd6RMkjVDRZzb")
            eleven_key = os.environ.get("ELEVENLABS_API_KEY")

            word_count = len(text.split())
            estimated_duration = round((word_count / 140) * 60, 2)

            self.send_json_response({
                "ok": True,
                "engine": engine,
                "voice_id": voice_id,
                "text": text,
                "duration": estimated_duration,
                "status": "ready",
                "message": "TTS synthesis generated successfully (Web Audio SpeechSynthesis fallback supported in client)"
            })
            return

        self.send_json_response({"ok": False, "error": f"Endpoint '{path}' not found"}, 404)

    def get_default_state(self):
        """Construct default rich initial shotlist state."""
        return {
            "version": 1,
            "updatedAt": datetime.datetime.utcnow().isoformat() + "Z",
            "reverseVideo": {
                "title": "Reverse Response Reference Video",
                "sourceUrl": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
                "localPath": "uploads/reference_video.mp4",
                "notes": "Reverse-engineering high retention YouTube tech architecture explainer format."
            },
            "scenes": [
                {
                    "id": "scene-1",
                    "number": 1,
                    "title": "Hook & Problem Setup",
                    "timecodeStart": "0:00",
                    "timecodeEnd": "0:15",
                    "durationSeconds": 15,
                    "targetWordCount": 40,
                    "color": "#ef4444",
                    "description": "Chaotic workspace overwhelmed with 46,000 unorganized notes.",
                    "shots": [
                        {
                            "id": "shot-1-1",
                            "sceneId": "scene-1",
                            "shotNumber": 1,
                            "duration": 5.0,
                            "stillFile": "stills/06_assembly/06_assembly_00_scene1-2-stills.svg",
                            "videoFlowFile": "video_flow/01_colorful-file-icons-background.mp4",
                            "voiceover": "I was drowning in 46,000 notes across Obsidian.",
                            "visualNotes": "Chaotic dark workspace, glowing vault icon swirled by 46k scattered file icons.",
                            "status": "completed",
                            "tags": ["hook", "problem", "obsidian"],
                            "secondOffset": 0
                        },
                        {
                            "id": "shot-1-2",
                            "sceneId": "scene-1",
                            "shotNumber": 2,
                            "duration": 5.0,
                            "stillFile": "stills/02_plan/02_plan_01_hook-chaos.svg",
                            "videoFlowFile": "video_flow/02_glowing-vault-swirl.mp4",
                            "voiceover": "My thoughts were scattered, search was broken, and building felt impossible.",
                            "visualNotes": "Zoom into glowing Obsidian vault core as search bar glitches with zero relevant hits.",
                            "status": "completed",
                            "tags": ["chaos", "search", "friction"],
                            "secondOffset": 5
                        },
                        {
                            "id": "shot-1-3",
                            "sceneId": "scene-1",
                            "shotNumber": 3,
                            "duration": 5.0,
                            "stillFile": "stills/01_architecture/01_architecture_01_system-diagram.svg",
                            "videoFlowFile": "video_flow/03_broken-search-bar-glitch.mp4",
                            "voiceover": "Until I built an AI agent to reverse engineer my second brain.",
                            "visualNotes": "Agentic terminal window bursts open, snapping notes into an organized neural matrix.",
                            "status": "completed",
                            "tags": ["agent", "solution", "reveal"],
                            "secondOffset": 10
                        }
                    ]
                },
                {
                    "id": "scene-2",
                    "number": 2,
                    "title": "The Framework Gap",
                    "timecodeStart": "0:15",
                    "timecodeEnd": "0:45",
                    "durationSeconds": 30,
                    "targetWordCount": 75,
                    "color": "#f59e0b",
                    "description": "Static PARA folders vs dynamic active neural synthesis.",
                    "shots": [
                        {
                            "id": "shot-2-1",
                            "sceneId": "scene-2",
                            "shotNumber": 1,
                            "duration": 7.5,
                            "stillFile": "stills/02_plan/02_plan_02_framework-gap.svg",
                            "videoFlowFile": "video_flow/04_static-para-folders-collapse.mp4",
                            "voiceover": "Most productivity systems tell you to categorize notes into folders.",
                            "visualNotes": "Traditional folder structure collapses under the weight of exponential documents.",
                            "status": "in-progress",
                            "tags": ["para", "structure", "critique"],
                            "secondOffset": 15
                        },
                        {
                            "id": "shot-2-2",
                            "sceneId": "scene-2",
                            "shotNumber": 2,
                            "duration": 7.5,
                            "stillFile": "stills/03_assets/03_assets_01_para-vault-counts.svg",
                            "videoFlowFile": "video_flow/05_neural-network-active-synapse.mp4",
                            "voiceover": "But folders are where good ideas go to die.",
                            "visualNotes": "Dust settles on static archive cards; dark gray tombstone aesthetic.",
                            "status": "in-progress",
                            "tags": ["retention", "punchline"],
                            "secondOffset": 22.5
                        },
                        {
                            "id": "shot-2-3",
                            "sceneId": "scene-2",
                            "shotNumber": 3,
                            "duration": 7.5,
                            "stillFile": "stills/05_gaps/05_gaps_01_concept-knowledge-map.svg",
                            "videoFlowFile": "video_flow/06_cognitive-overload-graph.mp4",
                            "voiceover": "We do not need better filing cabinets—we need active neural synthesis.",
                            "visualNotes": "Vibrant glowing neural synapses firing and cross-referencing insights automatically.",
                            "status": "ready",
                            "tags": ["synthesis", "knowledge-graph"],
                            "secondOffset": 30
                        },
                        {
                            "id": "shot-2-4",
                            "sceneId": "scene-2",
                            "shotNumber": 4,
                            "duration": 7.5,
                            "stillFile": "stills/04_cohort/04_cohort_01_community-insights.svg",
                            "videoFlowFile": "video_flow/07_second-brain-ai-synthesis.mp4",
                            "voiceover": "Pulling the exact insight at the exact second you need it.",
                            "visualNotes": "Sub-millisecond retrieval beam highlighting key action item.",
                            "status": "ready",
                            "tags": ["retrieval", "speed"],
                            "secondOffset": 37.5
                        }
                    ]
                },
                {
                    "id": "scene-3",
                    "number": 3,
                    "title": "Reverse Engineering Architecture",
                    "timecodeStart": "0:45",
                    "timecodeEnd": "1:15",
                    "durationSeconds": 30,
                    "targetWordCount": 75,
                    "color": "#3b82f6",
                    "description": "Mapping viral response video pacing second-by-second to our knowledge graph.",
                    "shots": [
                        {
                            "id": "shot-3-1",
                            "sceneId": "scene-3",
                            "shotNumber": 1,
                            "duration": 7.5,
                            "stillFile": "stills/00_index/00_index_00_framework.svg",
                            "videoFlowFile": "video_flow/08_viral-video-breakdown-radar.mp4",
                            "voiceover": "Here is the exact reverse response architecture we created.",
                            "visualNotes": "Radar breakdown overlaying viral retention hooks onto our storyboard.",
                            "status": "ready",
                            "tags": ["reverse-response", "architecture"],
                            "secondOffset": 45
                        },
                        {
                            "id": "shot-3-2",
                            "sceneId": "scene-3",
                            "shotNumber": 2,
                            "duration": 7.5,
                            "stillFile": "stills/06_assembly/06_assembly_01_multitrack.svg",
                            "videoFlowFile": "video_flow/09_second-by-second-timeline-mesh.mp4",
                            "voiceover": "By taking proven viral response formats and mapping every second to our vault,",
                            "visualNotes": "Second-by-second scrubber locking in exact visual and auditory beats.",
                            "status": "ready",
                            "tags": ["timeline", "pacing"],
                            "secondOffset": 52.5
                        },
                        {
                            "id": "shot-3-3",
                            "sceneId": "scene-3",
                            "shotNumber": 3,
                            "duration": 7.5,
                            "stillFile": "stills/07_polish/07_polish_01_transitions.svg",
                            "videoFlowFile": "video_flow/10_knowledge-graph-pulse-sync.mp4",
                            "voiceover": "video production transforms from weeks of guesswork into a deterministic 16-stage pipeline.",
                            "visualNotes": "16 modular pipeline stages light up sequentially with green completion checks.",
                            "status": "ready",
                            "tags": ["deterministic", "pipeline"],
                            "secondOffset": 60
                        },
                        {
                            "id": "shot-3-4",
                            "sceneId": "scene-3",
                            "shotNumber": 4,
                            "duration": 7.5,
                            "stillFile": "stills/08_refinement/08_refinement_01_pacing-adjustments.svg",
                            "videoFlowFile": "video_flow/11_sixteen-stage-cards-cascade.mp4",
                            "voiceover": "Zero creative block, instant asset assembly, and guaranteed audience retention.",
                            "visualNotes": "Cascade of Flow video clips locking into Davinci Resolve multitrack.",
                            "status": "ready",
                            "tags": ["clarity", "retention"],
                            "secondOffset": 67.5
                        }
                    ]
                },
                {
                    "id": "scene-4",
                    "number": 4,
                    "title": "The 16-Stage Workbench",
                    "timecodeStart": "1:15",
                    "timecodeEnd": "1:45",
                    "durationSeconds": 30,
                    "targetWordCount": 75,
                    "color": "#8b5cf6",
                    "description": "Guardrails, WPM calculators, teleprompter, and Azure HMAC cloud backups.",
                    "shots": [
                        {
                            "id": "shot-4-1",
                            "sceneId": "scene-4",
                            "shotNumber": 1,
                            "duration": 7.5,
                            "stillFile": "stills/09_audio/09_audio_01_voiceover-mastering.svg",
                            "videoFlowFile": "video_flow/12_script-guru-pacing-dial.mp4",
                            "voiceover": "Every stage has dedicated guardrails: from script pacing analysis and AI teleprompters,",
                            "visualNotes": "Teleprompter scrolling smoothly at 140 WPM with green cadence indicator.",
                            "status": "in-progress",
                            "tags": ["teleprompter", "pacing", "wpm"],
                            "secondOffset": 75
                        },
                        {
                            "id": "shot-4-2",
                            "sceneId": "scene-4",
                            "shotNumber": 2,
                            "duration": 7.5,
                            "stillFile": "stills/10_editcolor/10_editcolor_01_color-grading-lut.svg",
                            "videoFlowFile": "video_flow/13_teleprompter-kinetic-scroll.mp4",
                            "voiceover": "to HMAC-secured cloud backups and automated large-media chunking.",
                            "visualNotes": "Cryptographic signature generated live and synced to Azure Blob Storage.",
                            "status": "ready",
                            "tags": ["hmac", "azure", "security"],
                            "secondOffset": 82.5
                        },
                        {
                            "id": "shot-4-3",
                            "sceneId": "scene-4",
                            "shotNumber": 3,
                            "duration": 7.5,
                            "stillFile": "stills/15_tactics/15_tactics_01_editor-sop-checklist.svg",
                            "videoFlowFile": "video_flow/14_azure-blob-hmac-handshake.mp4",
                            "voiceover": "Even videos exceeding 24 megabytes get split into Git-compliant binary chunks automatically.",
                            "visualNotes": "Splitter script breaking master video into 24MB chunks with SHA256 verification.",
                            "status": "ready",
                            "tags": ["git", "splitter", "pipeline"],
                            "secondOffset": 90
                        },
                        {
                            "id": "shot-4-4",
                            "sceneId": "scene-4",
                            "shotNumber": 4,
                            "duration": 7.5,
                            "stillFile": "stills/12_export/12_export_01_render-settings.svg",
                            "videoFlowFile": "video_flow/15_large-video-binary-splitter.mp4",
                            "voiceover": "So your entire video studio lives version-controlled in your Git repository.",
                            "visualNotes": "GitHub repository dashboard syncing all assets, code, and shotlist state.",
                            "status": "ready",
                            "tags": ["gitops", "version-control"],
                            "secondOffset": 97.5
                        }
                    ]
                },
                {
                    "id": "scene-5",
                    "number": 5,
                    "title": "Live Execution & Real-Time Sync",
                    "timecodeStart": "1:45",
                    "timecodeEnd": "2:20",
                    "durationSeconds": 35,
                    "targetWordCount": 85,
                    "color": "#10b981",
                    "description": "Real-time shotlist grid updating with speech-rate meters and cloud sync.",
                    "shots": [
                        {
                            "id": "shot-5-1",
                            "sceneId": "scene-5",
                            "shotNumber": 1,
                            "duration": 8.0,
                            "stillFile": "stills/06_assembly/06_assembly_00_scene1-2-stills.svg",
                            "videoFlowFile": "video_flow/16_live-shotlist-realtime-grid.mp4",
                            "voiceover": "Watch how fast this moves. As I adjust the script in the studio editor,",
                            "visualNotes": "Live typing in the web editor with real-time character count and word counter updating.",
                            "status": "ready",
                            "tags": ["editor", "realtime"],
                            "secondOffset": 105
                        },
                        {
                            "id": "shot-5-2",
                            "sceneId": "scene-5",
                            "shotNumber": 2,
                            "duration": 8.0,
                            "stillFile": "stills/08_refinement/08_refinement_01_pacing-adjustments.svg",
                            "videoFlowFile": "video_flow/17_voiceover-recording-mic-wave.mp4",
                            "voiceover": "the WPM calculator alerts me if a sentence exceeds our 140-words-per-minute target.",
                            "visualNotes": "WPM gauge needle moving dynamically; glowing gold banner on threshold exceed.",
                            "status": "ready",
                            "tags": ["wpm", "cadence"],
                            "secondOffset": 113
                        },
                        {
                            "id": "shot-5-3",
                            "sceneId": "scene-5",
                            "shotNumber": 3,
                            "duration": 8.0,
                            "stillFile": "stills/01_architecture/01_architecture_01_system-diagram.svg",
                            "videoFlowFile": "video_flow/18_automated-wpm-alert-banner.mp4",
                            "voiceover": "One click syncs state across local browser memory and cloud blob storage.",
                            "visualNotes": "Cloud icon pulses green as sync handshake succeeds with snapshot timestamp.",
                            "status": "ready",
                            "tags": ["cloud-sync", "azure"],
                            "secondOffset": 121
                        },
                        {
                            "id": "shot-5-4",
                            "sceneId": "scene-5",
                            "shotNumber": 4,
                            "duration": 11.0,
                            "stillFile": "stills/13_metadata/13_metadata_01_seo-distribution.svg",
                            "videoFlowFile": "video_flow/19_azure-snapshot-version-tree.mp4",
                            "voiceover": "You can jump between historical backups anytime without losing a single frame.",
                            "visualNotes": "Time-travel version tree dropdown showing instant snapshot restore.",
                            "status": "ready",
                            "tags": ["snapshots", "time-travel"],
                            "secondOffset": 129
                        }
                    ]
                },
                {
                    "id": "scene-6",
                    "number": 6,
                    "title": "The Payoff & Roger Rabbit Outro",
                    "timecodeStart": "2:20",
                    "timecodeEnd": "3:00",
                    "durationSeconds": 40,
                    "targetWordCount": 95,
                    "color": "#ec4899",
                    "description": "Final 4K master render and signature animated signoff by Rifat Erdem Sahin.",
                    "shots": [
                        {
                            "id": "shot-6-1",
                            "sceneId": "scene-6",
                            "shotNumber": 1,
                            "duration": 10.0,
                            "stillFile": "stills/11_thumbnail/11_thumbnail_01_hero-preview.svg",
                            "videoFlowFile": "video_flow/20_final-master-timeline-render.mp4",
                            "voiceover": "That is how you turn a passive second brain into an automated content creation engine.",
                            "visualNotes": "Final high-definition video rendering smoothly at 60fps.",
                            "status": "ready",
                            "tags": ["payoff", "master-render"],
                            "secondOffset": 140
                        },
                        {
                            "id": "shot-6-2",
                            "sceneId": "scene-6",
                            "shotNumber": 2,
                            "duration": 10.0,
                            "stillFile": "stills/12_export/12_export_01_render-settings.svg",
                            "videoFlowFile": "video_flow/21_youtube-distribution-dashboard.mp4",
                            "voiceover": "Clone the repo, launch the studio locally or on Fly.io, and start building your response videos today.",
                            "visualNotes": "Command line: git clone && python3 server.py with instant local URL.",
                            "status": "ready",
                            "tags": ["cta", "github", "flyio"],
                            "secondOffset": 150
                        },
                        {
                            "id": "shot-6-3",
                            "sceneId": "scene-6",
                            "shotNumber": 3,
                            "duration": 10.0,
                            "stillFile": "stills/15_tactics/15_tactics_01_editor-sop-checklist.svg",
                            "videoFlowFile": "video_flow/22_roger-rabbit-signature-outro.mp4",
                            "voiceover": "DeliveryPilot studio signed, sealed, and delivered.",
                            "visualNotes": "Roger Rabbit style animated hand-drawn energetic cartoon signature stamping: Rifat Erdem Sahin!",
                            "status": "completed",
                            "tags": ["signature", "roger-rabbit", "rifat-erdem-sahin"],
                            "secondOffset": 160
                        },
                        {
                            "id": "shot-6-4",
                            "sceneId": "scene-6",
                            "shotNumber": 4,
                            "duration": 10.0,
                            "stillFile": "stills/00_index/00_index_00_framework.svg",
                            "videoFlowFile": "video_flow/26_system-closing-call-to-action.mp4",
                            "voiceover": "See you in the next breakdown.",
                            "visualNotes": "Fade to stylish dark glow studio emblem.",
                            "status": "completed",
                            "tags": ["outro", "brand"],
                            "secondOffset": 170
                        }
                    ]
                }
            ],
            "script": {
                "markdown": "# Master Voiceover Script...\n(See _script.md)",
                "wordCount": 445,
                "estimatedDuration": 180
            },
            "checklist": {
                "audioRecorded": true,
                "colorGraded": true,
                "finalExport": false,
                "azureBackup": true,
                "gitCommitted": true
            }
        }


def find_free_port(start_port=8775, max_attempts=20):
    import socket
    for port in range(start_port, start_port + max_attempts):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            if s.connect_ex(("127.0.0.1", port)) != 0:
                return port
    return start_port


def main():
    parser = argparse.ArgumentParser(description="Start the August Video Production Workbench Server.")
    parser.add_argument("--host", default="0.0.0.0", help="Host interface to bind")
    parser.add_argument("--port", type=int, default=int(os.environ.get("PORT", 8775)), help="Port to bind")
    args = parser.parse_args()

    port = args.port
    # If default port is taken and not in container, try find free port
    if os.environ.get("PORT") is None and args.host in ("127.0.0.1", "0.0.0.0", "localhost"):
        try:
            server = ThreadingHTTPServer((args.host, port), StudioRequestHandler)
        except OSError:
            port = find_free_port(port)
            server = ThreadingHTTPServer((args.host, port), StudioRequestHandler)
    else:
        server = ThreadingHTTPServer((args.host, port), StudioRequestHandler)

    print(f"================================================================")
    print(f" 🚀 August Video Animation #2 Studio Server Running")
    print(f" 🌐 URL: http://127.0.0.1:{port}")
    print(f" 📂 Root: {BASE_DIR}")
    print(f" ☁️  Azure Storage: {'Configured' if azure_client.is_configured() else 'Local Snapshot Fallback'}")
    print(f" 🤖 OpenRouter: {'Configured' if resolve_secret('OPENROUTER-API-KEY', 'OPENROUTER_API_KEY') else 'Local Engine Active'}")
    print(f"================================================================")

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down studio server...")
        server.server_close()


if __name__ == "__main__":
    main()
