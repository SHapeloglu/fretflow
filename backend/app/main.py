"""
FretFlow Smart TAB Engine'in API giriş dosyası (FastAPI).
Uç noktalar: nota yükleme (/api/upload), TAB düzeltme, oy verme ve TAB okuma. Sağlık kontrolü: /health.
Açılışta eksik tablolar oluşturulur. OMR ve TAB üretimi app.services, veritabanı oturumu app.core.database üzerinden gelir.
Bu dosyada kimlik doğrulama (giriş) yoktur.
"""

import time
from collections import defaultdict
from fastapi import FastAPI, UploadFile, File, Depends, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

from app.core.database import get_db, engine
from app.models.models import Base, SheetUpload, TabVersion, TabVote
from app.services.omr_service import OMRService, GuitarMappingService, TrustScoreService
from app.services.tab_renderer import render_tab

# Eksik tabloları oluşturur, var olanlara dokunmaz. Tablo değişiklikleri (kolon ekleme vb.) bu yolla yapılmaz.
Base.metadata.create_all(bind=engine, checkfirst=True)

# Swagger/OpenAPI herkese açık olmasın (2026-10-18)
app = FastAPI(title="FretFlow Smart TAB Engine", docs_url=None, redoc_url=None, openapi_url=None)

# IP ve uç adına göre son istek zamanları. Bellekte tutulur: servis yeniden başlarsa sıfırlanır; birden çok işlem varsa her biri ayrı sayar.
_rate_store: dict = defaultdict(list)


def rate_limit(ad: str, max_istek: int, pencere: int = 60):
    """IP başına basit hız sınırı (bellekte, süreç başına). nginx X-Real-IP başlığını gönderiyor."""
    async def kontrol(request: Request):
        """
        İç kontrol: her istekte FastAPI tarafından çağrılır (Depends ile bağlanır).
        İstemci IP'sini X-Real-IP başlığından (yoksa bağlantı adresinden) alır; son 'pencere' saniyedeki istek sayısı max_istek değerine ulaşmışsa HTTP 429 fırlatır.
        Sınır aşılmamışsa bu isteği kayıt listesine ekler. TODO(kontrol): nginx X-Real-IP değerini istemciden gelenle değiştirmeden mi yazıyor, doğrulanmalı.
        """
        ip = request.headers.get("x-real-ip") or (request.client.host if request.client else "?")
        simdi = time.time()
        anahtar = f"{ad}:{ip}"
        kayitlar = [t for t in _rate_store[anahtar] if simdi - t < pencere]
        if len(kayitlar) >= max_istek:
            _rate_store[anahtar] = kayitlar
            raise HTTPException(status_code=429, detail="Çok fazla istek, biraz bekleyin",
                                headers={"Retry-After": str(pencere)})
        kayitlar.append(simdi)
        _rate_store[anahtar] = kayitlar
    return Depends(kontrol)

# CORS: yalnızca frontend'in yayınlandığı alan adı ve yerel geliştirme adresleri kabul edilir.
# Frontend /api'yi göreli yoldan çağırdığı için (aynı origin, nginx) bu liste dışarıdan erişimi kısıtlar.
# Kimlik bilgisi (cookie) kullanılmadığı için allow_credentials kapalı.
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://fretflow.dehateknikservis.com",
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=False,
    allow_methods=["GET", "POST", "PUT", "OPTIONS"],
    allow_headers=["Content-Type"],
)

omr_svc = OMRService()
mapping_svc = GuitarMappingService()
trust_svc = TrustScoreService()


@app.get("/health")
async def health():
    """Servisin çalıştığını kontrol eder (sağlık kontrolü). Veritabanına bakmaz; {"status": "ok"} döner."""
    return {"status": "ok", "app": "FretFlow"}


