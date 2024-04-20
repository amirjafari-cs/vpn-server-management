from manage_database import *
from paramiko import *
from check_host import *
from time import sleep
import http.client
import json
import ssl
import threading
import re
import os

# Constant values
DEL_WAIT = 10 # Wait DEL_WAIT seconds to delete a server after a failed attempt
READY_WAIT = 5 # for each time checking if the server is ready wait READY_WAIT seconds
DEFAULT_REGION = 209
DEFAULT_IMAGE = 2114
DEFAULT_PLAN = 2101
BANNER_TIMEOUT = 60
RUNNING_STATUS = 'running' # The 'power' field in server object when its running
MAX_DEL_WAIT = 11 # Maximum time to wait when trying to delete a server(in minutes)
TEMP_XUI_PATH = './x-ui.db' # Path to save x-ui.db on local machine temporary

# Commands
install_3x_ui = 'bash <(curl -Ls https://raw.githubusercontent.com/mhsanaei/3x-ui/master/install.sh)'
restart_x_ui = 'x-ui restart'
copy_database = 'scp /etc/x-ui/x-ui.db {username}@{host}:/etc/x-ui/'
add_host_key = 'ssh-keyscan {host} >> ~/.ssh/known_hosts'


def init_server(ex_server, server, ex_ppk_auth=True, ppk_auth=True): # servers are /v1.3/server/info endpoint objects

    load_dotenv()
    PANEL_USERNAME = os.getenv('PANEL_USERNAME')
    PANEL_PASSWORD = os.getenv('PANEL_PASSWORD')
    PANEL_PORT = os.getenv('PANEL_PORT')
    PK_PATH = os.getenv('PK_PATH')

    # Get expired server and new server login creditional
    try:
        ex_host = ex_server['iface']['v4'][0]['address']
        ex_username = 'root'
        ex_password = ex_server['password']
        ex_port = 22
        host = server['iface']['v4'][0]['address']
        username = 'root'
        password = server['password']
        port = 22
    
    except KeyError:
        print('Invalid input !')
        return False

    # Connect to expired server
    try:
        client1 = SSHClient()
        client1.set_missing_host_key_policy(AutoAddPolicy)
        if ex_ppk_auth:
            client1.connect(hostname=ex_host, port=ex_port, username=ex_username, key_filename=PK_PATH, banner_timeout=BANNER_TIMEOUT)
        else:
            client1.connect(hostname=ex_host, port=ex_port, username=ex_username, password=ex_password, banner_timeout=BANNER_TIMEOUT)
    
    except Exception as e:
        print('Error occured while connecting client1 !')
        print(e)
        return False

    # Connect to new server
    try:
        client2 = SSHClient()
        client2.set_missing_host_key_policy(AutoAddPolicy)
        if ppk_auth:
            client2.connect(hostname=host, port=port, username=username, key_filename=PK_PATH, banner_timeout=BANNER_TIMEOUT)
        else:
            client2.connect(hostname=host, port=port, username=username, password=password, banner_timeout=BANNER_TIMEOUT)
    
    except Exception as e:
        print('Error occured while connecting client2 !')
        print(e)
        return False

    # Install 3x-ui on new server
    try:
        stdin, stdout, stderr = client2.exec_command(install_3x_ui)
        stdin.write('y\n')
        stdin.write(f'{PANEL_USERNAME}\n')
        stdin.write(f'{PANEL_PASSWORD}\n')
        stdin.write(f'{PANEL_PORT}\n')
        stdout.read()
        stdin.close()
        
        # print(stdout.read().decode('utf-8'))
        # print(stderr.read().decode('utf-8'))
    
    except Exception as e:
        print('Error occured while installing 3x-ui !')
        print(e)
        return False

    # Copy the database to new server
    try:
        if ex_ppk_auth:
            client1.connect(hostname=ex_host, port=ex_port, username=ex_username, key_filename=PK_PATH, banner_timeout=BANNER_TIMEOUT)
        else:
            client1.connect(hostname=ex_host, port=ex_port, username=ex_username, password=ex_password, banner_timeout=BANNER_TIMEOUT)
        
        if ppk_auth:
            client2.connect(hostname=host, port=port, username=username, key_filename=PK_PATH, banner_timeout=BANNER_TIMEOUT)
        else:
            client2.connect(hostname=host, port=port, username=username, password=password, banner_timeout=BANNER_TIMEOUT)
        
        sftp1 = client1.open_sftp()
        sftp2 = client2.open_sftp()
        sftp1.get('/etc/x-ui/x-ui.db', TEMP_XUI_PATH)
        sftp2.put(TEMP_XUI_PATH, '/etc/x-ui/x-ui.db')

        # print(stderr.read().decode('utf-8'))
        sftp1.close()
        sftp2.close()
        os.remove(TEMP_XUI_PATH)
    
    except Exception as e:
        print('Error occured while copying database !')
        print(e)
        return False

    # Restart the x-ui panel on new server
    try:
        stdin, stdout, stderr = client2.exec_command(restart_x_ui)
        stdin.close()

        # print(stderr.read().decode('utf-8'))
    
    except Exception as e:
        print('Error occured while restarting the x-ui panel !')
        print(e)
        return False

    # Close the connections
    client1.close()
    client2.close()

    return True


