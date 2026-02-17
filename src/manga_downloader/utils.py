"""
Утилиты: парсинг URL, санитизация имён файлов, валидация ZIP.
"""

import os
import re
import zipfile
from pathlib import Path


def parse_download_url(raw_url: str) -> str:
    """Приводит URL из API-ответа к нормальному виду.

    Заменяет экранированные слеши и добавляет схему при необходимости.
    """
    url = raw_url.replace("\\/", "/")
    if url.startswith("//"):
        url = "https:" + url
    return url


def sanitize_filename(name: str) -> str:
    """Заменяет недопустимые символы в имени файла на ``_``."""
    return re.sub(r"[^\w\- ]", "_", name)


def validate_zip_file(path: Path) -> bool:
    """Проверяет, что файл существует и является корректным ZIP-архивом."""
    return path.exists() and zipfile.is_zipfile(path)


def get_file_size_kb(path: Path) -> float:
    """Возвращает размер файла в килобайтах."""
    return os.path.getsize(path) / 1024
