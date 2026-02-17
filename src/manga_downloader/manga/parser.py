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

    def fetch(self, url: str) -> MangaInfo | None:
        """Загружает страницу и парсит данные манги.

        Возвращает ``None`` при ошибке.
        """
        try:
            html = self._fetch_html(url)
            return self._parse_html(html, url)
        except Exception as exc:
            logger.error("Ошибка при получении данных манги: %s", exc)
            return None

    def _fetch_html(self, url: str) -> str:
        with curl_cffi.Session() as session:
            session.headers.update(BROWSE_HEADERS)
            self._cookie_manager.apply_to_session(session)
            response = session.get(url, impersonate="chrome", timeout=HTTP_TIMEOUT)
            return response.text

    @staticmethod
    def _parse_html(html: str, url: str) -> MangaInfo | None:
        match = _DATA_RE.search(html)
        if not match:
            logger.error("Не найден window.__DATA__ на странице %s", url)
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
