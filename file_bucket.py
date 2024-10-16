import sqlite3
import hashlib
import os
import time
import requests
from urllib.parse import urlparse
import urllib.request

class Filebucket:
    def __init__(self, path, dry_run=False):
        self.dry_run = dry_run
        self.client = requests.Session()

        self.load(path)
        self.init()

    def __del__(self):
        self.close()

    def init(self):
        self.cur.execute("CREATE TABLE IF NOT EXISTS files(hash, length, filename, time, data)")
        self.cur.execute("CREATE TABLE IF NOT EXISTS api(url, id, filename, time, hash)")

        self.save()

    def close(self):
        self.save()
        print("Close bucket")
        self.con.close()

    def load(self, path=None):
        if path is None:
            path = self.path
        else:
            self.path = path

        print("Connect to bucket:", path)
        self.con = sqlite3.connect(path)
        self.cur = self.con.cursor()

    def save(self):
        if not self.dry_run:
            print("Commit to bucket:", self.path)
            try:
                self.con.commit()
            except Exception as e:
                print("Failed to commit to bucket:", e)

    def get_hash(self, stream):
        return hashlib.file_digest(stream, "md5").hexdigest()

    def insert_stream(self, url, stream, length = None, time = None, id = None, filename = None):
        blob = stream.read()
        hash = hashlib.md5(blob).hexdigest()
        #print(stream)
        #stream.seek(0, os.SEEK_END)
        #length = stream.tell()
        #length = stream
        if not time:
            time = time.time()

        self.cur.execute("INSERT OR REPLACE INTO files(hash, length, filename, time, data) VALUES(?,?,?,?,?)", (hash, length, filename, time, sqlite3.Binary(blob)))
        self.cur.execute("INSERT OR REPLACE INTO api(url, id, filename, time, hash) VALUES(?,?,?,?,?)", (url, id, filename, time, hash))

    def insert_file(self, url, path, length = None, time = None, id = None, filename = None):
        with open(path, 'rb') as fstream:
            self.insert_stream(url, fstream, length, time, id, filename)
    
    def insert_url(self, url, length = None, time = None, id = None, filename = None):
        print("Downloading:", url, end='', flush=True)
        with urllib.request.urlopen(url) as fstream:
            length = fstream.getheader('Content-Length')
            print(" Got response:", fstream.getcode())
            self.insert_stream(url, fstream, length, time, id, filename)

    def get_stream(self, hash):
        self.cur.execute("SELECT data FROM files WHERE hash=?", (hash,))
        return self.cur.fetchone()[0]
    
    def hash_exists(self, hash):
        self.cur.execute("SELECT count(*) FROM files WHERE hash=?", (hash,))
        return self.cur.fetchone()[0] > 0

    def url_exists(self, url):
        self.cur.execute("SELECT count(*) FROM api WHERE url=?", (url,))
        return self.cur.fetchone()[0] > 0

    def should_update_file(self, url, time):
        if not self.url_exists(url):
            return True

        self.cur.execute("SELECT time FROM api WHERE url=?", (url,))
        last_time = self.cur.fetchone()[0]

        return not last_time or not time or last_time < time

    def try_insert_url(self, url, time = None, length = None, id = None, filename = None):
        try:
            if not self.should_update_file(url, time):
                return

            self.insert_url(url, length, time, id, filename)
        except Exception as e:
            print("Failed to insert url:", url)
            print(e)