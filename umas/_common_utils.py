import os
import pickle
import struct
import time
import socket
import json
import sys


def get_job_id():
    for var in ['UMA_JOBID', 'PBS_JOBID', 'LSB_JOBID', 'SLURM_JOB_ID', 'PJM_JOBID']:
        jobid = os.environ.get(var)
        if jobid:
            return jobid
    user = os.environ.get('USER') or os.environ.get('LOGNAME') or 'unknown'
    return f'{user}_default'


def send_pickle(conn, obj):
    data = pickle.dumps(obj)
    conn.sendall(struct.pack("!I", len(data)))
    conn.sendall(data)


def recv_pickle(conn):
    raw_len = conn.recv(4)
    if not raw_len:
        return None
    msg_len = struct.unpack("!I", raw_len)[0]
    data = b""
    while len(data) < msg_len:
        packet = conn.recv(msg_len - len(data))
        if not packet:
            break
        data += packet
    return pickle.loads(data)


def get_port_file():
    job_id = get_job_id()
    port_file = f'/tmp/umas_port_{job_id}.json'
    return port_file


def get_port_number():
    port_file = get_port_file()
    if not os.path.isfile(port_file):
        print(f'Port file is not found.: {port_file}')
        sys.exit(1)
    with open(port_file) as f:
        port = json.load(f)['port']
        return port


def save_port_file(port):
    port_file = get_port_file()
    with open(port_file, 'w') as f:
        json.dump({'port': port}, f)


def remove_port_file():
    port_file = get_port_file()
    try:
        os.remove(port_file)
    except Exception as e:
        pass


def send_task(task):
    port_file = get_port_file()

    # Wait until port file is found (max 300 sec)
    timeout = 300
    interval = 0.5
    elapsed = 0.0
    while not os.path.isfile(port_file):
        time.sleep(interval )
        elapsed += interval
        if elapsed >= timeout:
            raise TimeoutError(f'Timeout: Port file not found after {timeout} seconds: {port_file}')

    port = get_port_number()

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.connect(('localhost', port))
        send_pickle(s, task)
        result = recv_pickle(s)
        return result


def read_int_list_string(list_string):
    blocks = [x.strip() for x in list_string.strip().replace(',', ' ').replace(';', ' ').replace(':', ' ').split()]
    index = []
    for block in blocks:
        if '-' in block:
            start, end = [int(x) for x in block.split('-')]
            for i in range(start, end + 1):
                index.append(i)
        else:
            index.append(int(block))
    return index


def get_device_list(num_workers, gpu_number_list):
    device_list = []
    for i in range(num_workers):
        if i < len(gpu_number_list):
            device_list.append(f'cuda:{gpu_number_list[i]}')
        else:
            device_list.append('cpu')
    return device_list

