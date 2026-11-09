# TASK.md — Şu Anki Görev

## 🔴 AÇIK SORUNLAR (2026-11-09) — araştırılıyor, çözülmedi

> Aşağıdakiler çözülmüş değildir. Sunucu tarafı bilgileri kullanıcı gözlemidir,
> repodan doğrulanamaz.

1. **Servis DB bağlantısı — ÖNCELİKLİ.** `fretflow` (uvicorn 127.0.0.1:8010)
   2026-11-08 13:51'den beri dinlemiyor; sebep DB bağlantısı olarak düşünülüyor.
   - Yerel PostgreSQL 16 `main` (5432) kümesinin veri dizini yok.
   - `.env` `apache` kullanıcısı ve `localhost:5432` kullanıyor.
   - Docker `postgres-ortak` (5434) içindeki `fretflow_db` eski kopya gibi
     görünüyor (son kayıt Temmuz 2026, `uygulama` rolü, `apache` rolü yok).
   - **Yapılacak (araştırma):** canlı verinin hangi kümede olduğunu doğrula;
     `.env`'deki DATABASE_URL'in hangi kümeye gittiğini ve `apache` rolünün
     var olup olmadığını teyit et. Doğrulanmadan DB'ye yazma yapılmasın.
2. **`fretflow.service` `disabled`** — reboot'ta servis kalkmaz. Karar
   verilmedi (enable edilmeli mi, DB sorunu çözülmeden mi?).
3. **Güvenlik:** CORS `*`, `user_id=1` sabiti (kimlik doğrulama yok). Karar
   ve tasarım bekliyor.
4. **oemer testi** (aşağıda) — bekliyor.

## ✅ TAMAMLANDI (2026-11-09) — Repo Temizliği ve Sunucu Eşitleme

- PR #1: `app/` (kök) ve `smart-tab/` kaldırıldı; `omr_service.py.bak` kaldırıldı, `.gitignore`'a `*.bak`.
- PR #2: `pymupdf==1.28.0` sabitlendi (`backend/requirements.txt`).
- PR #3: `backend/app/main.py` ve `backend/app/core/config.py` sunucuyla eşitlendi.
- PR #4: `SECRET_KEY` zorunlu yapıldı (varsayılan kaldırıldı).
- Ayrıntı: SESSION.md §18.

## ✅ TAMAMLANDI — Production Venv Restore

~~Production venv'in (`/opt/fretflow/venv`) durumu belirsiz/riskliydi~~ —
**çözüldü.** `requirements.txt` referans alınarak `oemer`, `onnxruntime`,
`onnxruntime-gpu`, `scipy`, `opencv-python-headless` (yanlış sürüm),
`scikit-learn`, `types-tensorflow` kaldırıldı; doğru sürümler
(`numpy==1.26.4`, `opencv-python-headless==4.9.0.80`) yeniden kuruldu.
Doğrulama:
- `pip check` → "No broken requirements found" ✅
- `python -c "from app.services.omr_service import *"` → hatasız ✅
- `systemctl restart fretflow` → servis "active (running)" ✅

(Detay: SESSION.md §11-13 sorunun oluşumu, §14 çözümü.)

## ✅ TAMAMLANDI — `TREBLE_MAP` Off-by-One Fix

ARCHITECT.md'de detaylandırılan, staff altı (ledger-line) notaların yanlış
pitch'e eşlenmesine yol açan `TREBLE_MAP` hatası bulundu ve düzeltildi:
- `omr_service.py` satır 30 (modül seviyesi) ve satır 537 (`PDFOMRService`
  sınıfı içi) — ikisi de güncellendi.
- Yedek alındı: `omr_service.py.bak_pre_treblemap_fix`
- `debug_omr.py`'ye pitch etiketi gösteren `cv2.putText` eklendi (görsel
  doğrulama için).
