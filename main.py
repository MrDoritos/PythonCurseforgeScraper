#!/bin/python3

import time
import json
import importlib
import argparse
import os

sqlite_helper = importlib.import_module("sqlite_helper")
api_helper = importlib.import_module("api_helper")
config = importlib.import_module("config")
file_bucket = importlib.import_module("file_bucket")

db = sqlite_helper.Sqlite_helper(config.db_filepath, config.dry_run)
bucket = file_bucket.Filebucket(config.bucket_filepath, config.dry_run)
api = api_helper.Api_helper(db, config)

hour = 3600
day = hour * 24 #86400
week = day * 7 #604800
month = week * 4 #2419200

target_games = config.game_filter
target_categories = config.category_filter

def retrieve_games():
    global target_games
    append = len(target_games) == 0
    for result in api_helper.Depaginator(api, '/games', time_diff=week):
        for game_stub in result['data']:
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
        if config.scrape_game_versions:
            api.get_json(f'/games/{game_id}/versions', write=True, use_local=True, time_diff=month)

def retrieve_categories():
    global target_categories
    append = len(target_categories) == 0
    for game_id in target_games:
        for result in api_helper.Depaginator(api, f'/categories?gameId={game_id}', time_diff=week):
            for category_stub in result['data']:
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

        # If results for category search results updated in the last day
        for result in api_helper.Depaginator(api, url, time_diff=day):
            stale_count = 0

            for mod_stub in result['data']:
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

            print('Stale count:', stale_count, 'Result count:', len(result['data']))

            if stale_count == len(result['data']) and not config.full:
                print("All mods were stale, breaking")
                break

def iterate_mods():
    cur_2 = db.con.cursor()
    cur_2.execute('SELECT * FROM mods')

    modifications = 0

    for row in cur_2:
        # Iterate addons for addon files
        json_data = json.loads(row[5])
        url = f'/mods/{json_data["id"]}/files?'

        depag = api_helper.Depaginator(api, url, use_local=False)

        modify_time = api.read_time(json_data['dateModified'])
        last_request = api.when_last_request(depag.current_url)

        if modify_time < last_request and not config.full:
            print(f'{json_data["id"]}.', end='', flush=True)
            continue

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

        print(f'Updating files for {json_data["slug"]} ({json_data["id"]}) ({modify_time} >= {last_request})')

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

retrieve_games()
retrieve_categories()
print("Target games:", target_games)
print("Target categories:", target_categories)
db.save()

iterate_games()
iterate_categories()
db.save()

iterate_mods()
db.save()

print("Done")
