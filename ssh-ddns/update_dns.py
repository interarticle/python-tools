#!/usr/bin/env python
# -*- coding: utf-8 -*-
import argparse
import yaml
import subprocess
import os
import sys
import logging

logging.basicConfig(
    format='%(asctime)s - %(process)d - %(name)s %(levelname)s: %(message)s',
    stream=sys.stdout,
)
logging.getLogger().setLevel(logging.INFO)
log = logging.getLogger(__name__)

def dig(server, host):
    result = subprocess.check_output(['dig', '+noall', '+answer', '@' + server, 'A', host])
    result_list = result.strip().split('\n')

    return [record.strip().split('\t')[-1] for record in result_list if record.strip()]

def unlist(lst):
    if len(lst) > 1:
        raise ValueError('more than one record received')
    return lst[0]

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('hosts_file')
    parser.add_argument('host_name')

    args = parser.parse_args()
    hosts_obj = yaml.safe_load(open(args.hosts_file, 'r'))

    for host in hosts_obj['hosts']:
        if host['host'] == args.host_name:
            break

    if host['host'] != args.host_name:
        raise ValueError('invalid host name ' + args.host_name + '. unconfigured')

    log.info('host is %s', host['host'])
    log.info('SSH_CONNECTION %s', os.environ['SSH_CONNECTION'])
    log.info('command %s', os.environ.get('SSH_ORIGINAL_COMMAND', '(none)'))
    client_ip = os.environ['SSH_CLIENT'].split(' ')[0]
    log.info('detected client ip %s', client_ip)

    updates = []
    for a_record in host['a_records']:
        current_ip = unlist(dig(hosts_obj['bind_server'], a_record))
        if current_ip != client_ip:
            log.info('host %s current has %s, needs to be updated to %s', a_record, current_ip, client_ip)
            updates.append(a_record)

    if os.environ.get('SSH_ORIGINAL_COMMAND') != 'commit':
        log.warn('dry run. exiting.')
        exit(0)

    if not updates:
        log.info('no changes. nothing to be done.')
        return

    p_nsupdate = subprocess.Popen(['nsupdate', '-k', hosts_obj['nssec_key']], stdin=subprocess.PIPE, stderr=subprocess.STDOUT)
    p_nsupdate.stdin.write('server {server}\n'.format(server=hosts_obj['bind_server']))
    p_nsupdate.stdin.flush()
    for a_record in updates:
        log.info('updating %s to %s', a_record, client_ip)
        p_nsupdate.stdin.write('update delete {record} A\n'.format(record=a_record))
        p_nsupdate.stdin.write('update add {record} {ttl} A {client_ip}\n'.format(
            record=a_record, ttl=hosts_obj['ttl'], client_ip=client_ip))
        p_nsupdate.stdin.write('show\n')
        p_nsupdate.stdin.flush()
        p_nsupdate.stdin.write('send\n')
        p_nsupdate.stdin.flush()

    p_nsupdate.stdin.close()

    p_nsupdate.wait()
    exit(p_nsupdate.poll())



if __name__ == '__main__':
    main()
