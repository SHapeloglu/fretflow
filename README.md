# FretFlow

Nota (sheet music) verisinden otomatik **gitar tab'ı** üreten bir OMR
(Optical Music Recognition) servisi. Kullanıcı bir nota dosyası (PDF,
MusicXML, MIDI veya görüntü) yükler; sistem notaları tespit edip gitar
üzerinde çalınabilir pozisyonlara (string / fret / finger) çevirir.

> **Durum (2026-11-11):** Aktif geliştirme. Sunucuda `fretflow` servisi
> (systemd, `enabled`, 127.0.0.1:8010) çalışıyor, `/health` 200. Canlı alan adı
> `selimkilic.online`. Veritabanı: Docker `postgres-ortak` (127.0.0.1:5434),
> `fretflow_db`, `uygulama` rolü; veri eşleşmesi teyit bekliyor (SESSION.md §19).
> PDF→OMR yolunda pitch doğruluğu düşük: oemer 2/10, mevcut OpenCV 0/10 (kabul
> testi, bkz. [Bilinen Sorunlar](#bilinen-sorunlar-ve-güncel-durum)).

---

## İçindekiler

- [Genel Bakış](#genel-bakış)
- [Mimari](#mimari)
- [Teknoloji Yığını](#teknoloji-yığını)
- [Kurulum](#kurulum)
- [Kullanım](#kullanım)
- [Bilinen Sorunlar ve Güncel Durum](#bilinen-sorunlar-ve-güncel-durum)
- [Geliştirme Ortamı Notları](#geliştirme-ortamı-notları)
- [Yol Haritası](#yol-haritası)
- [Proje Dokümanları](#proje-dokümanları)

---

## Genel Bakış

FretFlow, dört farklı girdi formatını destekleyen bir işlem hattı (pipeline)
üzerinden çalışır:

| Girdi | Yol | Güvenilirlik |
|---|---|---|
| `.xml` / `.musicxml` / `.mxl` | `music21` ile parse | ✅ Yüksek |
| `.mid` / `.midi` | `music21` ile parse | ✅ Yüksek |
| `.pdf` | Custom OpenCV tabanlı OMR (`PDFOMRService`) | ⚠️ Bilinen pitch sorunu |
| `.png` / `.jpg` / `.jpeg` / `.webp` | OpenCV tabanlı, ayrı basit yol | Değerlendirilmedi |

Her yolun çıktısı ortak bir formata normalize edilir:

```python
omr_data = {
    'tempo': int,
    'time_signature': '4/4',
    'key': 'C',
    'notes': [{'pitch': 'G4', 'midi': 67, 'duration': 1.0, 'beat': 1.0}, ...],
    'source': 'musicxml' | 'midi' | 'pdf_omr' | 'opencv_omr' | 'fallback',
}
```

Bu `omr_data`, ikinci katmanda `GuitarMappingService` tarafından gitar
string/fret/finger pozisyonlarına çevrilir. Pitch doğru geldiği sürece bu
katman sorunsuz çalışır. Üçüncü bir katman olan `TrustScoreService`,
üretilen tab için bir güven skoru hesaplar.

## Mimari

```
process_file(bytes, filename)
  ├─ .xml/.musicxml/.mxl  → _parse_musicxml()  → music21
  ├─ .mid/.midi           → _parse_midi()      → music21
  ├─ .pdf                 → _parse_pdf()       → PDFOMRService (OpenCV tabanlı)
  └─ .png/.jpg/.jpeg/.webp→ _parse_image()     → OpenCV (basit, ayrı yol)
```

### `PDFOMRService` (kritik bileşen, aktif olarak yeniden değerlendiriliyor)

PDF'ten nota tespiti şu adımlarla yapılıyor:

1. PyMuPDF ile sayfa 3x zoom render edilir.
2. `pytesseract` ile tempo / time-signature OCR edilir.
3. Hough dönüşümüyle yatay çizgiler bulunur, `_group_staff_lines()` ile
   5'li gruplara (staff'lara) ayrılır, treble/bass ayrımı yapılır.
4. Her staff için `_detect_notes_in_staff()` çağrılır:
   - Sol %15 (anahtar/clef alanı) crop'tan atlanır.
   - Kontur tabanlı blob tespiti (`find_blobs`) nota kafalarını bulur.
   - Her blobun staff üzerindeki dikey konumu ("step") hesaplanır ve
     `TREBLE_MAP` sözlüğü ile nota ismine (`G4`, `D5` vb.) çevrilir.
   - Birleşmiş nota kafaları `_split_blob()` ile distance-transform
     kullanılarak ayrılmaya çalışılır.

Bu custom OpenCV heuristic'i **elle ayarlanmış sabit eşiklere** dayanıyor
ve kırılgan olduğu tespit edildi (bkz. aşağıdaki bölüm). Bu yüzden paralel
olarak **`oemer`** (hazır, deep-learning tabanlı bir OMR kütüphanesi) ile
değiştirme/destekleme değerlendiriliyor. `oemer` görüntüden doğrudan
MusicXML üretir ve bu çıktı zaten güvenilir çalışan `_parse_musicxml()`
yoluna bağlanabilir.

**Hedeflenen (henüz uygulanmamış) mimari:**

```
.pdf → PDF→PNG (PyMuPDF) → oemer (izole venv, subprocess) → MusicXML → _parse_musicxml()
```

`oemer`'in ağır bağımlılıkları (ONNX Runtime / TensorFlow, ~200MB model
checkpoint) nedeniyle production venv'ine doğrudan kurulması yerine ayrı
bir izole venv'de (`/opt/oemer_venv`) tutulup `subprocess` ile çağrılması
planlanıyor.

## Teknoloji Yığını

- **Python 3.12**, FastAPI (production'da `uvicorn`, 2 worker ile çalışıyor)
- **OpenCV** (`opencv-python-headless==4.9.0.80`) — görüntü işleme, staff/nota tespiti
- **NumPy** (`1.26.4`)
- **PyMuPDF** (`fitz`, `1.28.0`) — PDF → görüntü render
- **music21** (`9.1.0`) — MusicXML/MIDI parse (en güvenilir yol)
- **pytesseract** — tempo / time-signature OCR
- **SQLAlchemy** + **Alembic** + **psycopg2** — veritabanı katmanı
- **Pydantic** / **pydantic-settings** — konfigürasyon ve veri doğrulama
- **python-jose** + **passlib\[bcrypt\]** — requirements'ta, ama kimlik doğrulama henüz kodda yok
- **Değerlendirilen alternatif:** [`oemer`](https://github.com/BreezeWhite/oemer)
  — deep-learning tabanlı OMR aracı, custom OpenCV pipeline'ının PDF
  yolundaki yerini alma adayı

## Kurulum

```bash
git clone <repo-url>
cd fretflow/backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

Üretim kodu `backend/` altındadır. Ortam değişkenleri `backend/.env`
dosyasından okunur; `DATABASE_URL` ve `SECRET_KEY` **zorunludur** (varsayılanı
yoktur, eksikse uygulama açılmaz). Örnek için `backend/.env.example`'a bakın;
gerçek değerleri repoya koymayın.

Sunucuda `DATABASE_URL`, Docker `postgres-ortak` (127.0.0.1:5434) içindeki
`fretflow_db` veritabanına `uygulama` rolüyle bağlanır. Dokümanda yalnızca
host/port/rol yazılıdır; şifre ve tam URL yoktur.

Servis systemd altında çalışacak şekilde kurulu (`fretflow.service`):

```bash
systemctl status fretflow
systemctl restart fretflow
```

> ⚠️ Bu repoda **iki farklı Python ortamı** olabilir: production venv
> (`/opt/fretflow/venv`) ve `oemer` denemeleri için izole bir venv
> (`/opt/oemer_venv`). Bu ikisini birbirine karıştırmamaya dikkat edin —
> `oemer`'in bağımlılıkları (belirli `numpy`/`opencv`/`onnxruntime`
> sürümleri) production'ın ihtiyaç duyduğu sürümlerle çakışıyor.

## Kullanım

```python
from app.services.omr_service import OMRService

svc = OMRService()
data = open('nota.pdf', 'rb').read()
result = svc.process_file(data, 'nota.pdf')

print(result['omr_data']['notes'])
# [{'pitch': 'G4', 'midi': 67, 'duration': 1.0, 'beat': 1.0}, ...]
```

## Bilinen Sorunlar ve Güncel Durum

### ✅ Çözüldü

- **Production venv kirlenmesi** — `oemer` denemeleri sırasında yanlışlıkla
  production venv'e sızan paketler (`scipy`, `onnxruntime`,
  `opencv-python-headless` yanlış sürüm, `oemer`, `scikit-learn`,
  `types-tensorflow`) tespit edildi, `requirements.txt` referans alınarak
  temizlendi ve doğru sürümler restore edildi. `pip check` artık temiz,
  servis sorunsuz ayakta.
- **Staff çizgi gruplama hatası** — sabit dilimleme (`groups[i:i+5]`)
  yerine ardışık gruplama + eksik çizgi enterpolasyonu ile değiştirildi.
- **Nota yüksekliği filtresi sınır hatası** — `h < spacing*2` filtresi
  sınırda (`42<42`) notaları reddediyordu; `h < spacing*2.3` yapıldı.
- **`TREBLE_MAP` off-by-one hatası** — staff'ın en alt çizgisinin hemen
  altındaki step (`-1`), yanlışlıkla en alt çizgiyle (`E4`) aynı notaya
  eşleniyordu; olması gereken `D4` idi. Bu, staff altındaki tüm ledger-line
  notalarının bir basamak yanlış (yüksek) tespit edilmesine yol açıyordu.
  Hem modül seviyesindeki hem `PDFOMRService` sınıfı içindeki
  `TREBLE_MAP` düzeltildi.
- **Servis DB bağlantısı** — uygulama Docker `postgres-ortak` (127.0.0.1:5434)
  / `fretflow_db` / `uygulama` rolüne bağlı; yerel PostgreSQL 16 `main` (5432)
  kullanılmıyor (veri dizini kayıp). Veri eşleşmesi teyit bekliyor (SESSION.md §19).
- **`fretflow.service` açılışta kalkıyor** — `enabled`, `active`; unit'ten
  `postgresql.service` bağımlılığı kaldırıldı, `docker.service` eklendi (2026-11-09).
- **CORS** — `*` değil; allowlist (`selimkilic.online` dahil) (PR #7, #10).
- **Anonim oylar** — `user_id=NULL` (PR #7); `user_id=1` sabiti kaldırıldı.

### 🟡 Teyit bekleyen / açık

- **Reboot testi** — `enabled` doğrulandı ama sunucu reboot'u ile açılış gözlemlenmedi.
- **Tekrar oy engeli ve kimlik doğrulama** — henüz yok (şema değişikliği gerekir; BACKLOG.md).
- **Dış alan adı `fretflow.dehateknikservis.com`** — yayında değil (vhost pasif, sertifika yok); karar sunucu sahibinde.

### 🔄 Devam Ediyor

- **PDF pitch tespiti hâlâ yeterince güvenilir değil** — yukarıdaki
  düzeltmelere rağmen, custom OpenCV pipeline'ının pitch çıktısı gerçek
  notayla sistematik olarak örtüşmüyor. Kabul testinde (10 nota) sadece
  "stepwise hareket" düzeyinde bir benzerlik gözlemlendi, mutlak pitch
  değerleri tutarsız kalmaya devam ediyor.
- **Yöntem değerlendirmesi:** Elle ayarlanmış sabit-eşikli bir heuristic
  yaklaşımının (whack-a-mole şeklinde her fix'in yeni bir sorun açması)
  yapısal olarak kırılgan olduğu görüldü. Bu nedenle **`oemer`** (hazır,
  deep-learning tabanlı OMR kütüphanesi) ile PDF yolunu değiştirmek/
  desteklemek değerlendiriliyor ve bağımsız açık kaynak projelerle
  (`PDF2Muse`, `homr`, karşılaştırmalı OMR benchmark'ları) bu yaklaşımın
  makul olduğu teyit edildi.
- **`oemer` kurulumu** — izole venv'de (`/opt/oemer_venv`) çalışıyor (oemer
  0.1.8, bağımlılık çakışmaları çözüldü, SESSION.md §11-14). Kabul testi
  (tek sayfa, 10 nota): oemer **2/10**. Entegrasyon kararı bekliyor (TASK.md).

### Kabul Kriteri (pitch doğruluğu için)

```python
from app.services.omr_service import OMRService
svc = OMRService()
data = open('/tmp/nota.pdf', 'rb').read()
result = svc.process_file(data, 'nota.pdf')
notes = result['omr_data']['notes']
omr = [n['pitch'] for n in notes[:10]]
beklenen = ['G4', 'G4', 'A4', 'G4', 'E4', 'F4', 'E4', 'D4', 'E4', 'D4']
print('Dogruluk:', sum(a == b for a, b in zip(omr, beklenen)), '/10')
```

## Geliştirme Ortamı Notları

- Sunucuda **iki venv** var: production (`/opt/fretflow/venv`, otomatik
  aktif) ve `oemer` denemeleri için izole (`/opt/oemer_venv`, manuel
  aktive edilmeli). Her komut öncesi terminal prompt'unun (`(venv)` mi
  `(oemer_venv)` mi yoksa çıplak `root@...` mi) kontrol edilmesi kritik —
  yanlış ortamda kurulum yapmak production'ı bozabilir (bu daha önce iki
  kez yaşandı ve restore edilmesi gerekti).
- Kod içi docstring/yorumlar Türkçe, fonksiyon/değişken isimleri İngilizce.
- `debug_omr.py`, servisin `find_blobs` filtre koşulunun **paralel, ayrı
  bir kopyasını** içeriyordu — servis tarafında bir filtre değişikliği
  yapıldığında bu kopyanın da güncellenmesi gerekiyor, aksi halde debug
  çıktısı yanıltıcı olur.

## Yol Haritası

- [x] Production venv'i restore et, bağımlılık çakışmalarını temizle
- [x] Staff çizgi gruplama hatasını düzelt
- [x] Nota yüksekliği filtresi sınır hatasını düzelt
- [x] `TREBLE_MAP` off-by-one hatasını düzelt
- [x] `oemer`'i izole venv'de çalışır hale getirmek (`/opt/oemer_venv`)
- [x] `oemer` çıktısını (MusicXML) test etmek, pitch doğruluğunu kabul
      kriteriyle ölçmek (2/10 — eşik geçilmedi)
- [ ] Tekrarlanabilir OMR ölçümü (birden fazla sayfa) ve üretim yolu kararı
- [ ] Başarılıysa: `PDFOMRService`'e `subprocess` tabanlı `oemer`
      entegrasyonu eklemek, eski custom pipeline'ı kademeli olarak
      devre dışı bırakmak
- [ ] Görüntü (PNG/JPG) pipeline'ını da benzer şekilde değerlendirmek

## Proje Dokümanları

Bu repo, Claude ile yürütülen geliştirme oturumları arasında bağlamı
korumak için ek markdown dosyaları kullanıyor:

- **`CLAUDE.md`** — ortam bilgileri, kritik kısıtlamalar, oturum yönetimi
  protokolü (nadiren değişir)
- **`TASK.md`** — o anki aktif görev ve kabul kriterleri
- **`ARCHITECT.md`** — `omr_service.py` mimarisinin detaylı açıklaması
- **`SESSION.md`** — kronolojik oturum günlüğü, bulgular ve fix geçmişi
