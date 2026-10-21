import unittest
from pathlib import Path
import sys

# Add scripts and app directories to path
SKILL_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(SKILL_DIR / "scripts"))
sys.path.insert(0, str(SKILL_DIR / "app"))

from validate_spartito import validate_spartito, parse_single_chord, extract_base_chord
from server import resolve_cover_images


class TestChordParsing(unittest.TestCase):
    def test_valid_italian_chords(self):
        valid = ["DO", "REm", "MIb", "FA#", "SOL7", "LAm7", "SIbmaj7", "DOsus4", "REdim", "SOL/SI", "DO/MI"]
        for c in valid:
            self.assertTrue(parse_single_chord(c), f"Expected '{c}' to be valid")

    def test_valid_english_chords(self):
        valid = ["C", "Dm", "Eb", "F#", "G7", "Am7", "Bbmaj7", "Csus4", "C/G", "F#/A#"]
        for c in valid:
            self.assertTrue(parse_single_chord(c), f"Expected '{c}' to be valid")

    def test_invalid_invented_notes(self):
        invalid = ["PO", "ZU", "MImario", "Cxyz", "HOLA", "BLA"]
        for c in invalid:
            self.assertFalse(parse_single_chord(c), f"Expected '{c}' to be invalid")

    def test_invalid_bass_notes(self):
        invalid = ["DO/P", "SOL/XYZ", "C/99"]
        for c in invalid:
            self.assertFalse(parse_single_chord(c), f"Expected '{c}' to be invalid")


class TestSpartitoValidation(unittest.TestCase):
    def test_valid_file_passes(self):
        sample = """
### 🎤 STROFA 1
[DO]Su di noi... ci avresti [MIm]scommesso tu
noi due respi[RE]rando lo stesso momento per fare l'a[SOL]more qua e [SI7]là
        """
        errors = validate_spartito(sample)
        self.assertEqual(len(errors), 0)

    def test_unclosed_bracket_detected(self):
        broken = "[DO Su di noi ci avresti scommesso"
        errors = validate_spartito(broken)
        self.assertGreater(len(errors), 0)
        self.assertTrue(any("Parentesi quadra non chiusa" in err[1] for err in errors))

    def test_unexpected_closing_bracket_detected(self):
        broken = "Su di noi] ci avresti scommesso"
        errors = validate_spartito(broken)
        self.assertGreater(len(errors), 0)
        self.assertTrue(any("Parentesi chiusa ']' inattesa" in err[1] for err in errors))

    def test_invented_chord_detected(self):
        broken = "[PIPPO]Su di noi ci avresti scommesso"
        errors = validate_spartito(broken)
        self.assertGreater(len(errors), 0)
        self.assertTrue(any("Accordo non valido o non riconosciuto: '[PIPPO]'" in err[1] for err in errors))

    def test_example_file(self):
        example_path = SKILL_DIR / "songs" / "su-di-noi.md"
        if not example_path.exists():
            example_path = SKILL_DIR / "examples" / "su-di-noi-pupo.md"
        self.assertTrue(example_path.exists())
        errors = validate_spartito(example_path.read_text(encoding="utf-8"))
        self.assertEqual(errors, [], f"Validation errors found in sample: {errors}")

    def test_all_songs_have_extracted_key_and_bpm(self):
        sys.path.insert(0, str(SKILL_DIR / "app"))
        from server import parse_song_file
        for song_path in sorted((SKILL_DIR / "songs").glob("*.md")):
            parsed = parse_song_file(song_path)
            key = parsed["meta"].get("original_key")
            bpm = parsed["meta"].get("bpm")
            self.assertTrue(key, f"Missing original_key for {song_path.name}")
            self.assertTrue(bpm, f"Missing bpm for {song_path.name}")

    def test_ui_template_contains_streamlined_controls_and_hud(self):
        html = (SKILL_DIR / "app" / "templates" / "index.html").read_text(encoding="utf-8")
        self.assertIn('id="settingsDialog" closedby="any"', html)
        self.assertIn('id="songProgressSlider"', html)
        self.assertIn('id="head-gesture-hud"', html)
        self.assertIn('id="split-divider"', html)

    def test_static_ghp_build_uses_static_songs_json(self):
        from build_ghp import build_docs
        import json
        build_docs()
        docs_html = (SKILL_DIR / "docs" / "index.html").read_text(encoding="utf-8")
        self.assertNotIn("fetch('/api/songs')", docs_html, "docs/index.html must not fetch /api/songs on GitHub Pages!")
        self.assertIn("fetch('songs.json')", docs_html, "docs/index.html must fetch static songs.json!")
        songs_data = json.loads((SKILL_DIR / "docs" / "songs.json").read_text(encoding="utf-8"))
        self.assertGreater(len(songs_data), 0, "docs/songs.json must not be empty!")

    def test_missing_yaml_base_chord_detected(self):
        no_yaml = """# 🎵 Test Song
### 🎤 STROFA 1
[C]Hello [G]world
"""
        errors = validate_spartito(no_yaml, require_base_chord=True)
        self.assertGreater(len(errors), 0)
        self.assertTrue(any("accordo di base" in err[1].lower() or "original_key" in err[1].lower() for err in errors))

    def test_invalid_yaml_base_chord_detected(self):
        bad_yaml = """---
title: Test Song
original_key: PIPPO
---
### 🎤 STROFA 1
[C]Hello [G]world
"""
        errors = validate_spartito(bad_yaml, require_base_chord=True)
        self.assertGreater(len(errors), 0)
        self.assertTrue(any("PIPPO" in err[1] for err in errors))

    def test_valid_yaml_base_chord_passes(self):
        good_yaml = """---
title: The Silent Man
artist: Dream Theater
original_key: A
---
### 🎤 STROFA 1
[F#m]A question of faith
"""
        self.assertEqual(extract_base_chord(good_yaml), "A")
        errors = validate_spartito(good_yaml, require_base_chord=True)
        self.assertEqual(errors, [])

    def test_all_songs_have_valid_base_chord_in_yaml(self):
        songs_dir = SKILL_DIR / "songs"
        missing_or_invalid = []
        for song_file in sorted(songs_dir.glob("*.md")):
            content = song_file.read_text(encoding="utf-8")
            base_chord = extract_base_chord(content)
            if not base_chord or not parse_single_chord(base_chord):
                missing_or_invalid.append(f"{song_file.name} (base_chord={base_chord!r})")
        self.assertEqual(
            missing_or_invalid,
            [],
            f"Canzoni senza accordo base valido nel YAML: {', '.join(missing_or_invalid)}"
        )


