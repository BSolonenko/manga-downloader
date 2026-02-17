"""
Хранилище истории скачанных манг.

Сохраняет метаданные в JSON-файл для быстрого доступа к ранее скачанным мангам
и определения новых глав для докачки.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any

from manga_downloader.config import HISTORY_FILE

logger = logging.getLogger(__name__)

_CURRENT_VERSION = 1


class DownloadHistory:
    """Управляет JSON-файлом с историей скачанных манг."""

    def __init__(self, path: Path | None = None) -> None:
        self._path = path or HISTORY_FILE
        self._data: dict[str, Any] = {"version": _CURRENT_VERSION, "manga": {}}
        self.load()

    # -- Чтение / запись -------------------------------------------------------

    def load(self) -> bool:
        """Загружает историю из файла. Возвращает ``True`` при успехе."""
        if not self._path.exists():
            return False
        try:
            with open(self._path, encoding="utf-8") as f:
                self._data = json.load(f)
            return True
        except Exception as exc:
            logger.error("Ошибка чтения истории: %s", exc)
            return False

    def save(self) -> bool:
        """Сохраняет историю в файл. Возвращает ``True`` при успехе."""
        try:
            self._path.parent.mkdir(parents=True, exist_ok=True)
            with open(self._path, "w", encoding="utf-8") as f:
                json.dump(self._data, f, ensure_ascii=False, indent=2)
            return True
        except Exception as exc:
            logger.error("Ошибка записи истории: %s", exc)
            return False

    # -- Доступ к данным -------------------------------------------------------

    @property
    def _manga(self) -> dict[str, Any]:
        return self._data.setdefault("manga", {})

    def get_all(self) -> list[dict[str, Any]]:
        """Все записи, отсортированные по дате последнего скачивания (новые первые)."""
        entries = list(self._manga.values())
        entries.sort(key=lambda e: e.get("last_download_date", ""), reverse=True)
        return entries

    def get(self, url: str) -> dict[str, Any] | None:
        """Запись по URL манги."""
        return self._manga.get(url)

    def upsert(
        self,
        url: str,
        title: str,
        news_id: str,
        downloaded_chapters: list[int],
        cbz_path: str,
        total_on_site: int = 0,
    ) -> None:
        """Создаёт или обновляет запись о манге и сохраняет файл."""
        existing = self._manga.get(url, {})
        prev_chapters: list[int] = existing.get("downloaded_chapters", [])
        merged = sorted(set(prev_chapters) | set(downloaded_chapters))

        known_total = total_on_site or existing.get("last_known_total", 0)

        self._manga[url] = {
            "title": title,
            "url": url,
            "news_id": news_id,
            "downloaded_chapters": merged,
            "last_chapter_downloaded": max(merged) if merged else 0,
            "last_known_total": known_total,
            "cbz_path": cbz_path,
            "last_download_date": datetime.now().isoformat(timespec="seconds"),
            "download_count": existing.get("download_count", 0) + 1,
        }
        self.save()

    def update_total(self, url: str, total_on_site: int) -> None:
        """Обновляет ``last_known_total`` для манги (из фоновой проверки)."""
        entry = self._manga.get(url)
        if entry and total_on_site > 0:
            entry["last_known_total"] = total_on_site
            self.save()

    def delete(self, url: str) -> bool:
        """Удаляет запись. Возвращает ``True`` если запись существовала."""
        if url in self._manga:
            del self._manga[url]
            self.save()
            return True
        return False

