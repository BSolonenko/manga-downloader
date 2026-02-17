#!/usr/bin/env bash
cd "$(dirname "$0")"
PYTHONPATH="$(pwd)/src" python -m manga_downloader
