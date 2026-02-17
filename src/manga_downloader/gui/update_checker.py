"""
Фоновый поток проверки новых глав для тайтлов в библиотеке.

Парсит страницу каждой манги и сравнивает total_chapters с last_chapter_downloaded.
Результаты отправляются по одному через сигнал.
"""

from __future__ import annotations

import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from threading import Event

from PyQt5.QtCore import QThread, pyqtSignal

from manga_downloader.cookies import CookieManager
from manga_downloader.manga.parser import MangaParser

logger = logging.getLogger(__name__)

_MAX_WORKERS = 3


class UpdateChecker(QThread):
    """Проверяет наличие новых глав для списка манг.

    Использует пул потоков для параллельных запросов.
    Тихо пропускает тайтлы, если cookies невалидны или сайт недоступен.

    Сигналы:
        result(str, int): (url, total_chapters_on_site) — результат для одной манги.
        finished_all(): все проверки завершены.
    """

    result = pyqtSignal(str, int)
    finished_all = pyqtSignal()

    def __init__(self, entries: list[dict], parent: object | None = None) -> None:
        super().__init__(parent)
        self._entries = entries
        self._stop_event = Event()

    def stop(self) -> None:
        """Запрашивает остановку потока."""
        self._stop_event.set()

    def run(self) -> None:
        cookie_mgr = CookieManager()
        if not cookie_mgr.path.exists():
            logger.debug("UpdateChecker: файл cookies не найден")
            self.finished_all.emit()
            return

        cookie_mgr.load()
        if not cookie_mgr.cookies:
            logger.debug("UpdateChecker: cookies пусты")
            self.finished_all.emit()
            return

        urls = [e.get("url", "") for e in self._entries if e.get("url")]
        if not urls:
            self.finished_all.emit()
            return

        logger.debug("UpdateChecker: проверяю %d тайтлов", len(urls))
        workers = min(_MAX_WORKERS, len(urls))

        with ThreadPoolExecutor(max_workers=workers) as pool:
            futures = {
                pool.submit(self._check_one, url, cookie_mgr): url
                for url in urls
            }
            for future in as_completed(futures):
                if self._stop_event.is_set():
                    pool.shutdown(wait=False, cancel_futures=True)
                    break
                url = futures[future]
                try:
                    total = future.result()
                    if total is not None:
                        logger.debug("UpdateChecker: %s -> %d глав", url, total)
                        self.result.emit(url, total)
                except Exception as exc:
                    logger.debug("Ошибка проверки %s: %s", url, exc)

        self.finished_all.emit()

    @staticmethod
    def _check_one(url: str, cookie_mgr: CookieManager) -> int | None:
        """Проверяет один тайтл (выполняется в потоке пула)."""
        parser = MangaParser(cookie_mgr)
        try:
            info = parser.fetch_quick(url)
            return info.total_chapters if info else None
        finally:
            parser.close()
