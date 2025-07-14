import sys
import re
import json
import os
import zipfile
import shutil
import requests
import time
from pathlib import Path

from PyQt5.QtWidgets import QApplication, QWidget, QVBoxLayout, QPushButton, QTextEdit
from PyQt5.QtCore import QThread, pyqtSignal

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By

class MangaDownloader(QThread):
    log = pyqtSignal(str)
    finished = pyqtSignal(bool)
    download_started = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.url = None
        self.cookies = None
        self.cookie_file = Path("comx_life_cookies_v2.json")
        self.headers = {
            "Referer": "https://comx.life/",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
        }
        self._is_cancelled = False

    def run(self):
        self.cleanup()
        try:
            self.log.emit("🌐 Открытие браузера...")
            driver = self._open_browser_with_cookies()
            if driver:
                self.log.emit("🔎 Запуск отслеживания страницы манги...")
                self._auto_download_if_manga_page(driver)
        except Exception as e:
            self.log.emit(f"❌ Ошибка: {e}")
            self.finished.emit(False)

    def cancel(self):
        self._is_cancelled = True

    def cleanup(self):
        for dir_name in ["downloads", "combined_cbz_temp"]:
            dir_path = Path(dir_name)
            if dir_path.exists():
                shutil.rmtree(dir_path)
                self.log.emit(f"🧹 Очищено: {dir_name}")

    def _open_browser_with_cookies(self):
        options = Options()
        options.add_experimental_option("detach", True)
        driver = webdriver.Chrome(options=options)

        driver.get("https://comx.life/")

        if self.cookie_file.exists():
            self.log.emit("🍪 Пробую восстановить сессию...")
            with open(self.cookie_file, "r", encoding="utf-8") as f:
                cookies = json.load(f)

            driver.delete_all_cookies()
            for c in cookies:
                c.pop("sameSite", None)
                try:
                    driver.add_cookie(c)
                except Exception as e:
                    self.log.emit(f"⚠️ Cookie {c.get('name')} не добавлен: {e}")

            driver.refresh()
            time.sleep(2)
            if driver.get_cookie("dle_user_id"):
                self.cookies = driver.get_cookies()
                self.log.emit("✅ Авторизация восстановлена!")
                return driver
            self.log.emit("⚠️ Сессия устарела, нужна новая авторизация")

        self.log.emit("🔐 Войдите вручную, я запомню cookies")
        self.log.emit("📦 Ожидание страницы манги...")

        while not driver.get_cookie("dle_user_id"):
            if self._is_cancelled:
                driver.quit()
                self.finished.emit(False)
                return None
            time.sleep(1)

        self.cookies = driver.get_cookies()
        with open(self.cookie_file, "w", encoding="utf-8") as f:
            json.dump(self.cookies, f, indent=2, ensure_ascii=False)

        return driver

    def _auto_download_if_manga_page(self, driver):
        processed_url = None

        while not self._is_cancelled:
            try:
                current_url = driver.current_url
                if current_url and current_url.endswith('/download'):
                    self.url = current_url.replace('/download', '')
                    self.log.emit(f"📍 Начинаем скачивание манги: {self.url}")
                    driver.quit()
                    self.download_manga()
                    self.finished.emit(True)
                    return

                elif current_url and "/" in current_url and ".html" in current_url and current_url != processed_url:
                    self.log.emit(f"🔍 Проверка страницы: {current_url}")
                    try:
                        btn = driver.find_element(By.CSS_SELECTOR, 'a.page__btn-track.js-follow-status')
                        driver.execute_script('''
                            arguments[0].textContent = '⬇️ Скачать';
                            arguments[0].style.backgroundColor = '#28a745';
                            arguments[0].style.color = '#fff';
                            arguments[0].style.fontWeight = 'bold';
                            arguments[0].onclick = () => { window.location.href += '/download'; };
                        ''', btn)
                        self.log.emit("✅ Кнопка заменена на 'Скачать'")
                        processed_url = current_url
                    except Exception as e:
                        self.log.emit(f"⚠️ Кнопка не найдена: {e}")

                time.sleep(0.1)

            except Exception as e:
                self.log.emit(f"❌ Ошибка: {e}")
                driver.quit()
                self.finished.emit(False)
                return

    def download_manga(self):
        if not self.cookies:
            self.log.emit("⚠️ Предупреждение: cookies не заданы — загружаю из файла")
            try:
                with open(self.cookie_file, "r", encoding="utf-8") as f:
                    raw = json.load(f)
                    self.cookies = raw if isinstance(raw, list) else [
                        {"name": k, "value": v} for k, v in raw.items()
                    ]
            except Exception as e:
                self.log.emit(f"❌ Не удалось загрузить cookies из файла: {e}")
                return

        self.download_started.emit()
        self.log.emit(f"📥 Скачивание HTML: {self.url}")
        resp = requests.get(self.url, headers=self.headers, cookies={c['name']: c['value'] for c in self.cookies})
        html = resp.text

        match = re.search(r'window\.__DATA__\s*=\s*({.*?})\s*;', html, re.DOTALL)
        if not match:
            self.log.emit("❌ Не найден window.__DATA__")
            return

        data = json.loads(match.group(1))
        chapters = data["chapters"][::-1]
        manga_title = data.get("title", "Manga").strip()
        manga_title_safe = re.sub(r"[^\w\- ]", "_", manga_title)
        final_cbz = Path(f"{manga_title_safe}.cbz")

        downloads_dir = Path("downloads")
        combined_dir = Path("combined_cbz_temp")

        downloads_dir.mkdir(exist_ok=True)
        combined_dir.mkdir(exist_ok=True)

        self.log.emit(f"🔢 Глав: {len(chapters)}")
        for i, chapter in enumerate(chapters, 1):
            if self._is_cancelled:
                self.log.emit("❌ Скачивание отменено")
                self.cleanup()
                return

            title = chapter["title"]
            chapter_id = chapter["id"]
            news_id = data["news_id"]
            filename = re.sub(r"[^\w\- ]", "_", f"{i:06}_{title}") + ".zip"
            zip_path = downloads_dir / filename

            self.log.emit(f"⬇️ {i}/{len(chapters)}: {title}")

            try:
                # Подготовка POST-запроса
                payload = f"chapter_id={chapter_id}&news_id={news_id}"
                headers = {
                    "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
                    "Referer": self.url,
                    "X-Requested-With": "XMLHttpRequest",
                    "Origin": "https://comx.life",
                    "User-Agent": self.headers["User-Agent"]
                }

                cookies = {c["name"]: c["value"] for c in self.cookies}
                link_resp = requests.post(
                    "https://comx.life/engine/ajax/controller.php?mod=api&action=chapters/download",
                    headers=headers,
                    data=payload,
                    cookies=cookies
                )

                try:
                    json_data = link_resp.json()
                    raw_url = json_data.get("data")
                    if not raw_url:
                        raise ValueError("Поле 'data' не найдено в JSON")

                    # Преобразуем \/\/ в // и добавляем протокол
                    download_url = "https:" + raw_url.replace("\\/", "/")

                    r = requests.get(download_url, headers=self.headers, cookies=cookies)
                    if r.ok:
                        with open(zip_path, "wb") as f:
                            f.write(r.content)
                    else:
                        self.log.emit(f"❌ Ошибка {r.status_code} при скачивании {title}")
                except Exception as e:
                    self.log.emit(f"❌ Ошибка при обработке главы {title}: {e}")
                    
                if r.ok:
                    with open(zip_path, "wb") as f:
                        f.write(r.content)
                else:
                    self.log.emit(f"❌ Ошибка {r.status_code} при скачивании {title}")

            except Exception as e:
                self.log.emit(f"❌ Ошибка при обработке главы {title}: {e}")

        if self._is_cancelled:
            self.cleanup()
            return

        index = 1
        self.log.emit("📦 Архивация в CBZ...")
        with zipfile.ZipFile(final_cbz, "w") as cbz:
            for zip_file in sorted(downloads_dir.glob("*.zip")):
                if self._is_cancelled:
                    self.log.emit("❌ Архивация отменена")
                    break

                with zipfile.ZipFile(zip_file) as z:
                    for name in sorted(z.namelist()):
                        if self._is_cancelled:
                            break

                        ext = os.path.splitext(name)[1].lower()
                        out_name = f"{index:06}{ext}"
                        z.extract(name, path=combined_dir)
                        os.rename(combined_dir / name, combined_dir / out_name)
                        cbz.write(combined_dir / out_name, arcname=out_name)
                        index += 1

        self.cleanup()
        if self._is_cancelled:
            if final_cbz.exists():
                try:
                    final_cbz.unlink()
                    self.log.emit(f"🧹 Удалён неполный архив: {final_cbz}")
                except Exception as e:
                    self.log.emit(f"⚠️ Не удалось удалить архив: {e}")
            return

        self.log.emit(f"✅ Готово: {final_cbz.resolve()}")


