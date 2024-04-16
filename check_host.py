import requests
from paramiko import *
import nmap

# Constant values
SSH_TIMEOUT = 3
tehran_node = 'ir1.node.check-host.net'
shiraz_node = 'ir3.node.check-host.net'
esfehan_node = 'ir5.node.check-host.net'
karaj_node = 'ir6.node.check-host.net'

# List of nodes to check ping with them
nodes = [tehran_node, karaj_node, shiraz_node, esfehan_node]

def check_server_ping(server): # server is /v1.3/server/info endpoint object
    
    try:
        host = server['iface']['v4'][0]['address']
    except Exception as e:
        print(e)
        return None
    
    check_url = 'https://check-host.net/check-ping?' + \
        f'host={host}&' + \
        ''.join([f'node={node}&' for node in nodes[:-1]]) + \
        f'node={nodes[-1]}'
    headers = {
        'Accept': 'application/json'
    }

    try:
        response = requests.get(check_url, headers=headers)
        request_id = response.json()['request_id']
        result_url = f'https://check-host.net/check-result/{request_id}'
    
    except Exception as e:
        print(e)
        return None

    try:
        result_ready = False
        while not result_ready:
            response = requests.get(result_url, headers=headers)
            response_json = response.json()
            node_results = [response_json[node] for node in nodes]
            result_ready = all(list(map(lambda x: x != None, node_results)))
    
    except Exception as e:
        print(e)
        return None

    ping = True
    try:
        node_results = [response_json[node][0] for node in nodes]
        node_results = [all('OK' in ping_result for ping_result in node_result) \
                        for node_result in node_results]
        ping = all(node_results)
    except:
        ping = False

    return ping

def check_server_ssh_(server): # server is /v1.3/server/info endpoint object
    
    try:
        host = server['iface']['v4'][0]['address']
        username = 'root'
        password = server['password']
        ssh_port = 22
    except Exception as e:
        print(e)
        return None
    
    ssh = True
    try:
        client = SSHClient()
        client.set_missing_host_key_policy(AutoAddPolicy)
        client.connect(hostname=host, port=ssh_port, username=username, password=password, timeout=SSH_TIMEOUT)
        client.close()
    except TimeoutError:
        ssh = False
    except Exception as e:
        print(e)
        return None

    return ssh

def check_server_ssh(server): # server is /v1.3/server/info endpoint object

    try:
        host = server['iface']['v4'][0]['address']
        ssh_port = 22
    
    except Exception as e:
        print(e)
        return None

    try:
        scanner = nmap.PortScanner()
        scanner.scan(host, f'{ssh_port}')
        res = scanner.scanstats()
    
    except Exception as e:
        print(e)
        return None
    
    return res['uphosts'] == '1'



def check_server(server): # server is /v1.3/server/info endpoint object
    return check_server_ping(server) and \
        check_server_ssh(server)
