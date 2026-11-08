"""
Uygulama ayarları (pydantic-settings ile).
Değerler ortam değişkeninden ya da .env dosyasından okunur; veritabanı adresi, gizli anahtar ve token süresi burada tanımlıdır.
Bu nesne 'settings' adıyla diğer dosyalar tarafından içe aktarılır (database.py buradan DATABASE_URL alır).
Gizli değerler bu dosyaya yazılmaz; ortam değişkeni ile verilir.
"""

from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    """
    Uygulama ayarlarını tek yerde toplar. Değerler önce ortam değişkenlerinden (ve .env dosyasından) okunur;
    ortamda yoksa buradaki varsayılan kullanılır. Varsayılanı olmayan bir alan eksikse uygulama açılırken hata verir.
    """
    APP_NAME: str = "FretFlow Smart TAB Engine"
    DATABASE_URL: str  # ortam değişkeninden gelir (backend/.env); koda gömülü bağlantı dizisi yok
    # DİKKAT: bu varsayılan değer yalnız geliştirme içindir. Kodda şu an kullanılmıyor; canlıda ortamdan gerçek bir değer verilmelidir.
    SECRET_KEY: str = "change-me-in-production"
    # Erişim anahtarının (token) geçerlilik süresi: 60 dakika x 24 saat = 1 gün (dakika cinsinden).
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24

    class Config:
        """pydantic-settings'e ayar dosyasının adını söyler. '.env' dosyası çalışma dizinine göre aranır."""
        env_file = ".env"

settings = Settings()
