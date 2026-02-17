"""
QThread-воркер для скачивания манги.

Управляет жизненным циклом:
1. Открытие браузера и авторизация.
2. Мониторинг страниц манги.
3. Скачивание глав через FallbackDownloader.
4. Сборка CBZ-архива.
"""

from __future__ import annotations

import os
import shutil
import time
import zipfile
from pathlib import Path
from threading import Event

from PyQt5.QtCore import QThread, pyqtSignal
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from manga_downloader.config import (
    BASE_URL,
    DOWNLOADS_DIR,
    IMAGE_EXTENSIONS,
    LOGIN_WAIT_TIMEOUT,
    OUTPUT_DIR,
    PAGE_LOAD_DELAY,
    POLL_INTERVAL,
    REQUEST_DELAY,
    SELENIUM_WAIT_TIMEOUT,
    TEMP_DIR,
    USER_AGENT,
)
from manga_downloader.cookies import CookieManager
from manga_downloader.downloaders import FallbackDownloader
from manga_downloader.manga.parser import MangaParser
from manga_downloader.utils import sanitize_filename


# JS-код для замены кнопки «Отслеживать» на «Скачать»
_INJECT_DOWNLOAD_BTN_JS = """
arguments[0].textContent = '⬇️ Скачать';
arguments[0].style.backgroundColor = '#28a745';
arguments[0].style.color = '#fff';
arguments[0].style.fontWeight = 'bold';
arguments[0].style.padding = '10px 20px';
arguments[0].style.borderRadius = '5px';
arguments[0].style.cursor = 'pointer';
arguments[0].onclick = function() {
    window.location.href = window.location.href + '/download';
};
"""


