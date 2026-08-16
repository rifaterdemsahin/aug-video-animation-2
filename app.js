/**
 * app.js - Shared Multimedia Studio Engine for aug-video-animation-2
 * Handles:
 * - State Management (Dual persistence: localStorage & Backend /api/state)
 * - Navigation generation & active link detection
 * - Cloud / Local Snapshot Synchronizer
 * - TTS Engine & Audio Prompter Playback
 * - Theme Switcher (Dark / Light)
 * - Global Roger Rabbit Footer Injection
 * - Toast system & Dialog controllers
 */

const STORAGE_KEY = "wiganimation_shotlist_state";
const THEME_KEY = "wiganimation_theme";

class StudioEngine {
  constructor() {
    this.state = null;
    this.apiBase = "";
    this.initTheme();
  }

  initTheme() {
    const saved = localStorage.getItem(THEME_KEY) || "dark";
    document.documentElement.setAttribute("data-theme", saved);
  }

  toggleTheme() {
    const current = document.documentElement.getAttribute("data-theme") || "dark";
    const next = current === "dark" ? "light" : "dark";
    document.documentElement.setAttribute("data-theme", next);
    localStorage.setItem(THEME_KEY, next);
    this.toast(`Switched to ${next} theme`, "info");
  }

  async loadState() {
    // 1. Try local storage first for speed
    const local = localStorage.getItem(STORAGE_KEY);
    if (local) {
      try {
        this.state = JSON.parse(local);
      } catch (e) {
        console.error("Failed to parse local state", e);
      }
    }

    // 2. Fetch fresh state from backend
    try {
      const res = await fetch("/api/state");
      if (res.ok) {
        const remoteState = await res.json();
        if (remoteState && remoteState.scenes) {
          // If remote is newer or local was empty, use remote
          if (!this.state || (remoteState.updatedAt && new Date(remoteState.updatedAt) > new Date(this.state.updatedAt || 0))) {
            this.state = remoteState;
            localStorage.setItem(STORAGE_KEY, JSON.stringify(this.state));
          }
        }
      }
    } catch (e) {
      console.warn("Backend state unavailable; using offline local state.", e);
    }

    if (!this.state) {
      this.state = this.getDefaultState();
      this.saveLocalState();
    }
    return this.state;
  }

  saveLocalState() {
    if (this.state) {
      this.state.updatedAt = new Date().toISOString();
      localStorage.setItem(STORAGE_KEY, JSON.stringify(this.state));
    }
  }

