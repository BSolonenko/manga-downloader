"""
Централизованное управление Chrome WebDriver.

Единая точка создания драйвера для всех модулей приложения.
Обрабатывает типичные ошибки и выдаёт понятные сообщения пользователю.
"""

from __future__ import annotations

import logging

from selenium import webdriver
from selenium.common.exceptions import (
    SessionNotCreatedException,
    WebDriverException,
)
from selenium.webdriver.chrome.options import Options

from manga_downloader.config import USER_AGENT

logger = logging.getLogger(__name__)


class ChromeDriverError(Exception):
    """Не удалось запустить Chrome WebDriver."""


def create_chrome_driver(*, detach: bool = False) -> webdriver.Chrome:
    """Создаёт Chrome WebDriver с единой конфигурацией.

    Args:
        detach: ``True`` — браузер остаётся после завершения драйвера,
                ``False`` — закрывается вместе с ним.

    Raises:
        ChromeDriverError: Chrome не найден, драйвер не скачан и т.д.
    """
    options = Options()
    options.add_argument(f"--user-agent={USER_AGENT}")
    options.add_argument("--log-level=3")
    options.add_experimental_option("detach", detach)
    options.add_experimental_option("excludeSwitches", ["enable-logging"])

    try:
        return webdriver.Chrome(options=options)
    except SessionNotCreatedException as exc:
        _raise_with_hint("Версия ChromeDriver несовместима с установленным Chrome.", exc)
    except WebDriverException as exc:
        msg = str(exc)
        if "unable to obtain" in msg.lower() or "cannot find" in msg.lower():
            _raise_with_hint(
                "Не удалось получить ChromeDriver автоматически.",
                exc,
            )
        _raise_with_hint("Ошибка запуска Chrome.", exc)
    except Exception as exc:
        _raise_with_hint("Непредвиденная ошибка при запуске Chrome.", exc)


def _raise_with_hint(summary: str, cause: Exception) -> None:
    logger.error("%s — %s", summary, cause)
    hint = (
        f"{summary}\n"
        "Возможные причины:\n"
        "  • Google Chrome не установлен или устарел — обновите до последней версии.\n"
        "  • Нет доступа в интернет — ChromeDriver скачивается автоматически.\n"
        "  • Антивирус блокирует chromedriver.exe — добавьте исключение."
    )
    raise ChromeDriverError(hint) from cause
