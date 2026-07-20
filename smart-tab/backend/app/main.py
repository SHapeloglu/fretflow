from fastapi import FastAPI, UploadFile, File, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

from app.core.database import get_db, engine
from app.models.models import Base, SheetUpload, TabVersion, TabVote
from app.services.omr_service import OMRService, GuitarMappingService, TrustScoreService
from app.services.tab_renderer import render_tab

Base.metadata.create_all(bind=engine)

app = FastAPI(title="FretFlow Smart TAB Engine")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

omr_svc = OMRService()
mapping_svc = GuitarMappingService()
trust_svc = TrustScoreService()


@app.get("/health")
async def health():
    return {"status": "ok", "app": "FretFlow"}


@app.post("/api/upload")
async def upload_sheet(
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
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
async def edit_tab(tab_id: int, edit_data: dict, db: Session = Depends(get_db)):
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
async def vote_tab(tab_id: int, vote: dict, db: Session = Depends(get_db)):
    tab = db.query(TabVersion).filter(TabVersion.id == tab_id).first()
    if not tab:
        raise HTTPException(status_code=404, detail="TAB bulunamadı")

    user_level = vote.get("user_level", "beginner")
    weight = trust_svc.get_level_weight(user_level)

    db_vote = TabVote(
        tab_id=tab_id,
        user_id=vote.get("user_id", 1),
        vote_type=vote["type"],
        value=vote["value"],
        user_level_weight=weight,
    )
    db.add(db_vote)

    all_votes = db.query(TabVote).filter(TabVote.tab_id == tab_id).all()
    rate_votes = [v for v in all_votes if v.vote_type == "rate"]
    acc_votes = [v for v in all_votes if v.vote_type == "accuracy"]

    if rate_votes:
        ws = sum(v.value * v.user_level_weight for v in rate_votes)
        tw = sum(v.user_level_weight for v in rate_votes)
        tab.rate_score = round(ws / tw, 2)

    if acc_votes:
        ws = sum(v.value * v.user_level_weight for v in acc_votes)
        tw = sum(v.user_level_weight for v in acc_votes)
        tab.accuracy_score = round(ws / tw, 2)
        tab.accuracy_count = len(acc_votes)

    tab.vote_count = len(rate_votes)
    tab.trust_score = trust_svc.compute_trust_score(tab.accuracy_score, tab.rate_score)
    db.commit()

    return {
        "trust_score": tab.trust_score,
        "category": trust_svc.classify_tab(tab),
    }


@app.get("/api/tab/{tab_id}")
async def get_tab(tab_id: int, db: Session = Depends(get_db)):
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
