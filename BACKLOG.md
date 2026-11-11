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

## Koddaki TODO / FIXME Notları

_(kodda TODO/FIXME notu bulunamadı)_

## Ekleme Şablonu

```markdown
### Başlık

- **Kategori:** yeni özellik / iyileştirme / teknik borç / araştırma
- **Neden istendi:** kısa gerekçe
- **Notlar:** büyüklük tahmini, bağımlılıklar, riskler
```
