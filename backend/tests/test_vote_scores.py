"""
Oy sonrası TAB puanları: yeni oy, puan hesabına o istekte dahil edilmeli.

Kök neden: SessionLocal autoflush=False. db.add(db_vote) sonrası yapılan sorgu
yeni oyu yazmaz, bu yüzden skor bir oy geride kalır.
"""
import itertools

from fastapi.testclient import TestClient
from music21 import stream, note, meter, tempo

import app.main as main_module
from app.core.database import SessionLocal
from app.models.models import TabVersion

# Upload önbelleği nota içeriğine (pitch-süre dizisi, tempo) göre çalışır; aynı içerik aynı TAB'ı
# döndürür. Her yüklemeye farklı bir tempo vererek her testin kendi TAB'ını almasını sağlıyoruz.
_tempo_sayac = itertools.count(40)


def _upload_unique_tab(client):
    s = stream.Score()
    p = stream.Part()
    p.append(meter.TimeSignature("4/4"))
    p.append(tempo.MetronomeMark(number=next(_tempo_sayac)))
    for n in ["C5", "B4", "A4", "G4"]:
        p.append(note.Note(n, quarterLength=1))
    s.append(p)
    data = open(s.write("musicxml"), "rb").read()
    r = client.post("/api/upload", files={"file": ("vote.musicxml", data, "application/xml")})
    assert r.status_code == 200
    return r.json()["tabs"][0]["id"]


def _rate_score(tab_id):
    db = SessionLocal()
    try:
        return db.query(TabVersion).filter(TabVersion.id == tab_id).first().rate_score
    finally:
        db.close()


def test_rate_score_includes_the_new_vote():
    with TestClient(main_module.app) as client:
        tab_id = _upload_unique_tab(client)
        r = client.post(f"/api/tab/{tab_id}/vote", json={"type": "rate", "value": 4})
        assert r.status_code == 200
        assert _rate_score(tab_id) == 4.0


def test_rate_score_is_average_of_all_votes():
    with TestClient(main_module.app) as client:
        tab_id = _upload_unique_tab(client)
        client.post(f"/api/tab/{tab_id}/vote", json={"type": "rate", "value": 4})
        client.post(f"/api/tab/{tab_id}/vote", json={"type": "rate", "value": 2})
        assert _rate_score(tab_id) == 3.0
