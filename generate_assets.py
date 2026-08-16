#!/usr/bin/env python3
"""Generate placeholder visual assets for stills and video_flow posters."""
import json
import os

with open('stills/images_manifest.json') as f:
    stills = json.load(f)

with open('video_flow/video_flow_manifest.json') as f:
    video_manifest = json.load(f)

def make_svg(title, subtitle, badge, color="#3b82f6", icon="🎬"):
    return f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1920 1080" width="100%" height="100%">
  <defs>
    <linearGradient id="bg" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#0b0e14" />
      <stop offset="100%" stop-color="#161b26" />
    </linearGradient>
    <linearGradient id="glow" x1="0%" y1="0%" x2="100%" y2="0%">
      <stop offset="0%" stop-color="{color}" stop-opacity="0.8"/>
      <stop offset="100%" stop-color="#8b5cf6" stop-opacity="0.8"/>
    </linearGradient>
  </defs>
  <rect width="1920" height="1080" fill="url(#bg)"/>
  <circle cx="960" cy="540" r="420" fill="none" stroke="rgba(255,255,255,0.03)" stroke-width="2"/>
  <circle cx="960" cy="540" r="280" fill="none" stroke="rgba(255,255,255,0.05)" stroke-width="2" stroke-dasharray="12 8"/>
  <rect x="120" y="100" width="1680" height="880" rx="24" fill="rgba(255,255,255,0.02)" stroke="rgba(255,255,255,0.08)" stroke-width="2"/>
  
  <!-- Top Badge -->
  <rect x="160" y="140" width="280" height="44" rx="8" fill="rgba(255,255,255,0.06)" stroke="{color}" stroke-width="1.5"/>
  <text x="300" y="168" fill="{color}" font-family="-apple-system, BlinkMacSystemFont, Segoe UI, Roboto, sans-serif" font-size="20" font-weight="700" text-anchor="middle" letter-spacing="1">{badge.upper()}</text>
  
  <!-- Icon & Main Visual -->
  <circle cx="960" cy="460" r="90" fill="url(#glow)"/>
  <text x="960" y="490" font-size="72" text-anchor="middle">{icon}</text>
  
  <!-- Title & Subtitle -->
  <text x="960" y="650" fill="#f0f3f8" font-family="-apple-system, BlinkMacSystemFont, Segoe UI, Roboto, sans-serif" font-size="44" font-weight="800" text-anchor="middle">{title}</text>
  <text x="960" y="715" fill="#9ba3b4" font-family="-apple-system, BlinkMacSystemFont, Segoe UI, Roboto, sans-serif" font-size="26" font-weight="400" text-anchor="middle">{subtitle}</text>
  
  <!-- Footer Brand -->
  <line x1="200" y1="900" x2="1720" y2="900" stroke="rgba(255,255,255,0.06)" stroke-width="2"/>
  <text x="200" y="935" fill="#626a7e" font-family="-apple-system, BlinkMacSystemFont, Segoe UI, Roboto, sans-serif" font-size="20">AUG VIDEO ANIMATION #2 • PRODUCTION WORKBENCH</text>
  <text x="1720" y="935" fill="#3b82f6" font-family="-apple-system, BlinkMacSystemFont, Segoe UI, Roboto, sans-serif" font-size="20" font-weight="600" text-anchor="end">DELIVERYPILOT / RIFAT ERDEM SAHIN</text>
</svg>"""

for item in stills:
    fpath = item['file']
    os.makedirs(os.path.dirname(fpath), exist_ok=True)
    svg_content = make_svg(
        title=item['caption'],
        subtitle=f"Stage {item['stage']} • {item['stageName']} Stage Asset",
        badge=f"STAGE {item['stage']} // {item['stageName']}",
        color="#3b82f6" if item.get('voiceoverDefault') else "#10b981",
        icon="🖼️"
    )
    with open(fpath, 'w') as out:
        out.write(svg_content)

for item in video_manifest['files']:
    fpath = os.path.join('video_flow', item['frame'])
    os.makedirs(os.path.dirname(fpath), exist_ok=True)
    svg_content = make_svg(
        title=f"Clip #{item['seq']}: {item['title']}",
        subtitle=f"Duration: {item['duration']}s • Slug: {item['slug']}",
        badge=f"FLOW CLIP {item['seq']:02d} // SCENE {item['scene']}",
        color="#8b5cf6",
        icon="🎥"
    )
    with open(fpath, 'w') as out:
        out.write(svg_content)

# Also create simulation readme
with open('3_Simulation/readme.md', 'w') as f:
    f.write("# 3_Simulation Directory\\n\\nContains Canva voiceover exports and raw master media files for simulation testing.\\n")

print("Generated all stills and video flow assets successfully.")
