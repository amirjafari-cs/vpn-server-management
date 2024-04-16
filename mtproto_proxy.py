from paramiko import *
import threading
import os
from time import sleep

# Constant values
PROXY_PORT = 443
CTRLZ_ASCII = 26
SSH_PORT = 22

# Commands
install_requirements = 'apt install git curl build-essential libssl-dev zlib1g-dev'
clone_proxy_repo = 'git clone https://github.com/TelegramMessenger/MTProxy'
obtain_secret = 'curl -s https://core.telegram.org/getProxySecret -o proxy-secret'
obtain_telegram_config = 'curl -s https://core.telegram.org/getProxyConfig -o proxy-multi.conf'
generate_secret = 'head -c 16 /dev/urandom | xxd -ps'
mtproto_exists = 'test -e /root/MTProxy/objs/bin/mtproto-proxy && echo 1 || echo 0'


def run_proxy(client, secret, proxy_port):
    
    run_proxy_command = f'./mtproto-proxy -u nobody -p 8888 -H {proxy_port} -S {secret} --aes-pwd proxy-secret proxy-multi.conf -M 1\n'
    client.exec_command('cd /root/MTProxy/objs/bin/;' + \
        run_proxy_command)


def install_proxy(host, ssh_port, proxy_port, username, key_path):
    
    client = SSHClient()
    client.set_missing_host_key_policy(AutoAddPolicy)
    client.connect(hostname=host, port=ssh_port, username=username, key_filename=key_path)

    stdin, stdout, stderr = client.exec_command(install_requirements)
    stdin.write('y\n')
    stdin.close()
    
    client.exec_command(clone_proxy_repo)

    client.connect(hostname=host, port=ssh_port, username=username, key_filename=key_path)
    sftp = client.open_sftp()
    sftp.get('/root/MTProxy/Makefile', '.\\Makefile')
    makefile = open('.\\Makefile')
    makefile2 = open('.\\Makefile2', 'w')
    for line in makefile:
        if line.startswith('CFLAGS'):
            line = line[:-1] + ' -fcommon\n'
        
        makefile2.write(line)
    makefile.close()
    makefile2.close()
    sftp.put('.\\Makefile2', '/root/MTProxy/Makefile')
    sftp.close()
    os.remove('.\\Makefile')
    os.remove('.\\Makefile2')

    stdin, stdout, stderr = client.exec_command('cd /root/MTProxy/; make\n')
    done = False
    while not done:
        stdin, stdout, stderr = client.exec_command(mtproto_exists)
        test = stdout.read().decode().strip()
        done = (test == '1')
        sleep(2)

    client.set_missing_host_key_policy(AutoAddPolicy)
    client.connect(hostname=host, port=ssh_port, username=username, key_filename=key_path)
    sftp = client.open_sftp()
    sftp.get('/root/MTProxy/common/pid.c', '.\\pid.c')
    pid = open('.\\pid.c')
    pid2 = open('.\\pid2.c', 'w')
    for line in pid:
        if 'assert (!(p & 0xffff0000))' in line:
            line = '//' + line
        
        pid2.write(line)

    pid.close()
    pid2.close()

    sftp.put('.\\pid2.c', '/root/MTProxy/common/pid.c')
    sftp.close()
    os.remove('.\\pid.c')
    os.remove('.\\pid2.c')

    stdin, stdout, stderr = client.exec_command(f'cd /root/MTProxy/objs/bin/; \
        {obtain_secret}; \
        {obtain_telegram_config}; \
        {generate_secret};')
    
    secret = stdout.read().decode()
    secret = secret[:-1]
    stdout.close()

    client.connect(hostname=host, port=ssh_port, username=username, key_filename=key_path)
    thread = threading.Thread(target=run_proxy, args=(client, secret, proxy_port))
    thread.start()
    
    channel = client.invoke_shell()
    channel.send(chr(CTRLZ_ASCII))
    channel.close()
    client.exec_command('bg\n')
    client.exec_command('disown\n')

    client.close()

    return secret

