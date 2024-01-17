from __future__ import annotations

import contextlib
import os
from datetime import datetime
from pathlib import Path

from requests import Response, Session

from .decompress_db import decompress_xz_file


def _get_last_modified(resp: Response) -> float:
    """
    :raise: KeyError when the header isn't found
    """

    return datetime.strptime(resp.headers["Last-Modified"], "%a, %d %b %Y %H:%M:%S %Z").timestamp()


def download_or_update_location_database(target_file: Path) -> None:
    if target_file.exists() and target_file.stat().st_mtime > datetime.now().timestamp() - 24 * 60 * 60:
        return  # Don't re-_download it so often! Just once a day should be fine.

    target_url = "https://location.ipfire.org/databases/1/location.db.xz"

    session = Session()
    response = session.head(target_url)
    try:
        server_last_modified_time = _get_last_modified(response)
        need_re_download = not target_file.exists() or target_file.stat().st_mtime < server_last_modified_time
    except KeyError:
        try:
            filesize = response.headers["Content-Length"]
            need_re_download = not target_file.exists() or filesize == target_file.stat().st_size
        except KeyError:
            need_re_download = True

    if not need_re_download:
        return

    response = session.get(target_url)

    target_file.write_bytes(response.content)
    with contextlib.suppress(KeyError):
        atime = target_file.stat().st_atime
        os.utime(target_file, (atime, _get_last_modified(response)))

    decompress_xz_file(target_file)
