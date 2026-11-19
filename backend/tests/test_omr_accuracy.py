"""
OMR doğruluk ölçümü (kabul seti).

Ground truth: tests/omr_cases/manifest.json. Her vaka bir dosya ve beklenen
nota listesi içerir: [{"pitch": "E4", "duration": 1.0, "beat": 1.0}, ...].
İsteğe bağlı eşikler: "min_pitch", "min_duration", "min_beat" (0-1 arası oran).
Eşik yoksa test yalnızca ölçümü raporlar (asla başarısız olmaz).

Vaka eklemek için: dosyayı tests/omr_cases/ altına koy, manifest.json'a yaz.
Ground truth kaynağı: elle yazılmış MusicXML veya notasyon yazılımı çıktısı.
"""
import json
from pathlib import Path

import pytest

from app.services.omr_service import OMRService

CASES_DIR = Path(__file__).parent / "omr_cases"
MANIFEST = CASES_DIR / "manifest.json"


def _load_cases():
    if not MANIFEST.exists():
        return []
    return json.loads(MANIFEST.read_text(encoding="utf-8")).get("cases", [])


def _ratio(actual, expected, key):
    if not expected:
        return 0.0
    hits = sum(1 for a, e in zip(actual, expected) if a.get(key) == e.get(key))
    return hits / len(expected)


CASES = _load_cases()


@pytest.mark.skipif(not CASES, reason="omr_cases/manifest.json içinde vaka yok (ground truth bekleniyor)")
@pytest.mark.parametrize("case", CASES or [None], ids=lambda c: c["file"] if isinstance(c, dict) else "yok")
def test_omr_accuracy(case):
    if case is None:
        pytest.skip("vaka yok")
    path = CASES_DIR / case["file"]
    assert path.exists(), f"vaka dosyası yok: {path}"
    result = OMRService().process_file(path.read_bytes(), path.name)
    actual = result["omr_data"]["notes"]
    expected = case["expected"]

    pitch = _ratio(actual, expected, "pitch")
    duration = _ratio(actual, expected, "duration")
    beat = _ratio(actual, expected, "beat")
    print(f"\n{case['file']}: pitch {pitch:.2f}  duration {duration:.2f}  beat {beat:.2f}  "
          f"(üretilen {len(actual)}, beklenen {len(expected)})")

    if "min_pitch" in case:
        assert pitch >= case["min_pitch"], f"pitch {pitch:.2f} < {case['min_pitch']}"
    if "min_duration" in case:
        assert duration >= case["min_duration"], f"duration {duration:.2f} < {case['min_duration']}"
    if "min_beat" in case:
        assert beat >= case["min_beat"], f"beat {beat:.2f} < {case['min_beat']}"
