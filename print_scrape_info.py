#!/bin/python3

import json
import sqlite3
import importlib
sqlh = importlib.import_module("sqlite_helper")

# INSERT or IGNORE into tmp_mods SELECT * FROM mods

db = sqlh.Sqlite_helper('./curseforge/curseforge.db')

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
                slug_files[slug] = open(f'./{slug}.txt', 'w')

            v = url_slugs.get(slug, 0)
            url_slugs[slug] = v + 1

            slug_files[slug].write(f'{json_data["id"]},{json_data["slug"]}\n')
        else:
            print("No slug found for: " + url)

for slug in slug_files:
    slug_files[slug].close()

print(url_slugs)