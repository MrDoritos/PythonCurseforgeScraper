#!/bin/python3

import time
import json
import importlib
import argparse
import os
import signal
import sys
import threading
import sqlite3
import re

sqlite_helper = importlib.import_module("sqlite_helper")
api_helper = importlib.import_module("api_helper")
config = importlib.import_module("config")
file_bucket = importlib.import_module(config.bucket_module)

db = sqlite_helper.Sqlite_helper(config.db_filepath, config.dry_run)
bucket = file_bucket.Filebucket(config.bucket_filepath, config.dry_run)
api = api_helper.Api_helper(db, config)

hour = 3600
day = hour * 24 #86400
week = day * 7 #604800
month = week * 4 #2419200
half_year = week * 26
year = week * 52

target_games = config.game_filter
target_categories = config.category_filter

interrupt_loop = False
busy_lock = threading.RLock() # signals interrupt main thread, use reentrant

def retrieve_games():
    global target_games
    append = len(target_games) == 0
    for result in api_helper.Depaginator(api, '/games', time_diff=week):
        for game_stub in result['data']:
            if interrupt_loop:
                return
            
            db.insert_game(game_stub)

            if config.download_media:
                dateModified = api.read_time(game_stub['dateModified'])
                assets = game_stub['assets']
                if assets:
                    bucket.try_insert_url(assets['iconUrl'], dateModified)
                    bucket.try_insert_url(assets['tileUrl'], dateModified)
                    bucket.try_insert_url(assets['coverUrl'], dateModified)

            if append:
                target_games.append(game_stub['id'])

def iterate_games():
    for game_id in target_games:
        if interrupt_loop:
            return

        if config.scrape_game_versions:
            api.get_json(f'/games/{game_id}/versions', write=True, use_local=True, time_diff=month)

def retrieve_categories():
    global target_categories
    append = len(target_categories) == 0
    for game_id in target_games:
        for result in api_helper.Depaginator(api, f'/categories?gameId={game_id}', time_diff=week):
            for category_stub in result['data']:
                if interrupt_loop:
                    return

                db.insert_category(category_stub)

                if config.download_media:
                    dateModified = api.read_time(category_stub['dateModified'])
                    bucket.try_insert_url(category_stub['iconUrl'], dateModified)

                if append:
                    target_categories.append(category_stub['id'])

def iterate_categories():
    for category_id in target_categories:
        # Iterate category list
        db.cur.execute('SELECT gameId FROM categories WHERE id=?', (category_id,))
        game_id = db.cur.fetchone()[0]
        url = f'/mods/search?categoryId={category_id}&gameId={game_id}&sortField=3&sortOrder=desc'
        stale_threshold = 0
        
        # Stale in a day or less
        for result in api_helper.Depaginator(api, url, time_diff=day):
            stale_count = 0

            for mod_stub in result['data']:
                if interrupt_loop:
                    return
                
                # Iterate search listing for addon ids
                if not db.field_exists('mods', mod_stub['id']):
                    db.insert_mod(mod_stub)
                    continue
                
                db.cur.execute('SELECT json FROM mods WHERE id=?', (mod_stub['id'],))
                stale_stub = json.loads(db.cur.fetchone()[0])

                mod_date_json = mod_stub['dateModified']
                stale_date_json = stale_stub['dateModified']

                mod_date = api.read_time(mod_date_json)
                stale_date = api.read_time(stale_date_json)

                if mod_date > stale_date:
                    db.insert_mod(mod_stub)
                    continue

                stale_count += 1

            print('Stale count:', stale_count, 'Result count:', len(result['data']), 'Threshold:', stale_threshold)

            if stale_count == len(result['data']) and not config.full:
                if stale_threshold > 1:
                    print("All mods were stale, breaking")
                    break
                else:
                    stale_threshold += 1

def ismodurl(url):
    reg = re.compile('^/mods/[0-9]+.*')
    return reg.search(url) is not None

def getmodid(url):
    reg = re.compile('^/mods/([0-9]+)')
    return reg.search(url).group(1)

def getmodtime(json_raw):
    j = json.loads(json_raw)
    return api.read_time(j['dateModified'])