def get_https_conn():

    load_dotenv()
    STACK_HOST = os.getenv('STACK_HOST')
    STACK_API_TOKEN = os.getenv('STACK_API_TOKEN')

    try:
        conn = http.client.HTTPSConnection(STACK_HOST, context=ssl._create_unverified_context())
    
    except Exception as e:
        print(e)
        return None
    
    headers = {
        'Authorization': f'Bearer {STACK_API_TOKEN}',
        'Content-Type': 'application/json'
    }

    return conn, headers


def get_ssh_key_uuid():
    
    conn, headers = get_https_conn()

    try:
        conn.request('GET', '/v1.3/ssh_key/list', headers=headers)
        
        res = conn.getresponse().read()
        res_json = json.loads(res)
        ssh_key_info = res_json['ssh_keys'][0]
    
    except Exception as e:
        print(e)
        return None
    
    return ssh_key_info.get('uuid', None)


def check_server_running(server_uuid):

    server_info = get_server_info(server_uuid)

    if server_info == None:
        return None
    return server_info['power'] == RUNNING_STATUS


def wait_to_ready(server_uuid):

    ready = False

    while not ready:
        ready = check_server_running(server_uuid)
        sleep(READY_WAIT)
    
    return


# add_db: create server -> wait to ready -> add server to database
# not add_db: create_server
def create_server(name, region, image, plan, add_db):

    conn, headers = get_https_conn()
    ssh_key_uuid = get_ssh_key_uuid()

    payload = (
        f'{{\n  "hostname": "{name}",'
        f'\n  "label": "{name}",'
        f'\n  "region": {region},'
        f'\n  "image": {image},'
        f'\n  "plan": {plan},'
        f'\n  "ssh_key": "{ssh_key_uuid}"\n}}'
    )

    try:
        conn.request('POST', '/v1.3/server/create', headers=headers, body=payload)
        
        res = conn.getresponse().read()
        server = json.loads(res)

        if add_db:
            server_uuid = server['uuid']
            wait_to_ready(server_uuid)
            server = get_server_info(server_uuid)
            available = 1 
            if not check_server(server):
                available = 0
            
            done = add_server_db(server, available, 1)
            if not done:
                raise Exception
    
    except Exception as e:
        print(e)
        return None
    
    return server


def create_default_server(name, add_db):
    
    return create_server(name, DEFAULT_REGION, DEFAULT_IMAGE, DEFAULT_PLAN, add_db)


def get_free_servers():

    conn, headers = get_https_conn()

    try:
        conn.request('GET', '/v1.3/server/list', headers=headers)

        res = conn.getresponse().read()
        servers = json.loads(res)['servers']

        servers = list(filter(lambda server: is_free(server['name']), servers))

    except Exception as e:
        print(e)
        return None

    return servers

def delete_server(server_uuid):
    
    conn, headers = get_https_conn()

    try:
        conn.request('DEL', f'/v1.3/server/remove/{server_uuid}', headers=headers)
    
    except Exception as e:
        print(e)
        return False

    res = conn.getresponse()
    if res.status != 204:
        return False

    return True

def wait_and_delete_server(server_uuid):
    
    done = False
    i = 0
    while not done:
        if i * DEL_WAIT > 60 * MAX_DEL_WAIT:
            break
        done = delete_server(server_uuid)
        sleep(DEL_WAIT)
        i += 1
    
    return done


# !!! ATTENTION: Non available servers will be deleted although they're not free
def clean_servers_list():
    
    server_names = get_server_names()
    
    threads = []
    for server_name in server_names:
        
        if not is_free(server_name) and is_available(server_name):
            continue
        
        # delete server
        server_uuid = get_server_uuid(server_name)
        thread = threading.Thread(target=wait_and_delete_server, args=(server_uuid,))
        threads.append(thread)
        thread.start()
    
        # delete server from database
        delete_server_db(server_name)

    # wait for all threads to finish their job
    for thread in threads:
        thread.join()
    
    return True


# server_id is server name or server uuid
def get_server_info(server_id):

    server_uuid = server_id
    if re.match('server-[0-9]+$', server_id) != None:
        server_uuid = get_server_uuid(server_id)

    conn, headers = get_https_conn()

    try:
        conn.request('GET', f'/v1.3/server/info/{server_uuid}', headers=headers)

        res = conn.getresponse().read()
        res_json = json.loads(res)

    except Exception as e:
        print(e)
        return None
    
    return res_json

def get_servers_list():

    conn , headers = get_https_conn()

    try:
        conn.request('GET', '/v1.3/server/list', headers=headers)

        res = conn.getresponse().read()
        res_json = json.loads(res)
        servers = res_json['servers']
    
    except Exception as e:
        print(e)
        return None

    return servers


def sync_database():

    try:
        server_names = get_server_names()
        for server_name in server_names:
            delete_server_db(server_name)

        servers = get_servers_list()

        for server in servers:
            available = 1
            if not check_server(server):
                available = 0
            
            free = 0 # !!!! TO CHANGE !!!!

            add_server_db(server, available, free)
        
        reset_id()
    
    except Exception as e:
        print(e)
        return False
    
    return True
