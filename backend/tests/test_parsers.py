"""
OMR parser testleri: MusicXML süre/beat, .mxl, hata yolları.
Çalıştırma: cd backend && pytest
"""
import numpy as np
import pytest
from music21 import stream, note, meter

from app.services.omr_service import OMRService, PDFOMRService, _measure_quarters


def _score_xml(time_sig: str, pitches, ql: float = 1.0, ext: str = "musicxml"):
    s = stream.Score()
    p = stream.Part()
    p.append(meter.TimeSignature(time_sig))
    for name in pitches:
        p.append(note.Note(name, quarterLength=ql))
    s.append(p)
    return s


@pytest.fixture
def svc():
    return OMRService()


def test_measure_quarters_values():
    assert _measure_quarters("4/4") == 4.0
    assert _measure_quarters("6/8") == 3.0
    assert _measure_quarters("3/4") == 3.0
    assert _measure_quarters("bozuk") == 4.0


def test_musicxml_68_beats_stay_within_one_measure(svc, tmp_path):
    # 6/8: 12 sekizlik = 4 ölçü. Beat 1.0 ile 4.0 arasında (exclusive) kalmalı.
    s = stream.Score()
    p = stream.Part()
    p.append(meter.TimeSignature("6/8"))
    for _ in range(12):
        p.append(note.Note("E4", quarterLength=0.5))
    s.append(p)
    data = open(s.write("musicxml"), "rb").read()
    r = svc.process_file(data, "a.musicxml")
    betas = [n["beat"] for n in r["omr_data"]["notes"]]
    assert r["omr_data"]["time_signature"] == "6/8"
    assert min(betas) >= 1.0 and max(betas) < 4.0, betas


def test_musicxml_44_beats_unchanged(svc):
    s = _score_xml("4/4", ["C4"] * 8)
    data = open(s.write("musicxml"), "rb").read()
    r = svc.process_file(data, "b.xml")
    assert [n["beat"] for n in r["omr_data"]["notes"]] == [1.0, 2.0, 3.0, 4.0] * 2


def test_compressed_mxl_parses_as_musicxml(svc):
    s = _score_xml("4/4", ["E4", "F4", "G4", "A4"])
    data = open(s.write("mxl"), "rb").read()
    r = svc.process_file(data, "c.mxl")
    assert r["omr_data"].get("source") == "musicxml"
    assert len(r["omr_data"]["notes"]) == 4


def test_invalid_musicxml_falls_back(svc):
    r = svc.process_file(b"not xml", "bad.xml")
    assert r["omr_data"]["source"] == "fallback"


def test_empty_staff_list_returns_empty(svc):
    gray = np.full((300, 400), 255, np.uint8)
    assert PDFOMRService()._detect_treble_staffs(gray) == []


def test_blank_pdf_falls_back(svc):
    import fitz
    doc = fitz.open()
    doc.new_page()
    r = svc.process_file(doc.tobytes(), "blank.pdf")
    assert r["omr_data"]["source"] == "fallback"


def test_pdf_render_zoom_keeps_normal_pages_at_3x():
    # A4 (595x842 pt) normal sayfada zoom değişmez: 3x.
    from app.services.omr_service import PDFOMRService
    assert PDFOMRService._pdf_render_zoom(595, 842) == 3.0


def test_pdf_render_zoom_caps_huge_pages():
    # Çok büyük sayfada render piksel bütçesini aşmamalı.
    from app.services.omr_service import MAX_RENDER_PIXELS, PDFOMRService
    zoom = PDFOMRService._pdf_render_zoom(20000, 20000)
    assert zoom < 3.0
    assert (20000 * zoom) * (20000 * zoom) <= MAX_RENDER_PIXELS * 1.0001
