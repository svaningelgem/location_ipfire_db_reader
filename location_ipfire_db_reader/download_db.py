from __future__ import annotations

import os
import time
import typing
from datetime import datetime

from requests import Session

from .decompress_db import decompress_xz_file

if typing.TYPE_CHECKING:
    from pathlib import Path


def download_or_update_location_database(target_file: Path) -> None:
    yesterday = time.time() - 24 * 60 * 60
    if target_file.exists() and target_file.stat().st_mtime > yesterday:
        return  # Don't re-_download it so often! Just once a day should be fine.

    target_url = "https://location.ipfire.org/databases/1/location.db.xz"

    session = Session()

    need_re_download = True
    if target_file.exists():
        response = session.head(target_url)

        if "Last-Modified" in response.headers:
            server_last_modified_time = datetime.strptime(response.headers["Last-Modified"], "%a, %d %b %Y %H:%M:%S %Z")
            need_re_download = target_file.stat().st_mtime < server_last_modified_time.timestamp()

    if need_re_download:
        response = session.get(target_url)
        target_file.write_bytes(response.content)
        decompress_xz_file(target_file)

    os.utime(target_file, (time.time(), time.time()))
