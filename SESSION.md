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
| **Sayısal doğrulama (kabul testi)** | ✅ 2026-11-09 yapıldı: oemer 2/10, OpenCV (üretim) 0/10 — eşik geçilmedi (bkz. §20) |
| **Yaklaşım kararı** | 🔄 oemer denendi (2/10), OpenCV 0/10. Hangi yolun üretime alınacağı kararı sahibinde (TASK.md "AKTİF") |
| **oemer kurulumu/testi** | ✅ `/opt/oemer_venv` içinde çalışıyor; test PNG'de ölçüldü (bkz. §20) |
| **Repo temizliği (2026-11-09)** | ✅ `app/` (kök) ve `smart-tab/` kaldırıldı (PR #1); `omr_service.py.bak` kaldırıldı, `.gitignore`'a `*.bak` eklendi. Üretim kodu `backend/` altında |
| **requirements.txt** | ✅ `pymupdf==1.28.0` sabitlendi (PR #2) |
| **main.py / config.py eşitleme** | ✅ Sunucudaki dosyalarla birebir eşitlendi (PR #3). Repoda artık sunucudaki güvenlik/hız sınırı kodu da var (bkz. §18) |
| **SECRET_KEY** | ✅ Varsayılan kaldırıldı, zorunlu (PR #4). Sunucu `.env` içinde 64 karakterlik değer var (değer repoda yok) |
| **omr_service.py (repo ↔ sunucu)** | ✅ AST düzeyinde aynı; sunucuda yalnızca fazladan docstring/yorum var. `TREBLE_MAP` düzeltmesi iki tarafta da var |
| **Servis DB bağlantısı** | ✅ Çözüldü — uygulama Docker `postgres-ortak` (127.0.0.1:5434) / `fretflow_db` / `uygulama` rolüne bağlı; `/health` 200. Veri eşleşmesi sahibi teyidi bekliyor (bkz. §19) |
| **fretflow.service enable durumu** | ✅ `enabled` + `active`, `Restart=always` (2026-11-11 doğrulandı). Reboot testi yapılmadı (bkz. §20) |
| **Güvenlik** | ✅ CORS allowlist (PR #7/#10); oylar `user_id=NULL` (PR #7). ⚠️ Tekrar oy engeli ve kimlik doğrulama henüz yok (BACKLOG.md) |
| **Dış alan adı** | ✅ Canlı alan adı `selimkilic.online`. `fretflow.dehateknikservis.com` yayında değil (vhost pasif, sertifika yok) — karar bekliyor (§20) |

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

> **Tarihsel bölüm:** Bu, 2026-11-09 sabahki durumun kaydıdır. Sonraki güncel
> durum §19 ve §20'dedir (ör. `fretflow.service` artık `enabled`; CORS artık allowlist).

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

### ✅ Çözüldü (güncel durum §19) — Servis DB bağlantısı (eski tanı)

- `fretflow` (uvicorn 127.0.0.1:8010) **2026-11-08 13:51'den beri 8010'da dinlemiyor.**
  Sebep olarak veritabanı bağlantısı düşünülüyor.
- Yerel PostgreSQL 16 `main` (5432) kümesinin veri dizini **yok**.
- `.env` `apache` kullanıcısı ve `localhost:5432` kullanıyor.
- Docker `postgres-ortak` (5434) içindeki `fretflow_db` eski bir kopya gibi görünüyor:
  son kayıt Temmuz 2026, `uygulama` rolü sahibi, `apache` rolü yok.
- **Canlı verinin hangi veritabanında olduğu DOĞRULANMADI.** Bu netleşmeden
  DB'ye yazan bir işlem yapılmamalı.

### 🔴 AÇIK — Diğer (2026-11-09 güncel durum: §19)

- ~~`fretflow.service` sunucuda `disabled`~~ — tarihsel; 2026-11-11'de `enabled` (§20).
- ~~Güvenlik: CORS `*`, `user_id=1` sabiti~~ — tarihsel; CORS allowlist ve `user_id=NULL` (PR #7, #10). Tekrar oy engeli açık.
- ~~oemer testi bekliyor~~ — tarihsel; 2026-11-09 kabul testi yapıldı (2/10, §20).

---

## 19. 2026-11-09 — DB Bağlantısı Çözüldü (veri teyidi bekliyor)

Bu bölüm §18'deki DB açığının güncel durumudur. Bu bölümün yazıldığı anda
sunucu bilgileri kullanıcı doğrulamasıydı; sonraki SSH kontrolleri §20'de.

### Doğrulanmış durum (sunucu, kullanıcı doğrulaması)

- `fretflow` systemd servisi 127.0.0.1:8010'da çalışıyor; `/health` 200 dönüyor.
- Yerel PostgreSQL 16 `main` (5432) kullanılmıyor; veri dizini kayıp.
- Uygulama Docker `postgres-ortak` konteynerindeki (127.0.0.1:5434)
  `fretflow_db` veritabanına `uygulama` rolüyle bağlanıyor.
- Bağlantı, `/opt/fretflow/.env` içindeki Docker dönemi ayarıyla aynıdır;
  `backend/.env` içindeki `DATABASE_URL` buna göre değiştirildi. Eski
  dosyanın yedeği: `/opt/fretflow/backend/.env.bak_20261109095730`
  (gizli değer içerir; repoya alınmamalı).

### Veri doğrulaması

- 18 Ekim geçiş dump'ı (`/root/yedekler/fretflow-gecis-20261018-2121/fretflow_db.dump`)
  geçici bir container'a geri yüklendi. İçeriği Docker `fretflow_db` ile aynı:
  `users` 0, `sheet_uploads` 4, `tab_versions` 4, `tab_votes` 0; son kayıt 2026-07-14.
- Bilinen en iyi kaynak bu dump. Kullanıcı/oy verisi kaybolmuş olmayabilir ama
  kesin değil; sahibinin teyidi gerekiyor.

### Yerel PostgreSQL veri kaybı

- Veri dizininin kaybolma zamanı: 19 Ekim – 8 Kasım arası. **Kanıtlanamadı.**
  Araştırma BACKLOG.md'ye eklendi.

### Açık kalanlar

- ~~`fretflow.service` enable durumu teyit bekliyor~~ — 2026-11-11'de `enabled` (§20). Reboot testi hâlâ açık.
- Docker `fretflow` container'ı: §20'de `restart=no`, `exited` olarak doğrulandı; silinmedi.
- ~~CORS `*` ve `user_id=1` sabiti~~ — düzeltildi (PR #7, #10); tekrar oy engeli açık.
- ~~oemer testi bekliyor~~ — yapıldı (§20).

---

## 20. 2026-11-09 (öğleden sonra) – 2026-11-11 — Sunucu Düzeltmeleri, Git Onarımı, Doküman Gözden Geçirmesi

### Yapılan değişiklikler

- **PR #10** (`8cc856b`, squash): CORS allowlist'e `https://selimkilic.online`
  eklendi (mevcut üç girdi korundu). TASK/BACKLOG notları düzeltildi
  (oemer "aşırı tespit" yorumu kaldırıldı; enable durumu, dış erişim notu).
- **Sunucu — systemd unit:** `/etc/systemd/system/fretflow.service`
  içinde `Requires=postgresql.service` kaldırıldı, `After=…docker.service` ve
  `Wants=docker.service` eklendi. Yedek: `fretflow.service.bak_20261109212332`.
  `daemon-reload` yapıldı; servis restart edilmedi.
- **Sunucu — `app/main.py`:** sunucudaki dosya repo sürümünden yalnızca
  `selimkilic.online` satırı eksikti. Tek satır eklendi (yedek:
  `main.py.bak_20261109212938`), servis restart edildi.
  Doğrulama: `/health` 200; `selimkilic.online` origin'i için
  `access-control-allow-origin` dönüyor; `evil.example` için dönmüyor.
- **PR #11** (`735dff0`, squash): TASK.md ve BACKLOG.md'de nginx bulgusu ve
  sunucu değişikliklerinin kaydı.

### Nginx bulgusu (salt okunur)

- Canlı FretFlow vhost'u: `/etc/nginx/sites-available/selimkilic.online`
  (`sites-enabled`'da var); `/api` ve `/health` → `127.0.0.1:8010`.
- `fretflow.dehateknikservis.com`: `sites-available/fretflow` dosyası var ama
  `sites-enabled`'da bağlantısı yok. 80. port bloğu `return 404` veriyor;
  443 bloğu `/etc/letsencrypt/live/fretflow.dehateknikservis.com/` altındaki
  sertifikaya bağlı, ama bu sertifika yok. Yani alan adı pasif — kod hatası değil.
- Seçenekler (karar sunucu sahibinde): vhost'u açıp sertifika üretmek ya da
  alan adını ve CORS girdisini kaldırmak. Şu an CORS listesinde zararsız duruyor.

### Git onarımı (yerel repo)

- Oturum kesintisinden sonra yerel `.git`'te `8cc856b…` commit nesnesi **0 bayt**
  bir dosya olarak kalmıştı; `refs/heads/main` bu commit'e işaret ediyordu.
  Aynı anda `BACKLOG.md`, `TASK.md`, `backend/app/main.py` dosyaları da 0 bayta
  dönmüştü. Yarım kalan bir `git pull` olası nedendi; kesin kanıtlanamadı.
- Onarım: boş nesne dosyası silindi, `git fetch origin` ile uzak nesne
  yeniden çekildi (uzak `main` = `8cc856b`, doğrulandı), üç dosya
  `git checkout -- <dosya>` ile commit'lenmiş sürümlerine döndü. Commit'ten
  kaybolan kullanıcı içeriği yoktu (dosyalar zaten boştu).

### Ajanlarla ilgili not

- Paralel ajan çağrıları oturum kesintisinde iptal oldu. Repo ajanı PR #10'u
  zaten birleştirmişti; sunucu ajanı unit değişikliğini uygulamış ama nginx
  incelemesini bitirememişti. Kalan işleri ana oturum tamamladı.

### 2026-11-11 salt okunur kontrol

- `fretflow`: `enabled`, `active`; `Requires` yalnızca `-.mount`, `system.slice`, `sysinit.target`; `Wants/After` `docker.service`.
- `/health` 200; sunucudaki `main.py`'de `selimkilic.online` var.
- Docker: `fretflow` → `restart=no`, `Exited (0)` (4 gün önce); `postgres-ortak` →
  `restart=unless-stopped`, `healthy`, `127.0.0.1:5434`.
- `postgresql.service` hâlâ `active` (sarmalayıcı). Yerel küme/veri dizini bu
  turda incelenmedi; §19'daki "veri dizini yok" bulgusu geçerli.
- Sunucu backup dosyaları (`main.py.bak_*`, unit `.bak_*`) gizli değer içermez;
  `.env.bak_*` içerir (BACKLOG).

### Doküman gözden geçirmesi (2026-11-11)

Altı md dosyası (`README.md`, `ARCHITECT.md`, `SESSION.md`, `TASK.md`,
`BACKLOG.md`, `CLAUDE.md`) kodla ve sunucu durumuyla karşılaştırıldı; eski
ifadeler (CORS `*`, `user_id=1`, `fretflow.service disabled`, oemer "henüz
çalıştırılmadı") düzeltildi.

---

## 21. 2026-11-12 – 2026-11-19 — Tur 2 Düzeltmeleri ve Dağıtım

### Birleşen ve dağıtılan PR'lar
- **PR #13** (`0ff02b9`, 2026-11-12): `main.py` — tanınmayan dosyanın (fallback) örnek TAB'ı
  önbelleğe alınmıyor, DB'ye yazılmıyor, `id/upload_id = None` dönüyor. Frontend: örnek TAB'da
  oy ve düzenleme gizlendi (`TabViewer.jsx`, `TabList.jsx`, `App.jsx`). `.gitignore`: `.claude/worktrees/`.
- **PR #14** (`acba31d`, 2026-11-19): yükleme boyutu 20 MB ile sınırlı (413); OMR
  `asyncio.to_thread` ile çalışıyor; MusicXML/MIDI beat'i ölçü uzunluğunu çeyrek nota cinsinden
  hesaplıyor (6/8 → 1..4); `.mxl` uzantısıyla parse; parse hatasında temp dosya siliniyor;
  `_detect_treble_staffs` boş girdide `[]`; PDF önbellek hash'i tüm dosyadan; `io`, `subprocess`,
  `process_image`, `_split_blob` kaldırıldı.
- Merge kararları kullanıcıda (2026-11-19 onayı ile #14 birleştirildi).

### Sunucu dağıtımı (2026-11-19, kullanıcı onayıyla)
- Yedekler: `app/main.py.bak_20261119174029`, `app/services/omr_service.py.bak_20261119174029`.
- Kontrol: sunucudaki `main.py` repo'nun `0ff02b9` sürümüyle aynıydı, yalnızca #13 bloğu eksikti.
  Sunucudaki `omr_service.py` kodu repo ile aynıydı; fark 122 satır docstring/yorumdu. Yeni
  dosya bu yorumları içermiyor (davranış değişmedi).
- `fretflow.service` restart edildi (NRestarts=0). İlk `/health` denemesi 6 sn beklemeye
  rağmen 000 döndü; birkaç saniye sonra 200 oldu. Servis başlangıcı beklenenden uzun sürüyor.
- Doğrulama (127.0.0.1:8010): MusicXML yükleme 200 (`source=musicxml`); CORS preflight
  (`selimkilic.online`) 200; tanınmayan dosya → `source=fallback`, `upload_id=None`;
  21 MB → 413; son 3 dakikalık journal'da hata yok.
- Sunucudaki `/opt/fretflow/.git` bu işte kullanılmadı; repo ile senkron değil.

### Yerelde doğrulama
- Test venv: `/tmp/fftest2` (uv ile; music21 9.1.0, numpy 1.26.4, OpenCV 4.9.0.80,
  PyMuPDF 1.28.0, FastAPI TestClient, python-multipart, SQLite). Kalıcı testler PR #16 ile eklendi (bkz. §22).
- 6/8 beat 1.0–3.5; 4/4 değişmedi; `.mxl` parse; bozuk XML → fallback; boş staff → `[]`;
  20 MB+ → 413; boş PDF → fallback, çökme yok.

### Açık kalanlar (tur 2)
Bkz. BACKLOG.md "Tur 2 — açık bulgular". En önemlisi: PDF/görüntü yollarında `duration`
hâlâ 1.0 (ritim tespiti yok); PDF yalnızca 1. sayfa ve en fazla 4 staff; A3-01 (X-Real-IP
spoof — 2026-11-25'te kapatıldı, bkz. §23).

---

## 22. 2026-11-20 – 2026-11-24 — Test Altyapısı, Depo Onarımı, Doküman Denetimi

- PR #15 (dokümanlar) ve PR #16 (pytest altyapısı) birleştirildi. `main` = `3222eee` → `fec4130`.
- Test: `backend/requirements-dev.txt` (pytest 8.2.2); `cd backend && pytest` → 11 geçti, 1 atlandı (vaka yok).
- **Depo onarımı:** `fec4130` commit objesi 0 bayt olmuştu. Objeyi silip `git fetch origin` ile geri aldım;
  `git fsck` temiz. Aynı oturumda 7 test dosyası da 0 bayta düşmüştü; `HEAD`'den
  `git checkout --` ile geri alındı. Kök neden kanıtlanmadı; yarıda kesilen işlemlerle uyumlu.
- **uv önbelleği:** kesilmiş indirmelerden bozuk wheel'ler (`psycopg2-binary`, `pydantic-core`) kurulumu
  bozdu. `uv cache clean` ile temizlendi, ortam yeniden kuruldu.
- **Doküman denetimi (2026-11-24):** ARCHITECT (`_split_blob` kaldırıldı, yükleme davranışı, testler,
  satır numaraları tarihli olarak işaretlendi), README (test komutları, PR #13/#14 çözümleri), TASK, BACKLOG ve
  CLAUDE (pytest) güncellendi.

---

## 23. 2026-11-25 — Vote skor fix, PDF render sınırı, nginx kontrolü

- **Vote skor gecikmesi (PR #18, `fix/vote-flush-before-query`):** `SessionLocal` `autoflush=False` olduğu için
  `vote_tab` yeni oyu flush etmeden sorguluyordu; skor bir oy geride kalıyordu. `db.flush()` eklendi;
  `backend/tests/test_vote_scores.py` fix öncesi 2 testte kırmızı, sonrasında yeşil. `edit_tab`, `get_tab`
  ve upload yolları incelendi: aynı hata yok.
- **PDF render sınırı (PR #19, `fix/pdf-render-cap`):** `PDFOMRService._pdf_render_zoom` zoom'u
  `MAX_RENDER_PIXELS = 25_000_000` bütçesiyle sınırlar (normal sayfa 3x). İki test eklendi.
- **Nginx X-Real-IP (A3-01):** Sunucuda salt okunur kontrol. `selimkilic.online` vhost'unun `/api`
  bloğu `X-Real-IP` değerini üzerine yazıyor; A3-01 kapatıldı. Sunucuda değişiklik yapılmadı.
- Test ortamı: `/tmp/fftest5` silinmişti; `/tmp/fftest6` (uv, Python 3.12, `requirements-dev.txt`) ile yeniden kuruldu.
- **Merge:** PR #18, #19, #20 squash-merge edildi (`e1a47ac`, `e95e64a`, `3b0b8b7`); `main` testleri 15 passed, 1 skipped.
- **Deploy (2026-11-25 12:40, onaylı):** `app/main.py` ve `app/services/omr_service.py` sunucuya kuruldu.
  Yedekler: `*.bak_20261125124054`. `py_compile` ve `fretflow.service` restart OK; `/health` 200.
  Boş PDF → fallback, DB'ye yazılmadı; 21 MiB yükleme → 413.
- **Canlı vote doğrulaması:** Test TAB'ı (upload 6, TAB 6) ile `rate 4` ve `rate 2` oyları verildi;
  DB'de `rate_score = 3.0`, `vote_count = 2`. Test kayıtları (upload 6, TAB 6, 2 oy) onayla silindi;
  sonrasında 5 TAB, 5 upload, 0 oy kaldı.
- Açık: OMR doğruluk ölçümü için referans nota (MusicXML) bekleniyor.

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
