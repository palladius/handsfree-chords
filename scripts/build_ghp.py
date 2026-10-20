#!/usr/bin/env python3
"""
Build static bundle for GitHub Pages in docs/.
Reads all songs in songs/, parses them into static JSON,
and creates docs/index.html and docs/songs.json.
"""

import glob
import json
import re
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
SONGS_DIR = BASE_DIR / "songs"
DOCS_DIR = BASE_DIR / "docs"
DOCS_DIR.mkdir(parents=True, exist_ok=True)


def slugify(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", (text or "").lower()).strip("-")


def resolve_cover_images(filename: str, meta: dict):
    stem = Path(filename).stem
    artist_slug = slugify(meta.get("artist", ""))
    cover = meta.get("cover") or meta.get("image") or meta.get("song_image") or ""
    artist_image = meta.get("artist_image") or meta.get("artist_cover") or ""
    exts = ("jpg", "jpeg", "png", "webp", "svg")
    if not cover:
        for ext in exts:
            for rel in (f"images/songs/{stem}.{ext}", f"images/{stem}.{ext}"):
                if (DOCS_DIR / rel).exists():
                    cover = rel
                    break
            if cover:
                break
    if not artist_image and artist_slug:
        for ext in exts:
            rel = f"images/artists/{artist_slug}.{ext}"
            if (DOCS_DIR / rel).exists():
                artist_image = rel
                break
    return cover, artist_image


def parse_frontmatter(yaml_text: str) -> dict:
    meta = {}
    for line in yaml_text.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if ":" in line:
            k, v = line.split(":", 1)
            meta[k.strip()] = v.strip().strip('"').strip("'")
    return meta


def parse_seconds(ts_str):
    m = re.match(r"(\d+):(\d+(?:\.\d+)?)", ts_str)
    return int(m.group(1)) * 60 + float(m.group(2)) if m else 0.0


def extract_harmonic_summary(raw_lines: list) -> dict:
    """Extract unique chords for strofa, ritornello, and bridge."""
    sections = {}
    curr_sec = None
    for line in raw_lines:
        if line.startswith("### "):
            title = line.replace("### ", "").strip().upper()
            if any(k in title for k in ["STROFA", "VERSE", "A1", "A2"]):
                curr_sec = "strofa"
            elif any(k in title for k in ["RITORNELLO", "CHORUS", "HOOK", "RIT"]):
                curr_sec = "ritornello"
            elif any(k in title for k in ["BRIDGE", "SPECIAL", "INCISO"]):
                curr_sec = "bridge"
            else:
                curr_sec = None
        elif curr_sec and not line.startswith("---") and not line.startswith(">"):
            chords = re.findall(r"\[([a-zA-Z0-9#b♯♭/]+)\]", line)
            if chords:
                if curr_sec not in sections:
                    sections[curr_sec] = []
                for c in chords:
                    if c not in sections[curr_sec]:
                        sections[curr_sec].append(c)
    return sections


def build_docs():
    all_songs = {}
    song_list = []

    for f in sorted(SONGS_DIR.glob("*.md")):
        lines = f.read_text(encoding="utf-8").splitlines()
        meta = {}
        tips = ""
        idx = 0
        if lines and lines[0].strip() == "---":
            yaml_lines = []
            idx = 1
            while idx < len(lines) and lines[idx].strip() != "---":
                yaml_lines.append(lines[idx])
                idx += 1
            idx += 1
            meta = parse_frontmatter("\n".join(yaml_lines))

        raw_content = "\n".join(lines)
        if "bpm" not in meta:
            bpm_m = re.search(r'bpm:\s*(\d+)', raw_content, re.I)
            if bpm_m:
                meta["bpm"] = int(bpm_m.group(1))
            else:
                bpm_m2 = re.search(r'[~≈]\s*(\d+)\s*bpm', raw_content, re.I)
                if bpm_m2:
                    meta["bpm"] = int(bpm_m2.group(1))
                else:
                    bpm_m3 = re.search(r'(\d+)\s*bpm', raw_content, re.I)
                    if bpm_m3:
                        meta["bpm"] = int(bpm_m3.group(1))
        else:
            try:
                meta["bpm"] = int(meta["bpm"])
            except (ValueError, TypeError):
                pass

        if "time_signature" not in meta:
            ts_m = re.search(r'time_signature:\s*["\']?(\d+/\d+)', raw_content, re.I)
            if ts_m:
                meta["time_signature"] = ts_m.group(1)
            else:
                ts_m2 = re.search(r'tempo:\*\*\s*(\d+/\d+)', raw_content, re.I)
                if ts_m2:
                    meta["time_signature"] = ts_m2.group(1)
                else:
                    meta["time_signature"] = "4/4"

        if not meta.get("original_key"):
            if meta.get("key"):
                meta["original_key"] = meta["key"]
            else:
                key_m = re.search(r"Tonalit[àa][^:\n]*:\*\*\s*[^(\n]*\(([A-G][#b♯♭]?m?)\)", raw_content)
                if key_m:
                    meta["original_key"] = key_m.group(1)
                else:
                    meta["original_key"] = "C"

        parsed_lines = []
        curr_time = 0.0
        while idx < len(lines):
            line = lines[idx].rstrip()
            idx += 1
            if line.startswith("# 🎵 ") and "title" not in meta:
                t = line.replace("# 🎵 ", "").strip()
                if "—" in t:
                    parts = t.split("—")
                    meta["title"] = parts[0].strip()
                    meta["artist"] = parts[1].strip()
                else:
                    meta["title"] = t

            if "Piano Tip" in line:
                m = re.search(r"Piano Tip[s]?:\*\*\s*(.*)", line)
                if m:
                    tips = m.group(1).strip()

            if line.startswith("### "):
                sec_title = line.replace("### ", "").strip()
                sec_time = None
                ts_m = re.search(r"\[(\d+:\d+(?:\.\d+)?)\]", sec_title)
                if ts_m:
                    sec_time = parse_seconds(ts_m.group(1))
                    curr_time = sec_time
                    sec_title = sec_title.replace(ts_m.group(0), "").strip()
                parsed_lines.append({"type": "section", "content": sec_title, "seconds": sec_time})
                continue

            if line.startswith("---") or line.startswith(">") or not line.strip():
                continue

            line_sec = None
            ts_m = re.match(r"^\[(\d+:\d+(?:\.\d+)?)\]\s*(.*)", line)
            if ts_m:
                line_sec = parse_seconds(ts_m.group(1))
                curr_time = line_sec
                line = ts_m.group(2)
            else:
                curr_time += 6.0
                line_sec = round(curr_time, 1)

            rendered = re.sub(r"\[(.*?)\]", r'<span class="chord">\1</span>', line)
            parsed_lines.append({"type": "lyric", "raw": line, "rendered": rendered, "seconds": line_sec})

        summary = extract_harmonic_summary(lines)
        cover, artist_image = resolve_cover_images(f.name, meta)
        if cover:
            meta["cover"] = cover
        if artist_image:
            meta["artist_image"] = artist_image
        if "audio" not in meta:
            audio_rel = f"audio/{f.stem}.mp3"
            if (DOCS_DIR / audio_rel).is_file():
                meta["audio"] = audio_rel

        song_obj = {
            "filename": f.name,
            "meta": meta,
            "tips": tips,
            "summary": summary,
            "lines": parsed_lines
        }
        all_songs[f.name] = song_obj
        song_list.append({
            "filename": f.name,
            "title": meta.get("title", f.stem),
            "artist": meta.get("artist", ""),
            "key": meta.get("key") or meta.get("original_key") or meta.get("base_chord", ""),
            "bpm": meta.get("bpm"),
            "time_signature": meta.get("time_signature", "4/4"),
            "cover": meta.get("cover", ""),
            "artist_image": meta.get("artist_image", ""),
            "audio": meta.get("audio", ""),
            "summary": summary
        })

    # Write songs.json
    (DOCS_DIR / "songs.json").write_text(json.dumps(all_songs, ensure_ascii=False, indent=2), encoding="utf-8")
    (DOCS_DIR / "songs_list.json").write_text(json.dumps(song_list, ensure_ascii=False, indent=2), encoding="utf-8")

    # Read template and embed or adapt for static hosting
    template_html = (BASE_DIR / "app" / "templates" / "index.html").read_text(encoding="utf-8")

    # Replace fetch APIs with static JSON logic
    static_js_logic = """
    // Static GitHub Pages Data Loading
    let staticSongsMap = {};

    async function init() {
      renderBeatDots();
      updateTransposeDisplay();
      try {
        const res = await fetch('songs.json');
        staticSongsMap = await res.json();
        const select = document.getElementById('songSelect');
        const songEntries = Object.values(staticSongsMap);
        allSongsList = songEntries.map(s => ({
          filename: s.filename,
          title: s.meta.title || s.filename,
          artist: s.meta.artist || 'Sconosciuto',
          key: s.meta.key || s.meta.original_key || s.meta.base_chord || '',
          bpm: s.meta.bpm,
          time_signature: s.meta.time_signature || '4/4',
          cover: s.meta.cover || '',
          artist_image: s.meta.artist_image || '',
          audio: s.meta.audio || '',
          summary: s.summary || {}
        }));
        select.innerHTML = songEntries.map(s => `<option value="${s.filename}">${s.meta.title || s.filename} (${s.meta.artist || ''})</option>`).join('');
        renderCatalog();
        showCatalogView();
      } catch (e) {
        console.error("Errore caricamento songs.json:", e);
      }
    }

    async function loadSelectedSong() {
      const filename = document.getElementById('songSelect').value || activeSongFilename;
      if (!filename || !staticSongsMap[filename]) return;
      activeSongFilename = filename;
      pause();
      currentTime = 0;

      songData = staticSongsMap[filename];
      renderSong(songData);
      updateTransposeDisplay();
      updateTimeDisplay();
      showPlayerView();
      play();
    }
    """

    # Replace the fetch block in template
    fetch_pattern = re.compile(r"async function init\(\)[\s\S]*?showPlayerView\(\);\s*play\(\);\s*}", re.MULTILINE)
    static_html = fetch_pattern.sub(static_js_logic.strip(), template_html)

    (DOCS_DIR / "index.html").write_text(static_html, encoding="utf-8")
    print(f"✅ GitHub Pages static site generato con successo in docs/ ({len(song_list)} brani)!")


if __name__ == "__main__":
    build_docs()