class DownloaderApp(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Manga Downloader")
        self.setGeometry(200, 200, 600, 400)
        layout = QVBoxLayout(self)

        self.button = QPushButton("Открыть сайт")
        self.cancel_button = QPushButton("Отмена")
        self.cancel_button.hide()
        self.logs = QTextEdit(readOnly=True)

        layout.addWidget(self.button)
        layout.addWidget(self.cancel_button)
        layout.addWidget(self.logs)

        self.button.clicked.connect(self.start_download)
        self.cancel_button.clicked.connect(self.cancel_download)

    def download_started(self):
        self.cancel_button.show()

    def start_download(self):
        self.button.setEnabled(False)
        self.logs.append("▶️ Ожидайте...")
        self.worker = MangaDownloader()
        self.worker.download_started.connect(self.download_started)
        self.worker.log.connect(self.logs.append)
        self.worker.finished.connect(self.download_finished)
        self.worker.start()

    def cancel_download(self):
        if hasattr(self, 'worker'):
            self.worker.cancel()
            self.logs.append("🛑 Отмена...")

    def download_finished(self, ok):
        self.button.setEnabled(True)
        self.cancel_button.hide()
        if (self.worker._is_cancelled):
            return
        elif ok:
            self.logs.append("✅ Скачивание завершено успешно!")
        else:
            self.logs.append("❌ Скачивание завершено с ошибкой.")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    win = DownloaderApp()
    win.show()
    sys.exit(app.exec_())
