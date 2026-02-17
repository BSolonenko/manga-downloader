"""
Модальный диалог выбора глав перед скачиванием.

Показывает информацию о манге, позволяет выбрать диапазон глав
и режим скачивания (новый архив / дополнить существующий).
"""

from __future__ import annotations

from pathlib import Path

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QDialog,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QRadioButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)


class ChapterSelectDialog(QDialog):
    """Модальное окно выбора глав и режима скачивания."""

    def __init__(
        self,
        parent: object | None = None,
        *,
        title: str = "",
        total_chapters: int = 0,
        url: str = "",
        last_chapter: int = 0,
        existing_cbz_path: str = "",
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("Выбор глав для скачивания")
        self.setMinimumWidth(500)
        self.setWindowFlags(
            self.windowFlags() & ~Qt.WindowContextHelpButtonHint
        )

        self._total = total_chapters
        self._existing_cbz_path = existing_cbz_path
        self._cbz_exists = bool(existing_cbz_path) and Path(existing_cbz_path).exists()

        self._build_ui(title, total_chapters, url, last_chapter)

    # -- Построение UI ---------------------------------------------------------

    def _build_ui(
        self,
        title: str,
        total: int,
        url: str,
        last_chapter: int,
    ) -> None:
        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(16, 16, 16, 16)

        # --- Информация о манге ---
        info_group = QGroupBox("Информация о манге")
        info_layout = QVBoxLayout()
        info_layout.setSpacing(4)

        lbl_title = QLabel(title)
        lbl_title.setObjectName("dialog_manga_title")
        lbl_title.setWordWrap(True)

        lbl_details = QLabel(f"Глав на сайте: {total}  |  {url}")
        lbl_details.setWordWrap(True)
        lbl_details.setObjectName("dialog_manga_details")

        info_layout.addWidget(lbl_title)
        info_layout.addWidget(lbl_details)
        info_group.setLayout(info_layout)

        # --- Выбор глав ---
        range_group = QGroupBox("Выбор глав")
        range_layout = QVBoxLayout()

        self._radio_all = QRadioButton("Все главы (новый архив)")
        self._radio_all.setChecked(False)
        self._radio_range = QRadioButton("Диапазон глав:")
        self._radio_range.setChecked(False)

        mode_row = QHBoxLayout()
        mode_row.addWidget(self._radio_all)
        mode_row.addWidget(self._radio_range)
        mode_row.addStretch()

        spin_row = QHBoxLayout()
        spin_row.addSpacing(30)

        self._spin_start = QSpinBox()
        self._spin_start.setMinimum(1)
        self._spin_start.setMaximum(max(total, 1))
        self._spin_start.setValue(1)
        self._spin_start.setEnabled(False)

        self._spin_end = QSpinBox()
        self._spin_end.setMinimum(1)
        self._spin_end.setMaximum(max(total, 1))
        self._spin_end.setValue(total or 1)
        self._spin_end.setEnabled(False)

        self._label_info = QLabel(f"(всего глав: {total})")
        self._label_info.setObjectName("label_info")

        spin_row.addWidget(QLabel("С:"))
        spin_row.addWidget(self._spin_start)
        spin_row.addWidget(QLabel("По:"))
        spin_row.addWidget(self._spin_end)
        spin_row.addWidget(self._label_info)
        spin_row.addStretch()

        range_layout.addLayout(mode_row)
        range_layout.addLayout(spin_row)

        # --- Режим архива (только для диапазона + существующий архив) ---
        self._mode_container = QVBoxLayout()
        self._mode_container.setSpacing(4)

        mode_dl_row = QHBoxLayout()
        mode_dl_row.addSpacing(30)

        self._radio_mode_new = QRadioButton("Новый архив")
        self._radio_mode_new.setChecked(False)
        self._radio_mode_append = QRadioButton("Дополнить существующий")
        self._radio_mode_append.setChecked(False)

        mode_dl_row.addWidget(QLabel("Режим:"))
        mode_dl_row.addWidget(self._radio_mode_new)
        mode_dl_row.addWidget(self._radio_mode_append)
        mode_dl_row.addStretch()

        self._mode_widget = self._wrap_layout(mode_dl_row)
        self._mode_container.addWidget(self._mode_widget)

        # Предупреждение о перезаписи
        self._warning_label = QLabel(
            "⚠️ Существующий архив будет удалён и создан заново!"
        )
        self._warning_label.setObjectName("dialog_warning")
        self._warning_label.setWordWrap(True)
        self._warning_label.hide()
        self._mode_container.addWidget(self._warning_label)

        range_layout.addLayout(self._mode_container)

        # --- Подсказка о докачке ---
        has_new = last_chapter > 0 and last_chapter < total

        self._hint_label = QLabel("")
        self._hint_label.setObjectName("dialog_hint")
        self._hint_label.setWordWrap(True)
        self._hint_label.hide()

        if has_new:
            self._hint_label.setText(
                f"💡 Ранее скачано до главы {last_chapter}. "
                f"Предложен диапазон {last_chapter + 1}–{total}."
            )
            self._hint_label.show()

        range_layout.addWidget(self._hint_label)
        range_group.setLayout(range_layout)

        # --- Кнопки ---
        btn_row = QHBoxLayout()
        btn_row.addStretch()

        self._btn_cancel = QPushButton("Отмена")
        self._btn_cancel.setObjectName("btn_cancel")

        self._btn_download = QPushButton("  Скачать")
        self._btn_download.setObjectName("btn_start")
        self._btn_download.setDefault(True)

        btn_row.addWidget(self._btn_cancel)
        btn_row.addWidget(self._btn_download)

        # --- Сборка ---
        layout.addWidget(info_group)
        layout.addWidget(range_group)
        layout.addLayout(btn_row)

        # --- Сигналы ---
        self._radio_all.toggled.connect(self._on_chapter_mode_changed)
        self._radio_range.toggled.connect(self._on_chapter_mode_changed)
        self._radio_mode_new.toggled.connect(self._on_archive_mode_changed)
        self._radio_mode_append.toggled.connect(self._on_archive_mode_changed)
        self._btn_download.clicked.connect(self.accept)
        self._btn_cancel.clicked.connect(self.reject)

        # --- Установка дефолтов ---
        if has_new:
            self._radio_range.setChecked(True)
            self._spin_start.setValue(last_chapter + 1)
            self._spin_end.setValue(total)
        else:
            self._radio_all.setChecked(True)

        # Принудительно обновить видимость секции режима
        self._on_chapter_mode_changed()

    # -- Вспомогательные -------------------------------------------------------

    @staticmethod
    def _wrap_layout(lay: QHBoxLayout) -> QWidget:
        """Оборачивает layout в виджет для удобного show/hide."""
        w = QWidget()
        w.setLayout(lay)
        return w

    # -- Слоты -----------------------------------------------------------------

    def _on_chapter_mode_changed(self) -> None:
        is_range = self._radio_range.isChecked()
        self._spin_start.setEnabled(is_range)
        self._spin_end.setEnabled(is_range)

        if is_range and self._cbz_exists:
            # Диапазон + архив есть → показать выбор режима, дефолт "Дополнить"
            self._mode_widget.show()
            self._radio_mode_append.setChecked(True)
        else:
            # Все главы или диапазон без архива → скрыть, всегда новый
            self._mode_widget.hide()
            self._radio_mode_new.setChecked(True)

        self._update_warning()

    def _on_archive_mode_changed(self) -> None:
        self._update_warning()

    def _update_warning(self) -> None:
        """Показывает предупреждение если будет создан новый архив при существующем."""
        will_overwrite = self._cbz_exists and (
            self._radio_all.isChecked()
            or (self._radio_range.isChecked() and self._radio_mode_new.isChecked())
        )
        self._warning_label.setVisible(will_overwrite)

    # -- Публичный API ---------------------------------------------------------

    def get_chapter_range(self) -> tuple[int, int] | None:
        """Возвращает ``(start, end)`` или ``None`` если выбраны все главы."""
        if self._radio_all.isChecked():
            return None
        return (self._spin_start.value(), self._spin_end.value())

    def get_download_mode(self) -> str:
        """Возвращает ``'new'`` или ``'append'``."""
        if self._radio_all.isChecked():
            return "new"
        if self._radio_mode_append.isChecked() and self._cbz_exists:
            return "append"
        return "new"

    def get_existing_cbz_path(self) -> str | None:
        """Возвращает путь к CBZ для дополнения, или ``None``."""
        if self.get_download_mode() == "append" and self._existing_cbz_path:
            return self._existing_cbz_path
        return None

    def should_delete_old_cbz(self) -> bool:
        """``True`` если будет создан новый архив при существующем."""
        if not self._cbz_exists:
            return False
        if self._radio_all.isChecked():
            return True
        return self._radio_mode_new.isChecked()
