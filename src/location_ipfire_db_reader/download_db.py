import os
from datetime import datetime
from pathlib import Path

from requests import Response, Session

session = Session()


def download_latest_location_database(target_file: str | os.PathLike) -> bool:
    """
    :return: True when the file is downloaded, False when the current one is still OK.
    """

    def _get_last_modified(resp: Response) -> float:
        """
        :raise: KeyError when the header isn't found
        """
        return datetime.strptime(resp.headers["Last-Modified"], "%a, %d %b %Y %H:%M:%S %Z").timestamp()

    target_file = Path(target_file)
    target_url = "https://location.ipfire.org/databases/1/location.db.xz"

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

    if need_re_download:
        response = session.get(target_url)

        target_file.write_bytes(response.content)
        try:
            atime = target_file.stat().st_atime
            os.utime(target_file, (atime, _get_last_modified(response)))
        except KeyError:
            pass

    return need_re_download
