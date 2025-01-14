import sqlite3
import hashlib
import os
import time
import requests
from urllib.parse import urlparse
import urllib.request
import importlib

Filebucket_module = importlib.import_module("file_bucket")
Filebucket = Filebucket_module.Filebucket

class Filebucket(Filebucket_module.Filebucket):
    def exists_filesystem_path(self, path):
        return os.path.exists(path)

    def insert_stream(self, url, stream, length=None, time=None, id=None, filename=None):
        bufsize = 65536
        md5 = hashlib.md5()

        stageid = 'dummy'
        length = 0

        if id:
            stageid = id

        stagedir = self.path + '/stage/'

        if not os.path.exists(stagedir):
            os.makedirs(stagedir, exist_ok=True)

        path = self.path + '/stage/' + stageid

        with open(path, 'wb') as ostream:
            while True:
                data = stream.read(bufsize)
                if not data:
                    break
                length += len(data)
                md5.update(data)
                ostream.write(data)

        hash = md5.hexdigest()
        depth = 3
        width = 2
        splithash = [hash[x*width:x*width+width] for x in range(depth)]

        if not id:
            filename = f'{hash}'
        elif not filename and id:
            filename = f'{hash} {id}'
        else:
            filename = f'{hash} {id}' + str(filename).split('.')[-1]

        stale_path = path
        pathdir = self.path + '/bucket/' + '/'.join(splithash) + '/'
        fullpath = pathdir + filename

        if not os.path.exists(pathdir):
            os.makedirs(pathdir, exist_ok=True)

        os.system(f'move -v \"{stale_path}\" \"{path}\"')

        if not time:
            time = time.time()

        self.cur.execute("INSERT OR REPLACE INTO files(hash, length, filename, time, data) VALUES(?,?,?,?,?)", (hash, length, filename, time, path))
        self.cur.execute("INSERT OR REPLACE INTO api(url, id, filename, time, hash) VALUES(?,?,?,?,?)", (url, id, filename, time, hash))
    
    def get_filesystem_path(self, hash):
        self.cur.execute("SELECT data FROM files WHERE hash=?", (hash,))
        return self.cur.fetchone()[0]

    def get_stream(self, hash):
        path = self.get_filesystem_path(hash)
        #if not self.exists_filesystem_path(self, path):
        ## just let the exception occur
        
        # different than file_bucket, fix?
        return os.open(path, 'rb')
