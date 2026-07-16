# This file handles two things:
#   1. Setting up the connection to MySQL (the "engine")
#   2. Keeping a small in-memory copy of the `cities` table, since it barely
#      ever changes and re-querying it on every single request would be wasteful

from sqlalchemy import create_engine, text
from api.config import MYSQL_ACCOUNT, MYSQL_HOST, MYSQL_PASSWORD, MYSQL_PORT

# create_engine() doesn't actually connect to MySQL yet — it just sets up
# a "connection factory" that knows HOW to connect, and manages a pool of
# reusable connections behind the scenes so we're not opening a brand new
# connection for every request (that would be slow).
engine = create_engine(
    f"mysql+pymysql://{MYSQL_ACCOUNT}:{MYSQL_PASSWORD}@{MYSQL_HOST}:{MYSQL_PORT}/data_jobs",

    # pool_pre_ping: before handing out a connection from the pool, SQLAlchemy
    # sends a tiny "are you still there?" check first. This matters for a
    # long-running process like an API server (unlike your scraper tasks,
    # which are short-lived) — if MySQL restarts or an idle connection times
    # out, the API reconnects automatically instead of the next request
    # just failing with a confusing error.
    pool_pre_ping=True,
)

# A plain Python dictionary acting as a cache: {city_id: {city_zh, city_en, is_overseas}}
# This starts empty and gets filled in once when the API starts up (see
# load_cities_cache() below, called from main.py's `lifespan` function).
CITIES_CACHE: dict[int, dict] = {}


def load_cities_cache():
    """Read the whole `cities` table from MySQL ONE TIME and store it in the
    CITIES_CACHE dictionary above. There are only ~23 cities and they never
    change while the API is running, so there's no reason to hit the
    database again for this — we just reuse this dictionary in memory."""
    with engine.connect() as conn:
        # text(...) wraps a raw SQL string so SQLAlchemy knows to run it as-is.
        # .mappings().all() gives us back a list of dict-like rows, e.g.
        # [{"id": 1, "city_zh": "海外", "city_en": "Overseas", "is_overseas": True}, ...]
        rows = conn.execute(
            text("SELECT id, city_zh, city_en, is_overseas FROM cities")
        ).mappings().all()

    # IMPORTANT: we mutate the SAME dictionary object in place (.clear() then
    # .update()) rather than doing `CITIES_CACHE = {...}`. Reassigning would
    # create a brand new dict and point THIS module's name at it — but any
    # other file that already did `from api.db import CITIES_CACHE` grabbed
    # a reference to the ORIGINAL dict, and reassigning here would leave
    # their copy permanently empty. Mutating the existing object means every
    # reference to it, wherever it was imported, sees the update.
    CITIES_CACHE.clear()
    CITIES_CACHE.update({row["id"]: dict(row) for row in rows})
    print(f"[startup] loaded {len(CITIES_CACHE)} cities into cache")  # TEMPORARY — remove once resolved


def cities_for_ids(city_ids_str: str | None) -> list[dict]:
    """The `jobs_unified` database view stores each job's cities as a single
    text string like "2,5,6,7" (because a Cake job can be posted in several
    cities at once). This function takes that raw string and turns it into
    a proper list of full city dictionaries, e.g.:

        "2,5,6,7"  →  [{"id": 2, "city_zh": "新北市", ...}, {"id": 5, ...}, ...]

    so the API can return real city names to the frontend instead of a
    comma-separated string of numbers.
    """
    if not city_ids_str:
        # covers both None and empty string "" — no cities to return
        return []

    # "2,5,6,7" → ["2", "5", "6", "7"] → [2, 5, 6, 7]
    # the `if x.strip()` guards against a stray empty piece if the string
    # ever looked like "2,,5" for some reason
    ids = [int(x) for x in city_ids_str.split(",") if x.strip()]

    # look each id up in our in-memory cache; skip any id that (for whatever
    # reason) isn't in the cache rather than crashing the whole request
    return [CITIES_CACHE[i] for i in ids if i in CITIES_CACHE]