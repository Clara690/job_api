import pandas as pd  
from fastapi import FastAPI
from sqlalchemy import create_engine, engine 
from api.config import MYSQL_ACCOUNT, MYSQL_HOST, MYSQL_PASSWORD, MYSQL_PORT

# a function for establishing the connection
def get_my_sql_conn()-> engine.base.Connection:
    address = f'mysql+pymysql://{MYSQL_ACCOUNT}:{MYSQL_PASSWORD}@{MYSQL_HOST}:{MYSQL_PORT}/data_jobs'
    engine = create_engine(address)
    connect = engine.connect()
    return connect # the connection object

# create FastAPI instance
app = FastAPI()

# define the root directory
@app.get("/")
def read_root():
    return {"Hello": "World"}

# define the api to get job posting on 104
@app.get('/104_jobs')
def jobs_at_104(
    job_name: str = '', # name of the role
    location: str = '',
    salary_min: int = 0
):
    sql = f"""
    select * from jobs_104
    where job_name like '%%{job_name}%%'
    and location like '%%{location}%%'
    and salary_low >= '{salary_min}'
    """

    # create database connection
    mysql_conn = get_my_sql_conn()
    # use pandas to execute sql and get the data
    data_df = pd.read_sql(sql, con=mysql_conn)
    # convert dataframe to list of dict
    data_dict = data_df.to_dict('records')
    return {'data': data_dict}
    
    


