from contextlib import asynccontextmanager
from typing import Literal, Optional

from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from api.db import engine, load_cities_cache, cities_for_ids, CITIES_CACHE
from api.schemas import JobsResponse, JobOut, CityOut, StatsResponse, SourceStats

with engine.connect() as conn:
    result = conn.execute(text("SHOW VARIABLES LIKE 'collation_connection'")).fetchone()
    print(result)
# maximum pages allowed 
MAX_PAGE_SIZE = 100

@asynccontextmanager
async def lifespan(app: FastAPI):

    load_cities_cache()
    yield

# create the actual application object
app = FastAPI(title='Job Hunter API', lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=['*'], # change this later to my domain
    allow_methods=['GET'],
    allow_headers=['*']
)

@app.get('/api/jobs', response_model=JobsResponse)
def list_jobs(
    q: Optional[str] = None,
    city_id: Optional[list[int]] = Query(None),
    source: Optional[Literal['104', 'Cake']] = None,
    salary_min: Optional[int] = Query(None, ge=0),
    sort: Literal['recent', 'salary'] = 'recent',
    page: int = Query(1, ge=1), # page num start at 1
    page_size:int = Query(20, ge=1, le=MAX_PAGE_SIZE),

):
    # build the SQL query based on the filters received
    where_clauses = []
    params: dict = {}

    if q:

        where_clauses.append("(job_name LIKE: q OR company LIKE :q)")
        params['q']= f"%{q}%"
    if source:
        where_clauses.append("(source = :source)")
        params['source'] = source

    if city_id:
        city_conditions = []
        for i, cid in enumerate(city_id):
            key = f'city_{i}' # place holder for city name
            city_conditions.append(f'FIND_IN_SET(:{key}, city_ids) > 0')
            params[key] = cid
            where_clauses.append("("+ " OR ".join(city_conditions)+ ")")

    if salary_min is not None:
        where_clauses.append("salary_max >= :salary_min")
        params['salary_min'] = salary_min
    
    # combine all the conditions with AND
    # if there's no filter -> fall back to "1=1" (a condition thay's always true)

    where_sql = " AND ".join(where_clauses) if where_clauses else "1=1"
    
    # decide the sort order based on the `sort` parameter
    order_sql = "inserted_at DESC" if sort == "recent" else "salary_max DESC"

    with engine.connect() as conn:
        # first query: the total number of rows match (ignore pagination)
        # scalar_one -> return exactly one value
        total = conn.execute(
            text(f'SELECT COUNT(*) FROM jobs_unified WHERE {where_sql}'),
            params
        ).scalar_one()
        # second query: the actual page of result
        # offset -> the number of rows to skip
        rows = conn.execute(
            text(
                f"""
                SELECT * FROM jobs_unified
                WHERE {where_sql}
                ORDER BY {order_sql}
                LIMIT :limit OFFSET :offset
                """
            ),
             {**params, "limit": page_size, "offset": (page - 1) * page_size},
        ).mappings().all()
 
    # convert the raw database row into a proper JobOut object (from schema.py)
    results = [
        JobOut(
            job_uid=row["job_uid"],
            source=row["source"],
            job_name=row["job_name"],
            company=row["company"],
            location_display=row["location_display"],
            # turn the raw "2,5,6,7" string into real city objects using
            # the helper function from db.py
            cities=[CityOut(**c) for c in cities_for_ids(row["city_ids"])],
            salary_min=row["salary_min"],
            salary_max=row["salary_max"],
            salary_note=row["salary_note"],
            link=row["link"],
            posted_at=row["inserted_at"],
        )
        for row in rows
    ]

    return JobsResponse(total=total, page=page, page_size=page_size, results=results)

@app.get("/api/cities", response_model=list[CityOut])
def list_cities():
    """Handles GET /api/cities — returns every city, straight from the
    in-memory cache (no database query needed). The frontend calls this
    once to build its city filter checkboxes/dropdown."""
    return [CityOut(**c) for c in sorted(CITIES_CACHE.values(), key=lambda c: c["id"])]
 
 
@app.get("/api/stats", response_model=StatsResponse)
def get_stats():
    """Handles GET /api/stats — a quick summary: how many jobs total, split
    by source, and when each source was last scraped. Useful for a small
    dashboard/stats display, and handy for noticing if a scraper stopped
    running (last_scraped_at would stop updating)."""
    with engine.connect() as conn:
        rows = conn.execute(
            text(
                """
                SELECT source, COUNT(*) AS total_jobs, MAX(inserted_at) AS last_scraped_at
                FROM jobs_unified
                GROUP BY source
                """
            )
        ).mappings().all()
 
    by_source = [SourceStats(**row) for row in rows]
    return StatsResponse(total_jobs=sum(s.total_jobs for s in by_source), by_source=by_source)
 