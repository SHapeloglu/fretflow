"""
Test ortamı: backend/ import yolu ve test veritabanı (SQLite, geçici dosya).
Gerçek DATABASE_URL veya SECRET_KEY değerleri testlerde KULLANILMAZ.
"""
import os
import sys
import tempfile
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND_DIR))

_tmp_db = Path(tempfile.mkdtemp(prefix="fretflow_test_")) / "test.db"
os.environ.setdefault("DATABASE_URL", f"sqlite:///{_tmp_db}")
os.environ.setdefault("SECRET_KEY", "test-only-not-secret")
