from sqlalchemy import Column, Integer, String, Float, JSON, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True)
    hashed_password = Column(String)
    level = Column(String, default="beginner")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    votes = relationship("TabVote", back_populates="user")

class SheetUpload(Base):
    __tablename__ = "sheet_uploads"
    id = Column(Integer, primary_key=True, index=True)
    music_hash = Column(String, index=True)
    filename = Column(String)
    omr_data = Column(JSON)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    tabs = relationship("TabVersion", back_populates="upload")

class TabVersion(Base):
    __tablename__ = "tab_versions"
    id = Column(Integer, primary_key=True, index=True)
    upload_id = Column(Integer, ForeignKey("sheet_uploads.id"))
    tab_data = Column(JSON)
    source = Column(String)
    accuracy_score = Column(Float, default=0.0)
    rate_score = Column(Float, default=0.0)
    trust_score = Column(Float, default=0.0)
    vote_count = Column(Integer, default=0)
    accuracy_count = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    upload = relationship("SheetUpload", back_populates="tabs")
    votes = relationship("TabVote", back_populates="tab")

class TabVote(Base):
    __tablename__ = "tab_votes"
    id = Column(Integer, primary_key=True, index=True)
    tab_id = Column(Integer, ForeignKey("tab_versions.id"))
    user_id = Column(Integer, ForeignKey("users.id"))
    vote_type = Column(String)
    value = Column(Float)
    user_level_weight = Column(Float, default=1.0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    tab = relationship("TabVersion", back_populates="votes")
    user = relationship("User", back_populates="votes")
