# location_ipfire_db_reader

## Main usage:
```python
from location_ipfire_db_reader import LocationDatabase
from pathlib import Path


location_db = Path('location.db')
# This call will download the location database into the provided file.
#   It will not re-download it if there are no updates.
LocationDatabase.download(location_db)

db = LocationDatabase(location_db)
print(db.find_country('8.8.8.8'))  # US
```

Should work for both IP4 & IP6.
