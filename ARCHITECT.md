# ARCHITECT.md — `omr_service.py` Mimarisi

> Bu dosya `omr_service.py`'nin yapısını anlatır. Kod değiştikçe güncellenmeli.

## Repo ve Kod Durumu (2026-11-09)

- Üretim kodu `backend/` altındadır (`backend/app/...`). Kök `app/` ve
  `smart-tab/` kaldırıldı (PR #1).
- `backend/app/services/omr_service.py` repo ve sunucuda AST düzeyinde aynı
  (sunucuda yalnızca fazladan docstring/yorum var).
- `backend/app/main.py` ve `backend/app/core/config.py` sunucuyla eşitlendi (PR #3).
  Bu dosyalardaki hız sınırı, Swagger kapatma, oy doğrulaması, `user_id=1`
  sabiti ve CORS `*` ayarları OMR mimarisinin parçası değildir, ama repoda
  bulunur.
- `SECRET_KEY` zorunludur (PR #4). `pymupdf==1.28.0` sabitli (PR #2).
- Servis katmanında `OMRService`, `GuitarMappingService`, `TrustScoreService`
  ve `PDFOMRService` sınıfları vardır (dosya 780 satır).

### Parser hata davranışı

- `_parse_pdf()` ve `_parse_image()` istisna olursa ya da sonuç nota
  içermezse `_fallback()` döner (sabit 4 notalık örnek: E4 F4 G4 E4,
  `source: 'fallback'`). Bu, hatanın sessizce örnek veriye dönüştüğü anlamına
  gelir; çağıran taraf `source` alanına bakmalıdır.

## Genel Pipeline (mevcut, custom OpenCV tabanlı)

```
process_file(bytes, filename)
  ├─ .xml/.musicxml/.mxl  → _parse_musicxml()  → music21, en güvenilir
  ├─ .mid/.midi           → _parse_midi()      → music21
  ├─ .pdf                 → _parse_pdf()       → PDFOMRService (OpenCV tabanlı)
  └─ .png/.jpg/.jpeg/.webp→ _parse_image()     → OpenCV (tek sistem, basit)
```

Her yol sonunda ortak format: `{'music_hash': str, 'omr_data': {...}}`
```python
omr_data = {
    'tempo': int, 'time_signature': '4/4', 'key': 'C',
    'notes': [{'pitch': 'G4', 'midi': 67, 'duration': 1.0, 'beat': 1.0}, ...],
    'source': 'musicxml' | 'midi' | 'pdf_omr' | 'opencv_omr' | 'fallback',
}
```

## ⚠️ Mimari Değerlendirme Notu (güncel)

`.pdf` yolundaki `PDFOMRService` (aşağıda detaylı) **elle yazılmış,
sabit-eşikli bir OpenCV heuristic'i.** `TREBLE_MAP` off-by-one hatası
düzeltildi (bkz. aşağıdaki bölüm ve SESSION.md §14) ama bu, pitch
tespitinin genel güvenilirliğini garanti etmiyor — nota kafası
tespiti/merkezi hesaplama zincirinde başka kaynaklardan gelen hatalar
(gürültü/lyrics blob'larının nota sanılması, staff spacing tahmini vb.)
hâlâ olası.

**Bağımsız araştırma (bkz. SESSION.md §15):** GitHub'da benzer projeler
tarandı. `oemer` tabanlı "PDF → MusicXML" akışının makul olduğu, en az bir
bağımsız projenin (`PDF2Muse`) aynı yaklaşımı zaten üretimde kullandığı
görüldü. Ayrıca `homr` (alternatif OMR kütüphanesi) ve Audiveris/HOMR/OeMeR
karşılaştırmalı bir OMR benchmark projesi bulundu — hangi kütüphanenin
daha isabetli olduğuna dair bağımsız veri sağlıyor. **Sonuç:** custom
OpenCV heuristic'ini piksel piksel debug etmek yerine `oemer`'e geçiş
kararı güçlendi.

**Değerlendirilen alternatif:** `oemer` (hazır, deep-learning tabanlı OMR
kütüphanesi) ile değiştirmek/desteklemek. oemer görüntüden doğrudan
**MusicXML** üretir, ki bu zaten `_parse_musicxml()` üzerinden projeye
bağlanabilir (o yol `music21` ile güvenilir çalışıyor). Böylece
`PDFOMRService`'in çoğu (`_detect_treble_staffs`, `_group_staff_lines`,
`_detect_notes_in_staff`, `find_blobs`, `_split_blob`, `TREBLE_MAP`)
gereksiz hale gelebilir.

**Önerilen hedef mimari (henüz uygulanmadı, kurulum sorunları nedeniyle
bloklu — bkz. TASK.md):**
```
process_file(bytes, filename)
  ├─ .xml/.musicxml/.mxl  → _parse_musicxml()          → music21
  ├─ .mid/.midi           → _parse_midi()               → music21
  ├─ .pdf                 → _parse_pdf_with_oemer()     → PDF→PNG (PyMuPDF)
  │                                                        → oemer (izole
  │                                                        subprocess/venv)
  │                                                        → MusicXML çıktı
  │                                                        → _parse_musicxml()
  └─ .png/.jpg/...        → benzer şekilde oemer'e yönlendirilebilir
```
**Not:** oemer, ağır bağımlılıklara (TensorFlow/ONNX Runtime, ~200MB model
checkpoint) sahip — production venv'ine DOĞRUDAN kurulması riskli (bkz.
SESSION.md §11, §13 — iki kez yanlışlıkla production'a bulaştı). Önerilen
entegrasyon şekli: oemer'i **ayrı bir venv'de** (`/opt/oemer_venv`) tutup,
`PDFOMRService` içinden `subprocess.run([...])` ile çağırmak — bu, iki
ortamın bağımlılıklarını (production'ın kendi cv2/numpy sürümleri vs.
oemer'in gerektirdiği sürümler) birbirine karıştırmadan izole eder.

## Eski Pipeline Detayı (custom OpenCV — halen kodda mevcut, henüz kaldırılmadı)

### `OMRService`
Ana giriş noktası. `process_file()` dosya uzantısına göre doğru parser'a yönlendirir.
Tüm parser'lar hata durumunda `_fallback()`'e düşer (sabit 4 notalık örnek veri).

**Görüntü (PNG/JPG/JPEG/WEBP) yolu** `_parse_image()` → kendi yardımcı
metodlarını kullanır (PDF yolundaki `PDFOMRService` değil):
`_detect_staff_lines` → `_binarize` → `_remove_staff_and_stems` →
`_detect_note_heads` → `_detect_tempo` / `_detect_time_signature` →
`_build_music_data` (pitch dönüşümü `_build_music_data` içinde
`_y_to_pitch` ile yapılır).

**Önemli:** Görüntü yolu `_y_to_pitch` içinde **modül seviyesindeki**
`TREBLE_MAP`'i kullanır (`PDFOMRService.TREBLE_MAP` değil). Yani
`TREBLE_MAP` düzeltmesi (SESSION.md §14) PDF yolunu olduğu kadar görüntü
yolunu da etkiler. Görüntü yolunun pitch doğruluğu ayrıca ölçülmedi.

### `PDFOMRService` — pitch bugları burada, değiştirilmesi/kaldırılması değerlendiriliyor

Metodlar (satır numaraları 2026-11-09 itibarıyla): `process_pdf` (544),
`_group_staff_lines` (598), `_detect_treble_staffs` (623),
`_detect_notes_in_staff` (677), `_detect_tempo_pdf` (726),
`_detect_time_sig_pdf` (740), `_split_blob` (758).

`TREBLE_MAP` sözlüğü (hem modül seviyesinde hem `PDFOMRService` sınıfı
içinde ayrı ayrı tanımlı — ikisi de düzeltildi), staff üzerindeki "step"
(yarım-aralık adımı) değerini nota ismine çevirir:

```python
TREBLE_MAP = {
    -4:('A',3,57), -3:('B',3,59), -2:('C',4,60), -1:('D',4,62),
     0:('E',4,64),  1:('F',4,65),  2:('G',4,67),  3:('A',4,69),
     4:('B',4,71),  5:('C',5,72),  6:('D',5,74),  7:('E',5,76),
     8:('F',5,77),  9:('G',5,79), 10:('A',5,81), 11:('B',5,83),
    12:('C',6,84),
}
```

> **✅ DÜZELTİLDİ (bkz. SESSION.md §14):** Eskiden `step -1` ve `step 0`
> ikisi de `E4`'e eşleniyordu (yanlış duplikasyon), bu da staff'ın
> **altındaki tüm ledger-line notalarının** bir basamak yüksek/kaymış
> tespit edilmesine yol açıyordu. Doğru dizilim: step 0 = E4 (en alt
> çizgi), step -1 = D4 (hemen altındaki boşluk), step -2 = C4, vs. Step
> 0 ve üzeri zaten doğruydu, sadece negatif (staff altı) taraf hatalıydı.
> Gitar notasyonunda düşük perdeler çok sık staff altına düştüğü için bu,
> "sistematik pitch hatası" izleniminin büyük kısmını açıklıyor olabilir.

**Metodlar:**

1. **`process_pdf(file_bytes)`** — PyMuPDF ile 3x zoom render, OCR
   (tempo/time-sig), `_detect_treble_staffs()`, her staff için
   `_detect_notes_in_staff()`.

2. **`_detect_treble_staffs(gray)`** — Hough ile yatay çizgi bulur,
   `_group_staff_lines()` ile grupla, treble/bass ayır. **Bug #1 buradaydı,
   çözüldü.**

3. **`_group_staff_lines(groups)`** — ardışık gruplama + eksik çizgi
   enterpolasyonu (sabit `groups[i:i+5]` dilimlemesinin yerini aldı):
   ```python
   def _group_staff_lines(self, groups):
       staves = []
       current = []
       for y in groups:
           if not current:
               current = [y]; continue
           if len(current) < 5:
               avg_gap = np.mean(np.diff(current)) if len(current) > 1 else None
               gap = y - current[-1]
               if avg_gap is None or gap <= avg_gap * 1.6:
                   current.append(y); continue
           if len(current) >= 4:
               if len(current) == 4:
                   sp = int(np.mean(np.diff(current)))
                   current.append(current[-1] + sp)
               staves.append(current[:5])
           current = [y]
       if len(current) >= 4:
           if len(current) == 4:
               sp = int(np.mean(np.diff(current)))
               current.append(current[-1] + sp)
           staves.append(current[:5])
       return staves
   ```

4. **`_detect_notes_in_staff(gray_raw, staff_ys, spacing)`** — satır 677'de
   başlıyor. `x_start = int(gray_raw.shape[1] * 0.15)` ile sol %15 (clef
   alanı) crop'tan atlanır — **tablo çıktılarındaki x, bu crop'un LOKAL
   koordinatı; FINAL nota listesindeki cx ise `cx+x_start` ile MUTLAK
   koordinat** (bu ayrım debug'da kafa karıştırdı, unutma).
   ```python
   def find_blobs(min_h_ratio):
       cnts,_ = cv2.findContours(no_stems, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
       notes = []
       for cnt in cnts:
           x,y,w,h = cv2.boundingRect(cnt)
           area = cv2.contourArea(cnt)
           cx,cy = x+w//2, y+h//2
           aspect = w/h if h>0 else 0
           if (area>40 and area<spacing*spacing*3 and top<cy<bot and w>8
                   and h>spacing*min_h_ratio and h<spacing*2.3 and 0.5<aspect<2.5):
               # ✅ h<spacing*2.3 (eskiden h<spacing*2, sınırda reddediyordu)
               step = math.floor((first_line_y-cy)/(spacing/2))
               step = max(-4, min(12, step))
               nm,oc,midi = self.TREBLE_MAP.get(step, ('C',4,60))
               # ✅ TREBLE_MAP artık düzeltilmiş hâliyle kullanılıyor
               notes.append({'cx':cx+x_start,'cy':cy,'pitch':f'{nm}{oc}','midi':midi})
       notes.sort(key=lambda n:n['cx'])
       merged, px = [], -999
       for n in notes:
           if n['cx']-px >= spacing*1.2:
               merged.append(n); px=n['cx']
       return merged

   primary = find_blobs(0.5)
   secondary = find_blobs(0.25)
   for n in secondary:
       if not any(abs(n['cx']-p['cx'])<spacing for p in primary):
           primary.append(n)
   primary.sort(key=lambda n:n['cx'])
   return primary
   ```
   **Durum:** `TREBLE_MAP` fix'i sonrası servis yeniden başlatıldı ve yeni
   final nota listesi eskisinden farklı/daha çeşitli pitch'ler üretiyor
   (D4, F4, G4, B4, C5, D5 gibi) — görsel overlay ile kısmen teyit edildi
   ama tam sayısal doğrulama (kabul kriteriyle) henüz yapılmadı (bkz.
   SESSION.md §14, TASK.md).

5. **`_split_blob(mask_roi)`** (satır 758) — distance-transform tabanlı,
   birleşmiş blob ayırma. Dosyada mevcut (doğrulandı) ama şu ana kadar
   hiçbir gerçek örnekte tetiklenip fayda sağladığı gösterilmedi.

### `GuitarMappingService`
Katman 2: `omr_data`'daki notaları gitar string/fret/finger'a çevirir.
Pitch doğruysa bu kısım genelde sorunsuz — dokunulmadı.

### `TrustScoreService`
Tab güven skoru hesaplama — pitch doğruluğu sorunuyla doğrudan ilgisiz.

## Debug Scripti Mimarisi (`debug_omr.py`)

Servisin iç metodlarını doğrudan çağırıp ara adımları/görüntüleri dışarı verir.

**Önemli (tarihsel):** Bu scriptin `find_blobs` filtre koşulunu gösteren
tablo kısmı, gerçek servisten AYRI, kendi paralel kopyasını kullanıyordu
(satır ~65, `passes_h`) — servis fix'lenince bu kopya da ayrıca
güncellenmesi gerekti. Yeni bir filtre değişikliği yapılırsa **iki yerde**
(servis + debug script) güncellenmesi unutulmamalı, yoksa debug tablosu
yanıltıcı kalır.

**Not:** `TREBLE_MAP` için bu ayrı kopya sorunu YOK — `debug_omr.py`,
`TREBLE_MAP`'i `PDFOMRService.TREBLE_MAP` üzerinden referans olarak import
ediyor (`TREBLE_MAP = PDFOMRService.TREBLE_MAP`), yani class'taki düzeltme
otomatik olarak debug scriptine de yansıyor.

**Görsel doğrulama eklendi (bkz. SESSION.md §14):** `cv2.rectangle(overlay,
...)` satırının hemen altına her kutunun tespit edilen pitch'ini yazan bir
`cv2.putText(...)` satırı eklendi — artık overlay PNG'lerinde her nota
kutusunun üzerinde tespit edilen isim (örn. `D4`, `G4`) görünüyor, gözle
doğrulama kolaylaştı.

Tam script sunucuda `/opt/fretflow/backend/debug_omr.py` içinde mevcut.
