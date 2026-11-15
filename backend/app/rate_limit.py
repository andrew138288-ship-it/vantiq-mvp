from slowapi import Limiter
from slowapi.util import get_remote_address


# In-memory limits are suitable for the current single-replica MVP.
# Move to shared Redis storage before running multiple API replicas.
limiter = Limiter(key_func=get_remote_address, storage_uri="memory://")
