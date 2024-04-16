from dotenv import load_dotenv
import os
import redis
from redis.commands.json.path import Path
from redis.commands.search.field import *
from check_host import *


def get_redis_client():

    load_dotenv()
    REDIS_HOST = os.getenv('REDIS_HOST')
    REDIS_PORT = os.getenv('REDIS_PORT')
    REDIS_PASSWORD = os.getenv('REDIS_PASSWORD')
    
    try:
        redis_client = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, password=REDIS_PASSWORD, decode_responses=True)
    except Exception as e:
        print(e)
        return None
    
    return redis_client


def get_id():

    redis_client = get_redis_client()

    try:
        id_str = redis_client.get('identifier')
        if id_str == None:
            return None

        id = int(id_str)
        redis_client.set('identifier', id + 1)   

    except Exception as e:
        print(e)
        return None
    
    return id

def reset_id():

    redis_client = get_redis_client()

    try:
        server_names = get_server_names()
        ids = [int(name.split('-')[1]) for name in server_names]
        max_id = max(ids)
        redis_client.set('identifier', max_id + 1)
    
    except Exception as e:
        print(e)
        return False
    
    return True

def get_name():

    id = get_id()
    return f'server-{id}'


def get_server_db(server_name):

    redis_client = get_redis_client()

    try:
        server = redis_client.json().get(server_name)
    
    except Exception as e:
        print(e)
        return None

    return server


def add_server_db(server, available, free): # server is the json object returned from 99stack /v1.3/server/info endpoint
    
    new_server = {
        'ipv4': server['iface']['v4'][0]['address'],
        'username': 'root',
        'password': server['password'],
        'available': available,
        'free': free,
        'uuid': server['uuid']
    }

    redis_client = get_redis_client()

    try:
        redis_client.json().set(server['name'], Path.root_path(), new_server)
    
    except Exception as e:
        print(e)
        return False

    return True


def delete_server_db(server_name):

    redis_client = get_redis_client()
    
    try:
        redis_client.json().delete(server_name, Path.root_path())
    
    except Exception as e:
        print(e)
        return False
    
    return True


def is_free(server_name):

    redis_client = get_redis_client()

    try:
        server = redis_client.json().get(server_name)
    
    except Exception as e:
        print(e)
        return None

    if server == None:
        return None    
    
    if server['free'] == 1:
        return True
    elif server['free'] == 0:
        return False

    return None


def is_available(server_name):

    redis_client = get_redis_client()

    try:
        server = redis_client.json().get(server_name)
    except Exception as e:
        print(e)
        return None

    if server == None:
        return None
    
    if server['available'] == 1:
        return True
    elif server['available'] == 0:
        return False
    
    return None


def get_server_uuid(server_name):

    redis_client = get_redis_client()

    try:
        server_uuid = redis_client.json().get(server_name)['uuid']
    except Exception as e:
        print(e)
        return None
    
    return server_uuid


def set_unavailable(server_name):

    redis_client = get_redis_client()

    try:
        server = redis_client.json().get(server_name)
        server['available'] = 0
        redis_client.json().set(server_name, Path.root_path(), server)
    
    except Exception as e:
        print(e)
        return False
    
    return True


def get_server_name(server_uuid):

    redis_client = get_redis_client()

    try:
        server_names = redis_client.keys('server-*')
        servers = [(i, redis_client.json().get(server_names[i])) for i in range(len(server_names))]
        server = list(filter(lambda server: server[1]['uuid'] == server_uuid, servers))[0]
    except Exception as e:
        print(e)
        return None

    return server_names[server[0]]


def get_server_names():

    try:
        redis_client = get_redis_client()
        names = redis_client.keys('server-*')
    except Exception as e:
        print(e)
        return None
    
    return names
