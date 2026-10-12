# 📄 SPECS.md — Handsfree-Chords Architecture & Roadmap

## 1. Vision & Problem Statement
Live musicians (pianists, keyboardists, guitarists) need both hands on their instruments.
Existing solutions suffer from major drawbacks:
- **Blind autoscroll**: Fixed pixel-per-second scrolling fails because verses and choruses vary in pacing.
- **Physical pedals (Bluetooth PageFlips)**: Expensive (\$100-\$150), require setup, battery management, and take foot real-estate (especially for pianisti who already use sustain/una-corda pedals!).
- **Messy chord layouts**: Standard tabs break on different screen sizes and zoom levels.

**Handsfree-Chords** introduces a synchronized web app running locally on tablet/mobile/desktop browsers with zero external hardware required.

---

## 2. Data Specification (`spartiti-md` + Time Tags)

Each song is an enhanced Markdown file supporting inline ChordPro format with LRC/SRT-style timestamps `[mm:ss.xx]`:

```markdown
---
title: Gloria
artist: Umberto Tozzi
bpm: 130
key: B
duration: 265
---

### 🎹 INTRO [00:00.00]
`| [SI] | [MI] | [SI] | [MI] |`

### 🎤 STROFA 1 [00:15.50]
[SI]Gloria, manchi tu nell'[MI]aria  
[00:22.00] manchi ad una [SI]mano che lavora [MI]piano  
[00:28.50] manchi a questa [SI]bocca che cibo più non [MI]tocca  

### 🌈 PRE-CHORUS [00:41.00]
Gloria sui tuoi [DO#m]fianchi  
la mat[FA#7]tina nasce il [SI]sole  
```

### Core Format Rules:
1. **Chords Inline**: `[DO]Testo` ensures chords stay bound to exact syllables regardless of font changes.
2. **Pianist & Guitarist Friendly**: Supports slash/bass chords (`[DO/MI]`, `[G/B]`), common jazz extensions (`maj7, add9, sus4`).
3. **No guitar tablature noise**: Focus strictly on chords, lyrics, and harmonic transitions.

---

## 3. Playback & Autoscroll Engine

1. **Playback Clock**:
   - Web Audio API master clock or silent internal timer tracking elapsed seconds.
   - Optional backing track / YouTube audio sync.
2. **Smooth Target Scrolling**:
   - When the clock passes a cue timestamp, the UI smoothly positions the active block in the upper third of the screen (the sweet reading spot on stage).
3. **Manual Drift Recovery ($\pm 20\text{s}$)**:
   - Big touch buttons & keyboard arrow shortcuts:
     - `⬅️ -20s` (Jump back 20 seconds)
     - `➡️ +20s` (Jump forward 20 seconds)
     - `Tap-on-line`: Tapping any line jumps the timer instantly to that timestamp.
   - *Why 20s?* The viewport maintains an active cache/view of ~30-40 seconds of lyrics; smaller skips (e.g. 5s) require too many taps while playing.

---

## 4. Vision Engine: Camera-Based Hands-Free Control

### Technology Stack
- **Framework**: Client-side JavaScript / WebAssembly using **Google MediaPipe Face Mesh** (runs in a WebWorker, 100% private, zero video uploaded).

### Gesture Recognition Model
1. **Page Forward (Next Section)**:
   - **Intentional Head Flick (Right)**: Fast horizontal yaw rotation ($> +25^\circ$) followed by return to center within 400ms.
   - **Alternative**: Prolonged blink or brow raise.
2. **Page Backward (Previous Section)**:
   - **Intentional Head Flick (Left)**: Fast horizontal yaw rotation ($< -25^\circ$) with quick reset.
3. **Failsafe / Anti-Thrash Cooldown**:
   - 1.5-second cooldown after every gesture trigger to prevent erratic scrolling during natural stage movements and headbanging.
   - Small non-distracting visual indicator dot (🟢 green: tracked, 🟡 yellow: calibrating).

---

## 5. UI/UX Guidelines for Stage Use
- **High-Contrast Dark Theme**: Deep black background (`#121212`), high-contrast white text, warm amber/yellow chords (`#FFD166`).
- **Responsive Viewport**: Optimized for iPads, Android tablets, and smartphones on music stands.
- **Offline First (PWA)**: All songs cached locally via service worker.

---

## 6. Implementation Milestones

- [x] **Milestone 0**: Define `spartiti-md` format, parser validator, and initial songs (*Pupo - Su di noi*, *Tozzi - Gloria*).
- [ ] **Milestone 1**: Static web viewer (PWA) with high-contrast stage UI.
- [ ] **Milestone 2**: Timestamp sync player & autoscroll with $\pm 20$s jump controls.
- [ ] **Milestone 3**: MediaPipe Face Mesh integration for hands-free head nod detection.
- [ ] **Milestone 4**: Song management, search, and local `.md` import/export.
