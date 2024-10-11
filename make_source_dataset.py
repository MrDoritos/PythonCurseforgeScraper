#!/bin/python3

import os
import sys
import sqlite3
import time

base_dir = os.getcwd()
data_dir = os.path.join(base_dir, 'curseforge/')

dir = os.path.join(data_dir, 'bucket/')
srcs = os.path.join(data_dir, 'source_urls.txt')
tmp_dir = os.path.join(data_dir, 'tmp/')


if not os.path.exists(srcs) or not os.path.exists(dir):
    print('Run other scripts first')
    sys.exit(1)

con = sqlite3.connect('curseforge/dataset.db')
cur = con.cursor()

cur.execute('CREATE TABLE IF NOT EXISTS train (slug TEXT, repo_id TEXT, file_path TEXT, content TEXT)')

def get_prefix(slug:str):
    for c in slug:
        if c.isalpha():
            return c.lower()
    return '0'

with open(srcs, 'r') as srcs_file:
    for line in srcs_file:
        slug = line.split(',')[0]
        url = line[len(slug)+1:].strip()
        
        prefix = get_prefix(slug)

        slug_dir = os.path.join(base_dir, f'{dir}/{prefix}/{slug}')
        #tmp_dir = os.path.join(base_dir, f'tmp')
        tmp_mirror = os.path.join(tmp_dir, slug)
        tmp_git = tmp_mirror + '.git'

        if not os.path.exists(slug_dir):
            print(f'No directory for {slug}')
            continue

        tar_path = None

        for file in os.listdir(slug_dir):
            if file.endswith('.tar'):
                tar_path = os.path.join(slug_dir, file)
                break

        if tar_path is None:
            print(f'No tar file for {slug}')
            continue
        
        os.makedirs(tmp_dir, exist_ok=True)

        os.system(f'tar -xf {tar_path} -C {tmp_dir}')
        time.sleep(0.5)
        os.system(f'git clone "{tmp_mirror}" "{tmp_git}"')
        time.sleep(0.5)

        good_files = [
            'md',
            'txt',
            'json',
            'gradle',
            'properties',
            'xml',
            'yml',
            'yaml',
            'java',
            'kt',
            'kts',
            'groovy',
            'js',
            'ts',
            'css',
        ]

        print(f'Processing {slug} {url}')

        files = [os.path.join(dp, f) for dp, dn, filenames in os.walk(tmp_git) for f in filenames if f.endswith(tuple(good_files))]

        #for file in os.listdir(tmp_git):
        #for _,_,files in os.walk(tmp_git):
        for file in files:
            rp = file[len(tmp_git)+1:]

            if not file.endswith(tuple(good_files)):
                continue

            if not os.path.isfile(file):
                continue

            try:
                with open(file, 'rb') as f:
                    #print(f'{file} -> {rp}')
                    cur.execute('INSERT INTO train (slug, repo_id, file_path, content) VALUES (?, ?, ?, ?)', (slug, url, rp, f.read()))
            except:
                pass

        os.system(f'rm -r {tmp_dir}/*')

        con.commit()

        #if input() in ['q', 'quit', 'exit']:
        #    break

con.commit()
con.close()
