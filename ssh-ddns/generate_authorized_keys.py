#!/usr/bin/env python
# -*- coding: utf-8 -*-

import argparse
import yaml

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('hosts_file')

    args = parser.parse_args()
    hosts_config = yaml.safe_load(open(args.hosts_file, 'r'))

    for host in hosts_config['hosts']:
        print hosts_config['authorized_keys_template'].format(**host)



if __name__ == '__main__':
    main()