def iterate_mods():
    db.con.create_function('ISMODURL', 1, ismodurl)
    db.con.create_function('GETMODID', 1, getmodid)
    db.con.create_function('GETMODTIME', 1, getmodtime)
    
    cur_2 = db.con.cursor()
    modifications = 0
    old_check = False

    # accumulate all mods that require a fetch
    cur_2.execute("ATTACH DATABASE ':memory:' AS dbtemp")
    cur_2.execute("CREATE TABLE dbtemp.api_calls(url,time,json)")
    cur_2.execute("CREATE TABLE dbtemp.stale_mods(id INTEGER PRIMARY KEY,name,slug,gameId,json,upstream_time,downstream_time)")

    print("Extracting most recent API calls")
    cur_2.execute("INSERT INTO dbtemp.api_calls SELECT * FROM (SELECT * FROM (SELECT GETMODID(url) AS 'url',time,'' AS 'json' FROM api WHERE ISMODURL(url)) GROUP BY url HAVING MAX(time))")

    print("Generating list of out-of-date mods")
    cur_2.execute('INSERT INTO dbtemp.stale_mods SELECT * FROM (SELECT mods.id,mods.name,mods.slug,mods.gameId,mods.json,GETMODTIME(mods.json),dbtemp.api_calls.time FROM mods INNER JOIN dbtemp.api_calls ON dbtemp.api_calls.url=mods.id WHERE GETMODTIME(mods.json) > dbtemp.api_calls.time)')
    
    cur_2.execute('SELECT COUNT(*) FROM dbtemp.stale_mods')
    print(f'Fetching {cur_2.fetchone()[0]} mods')

    cur_2.execute('SELECT * FROM dbtemp.stale_mods')
    for row in cur_2:
        if interrupt_loop:
            return
        
        json_data = None
        url = None
        modify_time = None
        last_request = None
        depag = None

        if old_check:
            # Iterate addons for addon files
            json_data = json.loads(row[5])
            url = f'/mods/{json_data["id"]}/files?'
            depag = api_helper.Depaginator(api, url, use_local=False)

            modify_time = api.read_time(json_data['dateModified'])
            last_request = api.when_last_request(depag.current_url)

            if modify_time < last_request and not config.full:
                print(f'{json_data["id"]}.', end='', flush=True)
                continue
        else:
            db.cur.execute('SELECT * FROM mods WHERE id=? LIMIT 1', (row[0],))
            _r = db.cur.fetchone()
            json_data = json.loads(_r[5])
            url = f'/mods/{json_data["id"]}/files?'
            depag = api_helper.Depaginator(api, url, use_local=False)

            modify_time = api.read_time(json_data['dateModified'])
            last_request = api.when_last_request(depag.current_url)


        if config.scrape_descriptions:
            api.get_json(f'/mods/{json_data["id"]}/description', write=True, use_local=True, time_diff=week)

        if config.download_media:
            logo = json_data['logo']
            screenshots = json_data['screenshots']
            authors = json_data['authors']

            if logo:
                bucket.try_insert_url(logo['url'], modify_time, None, logo['id'], logo['title'])
                bucket.try_insert_url(logo['thumbnailUrl'], modify_time, None, logo['id'], logo['title'])

            if authors:
                for author in authors:
                    if 'avatarUrl' in author:
                        bucket.try_insert_url(author['avatarUrl'], modify_time, None, author['id'], None)

            if screenshots:
                for screenshot in screenshots:
                    bucket.try_insert_url(screenshot['url'], modify_time, None, screenshot['id'], None)
                    bucket.try_insert_url(screenshot['thumbnailUrl'], modify_time, None, screenshot['id'], None)

        print(f'Updating files for {json_data["slug"]} ({json_data["id"]}) ({modify_time} >= {last_request} (up/down) ({last_request - modify_time}))')

        for result in depag:
            for file_stub in result['data']:
                db.insert_file(file_stub)
                file_time = api.read_time(file_stub['fileDate'])

                if config.scrape_changelogs:
                    api.get_json(f'/mods/{json_data["id"]}/files/{file_stub["id"]}/changelog', write=True, use_local=True, time_diff=week)

                if config.download_files:
                    bucket.try_insert_url(file_stub['downloadUrl'], file_time, file_stub['fileLength'], file_stub['id'], file_stub['fileName'])

        modifications += 1

        if modifications > 20:
            db.save()
            modifications = 0

# could be improved

def signal_handler(sig, frame):
    global interrupt_loop, busy_lock
    print("Caught kill signal, interrupting loop")
    interrupt_loop = True
    with busy_lock: #this way the resources are frozen until we exit safely
        print("Saving progress, releasing held resources, and exiting")
        # Currently these actions are implied
        # db.close()
        # bucket.close()
        sys.exit(0)

for sig in [signal.SIGINT, signal.SIGTERM, signal.SIGQUIT]:
    signal.signal(sig, signal_handler)

with busy_lock:
    if 'game_retrieve' not in config.skip:
        print('Game Retrieval')
        retrieve_games()

with busy_lock:
    if 'category_retrieve' not in config.skip:
        print('Category Retrieval')
        retrieve_categories()

with busy_lock:
    print("Target games:", target_games)
    print("Target categories:", target_categories)

with busy_lock:
    if not config.dry_run:
        print('Save Progress')
        db.save()

with busy_lock:
    if 'game_iterate' not in config.skip:
        print('Game Iteration')
        iterate_games()

with busy_lock:
    if 'category_iterate' not in config.skip:
        print('Category Iteration')
        iterate_categories()

with busy_lock:
    if not config.dry_run:
        print('Save Progress')
        db.save()

with busy_lock:
    if 'mod_iterate' not in config.skip:
        print('Mod Iteration')
        iterate_mods()

with busy_lock:
    if not config.dry_run:
        print('Save Progress')
        db.save()

with busy_lock:
    print("Done")