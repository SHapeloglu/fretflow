"""
/api/upload uç noktası: boyut sınırı, normal yükleme, fallback davranışı.
"""
import pytest
from fastapi.testclient import TestClient
from music21 import stream, note, meter

import app.main as main_module


@pytest.fixture(scope="module")
def client():
    with TestClient(main_module.app) as c:
        yield c


def _musicxml_bytes():
    s = stream.Score()
    p = stream.Part()
    p.append(meter.TimeSignature("4/4"))
    for n in ["E4", "F4", "G4", "A4"]:
        p.append(note.Note(n, quarterLength=1))
    s.append(p)
    return open(s.write("musicxml"), "rb").read()


def test_health(client):
    assert client.get("/health").status_code == 200


def test_oversize_upload_rejected(client):
    big = b"0" * (main_module.MAX_UPLOAD_BYTES + 10)
    r = client.post("/api/upload", files={"file": ("big.musicxml", big, "application/xml")})
    assert r.status_code == 413


def test_normal_upload_returns_tabs(client):
    r = client.post("/api/upload", files={"file": ("ok.musicxml", _musicxml_bytes(), "application/xml")})
    assert r.status_code == 200
    body = r.json()
    assert body["source"] == "musicxml"
    assert len(body["tabs"]) == 1


def test_fallback_upload_is_not_persisted(client):
    r = client.post("/api/upload", files={"file": ("unknown.txt", b"hello", "text/plain")})
    body = r.json()
    assert r.status_code == 200
    assert body["source"] == "fallback"
    assert body["upload_id"] is None
    assert body["tabs"][0]["id"] is None
