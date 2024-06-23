#!/bin/python3

import json
import sqlite3

con = sqlite3.connect('curseforge/curseforge.db')
cur = con.cursor()

cur.execute('SELECT json FROM mods')

with open('curseforge/source_urls.txt', 'w') as f:
    for row in cur:
        mod = json.loads(row[0])
        if mod.get('links', None) != None:
            if mod['links'].get('sourceUrl', None) != None:
                srcUrl = mod['links']['sourceUrl']
                if srcUrl != 'null' and srcUrl != "None" and srcUrl != "":
                    f.write(f'{mod["slug"]},{mod["links"]["sourceUrl"]}\n')