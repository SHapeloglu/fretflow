# OMR kabul seti

Bu klasöre ground truth'lu vakalar eklenir:

1. Nota dosyasını (PDF, PNG veya MusicXML) bu klasöre koy.
2. `manifest.json` → `cases` listesine ekle:
   ```json
   {"file": "sayfa1.pdf",
    "expected": [{"pitch": "G4", "duration": 1.0, "beat": 1.0}],
    "min_pitch": 0.8}
   ```
3. `cd backend && pytest tests/test_omr_accuracy.py -s` ile ölçümü gör.

Şu an vaka yok; test atlanıyor. Telif hakkı korumalı notaları repoya koyma.
