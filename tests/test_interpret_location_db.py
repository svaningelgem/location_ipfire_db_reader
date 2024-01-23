from location_ipfire_db_reader.interpret_location_db import as_int


def test_as_int() -> None:
    assert as_int(1) == 1
    assert as_int(1.001) == 1
    assert as_int(1.999) == 1
    assert as_int("1") == 1
    assert as_int("1.1") == 1
