# TASK.md — Şu Anki Görev

## 🟡 AÇIK / TEYİT BEKLİYOR (2026-11-11 gözden geçirildi)

> Sunucu bilgileri 2026-11-09 ve 2026-11-11 tarihlerinde SSH ile salt okunur
> doğrulandı (değişiklik yapılan yerler ayrıca işaretli). Ayrıntı: SESSION.md §19–§20.

1. **Servis DB bağlantısı — ✅ çözüldü, veri eşleşmesi teyit bekliyor.**
   - Uygulama Docker `postgres-ortak` (127.0.0.1:5434) içindeki `fretflow_db`
     veritabanına `uygulama` rolüyle bağlanıyor. `backend/.env` DATABASE_URL'i
     buna göre değiştirildi (eski dosya yedeği: `/opt/fretflow/backend/.env.bak_20261109095730`).
   - Yerel PostgreSQL 16 `main` (5432) kullanılmıyor; veri dizini kayıp.
     (`postgresql.service` hâlâ `active` — sarmalayıcı servis; kaldırma/disable kararı BACKLOG'da.)
   - **Teyit bekleyen:** `fretflow_db` içeriği 18 Ekim geçiş dump'ıyla aynı
     (users 0, sheet_uploads 4, tab_versions 4, tab_votes 0; son kayıt
     2026-07-14). Kayıp kullanıcı/oy verisi olmadığı sahibi tarafından teyit edilmeli.
2. **`fretflow.service` — ✅ enabled ve active (2026-11-11 doğrulandı).**
   `Restart=always`. **Teyit bekleyen:** reboot testi yapılmadı; açılışın
   gerçekten kalktığı yalnızca sunucuda reboot ile gözlemlenebilir (sahibi onayıyla).
3. **Güvenlik:** CORS allowlist (PR #7/#10); oylar `user_id=NULL`. Tekrar
   oy engeli ve kimlik doğrulama açık (BACKLOG.md).
4. **oemer kabul testi — ✅ yapıldı (2/10), karar bekliyor.** Ayrıntı aşağıda.
5. **Eski Docker `fretflow` container'ı** — `restart=no`, `exited`; silinmedi.
   AutoSleep kaydı hâlâ bu container'a işaret ediyor. Silme kararı sahibinde (BACKLOG.md).
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
- Sonuç: İki yaklaşım da kabul eşiğini geçmiyor. oemer'i üretime almak için karar verilmedi; üretim pipeline'ı değişmedi.

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

**Sayısal ölçüm:** 2026-11-09 oemer kabul testinde üretim pipeline 0/10 ölçüldü
(yukarıda). Fix'in tek başına etkisi (fix öncesi/sonrası karşılaştırma) ayrıca
ölçülmedi; bu açık bir ölçüm.

## 🔄 AKTİF — OMR Kalite Kararı (oemer vs OpenCV)

**Durum (2026-11-11):** oemer kurulu ve `/opt/oemer_venv` içinde çalışıyor
(oemer 0.1.8). Kurulum sorunları çözüldü (SESSION.md §11-14). Ancak kabul
testinde iki yaklaşım da eşiği geçmedi: oemer 2/10, OpenCV 0/10.

Bağımsız araştırma (SESSION.md §15): `PDF2Muse` gibi projeler "PDF → oemer →
MusicXML" akışını kullanıyor; bu yaklaşım makul. `homr` ve bir OMR benchmark
projesi de var.

**Önerilen sıra (karar sahibinde):**
1. Tek bir referans sayfayla (`/tmp/nota_page1.png`) yetinmeyip birkaç sayfayla,
   tekrarlanabilir bir ölçüm kurmak (BACKLOG: "OMR doğruluk ölçümünü sürekli
   hale getirmek"). Tek 10 notalık örnekle karar vermek güvenilir değil.
2. Ölçüm sonucuna göre: oemer'i `/opt/oemer_venv` üzerinden `subprocess` ile
   `PDFOMRService`'e bağlamak (ARCHITECT.md hedef mimari) veya OpenCV tarafında
   staff/nota tespitini düzeltmeye devam etmek.
3. Yeni bir motor (ör. `homr`) yalnızca 1 ve 2 sonuçsuz kalırsa değerlendirilsin.

**Kurallar:** oemer yalnızca `/opt/oemer_venv` içinde; production venv'e
(`/opt/fretflow/venv`) deneysel paket kurulmaz.

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

## Yaklaşım — İki Yol, İkisi de Eşik Altında

- **Seçenek A — oemer (izole venv):** kuruldu, ölçüldü: 2/10.
- **Seçenek B — OpenCV pipeline (TREBLE_MAP fix sonrası üretim):** ölçüldü: 0/10.

Karar: yukarıdaki "Önerilen sıra". Ölçüm sayısı az olduğu için sonuçlar kesin
değil; sadece bu tek sayfa için geçerli.

## Kapsam Dışı (şimdilik)

- MusicXML/MIDI pipeline'ları (zaten music21 ile güvenilir, dokunulmadı)
- Görüntü (PNG/JPG) pipeline'ı — ayrı, benzer ama farklı kod yolu
- `GuitarMappingService` (tab'a çevirme) — pitch doğru gelirse sorunsuz çalışır
