import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
CLEANER_PASSWORD = os.getenv("CLEANER_PASSWORD", "cleaner123")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "admin123")
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///tidyup.db")

COMPANY_PHONE = os.getenv("COMPANY_PHONE", "+7 (999) 123-45-67")
COMPANY_EMAIL = os.getenv("COMPANY_EMAIL", "info@tidyup.ru")
COMPANY_WEBSITE = os.getenv("COMPANY_WEBSITE", "tidyup.ru")
COMPANY_MANAGER = os.getenv("COMPANY_MANAGER", "@tidyup_manager")

PRICES = {
    "🧹 Поддерживающая уборка": 40,
    "✨ Генеральная уборка": 70,
    "🪟 Мойка окон": 30,
    "🧺 Химчистка мебели": 100,
    "🏭 Уборка после ремонта": 90,
    "🏢 Офисная уборка": 50,
    "📦 Уборка после переезда": 80,
    "🧽 Мытье люстр": 150,
    "🌳 Уборка территории": 60
}

def _parse_admin_ids():
    raw = os.getenv("ADMIN_IDS", "").strip()
    if not raw:
        return []
    out = []
    for x in raw.split(","):
        x = x.strip()
        if x.isdigit():
            out.append(int(x))
    return out


ADMIN_IDS = _parse_admin_ids()
if not BOT_TOKEN:
    raise ValueError(" BOT_TOKEN не найден")