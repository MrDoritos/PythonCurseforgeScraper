#!/bin/python3

import json
import requests
import importlib
import time
import os

class Api_helper:
    def __init__(self, db_helper, config):
        self.db = db_helper
        self.config = config
        self.api_url = config.api_url
        self.api_key = config.api_key
        self.wait_s = config.wait_ms / 1000.0
        self.retry_limit = config.retry_limit
        self.last_request = time.time() - self.wait_s

        self.client = requests.Session()

        self.client.headers.update({'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/87.0.4280.141 Safari/537.36 OverwolfClient/0.204.0.1'})
        self.client.headers.update({'Accept': 'application/json'})
        self.client.headers.update({'Accept-Encoding': 'gzip'})
        self.client.headers.update({'x-api-key': self.api_key})
        self.client.headers.update({'Authorization': 'OAuth'})
        self.client.headers.update({'X-Twitch-Id': ''})
    
    def get_retry(self, url, retries=0):
        try:
            print('Making request to: ' + url, end=' ')

            if (self.last_request + self.wait_s) > time.time():
                ms = (self.last_request + self.wait_s) - time.time()
                print('Waiting for ' + self.format_ms(ms) + 'ms', end=' ')
                time.sleep(ms)

            self.last_request = time.time()
            r = self.client.get(self.api_url + url)
            print('Got response: ' + str(r.status_code))
            return r
        except:
            print('Request failed')
            if retries > self.retry_limit:
                raise
            print('Retrying request attempt: ' + str(retries + 1))
            return self.get_retry(url, retries + 1)

    def write_file(self, path, data :str):
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, 'w') as f:
            f.write(data)

    def write_json(self, path, data: dict):
        self.write_file(path, json.dumps(data, indent=4))

    def get_json(self, url, write=False, use_local=False, time_diff=3600):
        _cache = self.config.cache_option
        _store = self.config.store_option

        _use = (use_local and _cache == 'default') or _cache not in ['none','default']
        _write = (write and _store == 'default') or _store not in ['none', 'default']

        if _use and _cache != 'only':
            _use = not self.should_update_entries(url, time_diff)

        if _use:
            try:
                return json.loads(self.db.get_request(url))
            except Exception as e:
                print('Failed to read local database: ' + url)
                print(e)
                pass

        if _cache == 'only':
            print("Cached requests only")
            return None

        json_data = self.get_retry(url).json()

        if _write:
            self.db.insert_request(url, json_data, self.last_request)

        return json_data

    def when_last_request(self, url):
        if not self.db.request_exists(url):
            return 0
        
        self.db.cur.execute('SELECT time FROM api WHERE url=? ORDER BY time DESC', (url,))
        return self.db.cur.fetchone()[0]

    def should_update_entries(self, url, time_diff):
        req_time = self.when_last_request(url)
        now_time = time.time()
        res = req_time + time_diff < now_time
        leftover = (now_time - req_time) - time_diff
        
        debug = f'({req_time:.3f} + {time_diff:.3f} > {now_time:.3f}) = {leftover:.3f}'

        if leftover > 0:
            print("Stale entry", url, debug)
        else:
            print("Cached entry", url, debug)

        return res

    def format_ms(self, ms):
        return f'{ms:.3f}'

    def read_time(self, stime):
        try:
            return time.mktime(time.strptime(stime, '%Y-%m-%dT%H:%M:%S.%fZ'))
        except:
            return time.mktime(time.strptime(stime, '%Y-%m-%dT%H:%M:%SZ'))


class Depaginator:
    def __init__(self, api, url, index=0, pageSize=50, write_local=True, use_local=True, time_diff=3600):
        self.api = api
        self.url = url
        self.index = index
        self.pageSize = pageSize
        self.page = None
        self.write_local = write_local
        self.use_local = use_local
        self.time_diff = time_diff

        self.current_url = self.format_url()
    
    def format_url(self):
        append = f'index={self.index}&pageSize={self.pageSize}'
        self.current_url = self.url

        if self.current_url[-1] not in '?&':
            if '?' in self.current_url:
                self.current_url += '&'
            else:
                self.current_url += '?'

        return self.current_url + append

    def get_page(self):
        return self.api.get_json(self.format_url(), self.write_local, self.use_local, self.time_diff)

    def __iter__(self):
        return self
    
    def __next__(self):
        # Iteration over when index + resultCount >= totalCount
        # However we must return the previous retrieved page and call stopiteration next iteration


        if self.page != None:
            if self.page.get('pagination', None) == None:
                raise StopIteration()
            
            resultCount = self.page['pagination']['resultCount']
            totalCount = self.page['pagination']['totalCount']

            if self.index >= totalCount:
                raise StopIteration()
            
            if self.index + resultCount >= totalCount:
                raise StopIteration()
            
            self.index += self.pageSize

        try:
            self.page = self.get_page()
            self.page['url'] = self.current_url
        except Exception as e:
            print(e)
            raise StopIteration()

        if self.page.get('pagination', None) == None:
            print('Url is not paginated')
            return self.page
        
        return self.page
