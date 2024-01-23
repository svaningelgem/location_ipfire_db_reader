from __future__ import annotations

import lzma
from pathlib import Path


def decompress_xz_file(file_path: str | Path) -> None:
    file_path = Path(file_path)
    target = file_path.with_suffix(".tmp")

    with lzma.open(file_path, "rb") as f_in, target.open("wb") as f_out:
        # Open the output file in binary mode and write the decompressed contents to it
        for chunk in iter(lambda: f_in.read(1024 * 1024), b""):
            f_out.write(chunk)

    file_path.unlink()
    target.rename(file_path)
