# --------- description --------- #
# this script setups connection to the MySQL database and 
# keep a small in-memory copy of the `cities` table because it barely ever changes
# and re-querying it on every single request would be wasteful

from sqlalchemy import create_engine, text
from api.config import MYSQL_ACCOUNT, MYSQL_HOST, MYSQL_PASSWORD, MYSQL_PORT

# create engine for connecting to the database
engine = create_engine(
    f'mysql+pymysql://{MYSQL_ACCOUNT}:{MYSQL_PASSWORD}@{MYSQL_HOST}:{MYSQL_PORT}/data_jobs',
    pool_pre_ping=True
)
# a python dictionary acting as a cache: {city_id: {city_zh, city_en, is_overseas}}
CITIES_CACHE: dict[int, dict] = {}

def load_cities_cache():
    # load the city information from the `cities` table and store it in the CITIES_CACHE dictionary 
    global CITIES_CACHE

    with engine.connect() as conn:
        rows = conn.execute(
            text('SELECT id, city_zh, city_en, is_overseas FROM cities')
        ).mappings().all()
        
        # turn the list of rows into a dictionary keyed by id
    CITIES_CACHE = {row['id']:dict(row) for row in rows}

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
        # covers both None and empty string
        return []
    ids = [int(x) for x in city_ids_str.split(',') if x.strip()]

    # look up the corresponding info in in-memory cache
    return [CITIES_CACHE[i] for i in ids if i in CITIES_CACHE]
    