@app.post("/api/upload")
async def upload_sheet(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    # Hız sınırı: IP başına dakikada en fazla 10 yükleme. Aşılırsa 429 döner.
    _hiz=rate_limit("upload", 10)
):
    """
    Nota dosyasını alır, okur ve TAB üretir. Desteklenen türler: MusicXML, MIDI, PNG/JPG, PDF.
    Aynı nota daha önce yüklendiyse kayıtlı TAB'ları döner (cache_hit=True). İlk yüklemede sistem TAB'ı üretip kaydeder.
    Tanınmayan ya da okunamayan dosyada örnek (fallback) veri döner.
    """
    file_bytes = await file.read()
    result = omr_svc.process_file(file_bytes, file.filename)
    music_hash = result["music_hash"]
    omr_data = result["omr_data"]

    # Hash kontrolü — topluluk cache
    existing = db.query(SheetUpload).filter(
        SheetUpload.music_hash == music_hash
    ).first()

    if existing:
        tabs = db.query(TabVersion).filter(
            TabVersion.upload_id == existing.id
        ).order_by(TabVersion.trust_score.desc()).all()

        categorized = []
        for tab in tabs:
            category = trust_svc.classify_tab(tab)
            categorized.append({
                "id": tab.id,
                "category": category,
                "tab_data": tab.tab_data,
                "ascii_tab": render_tab(tab.tab_data),
                "accuracy_score": tab.accuracy_score,
                "rate_score": tab.rate_score,
                "trust_score": tab.trust_score,
                "vote_count": tab.vote_count,
                "accuracy_count": tab.accuracy_count,
            })

        return {
            "cache_hit": True,
            "music_hash": music_hash,
            "upload_id": existing.id,
            "source": omr_data.get("source", "unknown"),
            "tabs": categorized,
        }

    # İlk yükleme — sistem üretir
    upload = SheetUpload(
        music_hash=music_hash,
        filename=file.filename,
        omr_data=omr_data,
    )
    db.add(upload)
    db.flush()

    tab_data = mapping_svc.map_notes_to_tab(omr_data)

    system_tab = TabVersion(
        upload_id=upload.id,
        tab_data=tab_data,
        source=omr_data.get("source", "system"),
        trust_score=0.0,
    )
    db.add(system_tab)
    db.commit()
    db.refresh(system_tab)

    return {
        "cache_hit": False,
        "music_hash": music_hash,
        "upload_id": upload.id,
        "source": omr_data.get("source", "unknown"),
        "tabs": [{
            "id": system_tab.id,
            "category": "new",
            "tab_data": tab_data,
            "ascii_tab": render_tab(tab_data),
            "accuracy_score": 0.0,
            "rate_score": 0.0,
            "trust_score": 0.0,
            "vote_count": 0,
            "accuracy_count": 0,
        }],
    }


@app.put("/api/tab/{tab_id}/edit")
# Hız sınırı: IP başına dakikada en fazla 20 düzeltme.
async def edit_tab(tab_id: int, edit_data: dict, db: Session = Depends(get_db), _hiz=rate_limit("edit", 20)):
    """
    Kullanıcının düzelttiği TAB'ı yeni bir sürüm olarak kaydeder; eski sürüm silinmez.
    Gövdede 'tab_data' alanı beklenir. TAB bulunamazsa 404 döner. Dönüş: yeni kaydın id'si ve ASCII TAB.
    """
    # tab_data yoksa hiçbir kayıt yapılmadan 422 (geçersiz istek) döner.
    if "tab_data" not in edit_data:
        raise HTTPException(status_code=422, detail="tab_data gerekli")
    original = db.query(TabVersion).filter(TabVersion.id == tab_id).first()
    if not original:
        raise HTTPException(status_code=404, detail="TAB bulunamadı")

    new_tab = TabVersion(
        upload_id=original.upload_id,
        tab_data=edit_data["tab_data"],
        source="user_edit",
        trust_score=0.0,
    )
    db.add(new_tab)
    db.commit()
    db.refresh(new_tab)

    return {
        "id": new_tab.id,
        "ascii_tab": render_tab(new_tab.tab_data),
        "message": "Düzeltme kaydedildi",
    }


