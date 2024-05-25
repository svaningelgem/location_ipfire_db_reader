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


## Get more information
What if you wanted to get (much) more information? Like the continent, or the provider? These are all things contained in the ipfires database.
```python
from location_ipfire_db_reader import LocationDatabase

db = LocationDatabase('location.db')
ip_info = db["8.8.8.8"]
print(f"""
ip: {ip_info.ip}
subnet_mask: {ip_info.subnet_mask}
network_address: {ip_info.network_address}
ip_with_cidr: {ip_info.ip_with_cidr}

asn: {ip_info.asn}
asn_name: {ip_info.asn_name}
country_code: {ip_info.country_code}
country_name: {ip_info.country_name}
country_continent: {ip_info.country_continent}

is_anonymous_proxy: {ip_info.is_anonymous_proxy}
is_satellite_provider: {ip_info.is_satellite_provider}
is_anycast: {ip_info.is_anycast}
is_drop: {ip_info.is_drop}
""")
```

This will output:
```text
ip: 8.8.8.8
subnet_mask: 24
network_address: 8.8.8.0
ip_with_cidr: 8.8.8.0/24

asn: 15169
asn_name: GOOGLE
country_code: US
country_name: United States of America
country_continent: NA

is_anonymous_proxy: False
is_satellite_provider: False
is_anycast: True
is_drop: False
```

## Exceptions
All exceptions within this package will inherit from `LocationIPFireDBReaderException`. So if you want a blanket-capture-all. That's what you'll need.

However, these are more fine-tuned versions:
- `UnknownASNName`: will be raised when an ASN is found, but there is no known name for it.
- `IPAddressError`: will be raised when an IP lookup fails. This happens with reserved IPs so far.

### What if you don't want exceptions?
If you don't like to handle exceptions, you can always initialize your `LocationDatabase` like this:

```python
db = LocationDatabase(raise_exceptions=False)
```

Now if for example the AS isn't known, it will output `0` for the asn, and `""` for the AS name. Instead of raising an exception.


## Developers information
(or more accurately named: _information for myself at a future point in time_ 😎)

* `database.py`: The wrapper, ie: consumer-facing code.
* `database_reader.py`: The wrapper around the filehandling and reading and stuff.
* `decompress_db.py` contains just the code to facilitate extraction of the database
* `download_db.py`: download (or update) once a day the newest ipfire location database.
* `interpret_location_db.py`: contains the low-level interpretation of the database file.
* `ip_information.py`: contains the class where all information can be retrieved from ipfires database.
