# 🎶 Handsfree-Chords

> **Hands-free, synchronized chord sheets for musicians (pianists, guitarists & live performers) with auto-scroll and AI face/head tracking.** 🎹🎸✨
> 
> 🌐 **Live Demo (Web / Tablet / Mobile):** [https://palladius.github.io/handsfree-chords/](https://palladius.github.io/handsfree-chords/)

Musicians on stage have their hands occupied playing instruments. Turning pages or scrolling screens with fingers disrupts the flow and ruins live performances. 

**Handsfree-Chords** solves this with:
1. **`spartiti-md` format**: Clean Markdown + ChordPro inline chords (`[DO]Su di noi...`), zero unstable spacing, pianist-friendly bass notes (`[DO/MI]`), and semantic section emojis.
2. **Deterministic Time-Synced Auto-scroll**: Timestamped cues (`[mm:ss.xx]`) synced with the song structure, avoiding clumsy constant-speed scrolling.
3. **Emergency Offset Controls**: Instant $\pm 20$s jump triggers for quick drift recovery.
4. **Hands-free AI Vision Page Turning**: Client-side computer vision (Google MediaPipe Face Mesh) detecting intentional head nods/flicks to scroll forward and backward without taking hands off the keys or strings.

---

## 📂 Repository Structure

- `SPECS.md` — Complete architectural specifications and roadmap.
- `songs/` — Library of time-synced song sheets in `spartiti-md` format.
  - `su-di-noi.md` (Pupo)
  - `gloria.md` (Umberto Tozzi)
- `scripts/` — Linter and song validation utilities.

---

## 🚀 Quick Start (Song Validation)

Validate that any chord sheet has valid chord notations, no typos, and perfectly balanced brackets:

```bash
python3 scripts/validate_spartito.py songs/gloria.md
```

---

## 📄 License
MIT © Riccardo Carlesso (palladius)