class TestCoverImages(unittest.TestCase):
    def test_resolve_cover_images_from_yaml(self):
        meta = {
            "title": "Fliegerlied",
            "artist": "Donikkl",
            "cover": "images/songs/fliegerlied.jpg",
            "artist_image": "images/artists/donikkl.jpg",
        }
        cover, artist_img = resolve_cover_images("fliegerlied.md", meta)
        self.assertEqual(cover, "images/songs/fliegerlied.jpg")
        self.assertEqual(artist_img, "images/artists/donikkl.jpg")

    def test_all_songs_have_existing_cover_and_artist_images(self):
        from server import parse_song_file
        docs_dir = SKILL_DIR / "docs"
        for song_path in sorted((SKILL_DIR / "songs").glob("*.md")):
            parsed = parse_song_file(song_path)
            cover = parsed["meta"].get("cover")
            artist_img = parsed["meta"].get("artist_image")
            self.assertTrue(cover, f"Missing cover in {song_path.name}")
            self.assertTrue(artist_img, f"Missing artist_image in {song_path.name}")
            self.assertTrue((docs_dir / cover).is_file(), f"Cover file not found on disk: {cover}")
            self.assertTrue((docs_dir / artist_img).is_file(), f"Artist image not found on disk: {artist_img}")

    def test_all_songs_have_existing_audio_mp3(self):
        from server import parse_song_file
        docs_dir = SKILL_DIR / "docs"
        for song_path in sorted((SKILL_DIR / "songs").glob("*.md")):
            parsed = parse_song_file(song_path)
            audio = parsed["meta"].get("audio")
            self.assertTrue(audio, f"Missing audio in {song_path.name}")
            self.assertTrue((docs_dir / audio).is_file(), f"Audio file not found on disk: {audio}")


if __name__ == "__main__":
    unittest.main()
