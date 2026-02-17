"""
Диалог с информацией о добровольных пожертвованиях.

Объясняет, что программа полностью бесплатна, а чаевые —
это добровольный взнос, не дающий никаких привилегий.
"""

from __future__ import annotations

from PyQt5.QtCore import Qt, QUrl
from PyQt5.QtGui import QDesktopServices
from PyQt5.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
)

DONATE_URL = "https://ko-fi.com/noxorium"


class DonationDialog(QDialog):
    """Модальное окно с предложением поддержать разработчика."""

    def __init__(self, parent: object | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Поддержать автора")
        self.setFixedWidth(460)
        self.setWindowFlags(
            self.windowFlags() & ~Qt.WindowContextHelpButtonHint
        )
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setSpacing(14)
        layout.setContentsMargins(28, 24, 28, 22)

        # --- Иконка ---
        icon_label = QLabel("☕")
        icon_label.setObjectName("donate_icon")
        icon_label.setAlignment(Qt.AlignCenter)

        # --- Заголовок ---
        title_label = QLabel("Угостить автора кофе")
        title_label.setObjectName("donate_title")
        title_label.setAlignment(Qt.AlignCenter)

        # --- Текст ---
        text_label = QLabel(
            'Manga Downloader — полностью <span style="color:#28a745; '
            'font-weight:bold;">бесплатная</span> программа '
            "и такой останется навсегда.<br><br>"
            'Это <span style="color:#ff813f; '
            'font-weight:bold;">добровольный</span> взнос, который не даёт '
            '<span style="color:#888888; font-style:italic;">'
            "никаких дополнительных привилегий или функций</span>. "
            "Это просто способ сказать «спасибо» и поддержать "
            "дальнейшую разработку.<br><br>"
            "А ещё автор очень любит кофе, и каждая чашечка "
            "превращается в новые фичи и баг-фиксы ☕💛"
        )
        text_label.setObjectName("donate_text")
        text_label.setTextFormat(Qt.RichText)
        text_label.setWordWrap(True)
        text_label.setAlignment(Qt.AlignCenter)

        # --- Кнопки ---
        btn_row = QHBoxLayout()
        btn_row.setSpacing(12)

        btn_cancel = QPushButton("Не сейчас")
        btn_cancel.setObjectName("btn_donate_cancel")
        btn_cancel.setCursor(Qt.PointingHandCursor)

        btn_confirm = QPushButton("☕  Угостить кофе")
        btn_confirm.setObjectName("btn_donate_confirm")
        btn_confirm.setCursor(Qt.PointingHandCursor)
        btn_confirm.setDefault(True)

        btn_row.addStretch()
        btn_row.addWidget(btn_cancel)
        btn_row.addWidget(btn_confirm)
        btn_row.addStretch()

        # --- Сборка ---
        layout.addWidget(icon_label)
        layout.addWidget(title_label)
        layout.addSpacing(4)
        layout.addWidget(text_label)
        layout.addSpacing(6)
        layout.addLayout(btn_row)

        # --- Сигналы ---
        btn_cancel.clicked.connect(self.reject)
        btn_confirm.clicked.connect(self._open_donate_page)

    def _open_donate_page(self) -> None:
        """Открывает страницу доната в браузере и закрывает диалог."""
        QDesktopServices.openUrl(QUrl(DONATE_URL))
        self.accept()
