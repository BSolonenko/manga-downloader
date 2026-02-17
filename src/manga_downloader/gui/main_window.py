"""
Главное окно приложения Manga Downloader.

Содержит только UI-логику; вся бизнес-логика делегируется ChapterWorker.
Общение с воркером -- исключительно через Qt-сигналы.
"""

from __future__ import annotations

from PyQt5.QtWidgets import (
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QRadioButton,
    QSpinBox,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from manga_downloader.gui.styles import LOG_AREA_STYLE
from manga_downloader.manga.chapter_worker import ChapterWorker


class DownloaderApp(QWidget):
    """Главное окно приложения для скачивания манги.

    Содержит:
    - Кнопку запуска скачивания.
    - Кнопку отмены.
    - Элементы выбора диапазона глав.
    - Область для отображения логов.
    """

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Manga Downloader")
        self.setGeometry(200, 200, 800, 650)

        self._worker: ChapterWorker | None = None
        self._current_manga_url: str | None = None

        self._build_ui()
        self._connect_ui_signals()

    # -- Построение интерфейса -------------------------------------------------

    def _build_ui(self) -> None:
        main_layout = QVBoxLayout(self)

        # Кнопки
        button_layout = QHBoxLayout()
        self._btn_start = QPushButton("🚀 Открыть сайт и начать")
        self._btn_cancel = QPushButton("⏹️ Отмена")
        self._btn_cancel.hide()
        button_layout.addWidget(self._btn_start)
        button_layout.addWidget(self._btn_cancel)
        button_layout.addStretch()

        # Группа выбора глав
        range_group = QGroupBox("Выбор глав")
        range_layout = QVBoxLayout()

        self._radio_all = QRadioButton("Все главы")
        self._radio_all.setChecked(True)
        self._radio_range = QRadioButton("Диапазон глав:")

        mode_layout = QHBoxLayout()
        mode_layout.addWidget(self._radio_all)
        mode_layout.addWidget(self._radio_range)
        mode_layout.addStretch()

        input_layout = QHBoxLayout()
        input_layout.addSpacing(30)

        self._label_start = QLabel("С:")
        self._spin_start = QSpinBox()
        self._spin_start.setMinimum(1)
        self._spin_start.setMaximum(9999)
        self._spin_start.setValue(1)
        self._spin_start.setEnabled(False)

        self._label_end = QLabel("По:")
        self._spin_end = QSpinBox()
        self._spin_end.setMinimum(1)
        self._spin_end.setMaximum(9999)
        self._spin_end.setValue(10)
        self._spin_end.setEnabled(False)

        self._label_info = QLabel("(перейдите на страницу манги для загрузки информации)")
        self._label_info.setStyleSheet("color: gray;")

        input_layout.addWidget(self._label_start)
        input_layout.addWidget(self._spin_start)
        input_layout.addWidget(self._label_end)
        input_layout.addWidget(self._spin_end)
        input_layout.addWidget(self._label_info)
        input_layout.addStretch()

        range_layout.addLayout(mode_layout)
        range_layout.addLayout(input_layout)
        range_group.setLayout(range_layout)

        # Логи
        self._logs = QTextEdit(readOnly=True)
        self._logs.setStyleSheet(LOG_AREA_STYLE)

        main_layout.addLayout(button_layout)
        main_layout.addWidget(range_group)
        main_layout.addWidget(self._logs)

    def _connect_ui_signals(self) -> None:
        self._btn_start.clicked.connect(self._on_start)
        self._btn_cancel.clicked.connect(self._on_cancel)
        self._radio_all.toggled.connect(self._on_range_mode_changed)
        self._radio_range.toggled.connect(self._on_range_mode_changed)
        self._spin_start.valueChanged.connect(self._on_range_values_changed)
        self._spin_end.valueChanged.connect(self._on_range_values_changed)

    # -- Слоты UI --------------------------------------------------------------

    def _on_range_mode_changed(self) -> None:
        is_range = self._radio_range.isChecked()
        self._spin_start.setEnabled(is_range)
        self._spin_end.setEnabled(is_range)

        if self._worker:
            if is_range:
                self._worker.set_chapter_range(
                    self._spin_start.value(), self._spin_end.value(),
                )
            else:
                self._worker.set_chapter_range()

    def _on_range_values_changed(self) -> None:
        if self._worker and self._radio_range.isChecked():
            self._worker.set_chapter_range(
                self._spin_start.value(), self._spin_end.value(),
            )

    def _on_start(self) -> None:
        self._btn_start.setEnabled(False)
        self._logs.append("▶️ Запуск Manga Downloader")
        self._logs.append("📡 Методы: curl_cffi → cloudscraper → Selenium")

        worker = ChapterWorker()

        # Подключаем сигналы воркера
        worker.download_started.connect(self._on_download_started)
        worker.log.connect(self._logs.append)
        worker.finished_ok.connect(self._on_finished)
        worker.chapters_found.connect(self._on_chapters_found)
        worker.range_updated.connect(self._on_range_updated)
        worker.cancellation_info.connect(self._on_cancellation_info)

        if self._radio_range.isChecked():
            worker.set_chapter_range(
                self._spin_start.value(), self._spin_end.value(),
            )

        self._worker = worker
        worker.start()

    def _on_cancel(self) -> None:
        if self._worker:
            self._worker.cancel()
            self._logs.append("🛑 Отмена...")

    # -- Слоты от воркера (через сигналы) --------------------------------------

    def _on_download_started(self) -> None:
        self._btn_cancel.show()
        self._logs.append("")

    def _on_chapters_found(self, total: int, title: str, url: str) -> None:
        self._current_manga_url = url
        self._label_info.setText(f"(всего глав: {total})")
        self._spin_start.setMaximum(total)
        self._spin_end.setMaximum(total)
        self._spin_end.setValue(total)
        self._logs.append(f'📊 Загружена информация о манге "{title}": {total} глав')

        if self._worker and self._radio_range.isChecked():
            self._worker.set_chapter_range(
                self._spin_start.value(), self._spin_end.value(),
            )

    def _on_range_updated(self, start: int, end: int) -> None:
        self._spin_start.setValue(start)
        self._spin_end.setValue(end)
        self._radio_range.setChecked(True)
        self._logs.append(f"📊 Используется сохраненный диапазон глав: {start}-{end}")

    def _on_cancellation_info(self, skipped: int) -> None:
        self._logs.append(f"\n⚠️ Завершено с пропусками ({skipped} глав не скачано)")

    def _on_finished(self, ok: bool) -> None:
        self._btn_start.setEnabled(True)
        self._btn_cancel.hide()

        if self._worker and self._worker.is_cancelled:
            self._logs.append("⏹️ Скачивание завершено пользователем.")
        elif ok:
            failed = self._worker.failed_count if self._worker else 0
            if failed:
                self._logs.append(
                    f"\n⚠️ Завершено с пропусками ({failed} глав не скачано)"
                )
            else:
                self._logs.append("\n✅ Скачивание полностью успешно!")
        else:
            self._logs.append("\n❌ Скачивание завершено с критической ошибкой.")

        self._worker = None
