# BACKLOG.md — FretFlow Fikir / Özellik Havuzu

Bu dosya henüz önceliklendirilmemiş, "bir gün yapılabilir" fikirler ve özellik talepleri içindir. Bir fikir somutlaşıp sıraya girdiğinde buradan çıkar, `TASK.md`ye taşınır.

## Fikirler

Aktif iş `TASK.md`'de (oemer değerlendirmesi — Seçenek A; yedek plan Seçenek B: custom OpenCV pipeline'ın `TREBLE_MAP` düzeltmesi sonrası sayısal kabul testi). Aşağıdakiler `TASK.md` "Kapsam Dışı (şimdilik)" ve oturum notlarından çıkan, henüz sıraya girmemiş işler:

### PNG/JPG görüntü pipeline'ının PDF OMR düzeltmelerinden geçirilmesi
- **Kategori:** iyileştirme
- **Neden:** Görüntü yolu ayrı ama benzer kod yolu; PDF tarafında bulunan hatalar (anahtar haritası, nota tespiti) orada da olabilir.
- **Notlar:** oemer kararı netleşince aynı motorla birleştirmek daha ucuz olabilir.

### OMR doğruluk ölçümünü sürekli hale getirmek
- **Kategori:** teknik borç / test
- **Neden:** `TREBLE_MAP` düzeltmesi sayısal doğrulanmadan kaldı (SESSION.md).
- **Notlar:** Referans PNG/PDF seti + beklenen pitch listesi → pytest ile doğruluk oranı; oemer ve OpenCV pipeline'ını aynı setle kıyasla.

### Bağımlılık izolasyonu
- **Kategori:** teknik borç
- **Neden:** Önceki oturumda yanlış venv'de `numpy` 2.x'e yükseltme `cv2`'yi kırdı.
- **Notlar:** oemer için ayrı venv (Seçenek A) kalıcı hale gelirse servis içinden subprocess ile çağırma ve sürüm sabitleme (`numpy<2`, `scipy<1.13`).

### Tab çıktısı iyileştirmeleri
- **Kategori:** yeni özellik
- **Notlar:** `GuitarMappingService` için alternatif akort (Drop D, DADGAD), capo, parmak pozisyonu tercihi; MusicXML/MIDI yolu güvenilir olduğundan ilk orada denenebilir.

### CORS kısıtlama
- **Kategori:** güvenlik
- **Neden:** `backend/app/main.py` içinde `allow_origins=["*"]`; her origin API'ye erişebiliyor.
- **Notlar:** Ayrı PR. İzinli origin listesi konfigürasyondan okunmalı.

### `user_id=1` sabiti / kimlik doğrulama
- **Kategori:** güvenlik / yeni özellik
- **Neden:** Kullanıcı kimliği sabit `1`; giriş ve kimlik doğrulama yok.
- **Notlar:** Ayrı PR. Önce tasarım kararı gerekli (oturum/token yaklaşımı).

### Yerel PostgreSQL 16 veri kaybının araştırılması
- **Kategori:** araştırma / altyapı
- **Neden:** Yerel `main` (5432) kümesinin veri dizini yok. Kaybolma zamanı 19 Ekim – 8 Kasım arası olarak düşünülüyor, **kanıtlanamadı**.
- **Notlar:** Sunucuda inceleme sahibi tarafından yapılmalı (SESSION.md §19).

### Eski Docker `fretflow` container'ının temizlenmesi
- **Kategori:** teknik borç
- **Neden:** Eski kurulum; AutoSleep yönetiminde. Systemd servisiyle çakışma kontrolü başka bir ajanda yapılıyor.
- **Notlar:** Çakışma kontrolü tamamlanmadan kaldırılmamalı.

### Sunucudaki `.env` yedeklerinin temizlenmesi
- **Kategori:** teknik borç / güvenlik
- **Neden:** `/opt/fretflow/backend/.env.bak_20261109095730` gibi yedekler gizli değer içerir.
- **Notlar:** Silmeden önce gerekiyorsa güvenli bir yere alınmalı; dosya izinleri kontrol edilmeli.

## Koddaki TODO / FIXME Notları

_(kodda TODO/FIXME notu bulunamadı)_

## Ekleme Şablonu

```markdown
### Başlık

- **Kategori:** yeni özellik / iyileştirme / teknik borç / araştırma
- **Neden istendi:** kısa gerekçe
- **Notlar:** büyüklük tahmini, bağımlılıklar, riskler
```
