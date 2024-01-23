import os
import time
from pathlib import Path

import pytest
from pytest_mock import MockerFixture
from pytest_mock.plugin import MockType

from location_ipfire_db_reader import LocationDatabase
from location_ipfire_db_reader.download_db import download_or_update_location_database


@pytest.fixture()
def fake_download_session(mocker: MockerFixture) -> MockType:
    session = mocker.patch("location_ipfire_db_reader.download_db.Session").return_value

    # "bumba" xz compressed
    xz_compressed_bumba_word = (
        b"\xfd\x37\x7a\x58\x5a\x00\x00\x04\xe6\xd6\xb4\x46\x02\x00\x21\x01"
        b"\x16\x00\x00\x00\x74\x2f\xe5\xa3\x01\x00\x05\x62\x75\x6d\x62\x61"
        b"\x0a\x00\x00\x00\x1a\xc0\x2f\x16\x4a\xd3\xbb\x2b\x00\x01\x1e\x06"
        b"\xc1\x2f\xa4\x1d\x1f\xb6\xf3\x7d\x01\x00\x00\x00\x00\x04\x59\x5a"
    )
    session.head.return_value = mocker.Mock(
        headers={"Last-Modified": "Wed, 15 Nov 2023 19:51:32 GMT", "Content-Length": str(len(xz_compressed_bumba_word))}
    )
    session.get.return_value = mocker.Mock(content=xz_compressed_bumba_word)

    return session


def test_dont_redownload_db(locdb: LocationDatabase, locdb_path: Path, mocker: MockerFixture) -> None:
    # locdb is already downloaded, so let's try it again

    # Trigger to make sure we downloaded the database:
    _ = locdb.header

    session_mock = mocker.patch("location_ipfire_db_reader.download_db.Session")

    _ = LocationDatabase(locdb_path).header
    session_mock.assert_not_called()  # So we didn't initiate another download.


def test_fake_download_file_not_exist_yet(tmp_path: Path, fake_download_session: MockType) -> None:
    tgt = tmp_path / "target.db"
    download_or_update_location_database(tgt)
    assert tgt.read_bytes() == b"bumba\n"


def test_fake_download_file_exists_but_is_old(tmp_path: Path, fake_download_session: MockType) -> None:
    """We expect a quick "HEAD" check, and then a download."""
    tgt = tmp_path / "target.db"
    download_or_update_location_database(tgt)  # Ensure the file is there
    assert tgt.read_bytes() == b"bumba\n"

    os.utime(tgt, (0, 0))  # Fake as old existing file
    download_or_update_location_database(tgt)
    fake_download_session.head.assert_called()
    fake_download_session.get.assert_called()


def test_fake_download_file_exists_but_no_newer_available(tmp_path: Path, fake_download_session: MockType) -> None:
    """We expect a quick "HEAD" check, but no download."""
    tgt = tmp_path / "target.db"
    download_or_update_location_database(tgt)  # Ensure the file is there
    assert tgt.read_bytes() == b"bumba\n"

    fake_download_session.reset_mock()

    little_more_than_a_day_ago = time.time() - 30 * 60 * 60
    os.utime(tgt, (little_more_than_a_day_ago, little_more_than_a_day_ago))  # Fake as old existing file
    download_or_update_location_database(tgt)
    fake_download_session.head.assert_called()
    fake_download_session.get.assert_not_called()
