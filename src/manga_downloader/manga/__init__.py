"""Бизнес-логика: парсинг манги и управление загрузкой."""

from manga_downloader.manga.parser import MangaParser
from manga_downloader.manga.chapter_worker import ChapterWorker

__all__ = ["MangaParser", "ChapterWorker"]
