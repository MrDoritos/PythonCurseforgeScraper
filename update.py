#!/bin/python3

import time
import json
import importlib

sqlite_helper = importlib.import_module("sqlite_helper")
api_helper = importlib.import_module("api_helper")
config = importlib.import_module("config")

db = sqlite_helper.Sqlite_helper(config.output_dir + '/curseforge.db')
api = api_helper.Api_helper(db)

day = 86400
hour = 3600
week = 604800

target_games = [432]
target_categories = []

def when_last_request(url):
    if not db.request_exists(url):
        return 0
    
    db.cur.execute('SELECT time FROM api WHERE url=? ORDER BY time DESC', (url,))
    return db.cur.fetchone()[0]

def should_update_entries(url, time_diff):
    req_time = when_last_request(url)
    now_time = time.time()
    res = req_time + time_diff < now_time
    
    debug = f'({req_time} + {time_diff} > {now_time})'

    if res:
        print("Updating entries for", url, debug)
    else:
        print("Not updating entries for", url, debug)

    return res

def read_time(stime):
    try:
        return time.mktime(time.strptime(stime, '%Y-%m-%dT%H:%M:%S.%fZ'))
    except:
        return time.mktime(time.strptime(stime, '%Y-%m-%dT%H:%M:%SZ'))

if should_update_entries('/games', week):
    for result in api_helper.Depaginator(api, '/games', use_local=False):
        for game_stub in result['data']:
            db.insert_game(game_stub)

if len(target_games) == 0: 
    # Determine game list from db
    db.cur.execute('SELECT DISTINCT gameId FROM categories')
    target_games = [x[0] for x in db.cur.fetchall()]

print("Target games:", target_games)

for game_id in target_games:
    if should_update_entries(f'/categories?gameId={game_id}', week):
        for result in api_helper.Depaginator(api, f'/categories?gameId={game_id}', use_local=False):
            for category_stub in result['data']:
                db.insert_category(category_stub)

if len(target_categories) == 0:
    # Determine category list from db
    db.cur.execute('SELECT id,gameId FROM categories')
    target_categories = [x[0] for x in db.cur.fetchall() if x[1] in target_games]

print("Target categories:", target_categories)

for category_id in target_categories:
    # Iterate category list
    db.cur.execute('SELECT gameId FROM categories WHERE id=?', (category_id,))
    game_id = db.cur.fetchone()[0]
    url = f'/mods/search?categoryId={category_id}&gameId={game_id}&sortField=3&sortOrder=desc'

    depag = api_helper.Depaginator(api, url, use_local=False)
    
    if should_update_entries(depag.current_url, day):
        # If results for category search results updated in the last day
        for result in depag:
            stale_count = 0
            last_request = when_last_request(depag.current_url)
            print(f'Last request for ({depag.current_url}): {last_request}')

            for mod_stub in result['data']:
                # Iterate search listing for addon ids
                if not db.field_exists('mods', mod_stub['id']):
                    db.insert_mod(mod_stub)
                    continue
                
                db.cur.execute('SELECT json FROM mods WHERE id=?', (mod_stub['id'],))
                stale_stub = json.loads(db.cur.fetchone()[0])

                mod_date_json = mod_stub['dateModified']
                stale_date_json = stale_stub['dateModified']

                mod_date = read_time(mod_date_json)
                stale_date = read_time(stale_date_json)

                if mod_date > stale_date:
                    db.insert_mod(mod_stub)
                    continue

                stale_count += 1

            print('Stale count:', stale_count, 'Result count:', len(result['data']))

            if stale_count == len(result['data']):
                print("All mods were stale, breaking")
                break

db.con.commit()

cur_2 = db.con.cursor()
cur_2.execute('SELECT * FROM mods')

for row in cur_2:
    # Iterate addons for addon files
    json_data = json.loads(row[5])
    url = f'/mods/{json_data["id"]}/files?'

    depag = api_helper.Depaginator(api, url, use_local=False)

    modify_time = read_time(json_data['dateModified'])
    last_request = when_last_request(depag.current_url)

    if modify_time < last_request:
        print(f'{json_data["id"]}.', end='')
        continue

    print(f'Updating files for {json_data["slug"]} ({json_data["id"]}) ({modify_time} >= {last_request})')
    for result in depag:
        for file_stub in result['data']:
            db.insert_file(file_stub)

    db.con.commit()

print("Done")

db.con.commit()
db.con.close()