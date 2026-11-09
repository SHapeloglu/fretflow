# CLAUDE.md — FretFlow Projesi Kalıcı Bağlam

> Bu dosya nadiren değişir. Proje/ortam hakkında her yeni sohbette bilinmesi
> gereken sabit bilgileri içerir. Görev-spesifik bilgi için TASK.md,
> mimari detay için ARCHITECT.md, oturum geçmişi için SESSION.md'ye bak.

## Proje

**FretFlow** — nota/OMR (Optical Music Recognition) verisinden gitar tab'ı
üreten bir servis. Kullanıcı notaları (PDF/MusicXML/MIDI/görüntü) yükler,
sistem notaları tespit edip gitar üzerinde çalınabilir pozisyonlara
(string/fret/finger) çevirir.

## Ortam Bilgileri

| Ne | Değer |
|---|---|
| Sunucu | `95.111.242.96` (SSH: `root@95.111.242.96`) |
| **Production venv** | `/opt/fretflow/venv` — `~/.bashrc`'de otomatik aktif oluyor (`source /opt/fretflow/venv/bin/activate`) |
| **oemer venv (izole, deneysel)** | `/opt/oemer_venv` — manuel aktive edilmeli: `source /opt/oemer_venv/bin/activate` |
| Proje dizini | `/opt/fretflow/backend` (repoda da `backend/` altında; kök `app/` ve `smart-tab/` kaldırıldı) |
| Ana kod dosyası | `/opt/fretflow/backend/app/services/omr_service.py` |
| Debug scripti | `/opt/fretflow/backend/debug_omr.py` |
| Requirements | `/opt/fretflow/backend/requirements.txt` (production'ın tek doğruluk kaynağı) |
| Servis yönetimi | `systemctl status/restart fretflow` (systemd, `fretflow.service`, port 8010, 2 uvicorn worker) |
| Veritabanı (production) | Docker `postgres-ortak` — `127.0.0.1:5434`, veritabanı `fretflow_db`, rol `uygulama`. Bağlantı `/opt/fretflow/backend/.env` içindeki `DATABASE_URL` ile tanımlı (gerçek değer bu dosyada/dokümanda yok) |
| Docker dönemi bağlantısı | `/opt/fretflow/.env` — Docker dönemine ait; güncel bağlantı için `backend/.env`'e bakın |
| Kullanılmayan yerel DB | Yerel PostgreSQL 16 `main` (5432) — veri dizini yok, kullanılmıyor |
| Eski Docker container | `fretflow` (AutoSleep yönetiminde) — systemd servisiyle çakışma kontrolü başka bir ajanda; bu repoda değişiklik yapılmadı |
| SECRET_KEY | Zorunlu (varsayılan yok). Değeri yalnızca sunucudaki `.env` içinde; repoda ve dokümanda yok |
| Sunucu yedekleri | Geçiş dump'ı: `/root/yedekler/fretflow-gecis-20261018-2121/fretflow_db.dump`; `.env` yedeği: `/opt/fretflow/backend/.env.bak_20261109095730` (gizli değer içerir) |
| Test PDF | `/tmp/nota.pdf` (kaynağı: `cp "/var/tmp/Yeni Proje.pdf" /tmp/nota.pdf`) |
| Test PNG (oemer için render edilmiş) | `/tmp/nota_page1.png` (3x zoom, PyMuPDF ile üretildi) |
| Debug çıktı dizini | `/tmp/omr_debug/` (crop/binary/no_staff/no_stems/overlay PNG'leri, staff başına) |

## ⚠️⚠️ KRİTİK: Terminal Prompt'unu HER KOMUTTAN ÖNCE Kontrol Et

Sunucuda **iki farklı Python ortamı** var ve bunları karıştırmak ciddi
zaman kaybına ve production'ı bozma riskine yol açtı — iki kez yaşandı
(bkz. SESSION.md §11, §13):

- `(venv) root@...` → **production venv** (`/opt/fretflow/venv`) — buraya
  sadece FretFlow'un gerçek bağımlılıkları (`requirements.txt`) kurulu
  olmalı, deneysel paket KURMA (özellikle `oemer`, `onnxruntime`, farklı
  `numpy`/`scipy`/`opencv` sürümleri).
- `(oemer_venv) root@...` → **izole deney ortamı** (`/opt/oemer_venv`) —
  oemer ve bağımlılıkları burada denenmeli, production'dan tamamen ayrı.
- Prompt'ta **hiçbir prefix yoksa** (`root@...` çıplak) → muhtemelen
  `deactivate` sonrası **sistem Python'una** düşülmüş demektir; `pip
  install` burada `externally-managed-environment` hatası verir ve
  yanlışlıkla `--break-system-packages` ile devam edilirse sistem Python'u
  kirlenebilir.

**Kural:** Her komut bloğu önerirken hangi ortamda çalıştırılması gerektiğini
açıkça belirt, kullanıcı da her `pip install` öncesi prompt'a bakıp doğru
ortamda olduğunu teyit etsin.

## ⚠️ Kritik Kısıtlama: Claude'un Sunucuya Erişimi YOK

Claude'un kendi sandbox'ı **izole** — `95.111.242.96` sunucusuna SSH/network
erişimi yok. İş akışı şöyle:
1. Claude bir kod değişikliği / komut önerir
2. **Kullanıcı** bunu kendi SSH oturumunda sunucuda çalıştırır
3. Kullanıcı çıktıyı/log'u (ve varsa görselleri) Claude'a yapıştırır/yükler
4. Claude çıktıyı analiz edip bir sonraki adımı önerir

Claude kendi sandbox'ında (network erişimi kısıtlı, sadece pip/npm/apt
registry'leri) PDF'i işleyip **görsel doğrulama / bağımsız test / genel
araştırma** yapabilir — ama bu, gerçek servisin sunucudaki haliyle **aynı
değildir**, sadece çapraz kontrol ve araştırma amaçlıdır.

## Dosya Transferi (Windows → Sunucu / Sunucu → Windows)

Kullanıcı Windows kullanıyor, dosyalar `C:\Users\yeliz\Downloads\` altına iniyor.

```powershell
# Windows'tan sunucuya
scp C:\Users\yeliz\Downloads\<dosya_adi> root@95.111.242.96:/opt/fretflow/backend/

# Sunucudan Windows'a (SSH oturumunu kapatmadan AYRI bir PowerShell penceresinde çalıştırılmalı)
scp root@95.111.242.96:/tmp/omr_debug/<dosya_adi> C:\Users\yeliz\Downloads\
```

Alternatif: WinSCP (sürükle-bırak) veya SSH içinden `cat > dosya << 'EOF' ... EOF`.

**Dikkat:** `scp` komutu SSH oturumunun *içinde* çalıştırılırsa dosya
sunucudan sunucuya kopyalanır, kullanıcının bilgisayarına inmez — bu
hataya bir kez düşüldü (bkz. SESSION.md §16).

## Teknoloji Yığını

- Python 3.12, FastAPI + uvicorn (2 worker, systemd altında)
- OpenCV (`opencv-python-headless==4.9.0.80`, production'da) — görüntü işleme, staff/nota tespiti
- NumPy (`1.26.4`)
- PyMuPDF (`fitz`, `1.28.0` sabitli) — PDF → görüntü render
- `music21==9.1.0` — MusicXML/MIDI parse (en güvenilir yol, dokunulmuyor)
- `pytesseract` — tempo/time-signature OCR
- SQLAlchemy + Alembic + psycopg2 — veritabanı katmanı
- python-jose + passlib[bcrypt] — kimlik doğrulama
- **Değerlendirilen/test edilen alternatif:** `oemer` (deep-learning tabanlı
  OMR aracı, MusicXML üretir) — custom OpenCV pipeline'ının PDF yolundaki
  yerini alma adayı, izole venv'de (`/opt/oemer_venv`) test ediliyor
  (bkz. TASK.md)

## Kod İçi Dil Kuralı

Kod içi Türkçe docstring/yorum kullanılıyor (örn. `"""PDF için multi-staff
OMR..."""`). Fonksiyon/değişken isimleri İngilizce. Bu konvansiyona uy.

## Oturum Yönetimi

### Token limiti yaklaştığında

Claude şu belirtileri fark ettiğinde oturum kapatma protokolünü başlatır:
- Konuşma 15+ mesaj uzunluğuna ulaştığında
- Büyük dosya okuma/yazma işlemleri yoğunlaştığında
- Kullanıcı "devam edelim" deyip yeni bir konu açtığında

### Oturum kapatma protokolü (Claude başlatır)

1. Tamamlanan görevleri TASK.md'ye işle
2. SESSION.md'yi güncelle (son durum, açık görevler, yarım kalanlar)
3. ARCHITECT.md'ye yeni öğrenilenleri ekle
4. Kullanıcıya güncellenmiş 4 dosyayı sun: "Oturumu kapatıyorum, md
   dosyalarını indirin"

### Bir sonraki oturum başlangıcı

Kullanıcı md dosyalarını (zip'leyip) yükler, Claude okur ve kaldığı yerden
devam eder.

### Claude'a not

Her 10 mesajda bir token durumunu değerlendir. Eğer konu değişikliği veya
büyük bir görev bitişi olduysa "Oturumu kapatmalı mıyız?" diye sor.
