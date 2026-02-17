"""
Константы и конфигурация приложения.
"""

import sys
from pathlib import Path

# --- Пути ---
# Рабочая директория = папка, откуда запущен EXE / скрипт.
# Все данные (куки, история, загрузки) хранятся рядом с исполняемым файлом.
if getattr(sys, "frozen", False):
    BASE_DIR = Path(sys.executable).parent
else:
    BASE_DIR = Path(__file__).parent.parent.parent
COOKIE_FILE = BASE_DIR / "comx_life_cookies_v3.json"
HISTORY_FILE = BASE_DIR / "manga_history.json"
DOWNLOADS_DIR = BASE_DIR / "downloads"
TEMP_DIR = BASE_DIR / "combined_cbz_temp"
OUTPUT_DIR = BASE_DIR / "output"

# --- Сайт ---
BASE_URL = "https://com-x.life"
API_URL = (
    "https://com-x.life/engine/ajax/controller.php"
    "?mod=api&action=chapters/download"
)

# --- HTTP ---
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/131.0.0.0 Safari/537.36"
)

# Заголовки для API-запросов (скачивание глав)
DEFAULT_HEADERS = {
    "User-Agent": USER_AGENT,
    "Accept": "application/json, text/javascript, */*; q=0.01",
    "Accept-Language": "ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7",
    "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
    "X-Requested-With": "XMLHttpRequest",
    "Origin": BASE_URL,
}

# Заголовки для просмотра страниц (имитация реального браузера)
BROWSE_HEADERS = {
    "User-Agent": USER_AGENT,
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
    "Accept-Language": "ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7",
    "Accept-Encoding": "gzip, deflate, br",
    "Cache-Control": "max-age=0",
    "Sec-Ch-Ua": '"Chromium";v="131", "Not_A Brand";v="24"',
    "Sec-Ch-Ua-Mobile": "?0",
    "Sec-Ch-Ua-Platform": '"Windows"',
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "none",
    "Sec-Fetch-User": "?1",
    "Upgrade-Insecure-Requests": "1",
}

# --- Таймауты (секунды) ---
HTTP_TIMEOUT = 30
DOWNLOAD_TIMEOUT = 60
LOGIN_WAIT_TIMEOUT = 300  # 5 минут на ручной логин
PAGE_LOAD_DELAY = 3
POLL_INTERVAL = 0.5
REQUEST_DELAY = 1.5
FALLBACK_DELAY = 1

# --- Selenium ---
SELENIUM_WAIT_TIMEOUT = 10
COOKIE_DOMAIN = ".com-x.life"

# --- Форматы изображений ---
IMAGE_EXTENSIONS = frozenset({".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp"})

# --- Cookies для авторизации ---
AUTH_COOKIES = ("dle_user_id", "dle_password")
IMPORTANT_COOKIE_NAMES = (
    "dle_user_id", "dle_password", "dle_hash", "PHPSESSID",
    "cf_clearance",
)