- Servis restart edildi, yeni final nota listesi gözlemlendi (farklı ve
  daha çeşitli pitch'ler: D4, F4, G4, B4, C5, D5).

**Henüz yapılmadı:** Kabul kriteriyle (aşağıda) sayısal doğrulama —
`/tmp/nota.pdf` üzerinde 10 notalık test çalıştırılıp `Dogruluk: x/10`
sonucu ölçülmedi. **Bir sonraki oturumda ilk iş bu olmalı** (aşağıdaki
"Sıradaki Adım" bölümüne bak).

## 🔄 AKTİF — oemer Değerlendirmesi (Seçenek A, kullanıcı onayladı)

Bağımsız GitHub araştırması yapıldı (bkz. SESSION.md §15): `PDF2Muse` adlı
bağımsız bir proje zaten "PDF → oemer → MusicXML" akışını üretimde
kullanıyor — bu, planlanan mimarinin (ARCHITECT.md) makul olduğunu
doğruluyor. `homr` (alternatif kütüphane) ve bir OMR benchmark projesi de
bulundu.

**Sıradaki adım (kaldığımız yer):** `/opt/oemer_venv` içinde oemer'i test
PNG (`/tmp/nota_page1.png`) üzerinde çalıştırıp gerçekten iyi sonuç verip
vermediğini görmek. Henüz çalıştırılmadı — komutlar aşağıda hazır.

```bash
# 1. Venv durumunu kontrol et
ls -la /opt/oemer_venv/bin/ 2>&1 | head -5
source /opt/oemer_venv/bin/activate
# prompt'ta (oemer_venv) olduğunu TEYİT ET
pip list 2>&1 | grep -iE "oemer|onnxruntime|numpy|opencv"

# 2. Test PNG üzerinde çalıştır (ilk çalıştırma yavaş olabilir, model yükleme dahil)
cd /tmp
time oemer /tmp/nota_page1.png -o /tmp/oemer_test/

# 3. Çıktıyı kontrol et
ls -la /tmp/oemer_test/
```

Eğer bağımlılık çakışması (numpy/scipy/opencv/onnxruntime) tekrar
çıkarsa, önceki denemelerde (SESSION.md §12-13) bulunan çözüm yolları:

1. **`--use-tf` bayrağı** (ONNX yerine TensorFlow checkpoint kullanır):
   ```bash
   source /opt/oemer_venv/bin/activate
   pip install "numpy<2" tensorflow-cpu
   oemer /tmp/nota_page1.png -o /tmp/oemer_out --use-tf
   ```
2. Eğer TF de sorun çıkarırsa: `scipy`/`opencv-python-headless`'i numpy<2
   ile uyumlu ESKİ sürümlere manuel sabitle (`scipy<1.13`,
   `opencv-python-headless<5`) — **SADECE `/opt/oemer_venv` içinde, prompt
   `(oemer_venv)` olduğundan emin olarak.**
3. Çalışırsa: `/tmp/oemer_test/` altındaki MusicXML çıktısını incele,
   mevcut `_parse_musicxml()` ile parse edilebiliyor mu test et, sonra
   pitch doğruluğunu aynı kabul testiyle ölç.
4. Entegrasyon: `PDFOMRService`'e, `subprocess` ile `/opt/oemer_venv`'in
   Python'unu çağıran yeni bir yol ekle (ARCHITECT.md'deki önerilen mimari).

## Kabul Kriteri / Test (değişmedi)

```bash
cd /opt/fretflow/backend && python3 -c "
from app.services.omr_service import OMRService
svc = OMRService()
data = open('/tmp/nota.pdf','rb').read()
result = svc.process_file(data, 'nota.pdf')
notes = result['omr_data']['notes']
omr = [n['pitch'] for n in notes[:10]]
beklenen = ['G4','G4','A4','G4','E4','F4','E4','D4','E4','D4']
print('OMR:    ', ' '.join(omr))
print('Beklenen:', ' '.join(beklenen))
print('Dogruluk:', sum(a==b for a,b in zip(omr,beklenen)), '/10')
"
```

## Yaklaşım — İki Paralel Seçenek

**Seçenek A (öncelikli, kullanıcı onayladı, ŞU AN AKTİF) — oemer'i izole
venv'de çalışır hale getirip entegre et.** Detay yukarıda.

**Seçenek B (yedek plan) — custom OpenCV pipeline'da TREBLE_MAP fix'inin
yeterli olup olmadığını sayısal olarak doğrula, gerekirse devam et:**

`TREBLE_MAP` fix'i uygulandı ama henüz kabul testiyle sayısal doğrulama
yapılmadı. Eğer oemer kurulumu makul sürede çözülemezse veya sonuçları
tatmin etmezse, önce şu kabul testi çalıştırılıp doğruluk oranı
ölçülmeli; hâlâ yetersizse `_detect_notes_in_staff`'taki diğer olası
hata kaynaklarına (gürültü/lyrics blob filtrelemesi, `spacing` tahmini)
bakılabilir.

## Kapsam Dışı (şimdilik)

- MusicXML/MIDI pipeline'ları (zaten music21 ile güvenilir, dokunulmadı)
- Görüntü (PNG/JPG) pipeline'ı — ayrı, benzer ama farklı kod yolu
- `GuitarMappingService` (tab'a çevirme) — pitch doğru gelirse sorunsuz çalışır
