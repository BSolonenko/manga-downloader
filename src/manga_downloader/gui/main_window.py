"""
Главное окно приложения Manga Downloader.

Содержит только UI-логику; вся бизнес-логика делегируется ChapterWorker.
Общение с воркером -- исключительно через Qt-сигналы.
"""

from __future__ import annotations

import html
import json
import os
import subprocess
import sys
from pathlib import Path

from PyQt5.QtGui import QCloseEvent, QTextCursor
from PyQt5.QtCore import QSize, Qt, QTimer
from PyQt5.QtWidgets import (
    QApplication,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QSizePolicy,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from manga_downloader.config import OUTPUT_DIR
from manga_downloader.gui.chapter_dialog import ChapterSelectDialog
from manga_downloader.gui.donation_dialog import DonationDialog
from manga_downloader.gui.styles import (
    APP_STYLE,
    LOG_COLOR_DEFAULT,
    LOG_COLOR_ERROR,
    LOG_COLOR_INFO,
    LOG_COLOR_SUCCESS,
    LOG_COLOR_WARNING,
)
from manga_downloader.gui.update_checker import UpdateChecker
from manga_downloader.history import DownloadHistory
from manga_downloader.manga.chapter_worker import ChapterWorker


class DownloaderApp(QWidget):
    """Главное окно приложения для скачивания манги."""

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Manga Downloader")
        self.setGeometry(200, 200, 900, 800)
        self.setMinimumSize(750, 600)

        self._worker: ChapterWorker | None = None
        self._update_checker: UpdateChecker | None = None
        self._last_cbz_path: str | None = None
        self._history = DownloadHistory()
        self._new_chapters: dict[str, int] = {}

        self._build_ui()
        self._apply_theme()
        self._connect_ui_signals()
        self._refresh_library_list()

        self._update_timer = QTimer(self)
        self._update_timer.timeout.connect(self._start_update_check)
        self._update_timer.start(5 * 60 * 1000)
        self._start_update_check()

    # -- Построение интерфейса -------------------------------------------------

    def _build_ui(self) -> None:
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(8)
        main_layout.setContentsMargins(14, 14, 14, 14)

        # === Кнопки ===
        button_layout = QHBoxLayout()
        button_layout.setSpacing(8)

        self._btn_start = QPushButton("  Открыть сайт и начать")
        self._btn_start.setObjectName("btn_start")

        self._btn_cancel = QPushButton("  Отмена")
        self._btn_cancel.setObjectName("btn_cancel")
        self._btn_cancel.hide()

        self._btn_open_folder = QPushButton("  Открыть папку")
        self._btn_open_folder.setObjectName("btn_open_folder")
        self._btn_open_folder.setVisible(self._has_output_files())

        self._btn_donate = QPushButton("☕ Кофе автору")
        self._btn_donate.setObjectName("btn_donate")
        self._btn_donate.setCursor(Qt.PointingHandCursor)
        self._btn_donate.setToolTip("Поддержать автора")

        button_layout.addWidget(self._btn_start)
        button_layout.addWidget(self._btn_cancel)
        button_layout.addWidget(self._btn_open_folder)
        button_layout.addStretch()
        button_layout.addWidget(self._btn_donate)

        # === Библиотека ===
        library_label = QLabel("Библиотека")
        library_label.setObjectName("label_section_library")

        self._library_list = QListWidget()
        self._library_list.setMinimumHeight(60)
        self._library_list.setMaximumHeight(200)

        # === Прогресс-бар ===
        progress_layout = QVBoxLayout()
        progress_layout.setSpacing(4)

        self._label_progress = QLabel("")
        self._label_progress.setObjectName("label_progress")

        self._progress_bar = QProgressBar()
        self._progress_bar.setMinimum(0)
        self._progress_bar.setMaximum(100)
        self._progress_bar.setValue(0)
        self._progress_bar.setFormat("%v/%m")
        self._progress_bar.hide()

        progress_layout.addWidget(self._label_progress)
        progress_layout.addWidget(self._progress_bar)

        # === Логи -- заголовок с кнопками ===
        log_header = QHBoxLayout()
        log_label = QLabel("Лог")
        log_label.setStyleSheet("font-weight: bold;")

        self._btn_save_log = QPushButton("Сохранить лог")
        self._btn_save_log.setObjectName("btn_save_log")

        self._btn_clear_log = QPushButton("Очистить")
        self._btn_clear_log.setObjectName("btn_clear_log")

        log_header.addWidget(log_label)
        log_header.addStretch()
        log_header.addWidget(self._btn_save_log)
        log_header.addWidget(self._btn_clear_log)

        self._logs = QTextEdit(readOnly=True)
        self._logs.setObjectName("logs")

        # === Собираем layout ===
        main_layout.addLayout(button_layout)
        main_layout.addWidget(library_label)
        main_layout.addWidget(self._library_list)
        main_layout.addLayout(progress_layout)
        main_layout.addLayout(log_header)
        main_layout.addWidget(self._logs)

    def _apply_theme(self) -> None:
        self.setStyleSheet(APP_STYLE)

    def _connect_ui_signals(self) -> None:
        self._btn_start.clicked.connect(self._on_start)
        self._btn_cancel.clicked.connect(self._on_cancel)
        self._btn_open_folder.clicked.connect(self._on_open_folder)
        self._btn_clear_log.clicked.connect(self._on_clear_log)
        self._btn_save_log.clicked.connect(self._on_save_log)
        self._btn_donate.clicked.connect(self._on_donate)

    # -- Закрытие окна ---------------------------------------------------------

    def closeEvent(self, event: QCloseEvent) -> None:  # noqa: N802
        """Корректно останавливаем фоновые потоки перед закрытием."""
        self._update_timer.stop()

        if self._update_checker is not None and self._update_checker.isRunning():
            self._update_checker.stop()
            self._update_checker.wait(5000)

        if self._worker is not None and self._worker.isRunning():
            self._worker.cancel()
            self._worker.wait(5000)

        super().closeEvent(event)

    # -- Вспомогательные -------------------------------------------------------

    @staticmethod
    def _has_output_files() -> bool:
        """Проверяет, есть ли файлы в папке вывода."""
        if not OUTPUT_DIR.exists():
            return False
        return any(OUTPUT_DIR.iterdir())

    def _set_library_buttons_enabled(self, enabled: bool) -> None:
        """Включает/выключает кнопки в строках библиотеки."""
        for i in range(self._library_list.count()):
            item = self._library_list.item(i)
            widget = self._library_list.itemWidget(item)
            if widget:
                for btn in widget.findChildren(QPushButton):
                    btn.setEnabled(enabled)

    # -- Библиотека ------------------------------------------------------------

    def _refresh_library_list(self) -> None:
        """Перезаполняет QListWidget из истории с кнопками в каждой строке."""
        scroll_pos = self._library_list.verticalScrollBar().value()
        self._library_list.clear()
        for entry in self._history.get_all():
            url = entry.get("url", "")
            title = entry.get("title", "???")
            last_ch = entry.get("last_chapter_downloaded", 0)
            known_total = entry.get("last_known_total", 0)
            date = entry.get("last_download_date", "")[:10]

            if known_total > 0:
                label_text = f"{title}  —  {last_ch}/{known_total} глав  —  {date}"
            else:
                label_text = f"{title}  —  скачано {last_ch} глав  —  {date}"

            row_widget = QWidget()
            row_layout = QHBoxLayout(row_widget)
            row_layout.setContentsMargins(6, 4, 6, 4)
            row_layout.setSpacing(8)

            label = QLabel(label_text)
            label.setObjectName("library_item_label")
            label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)

            new_count = self._new_chapters.get(url, 0)
            if new_count == 0 and known_total > last_ch:
                new_count = known_total - last_ch
            badge = QLabel(f"+{new_count}")
            badge.setObjectName("badge_new_chapters")
            badge.setVisible(new_count > 0)

            btn_download = QPushButton("Скачать")
            btn_download.setObjectName("btn_lib_download")
            btn_download.setCursor(Qt.PointingHandCursor)
            btn_download.setEnabled(new_count > 0 or known_total == 0)
            btn_download.clicked.connect(lambda checked, u=url: self._on_download_selected(u))

            btn_delete = QPushButton("✕")
            btn_delete.setObjectName("btn_lib_delete")
            btn_delete.setToolTip("Удалить из истории")
            btn_delete.setCursor(Qt.PointingHandCursor)
            btn_delete.clicked.connect(lambda checked, u=url, t=title: self._on_delete_history(u, t))

            row_layout.addWidget(label)
            row_layout.addWidget(badge)
            row_layout.addWidget(btn_download)
            row_layout.addWidget(btn_delete)

            item = QListWidgetItem()
            item.setData(Qt.UserRole, url)
            item.setSizeHint(QSize(0, 38))
            self._library_list.addItem(item)
            self._library_list.setItemWidget(item, row_widget)

        self._library_list.verticalScrollBar().setValue(scroll_pos)

    def _on_delete_history(self, url: str, title: str) -> None:
        """Удаление манги из истории и архива с подтверждением."""
        entry = self._history.get(url)
        cbz_path = entry.get("cbz_path", "") if entry else ""
        cbz_exists = bool(cbz_path) and Path(cbz_path).exists()

        msg = f'Удалить "{title}" из библиотеки?'
        if cbz_exists:
            msg += f"\n\nАрхив тоже будет удалён:\n{Path(cbz_path).name}"

        reply = QMessageBox.question(
            self,
            "Подтверждение удаления",
            msg,
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if reply != QMessageBox.Yes:
            return

        if cbz_exists:
            try:
                Path(cbz_path).unlink()
                self._append_log(f'🗑️ Архив удалён: {Path(cbz_path).name}')
            except Exception as exc:
                self._append_log(f'⚠️ Не удалось удалить архив: {exc}')

        self._history.delete(url)
        self._refresh_library_list()
        self._append_log(f'📊 "{title}" удалена из библиотеки')

    # -- Проверка обновлений ---------------------------------------------------

    def _start_update_check(self) -> None:
        """Запускает фоновую проверку новых глав для всех тайтлов."""
        entries = self._history.get_all()
        if not entries:
            return
        if self._update_checker and self._update_checker.isRunning():
            return

        self._new_chapters.clear()
        self._append_log("🔄 Проверка обновлений библиотеки...")

        self._update_checker = UpdateChecker(entries, self)
        self._update_checker.result.connect(self._on_update_check_result)
        self._update_checker.finished_all.connect(self._on_update_check_finished)
        self._update_checker.start()

    def _on_update_check_result(self, url: str, total_on_site: int) -> None:
        """Получен результат проверки одного тайтла -- сохраняем данные."""
        entry = self._history.get(url)
        if not entry:
            return
        self._history.update_total(url, total_on_site)
        last_ch = entry.get("last_chapter_downloaded", 0)
        new_count = max(0, total_on_site - last_ch)
        if new_count > 0:
            self._new_chapters[url] = new_count

    def _on_update_check_finished(self) -> None:
        """Все проверки завершены -- обновляем UI один раз."""
        total_new = sum(self._new_chapters.values())
        if total_new > 0:
            self._append_log(f"✅ Найдено новых глав: {total_new}")
        else:
            self._append_log("✅ Библиотека актуальна")
        self._refresh_library_list()
        if self._update_checker is not None:
            self._update_checker.deleteLater()
            self._update_checker = None

    # -- Цветные логи ----------------------------------------------------------

    def _append_log(self, text: str) -> None:
        """Добавляет строку в лог с цветовой разметкой на основе содержимого."""
        if not text or text.isspace():
            self._logs.append("")
            return

        color = self._detect_log_color(text)
        escaped = html.escape(text)
        self._logs.append(
            f'<span style="color:{color};">{escaped}</span>'
        )
        self._logs.moveCursor(QTextCursor.End)

    @staticmethod
    def _detect_log_color(text: str) -> str:
        if "\u274c" in text:  # ❌
            return LOG_COLOR_ERROR
        if "\u26a0" in text:  # ⚠️
            return LOG_COLOR_WARNING
        if "\u2705" in text:  # ✅
            return LOG_COLOR_SUCCESS
        for marker in ("\U0001f4ca", "\U0001f4e5", "\U0001f4e6", "\U0001f4d6",
                       "\U0001f4e1", "\U0001f522", "\U0001f4cd", "\U0001f50d",
                       "\U0001f310", "\U0001f36a", "\U0001f510"):
            if marker in text:
                return LOG_COLOR_INFO
        return LOG_COLOR_DEFAULT

    # -- Слоты UI --------------------------------------------------------------

    def _create_and_start_worker(
        self,
        *,
        initial_url: str | None = None,
        chapter_range: tuple[int, int] | None = None,
        download_mode: str | None = None,
        cbz_path: str | None = None,
        library_mode: bool = False,
    ) -> None:
        """Общая логика создания и запуска воркера."""
        self._btn_start.setEnabled(False)
        self._set_library_buttons_enabled(False)
        self._btn_cancel.show()
        self._progress_bar.setValue(0)
        self._progress_bar.hide()
        self._label_progress.setText("")
        self._last_cbz_path = None

        worker = ChapterWorker()
        if initial_url:
            worker.set_initial_url(initial_url)

        if download_mode:
            worker.set_download_mode(download_mode, cbz_path or "")
        if chapter_range:
            worker.set_chapter_range(*chapter_range)

        if library_mode:
            worker.set_library_mode(True)
        elif download_mode:
            worker.confirm_download()

        worker.download_started.connect(self._on_download_started)
        worker.log.connect(self._append_log)
        worker.finished_ok.connect(self._on_finished)
        worker.chapters_found.connect(self._on_chapters_found)
        worker.manga_info_ready.connect(self._on_manga_info_ready)
        worker.cancellation_info.connect(self._on_cancellation_info)
        worker.chapter_progress.connect(self._on_chapter_progress)
        worker.cbz_ready.connect(self._on_cbz_ready)
        worker.download_complete_info.connect(self._on_download_complete_info)

        self._worker = worker
        worker.start()

    def _on_start(self) -> None:
        self._append_log("▶️ Запуск Manga Downloader (режим браузера)")
        self._append_log("📡 Методы: curl_cffi → cloudscraper → Selenium")
        self._create_and_start_worker()

    def _on_download_selected(self, url: str) -> None:
        """Скачивание манги из библиотеки: сначала диалог, потом воркер."""
        if not url:
            return

        entry = self._history.get(url)
        if not entry:
            return

        title = entry.get("title", url)
        last_chapter = entry.get("last_chapter_downloaded", 0)
        existing_cbz = entry.get("cbz_path", "")
        known_total = entry.get("last_known_total", 0)

        new_count = self._new_chapters.get(url, 0)
        if new_count == 0 and known_total > last_chapter:
            new_count = known_total - last_chapter
        total = last_chapter + new_count if new_count > 0 else known_total
        if total <= 0:
            total = last_chapter

        result = self._show_chapter_dialog(title, total, url, last_chapter, existing_cbz)
        if result is None:
            return

        chapter_range, download_mode, cbz_path = result
        self._append_log(f'▶️ Скачивание из библиотеки: "{title}"')
        self._create_and_start_worker(
            initial_url=url,
            chapter_range=chapter_range,
            download_mode=download_mode,
            cbz_path=cbz_path,
            library_mode=True,
        )

    def _on_cancel(self) -> None:
        if self._worker:
            self._worker.cancel()
            self._append_log("🛑 Отмена...")

    def _on_open_folder(self) -> None:
        """Открывает папку с результатом в файловом менеджере."""
        target = Path(self._last_cbz_path).parent if self._last_cbz_path else OUTPUT_DIR
        target.mkdir(exist_ok=True)
        path_str = str(target.resolve())

        if sys.platform == "win32":
            os.startfile(path_str)
        elif sys.platform == "darwin":
            subprocess.Popen(["open", path_str])
        else:
            subprocess.Popen(["xdg-open", path_str])

    def _on_clear_log(self) -> None:
        self._logs.clear()

    def _on_donate(self) -> None:
        """Показывает диалог с информацией о добровольных пожертвованиях."""
        dialog = DonationDialog(self)
        dialog.setStyleSheet(APP_STYLE)
        dialog.exec()

    def _on_save_log(self) -> None:
        """Сохраняет лог в текстовый файл."""
        path, _ = QFileDialog.getSaveFileName(
            self, "Сохранить лог", "manga_downloader.log", "Text Files (*.txt *.log)",
        )
        if path:
            try:
                with open(path, "w", encoding="utf-8") as f:
                    f.write(self._logs.toPlainText())
                self._append_log(f"📊 Лог сохранён: {path}")
            except Exception as exc:
                self._append_log(f"❌ Ошибка сохранения лога: {exc}")

    # -- Общий диалог выбора глав -----------------------------------------------

    def _show_chapter_dialog(
        self,
        title: str,
        total: int,
        url: str,
        last_chapter: int,
        existing_cbz: str,
    ) -> tuple[tuple[int, int] | None, str, str | None] | None:
        """Показывает диалог выбора глав.

        Возвращает ``(chapter_range, download_mode, cbz_path)`` или ``None``
        если пользователь отменил.
        """
        dialog = ChapterSelectDialog(
            self,
            title=title,
            total_chapters=total,
            url=url,
            last_chapter=last_chapter,
            existing_cbz_path=existing_cbz,
        )
        dialog.setStyleSheet(APP_STYLE)

        if dialog.exec() != ChapterSelectDialog.Accepted:
            return None

        chapter_range = dialog.get_chapter_range()
        download_mode = dialog.get_download_mode()
        cbz_path = dialog.get_existing_cbz_path()

        if dialog.should_delete_old_cbz():
            old_path = Path(existing_cbz)
            if old_path.exists():
                old_path.unlink()
                self._append_log(f"🗑️ Старый архив удалён: {old_path.name}")

        return chapter_range, download_mode, cbz_path

    # -- Слоты от воркера (через сигналы) --------------------------------------

    def _on_download_started(self) -> None:
        self._btn_cancel.show()
        self._progress_bar.show()
        self._append_log("")

    def _on_manga_info_ready(self, total: int, title: str, url: str) -> None:
        """Воркер получил информацию о манге -- показываем диалог выбора глав."""
        if not self._worker:
            return

        last_chapter = 0
        existing_cbz = ""
        entry = self._history.get(url)
        if entry:
            last_chapter = entry.get("last_chapter_downloaded", 0)
            existing_cbz = entry.get("cbz_path", "")

        result = self._show_chapter_dialog(title, total, url, last_chapter, existing_cbz)
        if result is None:
            self._append_log("⏹️ Скачивание отменено.")
            self._worker.cancel()
            return

        chapter_range, download_mode, cbz_path = result
        self._worker.set_download_mode(download_mode, cbz_path)
        if chapter_range:
            self._worker.set_chapter_range(*chapter_range)
        else:
            self._worker.set_chapter_range()

        self._append_log(f'📊 Подтверждено скачивание "{title}"')
        self._worker.confirm_download()

    def _on_chapters_found(self, total: int, title: str, url: str) -> None:
        self._append_log(f'📊 Загружена информация о манге "{title}": {total} глав')

    def _on_chapter_progress(self, current: int, total: int, title: str) -> None:
        self._progress_bar.setMaximum(total)
        self._progress_bar.setValue(current)
        self._progress_bar.setFormat("%v/%m")
        self._label_progress.setText(f"Глава {current}/{total} — {title}")

    def _on_cbz_ready(self, path: str) -> None:
        self._last_cbz_path = path
        self._btn_open_folder.show()

    def _on_download_complete_info(
        self, url: str, title: str, news_id: str, indices_json: str, total_on_site: int,
    ) -> None:
        """Обновляет историю после завершения скачивания."""
        try:
            indices = json.loads(indices_json)
        except (json.JSONDecodeError, TypeError):
            indices = []

        cbz_path = self._last_cbz_path or ""
        self._history.upsert(url, title, news_id, indices, cbz_path, total_on_site)
        self._new_chapters.pop(url, None)

    def _on_cancellation_info(self, skipped: int) -> None:
        self._append_log(f"\n⚠️ Завершено с пропусками ({skipped} глав не скачано)")

    def _on_finished(self, ok: bool) -> None:
        self._btn_start.setEnabled(True)
        self._btn_cancel.hide()
        self._set_library_buttons_enabled(True)

        if self._worker and self._worker.is_cancelled:
            self._append_log("⏹️ Скачивание завершено пользователем.")
            self._progress_bar.hide()
            self._label_progress.setText("")
        elif ok:
            failed = self._worker.failed_count if self._worker else 0
            if failed:
                self._append_log(
                    f"\n⚠️ Завершено с пропусками ({failed} глав не скачано)"
                )
            else:
                self._append_log("\n✅ Скачивание полностью успешно!")
            self._label_progress.setText("Готово!")
        else:
            self._append_log("\n❌ Скачивание завершено с критической ошибкой.")
            self._progress_bar.hide()
            self._label_progress.setText("")

        self._btn_open_folder.setVisible(self._has_output_files())
        self._refresh_library_list()

        app = QApplication.instance()
        if app:
            app.alert(self, 0)
            app.beep()

        self._worker = None
        self._start_update_check()
