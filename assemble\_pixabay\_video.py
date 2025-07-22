#!/usr/bin/env python3
"""
Builds a 60‑second vertical video ‘The Joy of Christ’s Return’ using only
royalty‑free assets from Pixabay.

• Requires: moviepy==1.0.3 requests tqdm
• Needs an environment variable PIXABAY_KEY  – or will prompt for it.
• Optional: vo.wav  (voice‑over)  |  music.mp3  (background music)

Usage:   python assemble_pixabay_video.py
"""

import os, sys, requests, json, re, textwrap
from pathlib import Path
from urllib.parse import urlencode, quote_plus
from tqdm import tqdm
from moviepy.editor import (
    VideoFileClip, ImageClip, concatenate_videoclips,
    CompositeAudioClip, AudioFileClip, afx
)

###############################################################################
# 1.  Config – search queries + segment lengths
###############################################################################
SEGMENTS = [
    ("sunrise timelapse",           5,  "sunrise.mp4"),
    ("diverse friends smiling",     5,  "friends.mp4"),
    ("bible pages turning",        10,  "bible.mp4"),
    ("family hug reunion",         10,  "family.mp4"),
    ("people dancing field",       10,  "dancing.mp4"),
    ("worship church crowd",       10,  "worship.mp4"),
    ("cross silhouette sunset",    10,  "cross.mp4")
]

# folder to keep everything neat
ASSETS = Path("assets");  ASSETS.mkdir(exist_ok=True)

###############################################################################
# 2.  Pixabay helper
###############################################################################
API_KEY = os.getenv("PIXABAY_KEY") or input("Enter your Pixabay API key: ").strip()
BASE = "https://pixabay.com/api/videos/"

def px_search_video(query: str) -> str:
    "Return direct MP4 URL (largest size) for first Pixabay hit of query."
    params = dict(key=API_KEY, q=query, safesearch="true", per_page=3)
    resp   = requests.get(BASE, params=params, timeout=15)
    resp.raise_for_status()                               # <-- real error if key bad
    data   = resp.json()
    hits   = data.get("hits")
    if not hits:
        raise RuntimeError(f"No Pixabay results for {query!r}")
    best   = hits[0]["videos"]["large"] or hits[0]["videos"]["medium"]
    return best["url"]

def download(url: str, dst: Path):
    "Stream a file to disk with progress bar."
    if dst.exists(): return
    with requests.get(url, stream=True, timeout=60) as r:
        r.raise_for_status()
        total = int(r.headers.get("content-length", 0))
        with open(dst, "wb") as f, tqdm(
                total=total, unit="B", unit_scale=True,
                desc=f"DL {dst.name}") as bar:
            for chunk in r.iter_content(8192):
                f.write(chunk); bar.update(len(chunk))

###############################################################################
# 3.  Fetch every segment
###############################################################################
clips = []
for query, dur, fname in SEGMENTS:
    fp = ASSETS / fname
    print(f"Fetching [{query}] → {fname}")
    url = px_search_video(query)
    download(url, fp)
    # load & trim
    clip = VideoFileClip(str(fp)).subclip(0, dur)
    # resize to vertical 1080×1920 (crop wide clips)
    clip = clip.resize(height=1920) if clip.w < clip.h else clip.resize(width=1080)
    clips.append(clip.set_fps(30))

video = concatenate_videoclips(clips, method="compose")

###############################################################################
# 4.  Optional audio (VO + music)
###############################################################################
audios = []
if Path("music.mp3").exists():
    # lower bg music by 12 dB
    audios.append(AudioFileClip("music.mp3").volumex(0.25))
if Path("vo.wav").exists():
    audios.append(AudioFileClip("vo.wav").volumex(1.0))

if audios:
    from moviepy.audio.AudioClip import CompositeAudioClip
    audio = CompositeAudioClip(audios)
    # gentle 1‑sec fade‑out
    audio = audio.audio_fadeout(1)
    video = video.set_audio(audio)

###############################################################################
# 5.  Export
###############################################################################
out = "final_video.mp4"
print(f"Rendering {out} …")
video.write_videofile(
    out,
    codec="libx264",
    audio_codec="aac",
    bitrate="2e7",        # ~20 Mb/s
    fps=30,
    preset="medium"
)
print("✅  Done!  Check", out)
