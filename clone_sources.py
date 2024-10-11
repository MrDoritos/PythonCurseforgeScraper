#!/bin/python3

import os
import sys
import time
from datetime import datetime

srcs = 'curseforge/source_urls.txt'

if not os.path.exists(srcs):
    print('No sources')
    sys.exit(1)

pairs = []

with open(srcs, 'r') as file:
    for line in file:
        slug = line.split(',')[0]
        url = line[len(slug)+1:]
        pairs.append((slug, url))

base_dir = os.getcwd()    

def get_prefix(slug:str):
    for c in slug:
        if c.isalpha():
            return c.lower()
    return '0'

with open('curseforge/failed_sources.txt', 'w') as file:
    for slug, url in pairs:
        print(f'Downloading {slug} from {url.strip()}')
        
        slug_dir = os.path.join(base_dir, f'curseforge/bucket/{get_prefix(slug)}/{slug}')
        git_dir = os.path.join(slug_dir, f'{slug}/')

        #if not os.path.exists(out_dir):
        #    os.mkdir(slug)
        os.makedirs(os.path.dirname(git_dir), exist_ok=True)
        #os.chdir(out_dir)

        os.system(f'git clone --recursive --mirror "{url.strip()}" "{git_dir}"')

        file_count = len(os.listdir(git_dir))
        print('Number of files:', file_count)

        date = datetime.now().strftime('%y%m%d')
        os.system(f'7z a "{slug_dir}/{date}{slug}.7z" "{git_dir}" -y')
        os.system(f'7z a "{slug_dir}/{slug}.tar" "{git_dir}" -ttar -y -sdel')
        
        if file_count < 1:
            file.write(f'{slug},{url}\n')

        #input()
        #os.chdir(base_dir)