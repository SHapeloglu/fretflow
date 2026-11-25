# BACKLOG.md — FretFlow Fikir / Özellik Havuzu

Bu dosya henüz önceliklendirilmemiş, "bir gün yapılabilir" fikirler ve özellik talepleri içindir. Bir fikir somutlaşıp sıraya girdiğinde buradan çıkar, `TASK.md`ye taşınır.

## Fikirler

Aktif iş `TASK.md`'de (OMR kalite kararı: oemer 2/10 vs OpenCV 0/10; eşik geçilmedi). Aşağıdakiler `TASK.md` "Kapsam Dışı (şimdilik)" ve oturum notlarından çıkan, henüz sıraya girmemiş işler:

### PNG/JPG görüntü pipeline'ının PDF OMR düzeltmelerinden geçirilmesi
- **Kategori:** iyileştirme
- **Neden:** Görüntü yolu ayrı ama benzer kod yolu; PDF tarafında bulunan hatalar (anahtar haritası, nota tespiti) orada da olabilir.
- **Notlar:** oemer kararı netleşince aynı motorla birleştirmek daha ucuz olabilir.

### OMR doğruluk ölçümünü sürekli hale getirmek
- **Kategori:** teknik borç / test
- **Neden:** Şu an tek sayfa, tek 10 notalık ölçüm var (2026-11-09: oemer 2/10, OpenCV 0/10). Tek örnekle karar vermek güvenilir değil; `TREBLE_MAP` fix'inin tek başına etkisi de ölçülmedi.
- **Notlar:** Referans PNG/PDF seti + beklenen pitch listesi → pytest ile doğruluk oranı; oemer ve OpenCV pipeline'ını aynı setle kıyasla.
- **Durum (2026-11-24):** Harness PR #16 ile main'de (`backend/tests/test_omr_accuracy.py`). Vaka yok; ground truth bekleniyor.

### Bağımlılık izolasyonu
- **Kategori:** teknik borç
- **Neden:** Önceki oturumda yanlış venv'de `numpy` 2.x'e yükseltme `cv2`'yi kırdı.
- **Notlar:** oemer için ayrı venv (Seçenek A) kalıcı hale gelirse servis içinden subprocess ile çağırma ve sürüm sabitleme (`numpy<2`, `scipy<1.13`).

### Tab çıktısı iyileştirmeleri
- **Kategori:** yeni özellik
- **Notlar:** `GuitarMappingService` için alternatif akort (Drop D, DADGAD), capo, parmak pozisyonu tercihi; MusicXML/MIDI yolu güvenilir olduğundan ilk orada denenebilir.

