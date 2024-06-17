#!/bin/python3

import sqlite3
import sys
import os
import requests
import json
import time
import importlib

sqlite_helper = importlib.import_module('sqlite_helper')
api_helper = importlib.import_module('api_helper')
config = importlib.import_module('config')

#Global State

#Set these arrays to change which games / categories are captured
#Just run the program to see the ids when they populate in the database

target_games = [] #432
target_categories = [] #399

#Start program

db = sqlite_helper.Sqlite_helper(config.output_dir + '/curseforge.db')
api = api_helper.Api_helper(db)

for game_stub in api.get_json('/games', True, True)['data']:
    db.insert_game(game_stub)

    game_id = game_stub['id']

    if len(target_games) > 0 and game_id not in target_games: 
        continue
    
    print('Processing game: ' + game_stub['name'])

    game = api.get_json('/games/' + str(game_id), True, True)
    versions = api.get_json(f'/games/{game_id}/versions', True, True)
    categories = api.get_json(f'/categories?gameId={game_id}', True, True)

    for category_stub in categories['data']:
        db.insert_category(category_stub)

        category_id = category_stub['id']

        if len(target_categories) > 0 and category_id not in target_categories: 
            continue

        print('Processing category: ' + category_stub['name'])

        for result in api_helper.Depaginator(api, f'/mods/search?categoryId={category_id}&gameId={game_id}&sortField=3'):
            for mod_stub in result['data']:
                db.insert_mod(mod_stub)

        db.con.commit()

cur_2 = db.con.cursor()
cur_2.execute("SELECT * FROM mods")

for mod_row in cur_2:
    print('Processing mod: ' + mod_row[1])
    for result in api_helper.Depaginator(api, f'/mods/{mod_row[0]}/files?'):
        for file_stub in result['data']:
            db.insert_file(file_stub)
    db.con.commit()

print("Done")

db.con.commit()
db.con.close()