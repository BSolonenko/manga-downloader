"""
Оркестратор загрузки с цепочкой fallback-методов.
"""

from __future__ import annotations

import logging
import time
from pathlib import Path

from manga_downloader.config import FALLBACK_DELAY
from manga_downloader.cookies import CookieManager
from manga_downloader.downloaders.base import LogCallback
from manga_downloader.downloaders.curl_downloader import CurlCffiDownloader
from manga_downloader.downloaders.cloud_downloader import CloudscraperDownloader
from manga_downloader.downloaders.selenium_downloader import SeleniumRecoveryDownloader

logger = logging.getLogger(__name__)


class FallbackDownloader:
    """Пробует загрузчики по цепочке: curl_cffi -> cloudscraper -> Selenium."""

    def __init__(
        self,
        referer_url: str,
        cookie_manager: CookieManager,
        log_fn: LogCallback | None = None,
    ) -> None:
        self._log_fn = log_fn
        self._downloaders = [
            CurlCffiDownloader(referer_url, cookie_manager, log_fn),
            CloudscraperDownloader(referer_url, cookie_manager, log_fn),
            SeleniumRecoveryDownloader(referer_url, cookie_manager, log_fn),
        ]

    def log(self, msg: str) -> None:
        if self._log_fn:
            self._log_fn(msg)
        else:
            logger.info(msg)

    def download(
        self,
        chapter_id: int | str,
        news_id: int | str,
        zip_path: Path,
        title: str,
    ) -> bool:
        """Пробует все методы по очереди, возвращает ``True`` при первом успехе."""
        for i, dl in enumerate(self._downloaders):
            if dl.download(chapter_id, news_id, zip_path, title):
                return True
            if i < len(self._downloaders) - 1:
                time.sleep(FALLBACK_DELAY)

        self.log(f"  ❌ Все методы не сработали для {title}")
        return False

    def close(self) -> None:
        for dl in self._downloaders:
            dl.close()

    def __enter__(self) -> "FallbackDownloader":
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()