### Oy kimliği ve tekrar oy engeli (kimlik doğrulama yok)
- **Kategori:** güvenlik / yeni özellik
- **Neden:** Anonim oylar `user_id=NULL` ile yazılıyor (PR #7). Aynı kişi aynı TAB'a defalarca oy verebilir.
- **Notlar:** `tab_votes`'a bir oy kimliği kolonu (ör. IP+UA özeti) eklemek şema değişikliği gerektirir (`create_all` kolon eklemez; ALTER gerekir). Giriş sistemi için önce tasarım kararı (oturum/token).

### CORS (tamamlandı — PR #7, #10)
- Origin listesi `backend/app/main.py` içinde sabit (4 girdi: `fretflow.dehateknikservis.com`, `selimkilic.online`, `localhost:5173`, `127.0.0.1:5173`). Konfigürasyondan okunması isteğe bağlı iyileştirme.
- Dış alan adı `fretflow.dehateknikservis.com` yayında değil: `sites-available/fretflow` `sites-enabled`'da yok, 443 bloğu olmayan bir Let's Encrypt sertifikasına bağlı (80. port 404). CORS listesinde zararsız olarak duruyor. Karar: vhost'u açıp sertifika üretmek mi, yoksa alan adını ve CORS girdisini kaldırmak mı — sunucu sahibi seçmeli.

### Yerel PostgreSQL 16 veri kaybının araştırılması
- **Kategori:** araştırma / altyapı
- **Neden:** Yerel `main` (5432) kümesinin veri dizini yok. Kaybolma zamanı 19 Ekim – 8 Kasım arası olarak düşünülüyor, **kanıtlanamadı**.
- **Notlar:** Sunucuda inceleme sahibi tarafından yapılmalı (SESSION.md §19).

### Eski Docker `fretflow` container'ının temizlenmesi
- **Kategori:** teknik borç / altyapı
- **Neden:** Eski kurulum; AutoSleep yönetiminde. Durum (2026-11-11): `restart=no`, `Exited (0)`; silinmedi. AutoSleep kaydı (`fretflow` → kapsayicilar `["fretflow"]`, port 8010) hâlâ bu container'a işaret ediyor.
- **Notlar:** AutoSleep bu container'ı başlatmaya çalışırsa systemd servisiyle 8010 portunda çakışma olabilir. Silme veya AutoSleep kaydını güncelleme kararı sunucu sahibinde; çakışma riski giderilmeden kaldırılmamalı.

### systemd `postgresql.service` (sarmalayıcı)
- **Kategori:** teknik borç / altyapı
- **Neden:** `fretflow` unit'inden bağımlılık kaldırıldı (2026-11-09), ama `postgresql.service` hâlâ `active`. Uygulama bu yerel kümeyi kullanmıyor.
- **Notlar:** Servisi `disable`/`stop` etmek ya da kümeyi tamamen temizlemek sunucu sahibinin kararı. Önce yerel küme/veri dizini kaybının araştırılması (yukarıdaki madde) önerilir.

### Kullanılmayan requirements paketleri
- **Kategori:** teknik borç
- **Neden:** `python-jose`, `passlib[bcrypt]`, `alembic`, `httpx` `requirements.txt`'te, ama kodda kullanılmıyor (kimlik doğrulama ve migrasyon henüz yok).
- **Notlar:** Kimlik doğrulama işi başlayınca kullanılacak; o zamana kadar kaldırılabilir. Production venv'ini değiştirmeden önce sunucu sahibine danışılmalı.

### Sunucudaki `.env` yedeklerinin temizlenmesi
- **Kategori:** teknik borç / güvenlik
- **Neden:** `/opt/fretflow/backend/.env.bak_20261109095730` gibi yedekler gizli değer içerir.
- **Notlar:** Silmeden önce gerekiyorsa güvenli bir yere alınmalı; dosya izinleri kontrol edilmeli. (`main.py.bak_*` ve unit `.bak_*` dosyaları gizli değer içermez; bunlar ayrı bir karar.)

### Reboot testi (açılış doğrulaması)
- **Kategori:** güvenlik / altyapı doğrulama
- **Neden:** `fretflow` `enabled`, ama sunucu reboot'u ile açılışın gerçekten kalktığı gözlemlenmedi.
- **Notlar:** Sahibi onayıyla planlı bir pencerede yapılmalı; reboot sonrası `/health`, `systemctl is-active fretflow` ve `docker ps` kontrol edilmeli.

## Tur 2 — açık bulgular (2026-11-19)

Yüksek öncelikli olanlar PR #14 ile kapandı. Kalanlar (dosya:satır, 2026-11-19 kodu):

### PDF/görüntü ritmi (duration ve beat)
- **Kategori:** iyileştirme (en büyük doğruluk kazancı)
- **Neden:** `PDFOMRService.process_pdf` (`omr_service.py` ~satır 580) ve `_build_music_data` `duration`'ı 1.0 yazıyor; beat sıralı sayılıyor. Tab'ın ritmi güvenilmez.
- **Notlar:** Önce OMR ölçüm seti (aşağıdaki madde) kurulmalı.

### PDF çok sayfalı ve staff sınırı
- **Kategori:** iyileştirme
- **Neden:** `doc[0]` (process_pdf) yalnızca 1. sayfa; `treble_staffs[:4]` (`_detect_treble_staffs` sonu) fazlasını atar.
- **Notlar:** Sessiz kırpma; uyarı veya çoklu sayfa desteği gerekir.

### PDF bellek ve süre limitleri
- **Kategori:** dayanıklılık
- **Neden:** 3x render (`get_pixmap` matrix 3.0) büyük sayfada bellek kullanır; render için boyut tavanı yok. tesseract çağrılarında (`_detect_tempo`, `_detect_time_signature`, `*_pdf` varyantları) timeout yok.
- **Notlar:** `pytesseract` `timeout=` parametresi; render için piksel tavanı.

### Akor ve nota elemesi
- **Kategori:** iyileştirme
- **Neden:** Aynı x konumundaki notalar tek nota sayılıyor (x-only dedupe, `_detect_notes_in_staff` ~711–715); pitch adımı sınırlanıyor (clamp, ~707–708). Hiçbiri test edilmedi.

### Sabit anahtar `C` ve print loglama
- **Kategori:** teknik borç
- **Neden:** `'key': 'C'` her yolda sabit; `print(...)` ile hata yazılıyor (logging yok).

### X-Real-IP güveni (A3-01)
- **Kategori:** güvenlik
- **Neden:** Rate limit `x-real-ip` başlığına güveniyor (`main.py` `rate_limit`). Başlığın nginx tarafından üzerine yazılıp yazılmadığı repo dışı nginx yapılandırmasında; doğrulanmadı.
- **Notlar:** Sunucuda nginx `proxy_set_header X-Real-IP $remote_addr` kontrolü salt okunur yapılmalı.

### Verifier gözlemi: autoflush (kapatıldı)
- **Kategori:** hata (giderildi)
- **Neden:** `database.py:7` `autoflush=False`; `vote_tab` yeni oyu flush etmeden sorguladığı için skor bir oy geride kalıyordu. Test: `backend/tests/test_vote_scores.py` (fix öncesi 2 kırmızı, sonrası yeşil). Düzeltme: `vote_tab` içinde `db.add(db_vote)` sonrası `db.flush()`. `edit_tab` ve `get_tab` gözden geçirildi: yeni kayıttan sonra sorgu yapmıyor, aynı hata yok. Upload yolunda `add` sonrası `flush` zaten var.

### Tur 2 ölçüm seti
- **Kategori:** test
- **Notlar:** Birkaç sayfalık referans PDF/PNG + beklenen pitch/süre listesi; pytest ile doğruluk. Harness PR #16 ile geldi; vaka ekleme kılavuzu `backend/tests/omr_cases/README.md`.

## Koddaki TODO / FIXME Notları

_(kodda TODO/FIXME notu bulunamadı)_

## Ekleme Şablonu

```markdown
### Başlık

- **Kategori:** yeni özellik / iyileştirme / teknik borç / araştırma
- **Neden istendi:** kısa gerekçe
- **Notlar:** büyüklük tahmini, bağımlılıklar, riskler
```
