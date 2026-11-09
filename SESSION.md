# SESSION.md — Oturum Günlüğü

> Kronolojik ilerleme kaydı. Yeni bulgu/fix oldukça buraya ekle.

## Durum Özeti (şu an — EN GÜNCEL)

| Konu | Durum |
|---|---|
| Bug #1 — Staff çizgi gruplama | ✅ Çözüldü, doğrulandı |
| Bug #2 — `h<spacing*2` filtresi | ✅ Fix uygulandı (`spacing*2.3`) |
| Bug #3 — `_split_blob` patch'inin dosyada var mı | ✅ Doğrulandı, var (satır 758) |
| **Production venv** | ✅ RESTORE EDİLDİ — `pip check` temiz, servis sağlıklı çalışıyor |
| **Bug #4 — `TREBLE_MAP` off-by-one** | ✅ Bulundu ve düzeltildi (hem modül hem class seviyesi) |
| **Sayısal doğrulama (kabul testi)** | ❌ Henüz yapılmadı — bir sonraki oturumda ilk iş |
| **Yaklaşım kararı** | 🔄 Custom OpenCV pipeline'dan **oemer**'e geçiş kararlaştırıldı, bağımsız araştırmayla desteklendi |
| **oemer kurulumu/testi** | 🔄 İzole venv (`/opt/oemer_venv`) hazır ama test PNG üzerinde henüz ÇALIŞTIRILMADI (kaldığımız yer) |
| **Repo temizliği (2026-11-09)** | ✅ `app/` (kök) ve `smart-tab/` kaldırıldı (PR #1); `omr_service.py.bak` kaldırıldı, `.gitignore`'a `*.bak` eklendi. Üretim kodu `backend/` altında |
| **requirements.txt** | ✅ `pymupdf==1.28.0` sabitlendi (PR #2) |
| **main.py / config.py eşitleme** | ✅ Sunucudaki dosyalarla birebir eşitlendi (PR #3). Repoda artık sunucudaki güvenlik/hız sınırı kodu da var (bkz. §18) |
| **SECRET_KEY** | ✅ Varsayılan kaldırıldı, zorunlu (PR #4). Sunucu `.env` içinde 64 karakterlik değer var (değer repoda yok) |
| **omr_service.py (repo ↔ sunucu)** | ✅ AST düzeyinde aynı; sunucuda yalnızca fazladan docstring/yorum var. `TREBLE_MAP` düzeltmesi iki tarafta da var |
| **🔴 Servis DB bağlantısı (AÇIK)** | 🔍 Araştırılıyor — uvicorn 127.0.0.1:8010 2026-11-08 13:51'den beri dinlemiyor. Sebep DB bağlantısı (bkz. §18). Canlı verinin yeri doğrulanmadı |
| **🔴 fretflow.service (AÇIK)** | ⚠️ Sunucuda `disabled` — reboot sonrası kalkmaz |
| **🔴 Güvenlik (AÇIK)** | ⚠️ CORS `*`, `user_id=1` sabiti (giriş yok), kimlik doğrulama yok — araştırılıyor, çözülmedi |

---

## 1-8. (Çok eski oturum — özet)

- Bug #1 (staff çizgi gruplama, `_group_staff_lines`) bulundu ve çözüldü.
- Ground truth görsel olarak doğrulandı (Sistem 1: "Yir-mi üç Ni-san kut-lu
  ol-sun" → G4-A4-G4-E4-F4-E4-D4 civarı melodi).
- Bug #2 ilk teşhisi ("2 nota birleşmiş") **yanlış** çıktı — gerçek sorun
  `h<spacing*2` filtresinin sınırda (`42<42`) reddetmesiydi.
- `_split_blob` patch'i verildi ama bu spesifik örneği kapsamıyordu.

## 9. Bug #2 Fix'i Uygulandı — Pitch Hâlâ Şüpheliydi

`h<spacing*2` → `h<spacing*2.3` yapıldı. `debug_omr.py`'nin **kendi ayrı/
paralel filtre kopyası** olduğu keşfedildi, o da güncellendi. Koordinat
karışıklığı (lokal crop x vs. mutlak `cx+x_start`) çözüldü — yanlış
alarmdı, nota kaybolmamıştı.

Fix sonrası gözlemlenen (`omr_debug_log7.txt`):
```
FINAL (ilk 10 pitch): E4 E4 D4 D4 D4 E4 D4 C4 G4 D5
Beklenen:             G4 G4 A4 G4 E4 F4 E4 D4 E4 D4
```
Sadece "stepwise hareket" düzeyinde örtüşme, pitch'ler sistematik olarak
kaymış görünüyordu. **Bu gözlem, sonradan Bug #4'ün (TREBLE_MAP) ipucuydu.**

## 10. Yaklaşım Kararı — Custom Pipeline'dan oemer'e Geçiş

Kullanıcıya "yanlış kütüphane mi kullanıyoruz" sorusu soruldu. Elle
yazılmış OpenCV heuristic'inin kırılgan olduğu değerlendirildi (whack-a-mole
belirtisi). **Karar:** `oemer` denenecek. Kullanıcı onayladı.

## 11. İlk oemer Kurulum Denemesi — YANLIŞ ORTAMDA (production venv)

`pip install oemer` **production venv'de** (`(venv)` prompt'unda, farkında
olmadan) çalıştırıldı. `numpy`'yi `2.5.1`'e yükseltip `cv2` importunu
kırdı. `deactivate` sonrası sistem Python'una düşüldüğü fark edilmeden
"production düzeldi" sanıldı — aslında hiç dokunulmamıştı (yanlış
yönlendirme).

## 12. İzole `/opt/oemer_venv` Kuruldu — Doğru Yaklaşım

```bash
python3 -m venv /opt/oemer_venv
source /opt/oemer_venv/bin/activate
pip install oemer
```
Başarılı kuruldu, production'a dokunmadı. Ama çalıştırıldığında:
```
[ShapeInferenceError] Attribute pads must not contain negative values
```
(ONNX model, kurulu `onnxruntime==1.28.0` ile uyumsuz.) Denenen fixler
`onnxruntime==1.17.0` → numpy<2 gerektiriyor, ama oemer'in çektiği güncel
`scipy`/`opencv-python-headless` numpy>=2 istiyor — **doğrudan çelişki.**

## 13. ⚠️ İKİNCİ KAZA — Production Venv'e Tekrar Yanlışlıkla Kurulum

Bir sonraki fix denemesi (`pip install "numpy<2" "scipy<1.13"
"opencv-python-headless<5" "onnxruntime==1.17.0" --force-reinstall`)
**yine production venv'de** çalıştırıldı. Production'a `oemer`,
`onnxruntime`, `scipy`, yanlış sürüm `opencv-python-headless` ve ~200MB
model checkpoint'i bulaştı. Oturum burada durduruldu, restore gerekiyordu.

## 14. ✅ Production Restore Edildi + `TREBLE_MAP` Bug'ı Bulundu ve Düzeltildi

**Yeni oturum, TASK.md'nin acil önceliğiyle başlandı.**

1. `find /opt/fretflow -maxdepth 3 -iname "requirements*.txt" ...` →
   `/opt/fretflow/backend/requirements.txt` bulundu.
2. `pip list | grep -iE "numpy|scipy|opencv|onnxruntime|oemer"` ile kirlilik
   teyit edildi: `numpy 1.26.4` (şans eseri doğruydu), `oemer 0.1.8`,
   `onnxruntime 1.17.0`/`onnxruntime-gpu 1.28.0`, `opencv-python-headless
   4.11.0.86` (yanlış sürüm), `scipy 1.12.0` (requirements'ta hiç yok).
3. Restore:
   ```bash
   pip uninstall -y oemer onnxruntime onnxruntime-gpu opencv-python-headless numpy scipy
   pip install -r /opt/fretflow/backend/requirements.txt
   ```
   `numpy==1.26.4` ve `opencv-python-headless==4.9.0.80` doğru kuruldu.
4. `pip check` ilk seferde `scikit-learn`/`types-tensorflow` (requirements'ta
   olmayan, oemer denemelerinden kalma artıklar) yüzünden uyarı verdi.
   `grep -riE "sklearn|scikit-learn|tensorflow" app/` → kod içinde hiç
   kullanılmadığı doğrulandı → `pip uninstall -y scikit-learn
   types-tensorflow` → **`pip check` artık "No broken requirements found."**
5. `python -c "from app.services.omr_service import *"` → hatasız.
6. `systemctl restart fretflow` → servis "active (running)", worker'lar
   sağlıklı ayakta.

**Ardından ARCHITECT.md yeniden okunarak asıl pitch bug'ı arandı.**
`TREBLE_MAP` incelendiğinde: `step -1` ve `step 0` ikisi de `E4`'e
eşleniyordu (duplikasyon) — staff'ın en alt çizgisi (step 0) doğru E4 iken,
onun hemen altındaki boşluk (step -1) **D4** olması gerekirken yanlışlıkla
tekrar E4 yazılmıştı. Bu, staff altındaki (ledger-line) tüm notaların bir
basamak kaymasına yol açıyordu. Step 0 ve üzeri (F4, G4, A4...) baştan
beri doğruydu.

**Fix (iki yerde, hem modül seviyesi satır 30 hem `PDFOMRService` sınıfı
içi satır 537):**
```python
# önce
-4:('B',3,59), -3:('C',4,60), -2:('D',4,62), -1:('E',4,64), 0:('E',4,64), ...
# sonra
-4:('A',3,57), -3:('B',3,59), -2:('C',4,60), -1:('D',4,62), 0:('E',4,64), ...
```
Yedek alındı (`omr_service.py.bak_pre_treblemap_fix`), `sed` ile uygulandı,
`sed -n` ile doğrulandı, import testiyle sözdizimi hatası olmadığı
teyit edildi, servis restart edildi.

**Görsel doğrulama için `debug_omr.py`'ye pitch etiketi eklendi:**
`cv2.rectangle(overlay, ...)` satırının hemen altına:
```python
cv2.putText(overlay, f'{nm}{oc}', (x, max(y-3,10)), cv2.FONT_HERSHEY_SIMPLEX, 0.35, color, 1)
```
`debug_omr.py` çalıştırıldı, yeni final nota listesi eskisinden belirgin
şekilde farklı (D4, F4, G4, B4, C5, D5 gibi çeşitli pitch'ler) — artık
staff üstü/altı ayrımı yapılıyor gibi görünüyor. `staff2_4_overlay.png`
indirilip incelendi: kutucuklar staff'a göre doğru pozisyonlarda (soldaki
iki nota belirgin şekilde staff altında/ledger-line bölgesinde) ama o
görselde henüz pitch etiketi yoktu (putText eklemesinden ÖNCE alınmıştı) —
yeni overlay (etiketli) henüz indirilip gözle teyit edilmedi.

**AÇIK KALAN:** Kabul kriteriyle (10 notalık test, `Dogruluk: x/10`) sayısal
doğrulama henüz yapılmadı. Bir sonraki oturumda ilk iş bu olmalı.

## 15. Bağımsız Araştırma — Benzer Açık Kaynak Projeler

Kullanıcı "yöntem hatası yapıyor olabiliriz, benzer repo var mı" diye
sordu. Web'de arama yapıldı:
- **`PDF2Muse`** — `oemer` kullanarak PDF'i MusicXML/MuseScore'a çeviren
  bağımsız bir CLI aracı. Planlanan "PDF→oemer→MusicXML" mimarisinin
  başkası tarafından zaten üretimde kullanıldığının kanıtı.
- **`homr`** — kamera görüntüsünden MusicXML üreten alternatif OMR
  kütüphanesi (oemer'e alternatif).
- Bir **OMR benchmark projesi** — Audiveris/HOMR/OeMeR'i karşılaştırıyor,
  hangi kütüphanenin daha isabetli olduğuna dair bağımsız veri sağlıyor.
- `Mozart` (aashrafh) — daha akademik/basit, production için olgun değil.

**Sonuç:** Custom `TREBLE_MAP`/blob-detection yaklaşımını piksel piksel
debug etmeye devam etmek yerine, zaten planlanmış olan oemer geçişine
öncelik verilmesi kararı güçlendi (ARCHITECT.md güncellendi).

## 16. Dosya Transferi Hatası (öğrenilen ders)

`scp root@95.111.242.96:/tmp/omr_debug/staff2_4_overlay.png .` komutu
kullanıcı tarafından **SSH oturumunun içinde** çalıştırıldı — bu, dosyayı
sunucudan sunucuya (kendi home'una) kopyaladı, Windows'a indirmedi. Doğru
kullanım: bu komut Windows'ta **ayrı bir PowerShell penceresinde**
çalıştırılmalı. CLAUDE.md'ye bu uyarı eklendi.

## 17. `staff2_4_overlay.png` Görsel İncelemesi

Kullanıcı doğru şekilde indirip yükledi. Kutucuklar (yeşil=kabul,
kırmızı=red) staff çizgileriyle birlikte görüldü; soldaki iki nota
belirgin şekilde staff'ın altında (ledger-line bölgesi) — düzeltilen
negatif step aralığıyla örtüşüyor. Ama bu görsel `putText` eklemesinden
**önce** alınmıştı, üzerinde pitch ismi yazmıyordu — kesin gözle teyit
için etiketli yeni overlay gerekiyor (bkz. §14 sonu, açık kalan iş).

## 18. 2026-11-09 — Repo Temizliği, Sunucu Eşitleme ve Açık Sorunlar

Bu oturumda yalnızca dokümanlar güncellendi; kod değiştirilmedi. Sunucuya
bağlanılmadı; sunucu ile ilgili maddeler kullanıcının bildirdiği
gözlemlerdir ve repodan doğrulanamaz.

### Repo (git'te doğrulandı)

1. **PR #1** — `app/` (kök) ve `smart-tab/` kaldırıldı. Üretim kodu `backend/` ağacıdır.
   `backend/app/services/omr_service.py.bak` kaldırıldı; `.gitignore`'a `*.bak` eklendi.
2. **PR #2** — `backend/requirements.txt` içinde `pymupdf==1.28.0` sabitlendi.
3. **PR #3** — `backend/app/main.py` ve `backend/app/core/config.py` sunucudaki
   dosyalarla birebir eşitlendi. Repoda artık şunlar var (sunucudan gelen kod):
   - IP başına hız sınırı: upload 10/dk, edit 20/dk, vote 30/dk
   - Swagger/OpenAPI kapalı (`docs_url=None`, `openapi_url=None`)
   - Oy (`vote`) türü doğrulaması (`rate` / `accuracy`)
   - `user_id=1` sabiti (giriş/kimlik doğrulama yok)
   - CORS `allow_origins=["*"]`
4. **PR #4** — `SECRET_KEY` varsayılanı kaldırıldı, zorunlu yapıldı
   (`config.py`). `DATABASE_URL` da zaten zorunlu ve koddan gömülü değil.
5. `omr_service.py` repo ve sunucuda AST düzeyinde aynı. Modül seviyesi ve
   `PDFOMRService` içi `TREBLE_MAP` düzeltmesi (`-1:('D',4,62)`) iki tarafta da var.

### Sunucu (kullanıcı gözlemi — repodan doğrulanamaz)

- Sunucuda `config.py` yedeği: `/opt/fretflow/backend/app/core/config.py.bak_20261108155131`
- `.env` içinde 64 karakterlik SECRET_KEY doğrulandı (değer bu dosyada yok, olmamalı).

### 🔴 AÇIK — Servis DB bağlantısı (araştırılıyor, çözülmedi)

- `fretflow` (uvicorn 127.0.0.1:8010) **2026-11-08 13:51'den beri 8010'da dinlemiyor.**
  Sebep olarak veritabanı bağlantısı düşünülüyor.
- Yerel PostgreSQL 16 `main` (5432) kümesinin veri dizini **yok**.
- `.env` `apache` kullanıcısı ve `localhost:5432` kullanıyor.
- Docker `postgres-ortak` (5434) içindeki `fretflow_db` eski bir kopya gibi görünüyor:
  son kayıt Temmuz 2026, `uygulama` rolü sahibi, `apache` rolü yok.
- **Canlı verinin hangi veritabanında olduğu DOĞRULANMADI.** Bu netleşmeden
  DB'ye yazan bir işlem yapılmamalı.

### 🔴 AÇIK — Diğer

- `fretflow.service` sunucuda `disabled` (reboot'ta kalkmaz). — araştırılıyor
- Güvenlik: CORS `*`, `user_id=1` sabiti, kimlik doğrulama yok. — araştırılıyor, çözülmedi
- oemer testi (TASK.md) hâlâ bekliyor; kabul testi (`Dogruluk: x/10`) ölçülmedi.

---

## Debug Log / Dosya Envanteri (sunucuda)

- `/tmp/omr_debug_log.txt` … `/tmp/omr_debug_log7.txt` — kronolojik debug
  çıktıları (Bug #1'den TREBLE_MAP fix'inden hemen önceye kadar)
- `/tmp/omr_debug/*.png` — binary/no_staff/no_stems/overlay görüntüleri
  (staff0/1/2 için ayrı ayrı)
- `/tmp/nota.pdf` — ana test dosyası
- `/tmp/nota_page1.png` — oemer testi için PyMuPDF ile üretilen sayfa görüntüsü
- `/opt/fretflow/backend/debug_omr.py` — güncel (filtre satırı + pitch
  etiketi `putText` eklenmiş hâli)
- `/opt/fretflow/backend/app/services/omr_service.py.bak_pre_treblemap_fix`
  — TREBLE_MAP fix'inden önceki yedek

---

## Claude'a Not

Her 10 mesajda bir token durumunu değerlendir. Eğer konu değişikliği veya
büyük bir görev bitişi olduysa "Oturumu kapatmalı mıyız?" diye sor.
(Bkz. CLAUDE.md § Oturum Yönetimi — tam protokol için.)
