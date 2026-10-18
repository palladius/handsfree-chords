#!/usr/bin/env python3
"""
Handsfree-Chords local web server.
Exposes JSON APIs for songs, renders lyrics, and serves the live stage player.
Zero external pip dependencies: built with Python standard library http.server!
"""

import os
import re
import json
from pathlib import Path
from http.server import HTTPServer, SimpleHTTPRequestHandler

BASE_DIR = Path(__file__).resolve().parent
SONGS_DIR = BASE_DIR.parent / "songs"
TEMPLATES_DIR = BASE_DIR / "templates"


def parse_timestamp_to_seconds(ts_str: str) -> float:
    """Converts mm:ss or mm:ss.xx to seconds float."""
    m = re.match(r"(\d+):(\d+(?:\.\d+)?)", ts_str)
    if m:
        minutes = int(m.group(1))
        seconds = float(m.group(2))
        return minutes * 60 + seconds
    return 0.0


def parse_frontmatter(yaml_text: str) -> dict:
    """Zero-dependency parser for flat YAML frontmatter."""
    meta = {}
    for line in yaml_text.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if ":" in line:
            key, val = line.split(":", 1)
            key = key.strip()
            val = val.strip().strip('"').strip("'")
            meta[key] = val
    return meta


def parse_song_file(file_path: Path):
    """
    Parses a spartiti-md file:
    Extracts YAML Frontmatter, Piano Tips, and lines with chords & timestamps.
    """
    content = file_path.read_text(encoding="utf-8")
    meta = {}
    tips = ""
    raw_lines = content.splitlines()

    # 1. Parse YAML Frontmatter
    idx = 0
    if raw_lines and raw_lines[0].strip() == "---":
        yaml_lines = []
        idx = 1
        while idx < len(raw_lines) and raw_lines[idx].strip() != "---":
            yaml_lines.append(raw_lines[idx])
            idx += 1
        idx += 1  # Skip closing ---
        meta = parse_frontmatter("\n".join(yaml_lines))

    # Extract BPM and Time Signature if not in frontmatter
    if "bpm" not in meta:
        bpm_m = re.search(r'bpm:\s*(\d+)', content, re.I)
        if bpm_m:
            meta["bpm"] = int(bpm_m.group(1))
        else:
            bpm_m2 = re.search(r'[~≈]\s*(\d+)\s*bpm', content, re.I)
            if bpm_m2:
                meta["bpm"] = int(bpm_m2.group(1))
            else:
                bpm_m3 = re.search(r'(\d+)\s*bpm', content, re.I)
                if bpm_m3:
                    meta["bpm"] = int(bpm_m3.group(1))
    else:
        try:
            meta["bpm"] = int(meta["bpm"])
        except (ValueError, TypeError):
            pass

    if "time_signature" not in meta:
        ts_m = re.search(r'time_signature:\s*["\']?(\d+/\d+)', content, re.I)
        if ts_m:
            meta["time_signature"] = ts_m.group(1)
        else:
            ts_m2 = re.search(r'tempo:\*\*\s*(\d+/\d+)', content, re.I)
            if ts_m2:
                meta["time_signature"] = ts_m2.group(1)
            else:
                meta["time_signature"] = "4/4"

    # 2. Parse Remaining Markdown
    parsed_lines = []
    current_time_sec = 0.0
    time_increment = 6.0  # fallback step if timestamps aren't present on every line

    while idx < len(raw_lines):
        line = raw_lines[idx].rstrip()
        idx += 1

        # Check for title if not in YAML
        if line.startswith("# 🎵 ") and "title" not in meta:
            title_part = line.replace("# 🎵 ", "").strip()
            if "—" in title_part:
                parts = title_part.split("—")
                meta["title"] = parts[0].strip()
                meta["artist"] = parts[1].strip()
            else:
                meta["title"] = title_part

        # Check for Piano Tip in blockquote
        if "Piano Tip" in line:
            m = re.search(r"Piano Tip[s]?:\*\*\s*(.*)", line)
            if m:
                tips = m.group(1).strip()

        # Section headers
        if line.startswith("### "):
            section_title = line.replace("### ", "").strip()
            sec_time = None
            ts_m = re.search(r"\[(\d+:\d+(?:\.\d+)?)\]", section_title)
            if ts_m:
                sec_time = parse_timestamp_to_seconds(ts_m.group(1))
                current_time_sec = sec_time
                section_title = section_title.replace(ts_m.group(0), "").strip()

            parsed_lines.append({
                "type": "section",
                "content": section_title,
                "seconds": sec_time
            })
            continue

        # Skip dividers, title header, empty lines or blockquote info
        if line.startswith("---") or line.startswith(">") or line.startswith("# 🎵") or not line.strip():
            continue

        # Lyric / Chord line
        line_sec = None
        ts_m = re.match(r"^\[(\d+:\d+(?:\.\d+)?)\]\s*(.*)", line)
        if ts_m:
            line_sec = parse_timestamp_to_seconds(ts_m.group(1))
            current_time_sec = line_sec
            line = ts_m.group(2)
        else:
            current_time_sec += time_increment
            line_sec = round(current_time_sec, 1)

        # Convert chords [Chord] to styled HTML spans
        rendered_html = re.sub(
            r"\[(.*?)\]",
            r'<span class="chord">\1</span>',
            line
        )

        parsed_lines.append({
            "type": "lyric",
            "raw": line,
            "rendered": rendered_html,
            "seconds": line_sec
        })

    return {
        "filename": file_path.name,
        "meta": meta,
        "tips": tips,
        "lines": parsed_lines
    }


class ChordsHandler(SimpleHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/" or self.path == "/index.html":
            index_path = TEMPLATES_DIR / "index.html"
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(index_path.read_bytes())
            return

        # API: List all songs
        if self.path == "/api/songs":
            songs = []
            for f in sorted(SONGS_DIR.glob("*.md")):
                try:
                    data = parse_song_file(f)
                    songs.append({
                        "filename": f.name,
                        "title": data["meta"].get("title", f.stem),
                        "artist": data["meta"].get("artist", "Sconosciuto"),
                        "key": data["meta"].get("original_key", ""),
                        "bpm": data["meta"].get("bpm"),
                        "time_signature": data["meta"].get("time_signature", "4/4"),
                    })
                except Exception as e:
                    print(f"Errore lettura {f.name}: {e}")

            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.end_headers()
            self.wfile.write(json.dumps(songs, ensure_ascii=False).encode("utf-8"))
            return

        # API: Get single song details
        if self.path.startswith("/api/song/"):
            filename = self.path.replace("/api/song/", "")
            target_file = SONGS_DIR / filename
            if target_file.exists():
                song_data = parse_song_file(target_file)
                self.send_response(200)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.end_headers()
                self.wfile.write(json.dumps(song_data, ensure_ascii=False).encode("utf-8"))
                return
            else:
                self.send_response(404)
                self.end_headers()
                self.wfile.write(b'{"error": "Song not found"}')
                return

        super().do_GET()


def run_server(port=4321):
    server = HTTPServer(("127.0.0.1", port), ChordsHandler)
    print(f"🎹 Handsfree-Chords server pronto su: http://localhost:{port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nArresto server.")
        server.server_close()


if __name__ == "__main__":
    run_server()
