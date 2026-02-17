"""
Загрузчик с восстановлением сессии через Selenium.

Используется как последний fallback при ошибках 403.
Открывает Chrome, обновляет cookies и повторяет запрос через curl_cffi.
"""

from __future__ import annotations

import time
from pathlib import Path
from typing import Any

import curl_cffi
from selenium import webdriver
from selenium.webdriver.chrome.options import Options

from manga_downloader.config import (
    API_URL,
    BASE_URL,
    COOKIE_DOMAIN,
    DOWNLOAD_TIMEOUT,
    HTTP_TIMEOUT,
    USER_AGENT,
)
from manga_downloader.cookies import CookieManager
from manga_downloader.downloaders.base import BaseDownloader, LogCallback
from manga_downloader.utils import get_file_size_kb, parse_download_url, validate_zip_file


class SeleniumRecoveryDownloader(BaseDownloader):
    """Метод 3: восстановление сессии через Selenium + curl_cffi."""

    name = "Selenium recovery"

    def __init__(
        self,
        referer_url: str,
        cookie_manager: CookieManager,
        log_fn: LogCallback | None = None,
    ) -> None:
        super().__init__(referer_url, log_fn)
        self._cookie_manager = cookie_manager

    # Переопределяем download целиком, т.к. логика сильно отличается:
    # нужно открыть браузер, обновить cookies, затем скачать через curl_cffi.
    def download(
        self,
        chapter_id: int | str,
        news_id: int | str,
        zip_path: Path,
        title: str,
    ) -> bool:
        driver = None
        session = None
        try:
            self.log(f"  🔄 Метод {self.name} для {title}...")

            driver = self._open_browser()
            self._refresh_cookies(driver)

            session = self._build_session()
            json_data = self._api_post(session, chapter_id, news_id)

            raw_url = json_data.get("data")
            if not raw_url:
                raise ValueError("Нет URL в ответе API")

            download_url = parse_download_url(raw_url)
            self._fetch_file(session, download_url, zip_path)

            if not validate_zip_file(zip_path):
                raise ValueError("Скачанный файл не является ZIP-архивом")

            size = get_file_size_kb(zip_path)
            self.log(f"  ✅ Метод {self.name} успешен ({size:.1f} KB)")

            self._cookie_manager.save_all()
            self.log("  💾 Обновленные куки сохранены")
            return True

        except Exception as exc:
            self.log(f"  ⚠️ Метод {self.name} не сработал: {str(exc)[:100]}")
            return False
        finally:
            if session is not None:
                session.close()
            if driver is not None:
                driver.quit()

    # -- Внутренние методы -----------------------------------------------------

    def _open_browser(self) -> webdriver.Chrome:
        options = Options()
        options.add_argument(f"--user-agent={USER_AGENT}")
        options.add_argument("--log-level=3")
        options.add_experimental_option("detach", False)
        options.add_experimental_option("excludeSwitches", ["enable-logging"])
        driver = webdriver.Chrome(options=options)
        driver.get(BASE_URL)
        return driver

    def _refresh_cookies(self, driver: webdriver.Chrome) -> None:
        self._cookie_manager.apply_to_driver(driver, COOKIE_DOMAIN)
        driver.refresh()
        time.sleep(2)
        self._cookie_manager.update_from_driver(driver)
        self.log("  🔄 Повторная попытка с обновленными куками...")

    def _build_session(self) -> curl_cffi.Session:
        session = curl_cffi.Session()
        session.headers.update(self._make_headers())
        self._cookie_manager.apply_to_session(session)
        return session

    def _api_post(
        self,
        session: curl_cffi.Session,
        chapter_id: int | str,
        news_id: int | str,
    ) -> dict[str, Any]:
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

    @staticmethod
    def _fetch_file(session: curl_cffi.Session, url: str, dest: Path) -> None:
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

    # Не используются в Selenium-загрузчике, но нужны для ABC
    def _api_request(self, chapter_id: int | str, news_id: int | str) -> dict[str, Any]:
        raise NotImplementedError  # pragma: no cover

    def _download_file(self, url: str, dest: Path) -> None:
        raise NotImplementedError  # pragma: no cover
