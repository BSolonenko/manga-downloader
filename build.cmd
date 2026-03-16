@echo off
cd /d "%~dp0"

echo === Manga Downloader: сборка EXE ===
echo.

python -m PyInstaller ^
    --noconfirm ^
    --windowed ^
    --onefile ^
    --name "MangaDownloader" ^
    --distpath "win" ^
    --paths "src" ^
    --hidden-import "manga_downloader.driver" ^
    --hidden-import "manga_downloader.downloaders.curl_downloader" ^
    --hidden-import "manga_downloader.downloaders.cloud_downloader" ^
    --hidden-import "manga_downloader.downloaders.selenium_downloader" ^
    --hidden-import "curl_cffi" ^
    --hidden-import "cloudscraper" ^
    --collect-all "selenium" ^
    src\manga_downloader\__main__.py

if %ERRORLEVEL% EQU 0 (
    echo.
    echo === Готово! EXE: win\MangaDownloader.exe ===
) else (
    echo.
    echo === Ошибка сборки ===
)

pause
