"""
Загрузчик на основе cloudscraper для обхода Cloudflare.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import cloudscraper

from manga_downloader.config import API_URL, HTTP_TIMEOUT, DOWNLOAD_TIMEOUT
from manga_downloader.cookies import CookieManager
from manga_downloader.downloaders.base import BaseDownloader, LogCallback


class CloudscraperDownloader(BaseDownloader):
    """Метод 2: cloudscraper."""

    name = "cloudscraper"

    def __init__(
        self,
        referer_url: str,
        cookie_manager: CookieManager,
        log_fn: LogCallback | None = None,
    ) -> None:
        super().__init__(referer_url, log_fn)
        self._cookie_manager = cookie_manager
        self._scraper: cloudscraper.CloudScraper | None = None

    def _ensure_scraper(self) -> cloudscraper.CloudScraper:
        if self._scraper is None:
            self._scraper = cloudscraper.create_scraper(
                browser={
                    "browser": "chrome",
                    "platform": "windows",
                    "desktop": True,
                    "mobile": False,
                }
            )
            self._scraper.headers.update(self._make_headers())
            self._cookie_manager.apply_to_scraper(self._scraper)
        return self._scraper

    def _api_request(self, chapter_id: int | str, news_id: int | str) -> dict[str, Any]:
        scraper = self._ensure_scraper()
        payload = self._make_payload(chapter_id, news_id)
        response = scraper.post(API_URL, data=payload, timeout=HTTP_TIMEOUT)
        if response.status_code != 200:
            raise RuntimeError(f"HTTP {response.status_code}")
        return response.json()

    def _download_file(self, url: str, dest: Path) -> None:
        scraper = self._ensure_scraper()
        response = scraper.get(
            url,
            timeout=DOWNLOAD_TIMEOUT,
            allow_redirects=True,
            headers={
                "Referer": self.referer_url,
                "Accept": "application/zip,*/*",
            },
        )
        if response.status_code != 200:
            raise RuntimeError(f"Ошибка скачивания: HTTP {response.status_code}")
        with open(dest, "wb") as fh:
            fh.write(response.content)

    def close(self) -> None:
        if self._scraper is not None:
            self._scraper.close()
            self._scraper = None
