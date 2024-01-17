# location_ipfire_db_reader

## Introduction
I was looking for a geo-ip library where I can easily convert IPs into countries. And this preferably in Python and preferably offline.

Couldn't find any, but [ipfires `location` utility](https://github.com/ipfire/libloc/) came very close. Sadly it was coded in C.

That's why I re-interpreted the location databases structure into Python and made a tiny wrapper around it for easy access.


## Installation:
```shell
pip install -U location-ipfire-db-reader
```


## Main usage:
```python
from location_ipfire_db_reader import LocationDatabase

# This call will _download the location database into the provided file.
#   It will not re-_download it if there are no updates.
db = LocationDatabase('location.db')
print(db.find_country('8.8.8.8'))  # US
```

This library should work for both IP4 & IP6.


## Developers information
(or more accurately named: _information for myself at a future point in time_ 😎)

* `decompress_db.py` contains just the code to facilitate extraction of the database
* `download_db.py`: download (or update) once a day the newest ipfire location database.
* `database.py`: The wrapper (consumer-facing code) around the filehandling and reading and stuff.
* `interpret_location_db.py`: contains the low-level interpretation of the database file.
