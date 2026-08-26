# 📊 DataPortal

**Excel → MySQL ETL Portalı** — Kurumsal veri yükleme, onay akışı ve kalite kontrolü için geliştirilmiş web tabanlı yönetim platformu.

![Python](https://img.shields.io/badge/Python-3.11-blue?logo=python)
![Flask](https://img.shields.io/badge/Flask-3.x-lightgrey?logo=flask)
![MySQL](https://img.shields.io/badge/MySQL-8.x-orange?logo=mysql)
![Docker](https://img.shields.io/badge/Docker-Compose-blue?logo=docker)

---

## 🗂️ İçindekiler

- [Genel Bakış](#-genel-bakış)
- [Özellikler](#-özellikler)
- [Mimari](#-mimari)
- [Kurulum](#-kurulum)
- [Kullanım](#-kullanım)
- [Veritabanı Şeması](#-veritabanı-şeması)
- [Yetki Sistemi](#-yetki-sistemi)
- [API Referansı](#-api-referansı)
- [Geliştirme](#-geliştirme)

---

## 🌐 Genel Bakış

DataPortal, Excel dosyalarını kurumsal MySQL veritabanlarına güvenli ve denetlenebilir şekilde aktarmak için tasarlanmış bir Flask uygulamasıdır. Dosya yükleme, çok adımlı onay akışı, kalite kontrolü, stored procedure entegrasyonu ve cron tabanlı otomasyon özelliklerini tek bir arayüzde sunar.

**Hedef kullanıcılar:** Veri analisti, data engineer ve kurumsal veri operasyonu ekipleri.

---

## ✨ Özellikler

### 📁 Dosya Yükleme & Onay Akışı
- **3 Adımlı Wizard:** Dosya & dizin seçimi → Hedef tablo + sütun eşleşme önizlemesi → Özet & Yükleme
- **Dizin tabanlı erişim kontrolü:** Hiyerarşik klasör yapısı, kullanıcı/rol bazlı izinler
- **Çok kademeli onay:** Onaylayan atama, onay/red kararı, bildirim sistemi
- **Admin bypass:** Admin kullanıcılar doğrudan onaylayarak arka planda aktarım başlatabilir
- **Dosya arşivi:** Yüklenen tüm Excel dosyaları `excel_store/`'da kalıcı olarak saklanır

### 🔄 ETL İşlemleri
- **Truncate / Append modları:** Tablo konfigürasyonundan ayarlanabilir
- **Sütun eşleşme:** Excel sütunları ile DB sütunları otomatik eşleştirilir (büyük/küçük harf duyarsız)
- **ETL_DATE:** Her yüklemeye otomatik timestamp eklenir
- **Duplicate kontrolü:** Append modunda tekrar eden satırlar atlanır
- **BeforeSP / AfterSP:** Aktarım öncesi ve sonrası stored procedure desteği

### ✅ Kalite Kontrolü
- Sütun bazında kural tanımlama (boş değer, benzersizlik, vb.)
- Hata seviyesi: `hata` (aktarımı durdurur) / `uyari` (loglanır, devam eder)
- Kalite raporu `yukle_log` tablosuna JSON olarak kaydedilir

### 🔔 Bildirim Sistemi
- Gerçek zamanlı bildirim paneli (5 saniyede bir polling)
- Bildirim tipleri: onay bekleniyor, onaylandı, reddedildi, yüklendi, hata
- Okundu / okunmadı yönetimi

### ⏰ Cron & Otomasyon
- APScheduler ile zamanlanmış SP çalıştırma
- Aktif/pasif cron yönetimi, son çalışma logu

### 🔒 Güvenlik
- CSRF koruması (tüm state-değiştiren endpoint'lerde)
- Brute-force koruması (rate limiting)
- Şifre hashing (werkzeug bcrypt)
- SQL injection koruması (`sanitize()`)
- Audit log: her kritik işlem kaydedilir

---

## 🏗️ Mimari

```
DataPortal_son/
├── app.py               # Tek dosya uygulama (~2500+ satır)
├── templates/           # Jinja2 şablonları
│   ├── base.html        # Ana layout (accordion nav, bildirim paneli)
│   ├── dosya_yukle.html # 3 adımlı yükleme wizard
│   ├── onay_bekleyenler.html
│   ├── kalite_kurallari.html
│   ├── tablo_konfig.html
│   ├── cron_yonetimi.html
│   └── ...
├── uploads/             # Geçici yükleme dizini
├── excel_store/         # Kalıcı dosya arşivi (chmod 777)
├── .env                 # Çevre değişkenleri
└── docker-compose.yml
```

### Stack

| Katman | Teknoloji |
|---|---|
| Backend | Python 3.11 + Flask |
| Veritabanı | MySQL 8 |
| ORM/Driver | mysql-connector-python |
| Veri İşleme | pandas |
| Zamanlayıcı | APScheduler |
| Container | Docker + Compose |
| Web Sunucu | Gunicorn |

### Bağlantı Yönetimi

```
Request içi:         query() / execute() → Flask g nesnesi üzerinden pool
Background thread:   get_conn_direct()   → .env'den direkt bağlantı
```

---

## 🚀 Kurulum

### Gereksinimler
- Docker & Docker Compose
- Git

### 1. Repoyu klonla

```bash
git clone https://github.com/kullanici/dataportal.git
cd dataportal
```

### 2. `.env` dosyasını oluştur

```env
SECRET_KEY=guclu-gizli-anahtar-buraya
DB_HOST=db
DB_PORT=3306
DB_USER=dpuser
DB_PASSWORD=guclu-sifre-buraya
DB_NAME=dataportal
DB_ROOT_PASSWORD=root-sifre-buraya
HTTPS=false
```

### 3. `excel_store/` dizinine izin ver

```bash
mkdir -p excel_store uploads
chmod 777 excel_store
```

### 4. Container'ları başlat

```bash
docker compose up -d
```

### 5. DB migration (ilk kurulumda)

```sql
-- yukle_log tablosu
CREATE TABLE IF NOT EXISTS yukle_log (
    LogID         INT AUTO_INCREMENT PRIMARY KEY,
    DosyaID       VARCHAR(36),
    TabloAdi      VARCHAR(100),
    Durum         ENUM('basarili','hata','uyari'),
    Mesaj         TEXT,
    EklenenSatir  INT DEFAULT 0,
    AtlananSatir  INT DEFAULT 0,
    KalisonucJSON JSON,
    Tarih         DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- excel_dosya Durum alanı
ALTER TABLE excel_dosya
  MODIFY COLUMN Durum ENUM(
    'bekliyor','onaylandi','reddedildi',
    'yukleniyor','yuklendi','yukleme_hatasi'
  ) DEFAULT 'bekliyor';
```

Uygulama `http://localhost:5001` adresinde çalışmaya başlar.

---

## 📖 Kullanım

### Excel Dosyası Yükleme

1. **Dosya Yükle** menüsüne git
2. **Adım 1:** Excel dosyasını seç, dizin belirle
3. **Adım 2:** Hedef MySQL tablosunu seç, sütun eşleşmelerini kontrol et
4. **Adım 3:** Özeti gözden geçir, yükle

> Admin kullanıcılar dosyayı anında onaylayarak aktarımı başlatır.  
> Normal kullanıcılar için dizinde tanımlı onaylayanlara bildirim gider.

### Onay Akışı

```
Dosya Yüklendi
    │
    ▼
[Admin?] ──Evet──► Otomatik Onay ──► dosya_db_aktar() ──► Tamamlandı
    │
   Hayır
    │
    ▼
Onaylayanlara Bildirim
    │
    ▼
Onaylayan Karar Verir (Onay / Red)
    │
    ▼ Onay
dosya_db_aktar() ──► BeforeSP ──► Excel → MySQL ──► Kalite Kontrol ──► AfterSP ──► Bildirim
```

### Tablo Konfigürasyonu

`Tablo Konfig` menüsünden her tablo için:
- **Yükleme Modu:** `truncate` (sil & doldur) veya `append` (ekle)
- **BeforeSP:** Aktarım öncesi çalışacak stored procedure
- **AfterSP:** Aktarım sonrası çalışacak stored procedure
- **Onay Gerekli:** Bu tabloya yükleme için onay akışı zorunlu mu?

---

## 🗄️ Veritabanı Şeması

### Kullanıcı & Yetki

| Tablo | Açıklama |
|---|---|
| `kullanici` | Kullanıcılar (KullaniciID, Adi, Sifre hash, Email, RolID) |
| `rol` | Roller |
| `yetki` | Yetki kodları (Y000001...) |
| `rol_yetki` | Rol ↔ Yetki bağlantıları |
| `rol_tablo` | Rol ↔ Tablo erişim izinleri |

### Dosya & Onay

| Tablo | Açıklama |
|---|---|
| `excel_dosya` | Yüklenen dosyalar ve durumları |
| `excel_onay` | Onay/red kararları |

### Dizin

| Tablo | Açıklama |
|---|---|
| `dizin` | Hiyerarşik klasör yapısı |
| `dizin_yetki` | Dizin erişim izinleri |
| `dizin_onaylayan` | Dizin bazlı onaylayan listesi |

### Kalite & Konfig

| Tablo | Açıklama |
|---|---|
| `kalite_kural` | Sütun bazlı kalite kuralları |
| `tablo_konfig` | Tablo yükleme konfigürasyonları |

### Sistem

| Tablo | Açıklama |
|---|---|
| `audit_log` | Tüm kritik işlem kayıtları |
| `bildirim` | Kullanıcı bildirimleri |
| `tablo_log` | Tablo bazlı yükleme istatistikleri |
| `yukle_log` | Aktarım detayları + kalite JSON |
| `cron_gorev` | Zamanlanmış görevler |

---

## 🔐 Yetki Sistemi

| Kod | Açıklama |
|---|---|
| Y000001 | Dashboard erişimi |
| Y000002 | Kullanıcı yönetimi |
| Y000003 | Rol yönetimi |
| Y000004 | Excel → MySQL (direkt yükleme) |
| Y000005 | Tablo görüntüleme |
| Y000006 | Tablo silme |
| Y000007 | Dizin yönetimi |
| Y000008 | Dosya yükleme |
| Y000009 | Dosya onaylama |
| Y000010 | Tablo konfigürasyonu |
| Y000011 | Kalite kuralları |
| Y000012 | Cron yönetimi |

---

## 📡 API Referansı

### Dosya Yükleme Wizard

| Endpoint | Method | Açıklama |
|---|---|---|
| `/api/excel-kolonlar` | POST | Excel dosyasının sütunlarını döner |
| `/api/tablo-kolonlar/<tablo>` | GET | DB tablosunun sütunlarını döner |
| `/api/tablolar` | GET | Kullanıcının yetkili tablolarını döner |
| `/api/tablo-konfig-listesi` | GET | Tablo konfigürasyonlarını döner |
| `/api/dosya-yukle` | POST | Dosyayı yükler ve aktarımı başlatır |

### Bildirim

| Endpoint | Method | Açıklama |
|---|---|---|
| `/api/bildirimler` | GET | Son 50 bildirim + okunmamış sayısı |
| `/api/bildirimler/okundu` | POST | Tüm bildirimleri okundu işaretle |
| `/api/bildirimler/<id>/okundu` | POST | Tekil bildirimi okundu işaretle |

---

## 🛠️ Geliştirme

### Kod Değişikliği Sonrası Deploy

```bash
# app.py veya template değişikliği:
cd /root/DataPortal_son && docker compose restart web

# requirements.txt veya Dockerfile değişikliği:
cd /root/DataPortal_son && docker compose up -d --build web
```

### Loglar

```bash
# Uygulama logları:
docker logs -f dataportal_son-web-1

# Veritabanı logları:
docker logs -f dataportal_son-db-1

# Hata filtreleme:
docker logs dataportal_son-web-1 2>&1 | grep ERROR
```

### Korunan Sistem Tabloları

Aşağıdaki tablolar uygulama tarafından korunur ve silme/değiştirme işlemlerine kapatılmıştır:

```
audit_log, bildirim, cron_gorev, dizin, dizin_onaylayan, dizin_yetki,
excel_dosya, excel_onay, kalite_kural, kullanici, kullanici_tercih,
rol, rol_tablo, rol_yetki, tablo_konfig, tablo_log, yetki, yukle_log
```

### Background Thread Kuralları

`dosya_db_aktar()` ve scheduler görevleri Flask request context dışında çalışır. Bu fonksiyonlarda:

```python
# ✅ DOĞRU
conn = get_conn_direct()
_bildirim_direct(alici_id, tip, baslik, mesaj, dosya_id)
_audit_direct('EYLEM', 'detay')

# ❌ YANLIŞ — request context gerektirir
query("SELECT ...")
execute("INSERT ...")
bildirim_gonder(...)
audit(...)
session['kullanici_id']
```

### Sık Karşılaşılan Hatalar

| Hata | Neden | Çözüm |
|---|---|---|
| `Working outside of request context` | Background thread'de `query()`/`session` kullanımı | `get_conn_direct()` kullan |
| `Invalid cross-device link` | `os.rename()` farklı volume'lar arası | `shutil.move()` kullan |
| `Permission denied: excel_store` | Container appuser, host dizin root'a ait | `chmod 777 excel_store/` |
| `Table 'dataportal.v' doesn't exist` | `HedefTablo` alanı yanlış kaydedilmiş | DB'deki kaydı kontrol et |

---

## 📋 Yapılacaklar (Roadmap)

- [ ] Dosya versiyonlama (aynı tabloya gelen dosyaların geçmişi)
- [ ] E-posta bildirimi (SMTP entegrasyonu)
- [ ] Dashboard istatistikleri
- [ ] Çoklu onaylayan (2/3 onay şartı)
- [ ] Yükleme kuyruğu (Celery/Redis)
- [ ] API token desteği (harici sistem entegrasyonu)
- [ ] Otomatik şema güncellemesi (yeni sütun gelince ALTER TABLE)
- [ ] Veri soyu (data lineage)
- [ ] Detaylı kalite raporu (satır bazlı hata)
- [ ] Yükleme önizleme (onaylamadan önce ilk 10 satır)

---

## 📄 Lisans

Bu proje özel/kurumsal kullanım için geliştirilmiştir.