class ChapterWorker(QThread):
    """Фоновый поток загрузки манги.

    Сигналы:
        log(str): сообщение для лог-панели.
        finished_ok(bool): завершение (True = успех).
        download_started(): начало скачивания.
        chapters_found(int, str, str): (кол-во глав, название, URL).
        range_updated(int, int): обновлённый диапазон глав.
        cancellation_info(int): кол-во пропущенных глав при частичном завершении.
    """

    log = pyqtSignal(str)
    finished_ok = pyqtSignal(bool)
    download_started = pyqtSignal()
    chapters_found = pyqtSignal(int, str, str)
    range_updated = pyqtSignal(int, int)
    cancellation_info = pyqtSignal(int)

    def __init__(self) -> None:
        super().__init__()
        self.url: str | None = None
        self._cancel_event = Event()
        self._failed_chapters: list[str] = []
        self._chapter_range: tuple[int, int] | None = None
        self._driver: webdriver.Chrome | None = None
        self._cookie_manager = CookieManager()

    # -- Публичный API ---------------------------------------------------------

    def set_chapter_range(self, start: int | None = None, end: int | None = None) -> None:
        if start is not None and end is not None:
            self._chapter_range = (start, end)
            self.log.emit(f"📊 Установлен диапазон глав: {start}-{end}")
        else:
            self._chapter_range = None
            self.log.emit("📊 Установлено скачивание всех глав")

    def cancel(self) -> None:
        self._cancel_event.set()

    @property
    def is_cancelled(self) -> bool:
        return self._cancel_event.is_set()

    @property
    def failed_count(self) -> int:
        return len(self._failed_chapters)

    # -- QThread ---------------------------------------------------------------

    def run(self) -> None:
        self._cleanup()
        try:
            self.log.emit("🌐 Открытие браузера...")
            self._driver = self._open_browser()
            if self._driver:
                self.log.emit("🔎 Запуск отслеживания страницы манги...")
                self._monitor_pages()
        except Exception as exc:
            self.log.emit(f"❌ Ошибка: {exc}")
            self.finished_ok.emit(False)

    # -- Браузер и авторизация -------------------------------------------------

    def _open_browser(self) -> webdriver.Chrome | None:
        options = Options()
        options.add_experimental_option("detach", True)
        options.add_experimental_option("excludeSwitches", ["enable-logging"])
        options.add_argument(f"--user-agent={USER_AGENT}")
        options.add_argument("--log-level=3")
        driver = webdriver.Chrome(options=options)
        driver.get(BASE_URL)

        if self._cookie_manager.path.exists():
            self.log.emit("🍪 Пробую восстановить сессию...")
            self._cookie_manager.load()
            self._apply_cookies_to_driver(driver)
            driver.refresh()
            time.sleep(PAGE_LOAD_DELAY)

            if self._cookie_manager.has_auth(driver):
                self._cookie_manager.update_from_driver(driver)
                self.log.emit("✅ Авторизация восстановлена!")
                return driver

            self.log.emit("⚠️ Сессия устарела, нужна новая авторизация")

        self.log.emit("🔐 Войдите вручную, я запомню cookies")
        self.log.emit("📦 Ожидание страницы манги...")

        deadline = time.monotonic() + LOGIN_WAIT_TIMEOUT
        while not self._cookie_manager.has_auth(driver):
            if self.is_cancelled:
                driver.quit()
                self.finished_ok.emit(False)
                return None
            if time.monotonic() > deadline:
                self.log.emit("❌ Таймаут ожидания авторизации")
                driver.quit()
                self.finished_ok.emit(False)
                return None
            QThread.msleep(1000)

        self._cookie_manager.update_from_driver(driver)
        self._cookie_manager.save(only_important=True)
        return driver

    def _apply_cookies_to_driver(self, driver: webdriver.Chrome) -> None:
        driver.delete_all_cookies()
        for c in self._cookie_manager.cookies:
            cookie = dict(c)
            cookie.pop("sameSite", None)
            cookie.pop("secure", None)
            cookie.pop("httpOnly", None)
            try:
                driver.add_cookie(cookie)
            except Exception as exc:
                self.log.emit(f"⚠️ Cookie {cookie.get('name')} не добавлен: {exc}")

    # -- Мониторинг страниц ----------------------------------------------------

    def _monitor_pages(self) -> None:
        processed_urls: set[str] = set()
        wait = WebDriverWait(self._driver, SELENIUM_WAIT_TIMEOUT)
        parser = MangaParser(self._cookie_manager)

        while not self.is_cancelled:
            try:
                current_url = self._driver.current_url

                if current_url and current_url.endswith("/download"):
                    self.url = current_url.replace("/download", "")
                    self.log.emit(f"📍 Начинаем скачивание манги: {self.url}")
                    if self._chapter_range:
                        self.range_updated.emit(*self._chapter_range)
                    self._driver.quit()
                    self._driver = None
                    self._download_manga(parser)
                    self.finished_ok.emit(True)
                    return

                if current_url and "/" in current_url and ".html" in current_url:
                    if current_url not in processed_urls:
                        self.log.emit(f"🔍 Обнаружена страница манги: {current_url}")
                        info = parser.fetch(current_url)
                        if info:
                            self.log.emit(f"📊 Найдено глав: {info.total_chapters}")
                            self.chapters_found.emit(
                                info.total_chapters, info.title, current_url,
                            )
                            processed_urls.add(current_url)

                        self._inject_download_button(wait)

                QThread.msleep(int(POLL_INTERVAL * 1000))

            except Exception as exc:
                self.log.emit(f"❌ Ошибка: {exc}")
                if self._driver:
                    self._driver.quit()
                    self._driver = None
                self.finished_ok.emit(False)
                return

    def _inject_download_button(self, wait: WebDriverWait) -> None:
        try:
            btn = wait.until(
                EC.presence_of_element_located(
                    (By.CSS_SELECTOR, "a.page__btn-track.js-follow-status")
                )
            )
            self._driver.execute_script(_INJECT_DOWNLOAD_BTN_JS, btn)
            self.log.emit("✅ Кнопка заменена на 'Скачать'")
        except Exception as exc:
            self.log.emit(f"⚠️ Кнопка не найдена: {exc}")

    # -- Скачивание манги ------------------------------------------------------

    def _download_manga(self, parser: MangaParser) -> None:
        if not self._cookie_manager.cookies:
            self.log.emit("⚠️ Cookies не заданы — загружаю из файла")
            if not self._cookie_manager.load():
                self.log.emit("❌ Не удалось загрузить cookies")
                return

        self.download_started.emit()
        self.log.emit(f"📥 Скачивание HTML: {self.url}")

        info = parser.fetch(self.url)
        if not info:
            self.log.emit("❌ Не удалось получить данные манги")
            return

        chapters = info.chapters
        self.log.emit(f"📊 Название: {info.title}")
        self.log.emit(f"📊 ID манги: {info.news_id}")
        self.log.emit(f"📊 Всего глав: {info.total_chapters}")

        if self._chapter_range:
            start, end = self._chapter_range
            chapters = chapters[max(0, start - 1):min(len(chapters), end)]
            self.log.emit(f"📊 Выбран диапазон глав: {start}-{end} (всего {len(chapters)} глав)")
        else:
            self.log.emit(f"📊 Выбраны все главы (всего {len(chapters)} глав)")

        title_safe = sanitize_filename(info.title)
        OUTPUT_DIR.mkdir(exist_ok=True)
        final_cbz = OUTPUT_DIR / f"{title_safe}.cbz"
        DOWNLOADS_DIR.mkdir(exist_ok=True)
        TEMP_DIR.mkdir(exist_ok=True)

        self._failed_chapters = []

        with FallbackDownloader(self.url, self._cookie_manager, self.log.emit) as dl:
            self._download_chapters(chapters, info.news_id, dl)

        if self._failed_chapters and not self.is_cancelled:
            self.log.emit(f"\n⚠️ Не удалось скачать {len(self._failed_chapters)} глав:")
            for ch in self._failed_chapters:
                self.log.emit(f"  • {ch}")
            self.log.emit("")

        if not self.is_cancelled:
            if self._failed_chapters:
                self.log.emit("⚠️ Некоторые главы не удалось скачать, но архив будет создан из успешных")
            self._create_cbz(final_cbz)

        self._cleanup()

        if not self.is_cancelled:
            if self._failed_chapters:
                self.log.emit(f"\n⚠️ Частично завершено. Пропущено глав: {len(self._failed_chapters)}")
                self.log.emit(f"📦 Архив создан: {final_cbz.resolve()} (без пропущенных глав)")
                self.cancellation_info.emit(len(self._failed_chapters))
            else:
                self.log.emit(f"\n✅ Полностью готово: {final_cbz.resolve()}")

    def _download_chapters(
        self,
        chapters: list[dict],
        news_id: str,
        downloader: FallbackDownloader,
    ) -> None:
        total = len(chapters)
        self.log.emit(f"\n🔢 Начинаем скачивание {total} глав...")
        self.log.emit("📡 Используются методы: curl_cffi → cloudscraper → Selenium\n")

        for i, chapter in enumerate(chapters, 1):
            if self.is_cancelled:
                self.log.emit("❌ Скачивание отменено")
                return

            title = chapter["title"]
            chapter_id = chapter["id"]
            filename = sanitize_filename(f"{i:04}_{title}") + ".zip"
            zip_path = DOWNLOADS_DIR / filename

            self.log.emit(f"📖 Глава {i}/{total}: {title}")
            self.log.emit(f"   ID: {chapter_id}")

            success = downloader.download(chapter_id, news_id, zip_path, title)

            if success:
                self.log.emit("  ✅ Успешно\n")
            else:
                self._failed_chapters.append(f"Глава {i}: {title}")
                self.log.emit("  ❌ Не удалось скачать\n")

            time.sleep(REQUEST_DELAY)

    # -- CBZ -------------------------------------------------------------------

    def _create_cbz(self, final_cbz: Path) -> None:
        self.log.emit("📦 Архивация в CBZ...")
        zip_files = sorted(DOWNLOADS_DIR.glob("*.zip"))

        if not zip_files:
            self.log.emit("❌ Нет файлов для архивации")
            return

        index = 1
        successful = 0
        total_pages = 0

        try:
            with zipfile.ZipFile(final_cbz, "w", zipfile.ZIP_DEFLATED) as cbz:
                for zip_file in zip_files:
                    if self.is_cancelled:
                        self.log.emit("❌ Архивация отменена")
                        break

                    self.log.emit(f"📦 Обработка: {zip_file.name}")
                    try:
                        chapter_pages, index = self._process_chapter_zip(
                            zip_file, cbz, index,
                        )
                        self.log.emit(f"  📄 Страниц в главе: {chapter_pages}")
                        successful += 1
                        total_pages += chapter_pages
                    except Exception as exc:
                        self.log.emit(f"  ⚠️ Ошибка при обработке {zip_file.name}: {exc}")

            self.log.emit(f"\n📊 Статистика:")
            self.log.emit(f"  • Всего страниц: {total_pages}")
            self.log.emit(f"  • Успешно обработано глав: {successful}/{len(zip_files)}")

            if successful == 0:
                self.log.emit("❌ Не удалось обработать ни одной главы")
                if final_cbz.exists():
                    final_cbz.unlink()

        except Exception as exc:
            self.log.emit(f"❌ Ошибка при создании CBZ: {exc}")
            if final_cbz.exists():
                final_cbz.unlink()

    @staticmethod
    def _process_chapter_zip(
        zip_file: Path,
        cbz: zipfile.ZipFile,
        start_index: int,
    ) -> tuple[int, int]:
        """Извлекает изображения из ZIP главы и добавляет в CBZ.

        Возвращает (кол-во страниц, следующий индекс).
        """
        index = start_index
        pages = 0

        with zipfile.ZipFile(zip_file, "r") as zf:
            for name in sorted(zf.namelist()):
                ext = os.path.splitext(name)[1].lower()
                if ext not in IMAGE_EXTENSIONS:
                    continue

                out_name = f"{index:06}{ext}"
                src = TEMP_DIR / name
                dst = TEMP_DIR / out_name

                zf.extract(name, path=TEMP_DIR)
                if src.exists():
                    src.rename(dst)
                    cbz.write(dst, arcname=out_name)
                    index += 1
                    pages += 1

        return pages, index

    # -- Очистка ---------------------------------------------------------------

    @staticmethod
    def _cleanup() -> None:
        for dir_path in (DOWNLOADS_DIR, TEMP_DIR):
            if dir_path.exists():
                shutil.rmtree(dir_path)
