#!/bin/python3

import json
import sqlite3
import importlib

sqlh = importlib.import_module("sqlite_helper")
config = importlib.import_module("config")

# INSERT or IGNORE into tmp_mods SELECT * FROM mods

db = sqlh.Sqlite_helper('./curseforge/curseforge.db')

# Save each primary category to files

db.cur.execute("SELECT * FROM mods")

url_slugs = dict()
slug_files = dict()

for row in db.cur:
    json_data = json.loads(row[5])
    url = json_data['links']['websiteUrl']
    if len(url):
        slug = url.split('/')[-2]

        if slug:
            if slug_files.get(slug,0)==0:
                slug_files[slug] = open(f'{config.output_dir}/{slug}.txt', 'w')

            v = url_slugs.get(slug, 0)
            url_slugs[slug] = v + 1

            slug_files[slug].write(f'{json_data["id"]},{json_data["slug"]}\n')
        else:
            print(f'No slug found for: {url} ({json_data["slug"]})')

for slug in slug_files:
    slug_files[slug].close()

print(url_slugs)

# Ideal file count

ideal_file_count = 0
db.cur.execute("SELECT * FROM api")
for api_raw in db.cur:
    if 'files' in api_raw[0]:
        json_data = json.loads(api_raw[2])
        ideal_file_count += len(json_data['data'])
print("Theoretical file count:", ideal_file_count)

# Save files to a download list

print("Saving download links")

db.cur.execute("SELECT * FROM files")

with open(f'{config.output_dir}/download_list.txt', 'w') as f:
    for row in db.cur:
        json_data = json.loads(row[5])
        f.write(f'{json_data["id"]},{json_data["downloadUrl"]}\n')

print("Done")