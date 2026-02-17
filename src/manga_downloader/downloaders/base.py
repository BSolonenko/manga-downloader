"""
Базовый класс загрузчика глав.

Содержит общую логику: формирование payload, парсинг URL ответа,
скачивание файла и валидацию ZIP.
"""

from __future__ import annotations

import abc
import logging
from pathlib import Path
from typing import Any, Callable

from manga_downloader.config import DEFAULT_HEADERS
from manga_downloader.utils import get_file_size_kb, parse_download_url, validate_zip_file

logger = logging.getLogger(__name__)

LogCallback = Callable[[str], None]


class BaseDownloader(abc.ABC):
    """Абстрактный загрузчик одной главы.

    Подклассы реализуют :meth:`_create_session` и :meth:`_post` / :meth:`_get`.
    """

    name: str = "base"

    def __init__(self, referer_url: str, log_fn: LogCallback | None = None) -> None:
        self.referer_url = referer_url
        self._log_fn = log_fn

    # -- Логирование -----------------------------------------------------------

    def log(self, msg: str) -> None:
        if self._log_fn:
            self._log_fn(msg)
        else:
            logger.info(msg)

    # -- Шаблонный метод -------------------------------------------------------

    def download(
        self,
        chapter_id: int | str,
        news_id: int | str,
        zip_path: Path,
        title: str,
    ) -> bool:
        """Скачивает главу. Возвращает ``True`` при успехе."""
        try:
            self.log(f"  🔄 Метод {self.name} для {title}...")

            api_response = self._api_request(chapter_id, news_id)
            raw_url = api_response.get("data")
            if not raw_url:
                raise ValueError("Нет URL в ответе API")

            download_url = parse_download_url(raw_url)
            self._download_file(download_url, zip_path)

            if not validate_zip_file(zip_path):
                raise ValueError("Скачанный файл не является ZIP-архивом")

            size = get_file_size_kb(zip_path)
            self.log(f"  ✅ Метод {self.name} успешен ({size:.1f} KB)")
            return True

        except Exception as exc:
            self.log(f"  ⚠️ Метод {self.name} не сработал: {str(exc)[:100]}")
            return False

    # -- Абстрактные методы (реализуются в подклассах) -------------------------

    @abc.abstractmethod
    def _api_request(self, chapter_id: int | str, news_id: int | str) -> dict[str, Any]:
        """Отправляет POST-запрос к API и возвращает JSON-ответ."""

    @abc.abstractmethod
    def _download_file(self, url: str, dest: Path) -> None:
        """Скачивает файл по URL и сохраняет в *dest*."""

    # -- Вспомогательные -------------------------------------------------------

    def _make_headers(self, extra: dict[str, str] | None = None) -> dict[str, str]:
        """Возвращает заголовки с Referer и опциональными дополнениями."""
        headers = {**DEFAULT_HEADERS, "Referer": self.referer_url}
        if extra:
            headers.update(extra)
        return headers

    @staticmethod
    def _make_payload(chapter_id: int | str, news_id: int | str) -> dict[str, str]:
        return {"chapter_id": str(chapter_id), "news_id": str(news_id)}

    # -- Управление ресурсами --------------------------------------------------

    def close(self) -> None:
        """Освобождает ресурсы. Переопределяется в подклассах."""

    def __enter__(self) -> "BaseDownloader":
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()
