"""
QSS-стили для приложения Manga Downloader.

Полная тёмная тема для всех виджетов.
"""

# -- Палитра ------------------------------------------------------------------
_BG_DARK = "#1e1e1e"
_BG_MID = "#2b2b2b"
_BG_LIGHT = "#333333"
_BG_INPUT = "#3c3c3c"
_BORDER = "#555555"
_BORDER_FOCUS = "#6a9eda"
_TEXT = "#d4d4d4"
_TEXT_DIM = "#888888"
_TEXT_BRIGHT = "#ffffff"

_GREEN = "#28a745"
_GREEN_HOVER = "#2fbf50"
_GREEN_PRESSED = "#1e8c38"

_RED = "#dc3545"
_RED_HOVER = "#e8505e"
_RED_PRESSED = "#b52d3a"

_BLUE = "#3a86c8"
_BLUE_HOVER = "#4a96d8"
_BLUE_PRESSED = "#2a76b8"

_ACCENT = "#6a9eda"

_ORANGE = "#ff813f"
_ORANGE_HOVER = "#ff9a5c"
_ORANGE_PRESSED = "#e06a2a"

# -- Общие стили приложения ---------------------------------------------------
APP_STYLE = f"""
QWidget {{
    background-color: {_BG_MID};
    color: {_TEXT};
    font-family: "Segoe UI", sans-serif;
    font-size: 10pt;
}}

/* --- Кнопки --- */
QPushButton {{
    background-color: {_BG_LIGHT};
    color: {_TEXT_BRIGHT};
    border: 1px solid {_BORDER};
    border-radius: 6px;
    padding: 8px 18px;
    font-weight: bold;
    min-height: 20px;
}}
QPushButton:hover {{
    background-color: {_BG_INPUT};
    border-color: {_ACCENT};
}}
QPushButton:pressed {{
    background-color: {_BG_DARK};
}}
QPushButton:disabled {{
    background-color: {_BG_DARK};
    color: {_TEXT_DIM};
    border-color: {_BG_LIGHT};
}}

QPushButton#btn_start {{
    background-color: {_GREEN};
    border-color: {_GREEN};
}}
QPushButton#btn_start:hover {{
    background-color: {_GREEN_HOVER};
    border-color: {_GREEN_HOVER};
}}
QPushButton#btn_start:pressed {{
    background-color: {_GREEN_PRESSED};
}}
QPushButton#btn_start:disabled {{
    background-color: #1a5c2a;
    color: {_TEXT_DIM};
    border-color: #1a5c2a;
}}

QPushButton#btn_cancel {{
    background-color: {_RED};
    border-color: {_RED};
}}
QPushButton#btn_cancel:hover {{
    background-color: {_RED_HOVER};
    border-color: {_RED_HOVER};
}}
QPushButton#btn_cancel:pressed {{
    background-color: {_RED_PRESSED};
}}

QPushButton#btn_open_folder {{
    background-color: {_BLUE};
    border-color: {_BLUE};
}}
QPushButton#btn_open_folder:hover {{
    background-color: {_BLUE_HOVER};
    border-color: {_BLUE_HOVER};
}}
QPushButton#btn_open_folder:pressed {{
    background-color: {_BLUE_PRESSED};
}}

QPushButton#btn_clear_log {{
    background-color: transparent;
    border: 1px solid {_BORDER};
    border-radius: 4px;
    padding: 4px 10px;
    font-size: 9pt;
    font-weight: normal;
    min-height: 16px;
}}
QPushButton#btn_clear_log:hover {{
    background-color: {_BG_LIGHT};
    border-color: {_ACCENT};
}}

/* --- Группы --- */
QGroupBox {{
    background-color: {_BG_DARK};
    border: 1px solid {_BORDER};
    border-radius: 8px;
    margin-top: 14px;
    padding: 16px 12px 10px 12px;
    font-weight: bold;
    font-size: 10pt;
}}
QGroupBox::title {{
    subcontrol-origin: margin;
    subcontrol-position: top left;
    padding: 2px 10px;
    color: {_ACCENT};
}}

/* --- Радио-кнопки --- */
QRadioButton {{
    spacing: 6px;
    color: {_TEXT};
}}
QRadioButton::indicator {{
    width: 16px;
    height: 16px;
    border-radius: 8px;
    border: 2px solid {_BORDER};
    background-color: {_BG_INPUT};
}}
QRadioButton::indicator:checked {{
    background-color: {_ACCENT};
    border-color: {_ACCENT};
}}
QRadioButton::indicator:hover {{
    border-color: {_ACCENT};
}}

/* --- Спинбоксы --- */
QSpinBox {{
    background-color: {_BG_INPUT};
    color: {_TEXT_BRIGHT};
    border: 1px solid {_BORDER};
    border-radius: 4px;
    padding: 4px 8px;
    min-width: 60px;
}}
QSpinBox:focus {{
    border-color: {_BORDER_FOCUS};
}}
QSpinBox:disabled {{
    background-color: {_BG_DARK};
    color: {_TEXT_DIM};
    border-color: {_BG_LIGHT};
}}
QSpinBox::up-button, QSpinBox::down-button {{
    background-color: {_BG_LIGHT};
    border: none;
    width: 18px;
}}
QSpinBox::up-button:hover, QSpinBox::down-button:hover {{
    background-color: {_BG_INPUT};
}}
QSpinBox::up-arrow {{
    image: none;
    border-left: 4px solid transparent;
    border-right: 4px solid transparent;
    border-bottom: 5px solid {_TEXT};
    width: 0;
    height: 0;
}}
QSpinBox::down-arrow {{
    image: none;
    border-left: 4px solid transparent;
    border-right: 4px solid transparent;
    border-top: 5px solid {_TEXT};
    width: 0;
    height: 0;
}}

/* --- Метки --- */
QLabel {{
    background-color: transparent;
    color: {_TEXT};
}}
QLabel#label_info {{
    color: {_TEXT_DIM};
    font-style: italic;
}}
QLabel#label_section_library {{
    color: {_TEXT};
    font-size: 10pt;
    font-weight: bold;
    padding: 2px 0;
}}
QLabel#label_progress {{
    color: {_TEXT_DIM};
    font-size: 9pt;
}}

/* --- Лог-область --- */
QTextEdit#logs {{
    font-family: Consolas, "Courier New", Monospace;
    font-size: 10pt;
    background-color: {_BG_DARK};
    color: {_TEXT};
    border: 1px solid {_BORDER};
    border-radius: 6px;
    padding: 6px;
    selection-background-color: {_ACCENT};
    selection-color: {_TEXT_BRIGHT};
}}

/* --- Прогресс-бар --- */
QProgressBar {{
    background-color: {_BG_DARK};
    border: 1px solid {_BORDER};
    border-radius: 6px;
    text-align: center;
    color: {_TEXT_BRIGHT};
    font-weight: bold;
    font-size: 9pt;
    min-height: 22px;
    max-height: 22px;
}}
QProgressBar::chunk {{
    background-color: {_GREEN};
    border-radius: 5px;
}}

/* --- Список (библиотека) --- */
QListWidget {{
    background-color: {_BG_DARK};
    color: {_TEXT};
    border: 1px solid {_BORDER};
    border-radius: 6px;
    padding: 4px;
    outline: none;
}}
QListWidget::item {{
    padding: 6px 8px;
    border-radius: 4px;
    border: none;
}}
QListWidget::item:selected {{
    background-color: {_ACCENT};
    color: {_TEXT_BRIGHT};
}}
QListWidget::item:hover:!selected {{
    background-color: {_BG_LIGHT};
}}

/* --- Кнопка сохранения лога --- */
QPushButton#btn_save_log {{
    background-color: transparent;
    border: 1px solid {_BORDER};
    border-radius: 4px;
    padding: 4px 10px;
    font-size: 9pt;
    font-weight: normal;
    min-height: 16px;
}}
QPushButton#btn_save_log:hover {{
    background-color: {_BG_LIGHT};
    border-color: {_ACCENT};
}}

/* --- Кнопки в строках библиотеки --- */
QLabel#library_item_label {{
    background-color: transparent;
    color: {_TEXT};
    font-size: 9pt;
    padding: 0;
}}
QLabel#badge_new_chapters {{
    background-color: {_GREEN};
    color: {_TEXT_BRIGHT};
    font-size: 8pt;
    font-weight: bold;
    border-radius: 8px;
    padding: 1px 6px;
    min-width: 16px;
    max-height: 18px;
}}
QPushButton#btn_lib_download {{
    background-color: {_GREEN};
    color: {_TEXT_BRIGHT};
    border: none;
    border-radius: 4px;
    padding: 3px 10px;
    font-size: 8pt;
    font-weight: bold;
    min-height: 14px;
    max-height: 22px;
}}
QPushButton#btn_lib_download:hover {{
    background-color: {_GREEN_HOVER};
}}
QPushButton#btn_lib_download:pressed {{
    background-color: {_GREEN_PRESSED};
}}
QPushButton#btn_lib_download:disabled {{
    background-color: #1a5c2a;
    color: {_TEXT_DIM};
}}
QPushButton#btn_lib_delete {{
    background-color: transparent;
    color: {_RED};
    border: 1px solid {_BORDER};
    border-radius: 4px;
    padding: 2px 6px;
    font-size: 9pt;
    font-weight: bold;
    min-height: 14px;
    max-height: 22px;
    min-width: 22px;
    max-width: 22px;
}}
QPushButton#btn_lib_delete:hover {{
    background-color: {_RED};
    color: {_TEXT_BRIGHT};
    border-color: {_RED};
}}
QPushButton#btn_lib_delete:pressed {{
    background-color: {_RED_PRESSED};
}}
QPushButton#btn_lib_delete:disabled {{
    color: {_TEXT_DIM};
    border-color: {_BG_LIGHT};
}}

/* --- Диалог выбора глав --- */
QDialog {{
    background-color: {_BG_MID};
}}
QLabel#dialog_manga_title {{
    color: {_ACCENT};
    font-size: 12pt;
    font-weight: bold;
}}
QLabel#dialog_manga_details {{
    color: {_TEXT_DIM};
    font-size: 9pt;
}}
QLabel#dialog_hint {{
    color: {_GREEN};
    font-size: 9pt;
    padding: 4px 0;
}}
QLabel#dialog_warning {{
    color: {_RED};
    font-size: 9pt;
    font-weight: bold;
    padding: 4px 30px;
}}

/* --- Скроллбары --- */
QScrollBar:vertical {{
    background-color: {_BG_DARK};
    width: 10px;
    margin: 0;
    border: none;
    border-radius: 5px;
}}
QScrollBar::handle:vertical {{
    background-color: {_BORDER};
    min-height: 30px;
    border-radius: 5px;
}}
QScrollBar::handle:vertical:hover {{
    background-color: {_TEXT_DIM};
}}
QScrollBar::add-line:vertical,
QScrollBar::sub-line:vertical {{
    height: 0;
    border: none;
}}
QScrollBar::add-page:vertical,
QScrollBar::sub-page:vertical {{
    background: none;
}}

QScrollBar:horizontal {{
    background-color: {_BG_DARK};
    height: 10px;
    margin: 0;
    border: none;
    border-radius: 5px;
}}
QScrollBar::handle:horizontal {{
    background-color: {_BORDER};
    min-width: 30px;
    border-radius: 5px;
}}
QScrollBar::handle:horizontal:hover {{
    background-color: {_TEXT_DIM};
}}
QScrollBar::add-line:horizontal,
QScrollBar::sub-line:horizontal {{
    width: 0;
    border: none;
}}
QScrollBar::add-page:horizontal,
QScrollBar::sub-page:horizontal {{
    background: none;
}}

/* --- Кнопка доната --- */
QPushButton#btn_donate {{
    background-color: {_ORANGE};
    border-color: {_ORANGE};
    padding: 8px 14px;
    font-size: 10pt;
}}
QPushButton#btn_donate:hover {{
    background-color: {_ORANGE_HOVER};
    border-color: {_ORANGE_HOVER};
}}
QPushButton#btn_donate:pressed {{
    background-color: {_ORANGE_PRESSED};
}}

/* --- Диалог доната --- */
QLabel#donate_icon {{
    font-size: 36pt;
    background-color: transparent;
    padding: 0;
}}
QLabel#donate_title {{
    color: {_ORANGE};
    font-size: 14pt;
    font-weight: bold;
    background-color: transparent;
}}
QLabel#donate_text {{
    color: {_TEXT};
    font-size: 10pt;
    background-color: transparent;
    line-height: 150%;
}}
QPushButton#btn_donate_confirm {{
    background-color: {_ORANGE};
    border-color: {_ORANGE};
    padding: 10px 28px;
    font-size: 11pt;
}}
QPushButton#btn_donate_confirm:hover {{
    background-color: {_ORANGE_HOVER};
    border-color: {_ORANGE_HOVER};
}}
QPushButton#btn_donate_confirm:pressed {{
    background-color: {_ORANGE_PRESSED};
}}
QPushButton#btn_donate_cancel {{
    background-color: transparent;
    border: 1px solid {_BORDER};
    border-radius: 6px;
    padding: 10px 22px;
    font-size: 10pt;
    font-weight: normal;
    color: {_TEXT_DIM};
}}
QPushButton#btn_donate_cancel:hover {{
    background-color: {_BG_LIGHT};
    border-color: {_ACCENT};
    color: {_TEXT};
}}
"""

# -- Цвета для логов (используются в main_window._append_log) ----------------
LOG_COLOR_ERROR = "#ff6b6b"
LOG_COLOR_WARNING = "#ffa94d"
LOG_COLOR_SUCCESS = "#69db7c"
LOG_COLOR_INFO = "#74c0fc"
LOG_COLOR_DEFAULT = _TEXT
