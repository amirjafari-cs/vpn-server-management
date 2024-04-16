from check_host import *
from manage_database import *
from manage_servers import *
from manage_dns import *
from scheduling import *
import threading
import schedule

# Constant values
SERVER_COUNT = 3 # Number of servers to create to find a clean server
CHECK_WAIT = 5 # Run the check routine every CHECK_WAIT minutes
RUN_PENDING_WAIT = 5 # Do the pending jobs every RUN_PENDING_WAIT seconds
CLEAN_SERVERS_WAIT = 10 # Wait CLEAN_SERVERS_WAIT minutes before cleaning the servers list
CLEAN_TAG = 'clean'


# When ever a server is not available this function will be executed for it
def service_routine(server_name):
    
    done = False
    while not done:
        new_servers = []
        for _ in range(SERVER_COUNT):
            name = get_name()
            new_server = create_default_server(name, False)
            new_servers.append(new_server)
        
        for new_server in new_servers:
            wait_to_ready(new_server['uuid'])
            server = get_server_info(new_server['uuid'])
            
            if done or not check_server(server):
                add_server_db(server, 0, 1)
                continue
            
            ex_server = get_server_info(server_name)
            ex_ipv4 = ex_server['iface']['v4'][0]['address']
            ipv4 = server['iface']['v4'][0]['address']
            
            init_server(ex_server, server, True, True)
            update_dns(ex_ipv4, ipv4)
            add_server_db(server, 1, 0)
            set_unavailable(server_name)

            done = True
    
    return True


# This function executing periodic to check all the servers if there is a out of access server
def check_routine():
    
    # If there are cleaning servers list jobs remove them
    # We'll schedule a cleaning servers list job at the end of this function. no need to them !
    jobs = schedule.get_jobs()
    clean_jobs = list(filter(lambda job: job.tag == CLEAN_TAG, jobs))
    for job in clean_jobs:
        schedule.cancel_job(job)

    server_names = get_server_names()

    threads = []
    for server_name in server_names:
        server = get_server_info(get_server_uuid(server_name))

        if check_server(server):
            continue

        thread = threading.Thread(target=service_routine, args=(server_name,))
        threads.append(thread)
        thread.start()
    
    for thread in threads:
        thread.join()
    
    clean_job = schedule.every(CLEAN_SERVERS_WAIT).minutes.do(clean_servers_list_job)
    clean_job.tag = CLEAN_TAG

def run():
    
    schedule.every(CHECK_WAIT).minutes.do(check_routine)

    # Main loop
    while True:
        schedule.run_pending()
        sleep(RUN_PENDING_WAIT)