@app.post("/api/tab/{tab_id}/vote")
# Hız sınırı: IP başına dakikada en fazla 30 oy.
async def vote_tab(tab_id: int, vote: dict, db: Session = Depends(get_db), _hiz=rate_limit("vote", 30)):
    """
    TAB'a 'rate' ya da 'accuracy' türünde oy verir ve TAB'ın puanlarını yeniden hesaplar.
    Oy değeri 0-5 arası bir sayı olmalıdır. TAB yoksa 404 döner.
    """
    tab = db.query(TabVersion).filter(TabVersion.id == tab_id).first()
    if not tab:
        raise HTTPException(status_code=404, detail="TAB bulunamadı")

    # Kimlik doğrulama yok: istemcinin bildirdiği user_level/user_id'ye güvenilmez (güven puanı manipülasyonu).
    # Tüm anonim oylar en düşük ağırlıkla sayılır.
    weight = trust_svc.get_level_weight("beginner")
    if vote.get("type") not in ("rate", "accuracy"):
        raise HTTPException(status_code=422, detail="type rate veya accuracy olmalı")
    try:
        deger = float(vote["value"])
    except (KeyError, TypeError, ValueError):
        raise HTTPException(status_code=422, detail="value sayı olmalı")
    # Puan 0-5 aralığında olmalı; NaN ve sonsuz değerler de bu kontrole takılıp reddedilir.
    if not 0 <= deger <= 5:
        raise HTTPException(status_code=422, detail="value 0-5 aralığında olmalı")

    db_vote = TabVote(
        tab_id=tab_id,
        # Anonim oy: user_id boş bırakılır. Eskiden sabit 1 yazılıyordu; users tablosunda 1 numaralı kullanıcı
        # yoksa FK hatası veriyordu. Aynı kişinin tekrar oy vermesini engellemek için oy kimliği gerekir
        # (şema değişikliği gerektirir; BACKLOG'da).
        user_id=None,
        vote_type=vote["type"],
        value=deger,
        user_level_weight=weight,
    )
    db.add(db_vote)

    all_votes = db.query(TabVote).filter(TabVote.tab_id == tab_id).all()
    rate_votes = [v for v in all_votes if v.vote_type == "rate"]
    acc_votes = [v for v in all_votes if v.vote_type == "accuracy"]

    if rate_votes:
        # Ağırlıklı ortalama: yüksek seviyeli kullanıcıların oyu daha çok sayılır.
        ws = sum(v.value * v.user_level_weight for v in rate_votes)
        tw = sum(v.user_level_weight for v in rate_votes)
        tab.rate_score = round(ws / tw, 2)

    if acc_votes:
        ws = sum(v.value * v.user_level_weight for v in acc_votes)
        tw = sum(v.user_level_weight for v in acc_votes)
        tab.accuracy_score = round(ws / tw, 2)
        tab.accuracy_count = len(acc_votes)

    # vote_count yalnız beğeni (rate) oylarını sayar; doğruluk oylarının sayısı accuracy_count'tadır.
    tab.vote_count = len(rate_votes)
    tab.trust_score = trust_svc.compute_trust_score(tab.accuracy_score, tab.rate_score)
    db.commit()

    return {
        "trust_score": tab.trust_score,
        "category": trust_svc.classify_tab(tab),
    }


@app.get("/api/tab/{tab_id}")
async def get_tab(tab_id: int, db: Session = Depends(get_db)):
    """Bir TAB sürümünü ASCII TAB, kategori ve puanlarla birlikte döner. TAB yoksa 404 döner."""
    tab = db.query(TabVersion).filter(TabVersion.id == tab_id).first()
    if not tab:
        raise HTTPException(status_code=404, detail="TAB bulunamadı")
    return {
        "id": tab.id,
        "tab_data": tab.tab_data,
        "ascii_tab": render_tab(tab.tab_data),
        "category": trust_svc.classify_tab(tab),
        "trust_score": tab.trust_score,
    }
