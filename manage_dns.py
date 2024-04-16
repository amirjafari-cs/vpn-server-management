from dotenv import load_dotenv
import os
import http.client
import json


def get_https_conn():

    load_dotenv()
    CF_HOST = os.getenv('CF_HOST')
    CF_EMAIL = os.getenv('CF_EMAIL')
    CF_API_KEY = os.getenv('CF_API_KEY')
    
    conn = http.client.HTTPSConnection(CF_HOST)
    headers = {
        'Content-Type': 'application/json',
        'X-Auth-Email': CF_EMAIL,
        'X-Auth-Key': CF_API_KEY
        }
    
    return conn, headers


def get_zone_id(zone_name):

    conn, headers = get_https_conn()

    conn.request('GET', '/client/v4/zones', headers=headers)

    res = conn.getresponse()
    zones = json.loads(res.read().decode())['result']
    
    zones_filtered = list(filter(lambda zone: zone['name'] == zone_name, zones))
    if len(zones_filtered) == 0:
        return None

    return zones_filtered[0]['id']


def get_zone_records(zone_id):

    conn, headers = get_https_conn()

    conn.request('GET', f'/client/v4/zones/{zone_id}/dns_records', headers=headers)

    res = conn.getresponse()
    records = json.loads(res.read().decode())['result']
    return records
    

def get_record_id(name, zone_id):
    
    records = get_zone_records(zone_id)

    records_filtered = list(filter(lambda record: \
        record['name'] == name and \
        record['type'] == 'A', \
        records))
    if len(records_filtered) == 0:
        return None

    return records_filtered[0]['id']

# Update an A record with new content
def update_Arecord_by_id(zone_id, record_id, content):
    
    conn, headers = get_https_conn()

    payload = f'{{\n  "content": "{content}"\n}}'

    conn.request('PATCH', f'/client/v4/zones/{zone_id}/dns_records/{record_id}', body=payload, headers=headers)

    res = conn.getresponse()
    res_json = json.loads(res.read().decode())

    return res_json['success']


def update_Arecord(name, ipv4):
    
    zone_id = get_zone_id(name)
    record_id = get_record_id(name, zone_id)
    if record_id == None:
        print(f'No record found with name {name} !')
        return False

    return update_Arecord_by_id(zone_id, record_id, ipv4)


def get_zone_ids():

    conn, headers = get_https_conn()

    conn.request('GET', '/client/v4/zones', headers=headers)

    res = conn.getresponse().read().decode()
    res_json = json.loads(res)
    
    zones = res_json['result']
    zone_ids = list(map(lambda zone: zone['id'], zones))

    return zone_ids

# Update DNS records when a server is not available
# ex_ipv4 is the ip address of unavailable server
def update_dns(ex_ipv4, ipv4):

    zone_ids = get_zone_ids()

    for zone_id in zone_ids:
        records = get_zone_records(zone_id)

        to_update_records = list(filter(lambda record: \
            record['type'] == 'A' and \
            record['content'] == ex_ipv4, \
            records))

        to_update_record_ids = list(map(lambda record: record['id'], to_update_records))    
        for record_id in to_update_record_ids:
            update_Arecord_by_id(zone_id, record_id, ipv4)

    return True