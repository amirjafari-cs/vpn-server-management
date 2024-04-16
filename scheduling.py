import schedule
from time import sleep
from manage_servers import *

RUN_PENDING_WAIT = 5

def do_job_onetime():
    
    while True:
        jobs = schedule.get_jobs()
        if len(jobs) == 0:
            break
        schedule.run_pending()
        sleep(RUN_PENDING_WAIT)

def clean_servers_list_job():
    clean_servers_list()
    return schedule.CancelJob
