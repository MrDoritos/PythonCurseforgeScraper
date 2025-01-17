import sqlite3
import json

class Sqlite_helper:
    def __init__(self, file, dry_run=False):
        self.dry_run = dry_run
        
        self.load(file)
        self.init()

    def __del__(self):
        self.close()

    def init(self):
        self.cur.execute('CREATE TABLE IF NOT EXISTS games(id INTEGER PRIMARY KEY, name, slug, json)')
        self.cur.execute('CREATE TABLE IF NOT EXISTS categories(id INTEGER PRIMARY KEY, name, slug, gameId, json)')
        self.cur.execute('CREATE TABLE IF NOT EXISTS mods(id INTEGER PRIMARY KEY, name, slug, gameId, categoryIds, json)')
        self.cur.execute('CREATE TABLE IF NOT EXISTS files(id INTEGER PRIMARY KEY, displayName, fileName, gameId, modId, json)')
        self.cur.execute('CREATE TABLE IF NOT EXISTS api(url, time, json)')

    def close(self):
        self.save()
        print("Close connection")
        self.con.close()

    def load(self, path=None):
        if path is None:
            path = self.file
        else:
            self.file = path

        print("Connect to database:", path)
        self.con = sqlite3.connect(path)
        self.cur = self.con.cursor()

    def save(self):
        if not self.dry_run:
            print("Commit to database:", self.file)
            try:
                self.con.commit()
            except Exception as e:
                print("Failed to commit:", e)

    def request_exists(self, url:str):
        self.cur.execute('SELECT count(*) FROM api WHERE url=? LIMIT 1', (url,))
        return self.cur.fetchone()[0] > 0

    def insert_request(self, url:str, json_data:str, time):
        self.cur.execute('INSERT OR REPLACE INTO api(url, json, time) VALUES(?,?,?)', (url, json.dumps(json_data), time))

    def get_request(self, url:str):
        self.cur.execute('SELECT json FROM api WHERE url=? ORDER BY time LIMIT 1', (url,))
        return self.cur.fetchone()[0]
    
    def table_exists(self, table:str):
        self.cur.execute("SELECT count(*) FROM sqlite_master WHERE type='table' AND name=? LIMIT 1", (table,))
        return self.cur.fetchone()[0] > 0

    def field_exists(self, table:str, id:int):
        self.cur.execute(f'SELECT count(*) FROM {table} WHERE id=? LIMIT 1', (id,))
        return self.cur.fetchone()[0] > 0

    def insert_category(self, category:dict):
        self.cur.execute('INSERT OR REPLACE INTO categories(id, name, slug, gameId, json) VALUES(?,?,?,?,?)', (category['id'], category['name'], category['slug'], category['gameId'], json.dumps(category)))

    def insert_game(self, game:dict):
        self.cur.execute('INSERT OR REPLACE INTO games(id, name, slug, json) VALUES(?,?,?,?)', (game['id'], game['name'], game['slug'], json.dumps(game)))

    def insert_mod(self, mod:dict):
        categoryIds = json.dumps([x['id'] for x in mod['categories']])
        self.cur.execute('INSERT OR REPLACE INTO mods(id, name, slug, gameId, categoryIds, json) VALUES(?,?,?,?,?,?)', (mod['id'], mod['name'], mod['slug'], mod['gameId'], categoryIds, json.dumps(mod)))
        
    def insert_file(self, file:dict):
        self.cur.execute('INSERT OR REPLACE INTO files(id, displayName, fileName, gameId, modId, json) VALUES(?,?,?,?,?,?)', (file['id'], file['displayName'], file['fileName'], file['gameId'], file['modId'], json.dumps(file)))