  async syncToCloud() {
    this.saveLocalState();
    try {
      const res = await fetch("/api/state", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ state: this.state, backup: true })
      });
      if (res.ok) {
        const data = await res.json();
        this.toast(`State synced successfully! Backup: ${data.backup}`, "success");
        return true;
      }
      throw new Error("Failed to save remote state");
    } catch (e) {
      this.toast(`Cloud sync offline. State preserved locally in browser.`, "warning");
      return false;
    }
  }

  async aiRewriteText(text, action = "rewrite") {
    try {
      const res = await fetch("/api/text", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ action, text, model: "openai/gpt-4o-mini" })
      });
      if (res.ok) {
        const data = await res.json();
        return data.text;
      }
    } catch (e) {
      console.error(e);
    }
    return text;
  }

  speakVoiceover(text) {
    if ("speechSynthesis" in window) {
      window.speechSynthesis.cancel();
      const utterance = new SpeechSynthesisUtterance(text);
      utterance.rate = 1.0;
      utterance.pitch = 1.0;
      window.speechSynthesis.speak(utterance);
      this.toast("Playing voiceover preview...", "info");
    } else {
      this.toast("Speech synthesis not supported on this browser", "warning");
    }
  }

  stopVoiceover() {
    if ("speechSynthesis" in window) {
      window.speechSynthesis.cancel();
    }
  }

  toast(message, type = "info") {
    let container = document.getElementById("toast-container");
    if (!container) {
      container = document.createElement("div");
      container.id = "toast-container";
      container.className = "toast-container";
      document.body.appendChild(container);
    }
    const toast = document.createElement("div");
    toast.className = `toast toast-${type}`;
    const icon = type === "success" ? "✅" : type === "warning" ? "⚠️" : "ℹ️";
    toast.innerHTML = `<span>${icon}</span> <span>${message}</span>`;
    container.appendChild(toast);
    setTimeout(() => {
      toast.style.opacity = "0";
      setTimeout(() => toast.remove(), 300);
    }, 3500);
  }

  injectHeaderAndFooter(activePage) {
    // Header
    const header = document.querySelector("header.app-header");
    if (header) {
      header.innerHTML = `
        <div class="header-inner">
          <a href="index.html" class="brand-badge">
            <div class="brand-icon">⚡</div>
            <span>Aug Video #2 Studio</span>
          </a>
          <nav class="main-nav">
            <a href="index.html" class="${activePage === 'index' ? 'active' : ''}">Overview</a>
            <a href="research.html" class="${activePage === 'research' ? 'active' : ''}">Master Studio</a>
            <a href="timeline.html" class="${activePage === 'timeline' ? 'active' : ''}">Timeline</a>
            <a href="shotlist.html" class="${activePage === 'shotlist' ? 'active' : ''}">Shotlist Grid</a>
            <a href="scenes.html" class="${activePage === 'scenes' ? 'active' : ''}">Scenes</a>
            <a href="voice_over.html" class="${activePage === 'voice_over' ? 'active' : ''}">Teleprompter</a>
            <a href="script_guru.html" class="${activePage === 'script_guru' ? 'active' : ''}">Script Guru</a>
            <a href="gallery.html" class="${activePage === 'gallery' ? 'active' : ''}">Assets Gallery</a>
            <a href="tactic.html" class="${activePage === 'tactic' ? 'active' : ''}">Tactics & SOPs</a>
            <a href="analysis.html" class="${activePage === 'analysis' ? 'active' : ''}">Analytics</a>
          </nav>
          <div class="header-actions">
            <button class="btn btn-sm" id="btn-sync" title="Sync state to Cloud / Local Snapshots">☁️ Sync State</button>
            <button class="btn btn-icon btn-sm" id="btn-theme" title="Toggle Theme">🌓</button>
          </div>
        </div>
      `;

      document.getElementById("btn-theme")?.addEventListener("click", () => this.toggleTheme());
      document.getElementById("btn-sync")?.addEventListener("click", () => this.syncToCloud());
    }

    // Roger Rabbit Signature Footer (Mandated by Section 11 of specs.md)
    let footer = document.querySelector("footer.signature-footer");
    if (!footer) {
      footer = document.createElement("footer");
      footer.className = "signature-footer";
      document.body.appendChild(footer);
    }
    footer.innerHTML = `
      <div class="signature-container">
        <div class="signature-meta">
          <strong>aug-video-animation-2</strong> • 16-Stage Reverse Engineering Production System<br>
          Cloud & Local State Persistence • OpenRouter AI Script Optimization • 26 Flow Media Manifests
        </div>
        <div class="roger-rabbit-signature" title="Roger Rabbit Style Signature Outro">
          <div class="rr-cartoon-star">⭐</div>
          <div class="rr-text-wrap">
            <span class="rr-tagline">Directed & Engineered by</span>
            <span class="rr-handwritten-name">Rifat Erdem Sahin</span>
          </div>
        </div>
      </div>
    `;
  }

  getDefaultState() {
    return {
      version: 1,
      updatedAt: new Date().toISOString(),
      reverseVideo: {
        title: "Reverse Response Reference Video",
        sourceUrl: "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
        localPath: "uploads/reference_video.mp4",
        notes: "Reverse-engineering high retention YouTube tech architecture explainer format."
      },
      scenes: []
    };
  }
}

window.studio = new StudioEngine();
