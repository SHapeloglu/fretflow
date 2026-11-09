# FretFlow

Nota (sheet music) verisinden otomatik **gitar tab'ı** üreten bir OMR
(Optical Music Recognition) servisi. Kullanıcı bir nota dosyası (PDF,
MusicXML, MIDI veya görüntü) yükler; sistem notaları tespit edip gitar
üzerinde çalınabilir pozisyonlara (string / fret / finger) çevirir.

> **Durum (2026-11-09):** Aktif geliştirme. Sunucuda `fretflow` servisi
> **2026-11-08 13:51'den beri 8010'da dinlemiyor** (DB bağlantısı şüphesi,
> araştırılıyor — doğrulanmadı). PDF→OMR yolunda bilinen bir pitch-doğruluğu
> sorunu var (bkz. [Bilinen Sorunlar](#bilinen-sorunlar-ve-güncel-durum)).

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
- **python-jose** + **passlib\[bcrypt\]** — kimlik doğrulama
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

### 🔴 Açık (araştırılıyor, çözülmedi — 2026-11-09)

- **Servis DB bağlantısı:** sunucuda `fretflow` 2026-11-08 13:51'den beri
  8010'da dinlemiyor; DB bağlantısı şüphesi var. Yerel PostgreSQL 16 `main`
  kümesinin veri dizini yok, Docker `postgres-ortak` (5434) içindeki
  `fretflow_db` eski kopya gibi görünüyor. Canlı verinin yeri doğrulanmadı.
- **`fretflow.service` `disabled`** — reboot'ta kalkmaz.
- **Güvenlik:** CORS `*`, `user_id=1` sabiti (kimlik doğrulama yok).

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
- **`oemer` kurulumu** — izole venv'de (`/opt/oemer_venv`) bağımlılık
  çakışması yaşandı: `oemer`'in çektiği güncel `scipy`/
  `opencv-python-headless` sürümleri `numpy>=2` istiyor, ancak ONNX model
  hatasını çözen `onnxruntime==1.17.0` `numpy<2` gerektiriyor. Çözüm
  yolları (`--use-tf` bayrağı ile TensorFlow checkpoint kullanmak, ya da
  bağımlılıkları elle sabitlemek) deneniyor.

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
- [ ] `oemer`'i izole venv'de çalışır hale getirmek (bağımlılık çakışması
      çözülmeli: `numpy`/`scipy`/`opencv`/`onnxruntime` sürüm uyumu)
- [ ] `oemer` çıktısını (MusicXML) `_parse_musicxml()` ile test etmek,
      pitch doğruluğunu kabul kriteriyle ölçmek
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
