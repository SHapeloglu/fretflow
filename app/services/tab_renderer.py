"""
TAB Render Service
Tempo: 100 BPM
    ↓   ↑   ↓   ↑
e|--------------------|
B|--1(1)------3(3)----|
"""

STRING_NAMES = ["e", "B", "G", "D", "A", "E"]
MEASURE_WIDTH = 20

def render_tab(tab_data: dict) -> str:
    tempo = tab_data.get("tempo", 120)
    notes = tab_data.get("notes", [])
    if not notes:
        return ""

    rhythm_row = _build_rhythm_row(notes)
    strings = {i: ["-"] * MEASURE_WIDTH for i in range(1, 7)}

    for note in notes:
        col = _beat_to_col(note["beat"])
        s = note["string"]
        fret = note["fret"]
        finger = note["finger"]
        label = f"{fret}({finger})" if finger > 0 else f"{fret}"
        for j, ch in enumerate(label):
            if col + j < MEASURE_WIDTH:
                strings[s][col + j] = ch

    lines = [f"Tempo: {tempo} BPM", rhythm_row]
    for i, name in enumerate(STRING_NAMES, 1):
        row = "".join(strings[i])
        lines.append(f"{name}|{row}|")

    return "\n".join(lines)


def _build_rhythm_row(notes: list) -> str:
    row = [" "] * (MEASURE_WIDTH + 2)
    for note in notes:
        col = _beat_to_col(note["beat"]) + 1
        if col < len(row):
            row[col] = note.get("rhythm", "↓")
    return "    " + "".join(row)


def _beat_to_col(beat: float) -> int:
    return max(0, min(MEASURE_WIDTH - 3, int((beat - 1) * 4)))
