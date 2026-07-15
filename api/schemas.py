# --------- description --------- #
# this file defines the shape of the data the API sends back

from datetime import datetime
from typing import Literal, Optional
from pydantic import BaseModel

class CityOut(BaseModel):
    # represent the city
    # the Out suffix means the data is going out
    id: int
    city_zh: str
    city_en: str
    is_overseas: bool

class JobOut(BaseModel):
    # represent a single job listing 
    job_uid : str
    # limit the source to be either of the two
    source: Literal['104', 'Cake']
    job_name: str
    company: str

    # optional fields
    # if the field is left unfilled then the default is None
    location_display: Optional[str] = None

    # CityOut objects, default to an empty list []
    # if a job somehow has no city info at all
    cities : list[CityOut] = []

    # salary fields are all Optional 
    salary_min: Optional[float] = None
    salary_max: Optional[float] = None
    salary_note: Optional[str] = None

    link: str
    posted_at: datetime

class JobsResponse(BaseModel):
    # the overall shape of what GET / api / jobs returns: not just a list of jobs, but pagination
    # info alongside it so the frontend knows how many total results exist and which page it's 
    # looking at
    total: int
    page: int
    page_size: int
    results: list[JobOut]

class SourceStats(BaseModel):
    # stats breakdown e.g., '104 has 8412 jobs, last updated 2 hours ago'
    source: str
    total_jobs: int
    last_scraped_at: Optional[datetime] = None

class StatsResponse(BaseModel):
    # the overall shape returned by GET/api/stats
    total_jobs: int
    by_source: list[SourceStats]