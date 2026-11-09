# TASK.md — Şu Anki Görev

## 🟡 AÇIK / TEYİT BEKLİYOR (2026-11-09)

> Sunucu tarafı bilgileri kullanıcı doğrulamasıdır, repodan doğrulanamaz.
> Ayrıntı: SESSION.md §19.

1. **Servis DB bağlantısı — ✅ çözüldü, veri eşleşmesi teyit bekliyor.**
   - Uygulama Docker `postgres-ortak` (127.0.0.1:5434) içindeki `fretflow_db`
     veritabanına `uygulama` rolüyle bağlanıyor. `backend/.env` DATABASE_URL'i
     buna göre değiştirildi (eski dosya yedeği: `/opt/fretflow/backend/.env.bak_20261109095730`).
   - Yerel PostgreSQL 16 `main` (5432) kullanılmıyor; veri dizini kayıp.
   - **Teyit bekleyen:** `fretflow_db` içeriği 18 Ekim geçiş dump'ıyla aynı
     (users 0, sheet_uploads 4, tab_versions 4, tab_votes 0; son kayıt
     2026-07-14). Kayıp kullanıcı/oy verisi olmadığı sahibi tarafından teyit edilmeli.
2. **`fretflow.service` enable durumu — ✅ enabled (doğrulandı).** 2026-11-09
   kontrolünde servis `enabled` ve `active`; `Restart=always` olduğu doğrulandı.
   Reboot sonrası açılış yalnızca gözlemle (sunucuda reboot ile) teyit edilebilir.
3. **Güvenlik:** CORS artık allowlist (PR #7/#10); oylar `user_id=NULL`. Tekrar
   oy engeli ve kimlik doğrulama açık (BACKLOG.md).
4. **oemer testi** (aşağıda) — bekliyor.
5. **Eski Docker `fretflow` container'ı** — AutoSleep yönetiminde. systemd
   servisiyle çakışma kontrolü başka bir ajanda; bu repoda değişiklik yok.
6. **Dış erişim (doğrulandı, 2026-11-09).** Canlı FretFlow alan adı
   `selimkilic.online` (nginx `sites-enabled`, `/api` ve `/health` → 127.0.0.1:8010, 200).
   `fretflow.dehateknikservis.com` yayında değil: `sites-available/fretflow`
   `sites-enabled`'da yok; 80. port bloğu bilerek 404 dönüyor, 443 bloğu olmayan
   bir Let's Encrypt sertifikasına bağlı. Kod hatası değil; vhost/sertifika
   kararı sunucu sahibinde (BACKLOG.md).
7. **Sunucu değişiklikleri (2026-11-09, sahibi onayıyla).**
   - `/etc/systemd/system/fretflow.service`: `Requires=postgresql.service`
     kaldırıldı, `After=/Wants=docker.service` eklendi. Yedek:
     `fretflow.service.bak_20261109212332`. `daemon-reload` yapıldı.
   - `app/main.py`: CORS'a `https://selimkilic.online` eklendi (repo PR #10 ile
     birebir). Yedek: `main.py.bak_20261109212938`. Servis restart edildi;
     `/health` 200, selimkilic.online için ACAO dönüyor, yabancı origin dönmüyor.

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

## ✅ TAMAMLANDI — oemer Kabul Testi (2026-11-09)

- Test: `/tmp/nota_page1.png` (PDF'den 3x render) üzerinde `oemer` (`/opt/oemer_venv`, oemer 0.1.8) çalıştırıldı; ~12 dk sürdü, MusicXML üretildi.
- Beklenen ilk 10 pitch: `G4 G4 A4 G4 E4 F4 E4 D4 E4 D4`.
- **oemer:** 121 nota üretti, ilk 10: `C4 D4 E4 D4 C4 D4 E4 D4 C4 G4` → **2/10** (PDF'deki gerçek nota sayısı doğrulanmadı; 'aşırı tespit' yorumu kanıtlanmadı).
- **Mevcut OpenCV pipeline (`PDFOMRService`, üretim):** 55 nota, ilk 10: `D4 E4 C4 C4 C4 D4 C4 B3 G4 D5` → **0/10**.
- Sonuç: İki yaklaşım da kabul eşiğini geçmiyor. oemer'i üretime almak için karar verilmedi; üretim pipeline'ı değişmedi. Bir sonraki adım: `TREBLE_MAP`/staff tespiti için ayrı bir doğruluk iyileştirmesi (BACKLOG'a bakın).

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
