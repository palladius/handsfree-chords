#!/usr/bin/env python3
"""
Lint and validate Spartiti-MD files.
Verifies bracket matching, chord validity (Italian & Anglo-Saxon notation),
slash chords, and basic document structure.
"""

import sys
import re
from pathlib import Path
from typing import List, Optional, Tuple

# Valid root notes in Italian (solfeggio) and English/German notation
VALID_ROOTS = {
    # Italian
    "DO", "RE", "MI", "FA", "SOL", "LA", "SI",
    # English
    "C", "D", "E", "F", "G", "A", "B", "H"
}

ACCIDENTALS = ["#", "b", "♯", "♭"]

# Allowed chord qualities/suffixes for pop/jazz/rock/classical piano
CHORD_EXTENSIONS_PATTERN = r"""
    ^(
        m|min|-|maj|M|
        dim|aug|\+|°|ø|
        sus[24]?|add[29]?|
        2|4|5|6|7|9|11|13|
        m6|m7|m9|m11|m13|
        maj7|maj9|maj11|maj13|M7|
        dim7|aug7|m7b5|m\(maj7\)|
        sus|alt
    )*$
"""
CHORD_EXT_RE = re.compile(CHORD_EXTENSIONS_PATTERN, re.VERBOSE | re.IGNORECASE)


def parse_single_chord(chord_str: str) -> bool:
    """Validate a single chord like DO, MIm, C#7, SOL/SI, Bbmaj7."""
    chord_str = chord_str.strip()
    if not chord_str:
        return False

    # Handle slash chords (e.g., DO/MI or C/G)
    if "/" in chord_str:
        parts = chord_str.split("/")
        if len(parts) != 2:
            return False
        chord_part, bass_part = parts[0].strip(), parts[1].strip()
        # The bass note must be a valid note root + optional accidental
        bass_match = None
        for r in sorted(VALID_ROOTS, key=len, reverse=True):
            if bass_part.upper().startswith(r):
                rem = bass_part[len(r):]
                if rem in ["", "#", "b", "♯", "♭"]:
                    bass_match = True
                    break
        if not bass_match:
            return False
        chord_str = chord_part

    # Find matching root
    root_found = None
    upper = chord_str.upper()
    for r in sorted(VALID_ROOTS, key=len, reverse=True):
        if upper.startswith(r):
            root_found = r
            break

    if not root_found:
        return False

    suffix = chord_str[len(root_found):]

    # Check for accidental
    if suffix and suffix[0] in ACCIDENTALS:
        suffix = suffix[1:]

    # Check extensions
    # Clean parenthesis if any, like (add9) or (b5)
    cleaned_suffix = re.sub(r"[\(\)]", "", suffix)
    return bool(CHORD_EXT_RE.match(cleaned_suffix))


def extract_base_chord(content: str) -> Optional[str]:
    """
    Extract the base chord (key / original_key / base_chord) from the YAML frontmatter.
    Returns None if no YAML frontmatter or no base chord field is present.
    """
    lines = content.splitlines()
    if not lines or lines[0].strip() != "---":
        return None

    idx = 1
    meta = {}
    while idx < len(lines) and lines[idx].strip() != "---":
        line = lines[idx].strip()
        idx += 1
        if not line or line.startswith("#") or ":" not in line:
            continue
        k, v = line.split(":", 1)
        meta[k.strip()] = v.strip().strip('"').strip("'")

    # Match closing ---
    if idx >= len(lines) or lines[idx].strip() != "---":
        return None

    return meta.get("base_chord") or meta.get("original_key") or meta.get("key")


def validate_spartito(content: str, require_base_chord: bool = False) -> List[Tuple[int, str]]:
    """
    Validates the text of a spartito.
    Returns a list of errors: (line_number, error_message).
    """
    errors = []
    lines = content.splitlines()

    if require_base_chord:
        base_chord = extract_base_chord(content)
        if not base_chord:
            errors.append((1, "Manca l'accordo di base nel YAML frontmatter (key / original_key / base_chord)"))
        elif not parse_single_chord(base_chord):
            errors.append((1, f"Accordo di base nel YAML non valido: '{base_chord}'"))

    for idx, line in enumerate(lines, start=1):
        # Ignore comments or code fence markers
        trimmed = line.strip()
        if trimmed.startswith("```"):
            continue

        # 1. Check for unclosed brackets: e.g. [DO or DO]
        bracket_balance = 0
        in_bracket = False
        bracket_start_pos = -1

        for c_idx, char in enumerate(line):
            if char == "[":
                if in_bracket:
                    errors.append((idx, f"Parentesi aperta annidata non valida alla colonna {c_idx+1}"))
                in_bracket = True
                bracket_balance += 1
                bracket_start_pos = c_idx
            elif char == "]":
                if not in_bracket:
                    errors.append((idx, f"Parentesi chiusa ']' inattesa senza apertura alla colonna {c_idx+1}"))
                in_bracket = False
                bracket_balance -= 1

        if in_bracket or bracket_balance != 0:
            errors.append((idx, f"Parentesi quadra non chiusa nella riga: '{line}'"))

        # 2. Extract and validate chords in brackets: [xxx]
        chord_matches = re.finditer(r"\[(.*?)\]", line)
        for match in chord_matches:
            raw_chord = match.group(1).strip()
            # Special case: allow empty brackets or known annotations like [?] or [N.C.] (No Chord)
            if raw_chord.upper() in ["N.C.", "NC", "%", "", "?"]:
                continue
            # Special case: allow LRC timestamps like [01:23.45] or [01:23]
            if re.match(r"^\d{1,2}:\d{2}(?:\.\d{1,3})?$", raw_chord):
                continue
            if not parse_single_chord(raw_chord):
                errors.append((idx, f"Accordo non valido o non riconosciuto: '[{raw_chord}]'"))

    return errors


def main():
    if len(sys.argv) < 2:
        print("Uso: validate_spartito.py <file.md>")
        sys.exit(1)

    file_path = Path(sys.argv[1])
    if not file_path.exists():
        print(f"Errore: File '{file_path}' non trovato.")
        sys.exit(1)

    content = file_path.read_text(encoding="utf-8")
    base_chord = extract_base_chord(content)
    errors = validate_spartito(content, require_base_chord=True)

    if errors:
        print(f"❌ Errori di validazione trovati in {file_path.name} (accordo base: {base_chord or 'MANCANTE'}):")
        for line_num, msg in errors:
            print(f"  - Linea {line_num}: {msg}")
        sys.exit(1)
    else:
        print(f"✅ File '{file_path.name}' valido al 100%! (🎹 Accordo base: {base_chord})")
        sys.exit(0)


if __name__ == "__main__":
    main()
