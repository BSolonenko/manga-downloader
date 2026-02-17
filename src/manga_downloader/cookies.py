"""
Менеджер cookies: загрузка, сохранение и применение к HTTP-сессиям.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from manga_downloader.config import AUTH_COOKIES, COOKIE_FILE, IMPORTANT_COOKIE_NAMES

logger = logging.getLogger(__name__)

CookieList = list[dict[str, Any]]


class CookieManager:
    """Единая точка управления cookies для всех загрузчиков."""

    def __init__(self, path: Path | None = None) -> None:
        self.path = path or COOKIE_FILE
        self._cookies: CookieList = []

    # -- Публичный интерфейс --------------------------------------------------

    @property
    def cookies(self) -> CookieList:
        return self._cookies

    @cookies.setter
    def cookies(self, value: CookieList) -> None:
        self._cookies = value

    def load(self) -> bool:
        """Загружает cookies из JSON-файла.

        Возвращает ``True`` при успехе.
        """
        try:
            with open(self.path, "r", encoding="utf-8") as fh:
                raw = json.load(fh)
            if isinstance(raw, list):
                self._cookies = raw
            else:
                self._cookies = [
                    {"name": k, "value": v} for k, v in raw.items()
                ]
            logger.info("Загружено %d cookies из %s", len(self._cookies), self.path)
            return True
        except Exception as exc:
            logger.error("Не удалось загрузить cookies: %s", exc)
            return False

    def save(self, only_important: bool = True) -> bool:
        """Сохраняет cookies в JSON-файл.

        При *only_important=True* сохраняются только cookies из
        ``IMPORTANT_COOKIE_NAMES``.
        """
        try:
            data = self._cookies
            if only_important:
                data = [
                    c for c in self._cookies
                    if c.get("name") in IMPORTANT_COOKIE_NAMES
                ]
            with open(self.path, "w", encoding="utf-8") as fh:
                json.dump(data, fh, indent=2, ensure_ascii=False)
            logger.info("Сохранено %d cookies в %s", len(data), self.path)
            return True
        except Exception as exc:
            logger.error("Не удалось сохранить cookies: %s", exc)
            return False

    def save_all(self) -> bool:
        """Сохраняет все cookies (без фильтрации)."""
        return self.save(only_important=False)

    def apply_to_session(self, session: Any) -> None:
        """Устанавливает cookies в HTTP-сессию (curl_cffi / requests)."""
        for cookie in self._cookies:
            session.cookies.set(cookie["name"], cookie["value"])

    def apply_to_scraper(self, scraper: Any) -> None:
        """Устанавливает cookies в cloudscraper."""
        cookies_dict = {c["name"]: c["value"] for c in self._cookies}
        scraper.cookies.update(cookies_dict)

    def apply_to_driver(self, driver: Any, domain: str = ".com-x.life") -> None:
        """Добавляет cookies в Selenium WebDriver."""
        for cookie in self._cookies:
            try:
                driver.add_cookie({
                    "name": cookie["name"],
                    "value": cookie["value"],
                    "domain": domain,
                })
            except Exception as exc:
                logger.warning(
                    "Cookie %s не добавлен в драйвер: %s",
                    cookie.get("name"), exc,
                )

    def update_from_driver(self, driver: Any) -> None:
        """Обновляет cookies из Selenium WebDriver."""
        self._cookies = driver.get_cookies()

    def has_auth(self, driver: Any | None = None) -> bool:
        """Проверяет наличие авторизационных cookies.

        Если передан *driver*, проверяет через него; иначе -- по внутреннему списку.
        """
        if driver is not None:
            return all(driver.get_cookie(name) for name in AUTH_COOKIES)
        names = {c.get("name") for c in self._cookies}
        return all(name in names for name in AUTH_COOKIES)
