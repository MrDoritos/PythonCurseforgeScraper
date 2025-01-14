#!/bin/python3

import json
import sqlite3
import importlib
import os
import datetime

sqlh = importlib.import_module("sqlite_helper")
config = importlib.import_module("config")

db = sqlh.Sqlite_helper(config.db_filepath, dry_run=True)
dbcur = db.con.cursor()

# i dont trust python data structures?
# i dont know if all ids are unique lol

tmp_con = sqlite3.connect(":memory:")
tcur = tmp_con.cursor()
tcur.execute("CREATE TABLE entries(id, name, slug, parent, time)")

# detect mod insertions / deletions
# use time field of api table

tablecur = db.con.cursor()

tablecur.execute("SELECT COUNT(*) FROM api")

entry_count = tablecur.fetchone()[0]

tablecur.execute("SELECT * FROM api")

print(f"Processing {entry_count} records")

counter = 0

for api_raw in tablecur:
    json_data = json.loads(api_raw[2])
    time_point = api_raw[1]

    if counter % 5 == 0:
        print(f"\r{counter}/{entry_count}", end='', flush=True)
    counter += 1

    if not json_data and not 'data' in json_data:
        continue

    for entry in json_data['data']:
        if isinstance(entry, str) or not 'id' in entry:
            continue

        id = entry['id']
        name = id
        slug = id
        parent = id
        if 'displayName' in entry:
            name = entry['displayName']
        if 'name' in entry:
            name = entry['name']
        if 'slug' in entry:
            slug = entry['slug']
        if 'gameId' in entry:
            parent = entry['gameId']
        if 'primaryCategoryId' in entry:
            parent = entry['primaryCategoryId']
        if 'modId' in entry:
            parent = entry['modId']

        tcur.execute("INSERT OR REPLACE INTO entries(id, name, slug, parent, time) VALUES(?,?,?,?,?)",
                     (id, name, slug, parent, time_point))


# print data
tcur.execute("SELECT * FROM entries ORDER BY time")
for entry in tcur:
    print(entry)