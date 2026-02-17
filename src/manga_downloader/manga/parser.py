"""
Парсинг данных манги из HTML-страницы com-x.life.

Извлекает ``window.__DATA__`` и возвращает список глав, название и news_id.
"""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass
from typing import Any

import curl_cffi

from manga_downloader.config import BROWSE_HEADERS, HTTP_TIMEOUT
from manga_downloader.cookies import CookieManager

logger = logging.getLogger(__name__)

_DATA_RE = re.compile(r"window\.__DATA__\s*=\s*({.*?})\s*;", re.DOTALL)
_NEWS_ID_RE = re.compile(r"/(\d+)-")


@dataclass
class MangaInfo:
    """Результат парсинга страницы манги."""

    title: str
    news_id: str
    chapters: list[dict[str, Any]]

    @property
    def total_chapters(self) -> int:
        return len(self.chapters)


class MangaParser:
    """Парсит HTML-страницу манги и извлекает метаданные."""

    def __init__(self, cookie_manager: CookieManager) -> None:
        self._cookie_manager = cookie_manager
        self._session: curl_cffi.Session | None = None

    def _get_session(self, *, use_cookies: bool = True) -> curl_cffi.Session:
        """Возвращает переиспользуемую сессию (keep-alive, один TLS handshake)."""
        if self._session is None:
            self._session = curl_cffi.Session()
            self._session.headers.update(BROWSE_HEADERS)
            if use_cookies:
                self._cookie_manager.apply_to_session(self._session)
        return self._session

    def close(self) -> None:
        """Закрывает сессию."""
        if self._session is not None:
            self._session.close()
            self._session = None

    def fetch(self, url: str) -> MangaInfo | None:
        """Загружает страницу и парсит данные манги.

        Пробует сначала с cookies, затем без них (curl_cffi может
        самостоятельно пройти Cloudflare challenge).
        Возвращает ``None`` при ошибке.
        """
        for use_cookies in (True, False):
            try:
                html = self._fetch_html(url, use_cookies=use_cookies)
                result = self._parse_html(html, url)
                if result:
                    return result
            except Exception as exc:
                label = "с cookies" if use_cookies else "без cookies"
                logger.debug("Попытка %s не удалась для %s: %s", label, url, exc)
        return None

    def fetch_quick(self, url: str, timeout: int = 10) -> MangaInfo | None:
        """Быстрая проверка: одна попытка с cookies и коротким таймаутом."""
        try:
            html = self._fetch_html(url, use_cookies=True, timeout=timeout)
            return self._parse_html(html, url)
        except Exception as exc:
            logger.debug("Быстрая проверка не удалась для %s: %s", url, exc)
            return None

    def _fetch_html(self, url: str, *, use_cookies: bool = True, timeout: int = HTTP_TIMEOUT) -> str:
        session = self._get_session(use_cookies=use_cookies)
        response = session.get(url, impersonate="chrome", timeout=timeout)
        if response.status_code != 200:
            raise RuntimeError(f"HTTP {response.status_code}")
        return response.text

    @staticmethod
    def _parse_html(html: str, url: str) -> MangaInfo | None:
        match = _DATA_RE.search(html)
        if not match:
            logger.debug("Не найден window.__DATA__ на странице %s", url)
            return None

        data = json.loads(match.group(1))
        chapters = data["chapters"][::-1]  # от первой к последней
        title = data.get("title", "Manga").strip()

        news_id = data.get("news_id")
        if not news_id:
            url_match = _NEWS_ID_RE.search(url)
            if url_match:
                news_id = url_match.group(1)
            else:
                logger.error("news_id не найден ни в данных, ни в URL: %s", url)
                return None

        return MangaInfo(title=title, news_id=str(news_id), chapters=chapters)
