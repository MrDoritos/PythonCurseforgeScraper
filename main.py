#!/bin/python3

import sqlite3
import sys
import os
import requests
import json
import time

#Global State

api_url = 'https://api.curseforge.com/v1'
output_dir = './curseforge'

con = None
cur = None
api_key = None

target_games = [432]
target_categories = [399]

with open('api_key.txt', 'r') as f:
    api_key = f.read().strip()

client = requests.Session()

client.headers.update({'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/87.0.4280.141 Safari/537.36 OverwolfClient/0.204.0.1'})
client.headers.update({'Accept': 'application/json'})
client.headers.update({'Accept-Encoding': 'gzip'})
client.headers.update({'x-api-key': api_key})
client.headers.update({'Authorization': 'OAuth'})
client.headers.update({'X-Twitch-Id': ''})

last_request = time.time() - 1

#Helper functions

def get_retry(url, retries=0):
    global last_request
    try:
        print('Making request to: ' + url, end=' ')

        if (last_request + 1) > time.time():
            ms = (last_request + 1) - time.time()
            print('Waiting for ' + str(ms) + 'ms', end=' ')
            time.sleep(ms)

        last_request = time.time()
        r = client.get(api_url + url)
        print('Got response: ' + str(r.status_code))
        return r
    except:
        print('Request failed')
        if retries > 4:
            raise
        print('Retrying request attempt: ' + str(retries + 1))
        return get_retry(url, retries + 1)

def write_file(path, data :str):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w') as f:
        f.write(data)

def write_json(path, data: dict):
    write_file(path, json.dumps(data, indent=4))

def request_exists(url:str):
    cur.execute('SELECT count(*) FROM api WHERE url=?', (url,))
    return cur.fetchone()[0] == 1

def insert_request(url:str, json_data:str, time):
    cur.execute('INSERT OR REPLACE INTO api(url, json, time) VALUES(?,?,?)', (url, json.dumps(json_data), time))

def get_request(url:str):
    cur.execute('SELECT json FROM api WHERE url=?', (url,))
    return cur.fetchone()[0]

def get_json(url, write=False, use_local=False):
    if use_local and request_exists(url):
        try:
            print('Using local database: ' + url)
            return json.loads(get_request(url))
        except Exception as e:
            print('Failed to read local database: ' + url)
            print(e)
            pass    

    json_data = get_retry(url).json()

    if write:
        insert_request(url, json_data, last_request)

    return json_data

class Depaginator:
    def __init__(self, url, index=0, pageSize=50):
        self.url = url
        self.index = index
        self.pageSize = pageSize
        self.page = None
    
    def get_page(self):
        append = f'index={self.index}&pageSize={self.pageSize}'
        new_url = self.url
        if self.url[-1] == '?' or self.url[-1] == '&':
            new_url = self.url + append #Remove first &
        else:
            new_url = self.url + '&' + append 
        return get_json(new_url, True, True)

    def __iter__(self):
        print("Getting page 0", end=' ')
        self.page = self.get_page()
        return self
    
    def __next__(self):
        x = self.page

        if self.index + self.page['pagination']['resultCount'] >= self.page['pagination']['totalCount']:
            raise StopIteration()

        print(f"Getting ({self.index}/{self.page['pagination']['totalCount']})", end=' ')

        self.index = self.index + self.pageSize

        try:
            self.page = self.get_page()
        except:
            raise StopIteration()
        
        return x

def table_exists(table:str):
    cur.execute("SELECT count(*) FROM sqlite_master WHERE type='table' AND name=?", (table,))
    return cur.fetchone()[0] == 1

def field_exists(table:str, id:int):
    cur.execute(f'SELECT count(*) FROM {table} WHERE id=?', (id,))
    return cur.fetchone()[0] == 1

def insert_category(category:dict):
    cur.execute('INSERT OR REPLACE INTO categories(id, name, slug, gameId, json) VALUES(?,?,?,?,?)', (category['id'], category['name'], category['slug'], category['gameId'], json.dumps(category)))

def insert_game(game:dict):
    cur.execute('INSERT OR REPLACE INTO games(id, name, slug, json) VALUES(?,?,?,?)', (game['id'], game['name'], game['slug'], json.dumps(game)))

def insert_mod(mod:dict):
    categoryIds = json.dumps([x['id'] for x in mod['categories']])
    cur.execute('INSERT OR REPLACE INTO mods(id, name, slug, gameId, categoryIds, json) VALUES(?,?,?,?,?,?)', (mod['id'], mod['name'], mod['slug'], mod['gameId'], categoryIds, json.dumps(mod)))
    
def insert_file(file:dict):
    cur.execute('INSERT OR REPLACE INTO files(id, displayName, fileName, gameId, modId, json) VALUES(?,?,?,?,?,?)', (file['id'], file['displayName'], file['fileName'], file['gameId'], file['modId'], json.dumps(file)))

#Start program

os.makedirs(output_dir, exist_ok=True)

con = sqlite3.connect(output_dir + '/curseforge.db')
cur = con.cursor()

cur.execute('CREATE TABLE IF NOT EXISTS games(id, name, slug, json)')
cur.execute('CREATE TABLE IF NOT EXISTS categories(id, name, slug, gameId, json)')
cur.execute('CREATE TABLE IF NOT EXISTS mods(id, name, slug, gameId, categoryIds, json)')
cur.execute('CREATE TABLE IF NOT EXISTS files(id, displayName, fileName, gameId, modId, json)')
cur.execute('CREATE TABLE IF NOT EXISTS api(url, time, json)')

con.commit()

games = get_json('/games', True, True)

print("Retrieved " + str(len(games['data'])) + " games")

for game_stub in games['data']:
    insert_game(game_stub)

    game_id = game_stub['id']
    if game_id not in target_games: continue
    
    print('Processing game: ' + game_stub['name'])

    game = get_json('/games/' + str(game_id), True, True)
    versions = get_json(f'/games/{game_id}/versions', True, True)
    categories = get_json(f'/categories?gameId={game_id}', True, True)

    for category_stub in categories['data']:
        insert_category(category_stub)

        category_id = category_stub['id']
        #if category_id not in target_categories: continue

        print('Processing category: ' + category_stub['name'])

        for result in Depaginator(f'/mods/search?categoryId={category_id}&gameId={game_id}&sortField=3'):
            for mod_stub in result['data']:
                insert_mod(mod_stub)

        con.commit()

for result in Depaginator('/mods/search?categoryId=399&gameId=432&sortField=4'):
    for mod_stub in result['data']:
        insert_mod(mod_stub)

for result in Depaginator(f'/mods/{454382}/files?'):
    for file_stub in result['data']:
        insert_file(file_stub)

con.commit()
con.close()