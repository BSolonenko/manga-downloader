"""
Загрузчик на основе curl_cffi с эмуляцией Chrome.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import curl_cffi

from manga_downloader.config import API_URL, HTTP_TIMEOUT, DOWNLOAD_TIMEOUT
from manga_downloader.cookies import CookieManager
from manga_downloader.downloaders.base import BaseDownloader, LogCallback


class CurlCffiDownloader(BaseDownloader):
    """Метод 1: curl_cffi с ``impersonate="chrome"``."""

    name = "curl_cffi"

    def __init__(
        self,
        referer_url: str,
        cookie_manager: CookieManager,
        log_fn: LogCallback | None = None,
    ) -> None:
        super().__init__(referer_url, log_fn)
        self._cookie_manager = cookie_manager
        self._session: curl_cffi.Session | None = None

    def _ensure_session(self) -> curl_cffi.Session:
        if self._session is None:
            self._session = curl_cffi.Session()
            self._session.headers.update(self._make_headers())
            self._cookie_manager.apply_to_session(self._session)
        return self._session

    def _api_request(self, chapter_id: int | str, news_id: int | str) -> dict[str, Any]:
        session = self._ensure_session()
        payload = self._make_payload(chapter_id, news_id)
        response = session.post(
            API_URL,
            data=payload,
            impersonate="chrome",
            timeout=HTTP_TIMEOUT,
        )
        if response.status_code != 200:
            raise RuntimeError(f"HTTP {response.status_code}")
        return response.json()

    def _download_file(self, url: str, dest: Path) -> None:
        session = self._ensure_session()
        response = session.get(
            url,
            impersonate="chrome",
            allow_redirects=True,
            timeout=DOWNLOAD_TIMEOUT,
        )
        if response.status_code != 200:
            raise RuntimeError(f"Ошибка скачивания: HTTP {response.status_code}")
        with open(dest, "wb") as fh:
            fh.write(response.content)

    def reset_session(self, cookie_manager: CookieManager | None = None) -> None:
        """Пересоздаёт сессию (например, после обновления cookies)."""
        self.close()
        if cookie_manager is not None:
            self._cookie_manager = cookie_manager

    def close(self) -> None:
        if self._session is not None:
            self._session.close()
            self._session = None
