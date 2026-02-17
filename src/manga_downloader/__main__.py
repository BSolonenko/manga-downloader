"""
Точка входа: ``python -m manga_downloader``.
"""

import sys

from PyQt5.QtWidgets import QApplication

from manga_downloader.gui import DownloaderApp


def main() -> None:
    app = QApplication(sys.argv)
    window = DownloaderApp()
    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
