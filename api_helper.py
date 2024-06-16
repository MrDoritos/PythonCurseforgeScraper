#!/bin/python3

import json
import requests
import importlib
import time
import os

sqlite_helper = importlib.import_module("sqlite_helper")
config = importlib.import_module("config")

class Api_helper:
    def __init__(self, db_helper):
        self.db = db_helper
        self.api_key = self.get_api_key(config.api_key_file)
        self.api_url = config.api_url
        self.last_request = time.time() - 1

        self.client = requests.Session()

        self.client.headers.update({'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/87.0.4280.141 Safari/537.36 OverwolfClient/0.204.0.1'})
        self.client.headers.update({'Accept': 'application/json'})
        self.client.headers.update({'Accept-Encoding': 'gzip'})
        self.client.headers.update({'x-api-key': self.api_key})
        self.client.headers.update({'Authorization': 'OAuth'})
        self.client.headers.update({'X-Twitch-Id': ''})

    def get_api_key(self, file):
        if not os.path.isfile(file):
            raise Exception('API key file not found: ' + file)
        
        with open(file, 'r') as f:
            return f.read().strip()
    
    def get_retry(self, url, retries=0):
        try:
            print('Making request to: ' + url, end=' ')

            if (self.last_request + 1) > time.time():
                ms = (self.last_request + 1) - time.time()
                print('Waiting for ' + str(ms) + 'ms', end=' ')
                time.sleep(ms)

            self.last_request = time.time()
            r = self.client.get(self.api_url + url)
            print('Got response: ' + str(r.status_code))
            return r
        except:
            print('Request failed')
            if retries > 4:
                raise
            print('Retrying request attempt: ' + str(retries + 1))
            return self.get_retry(url, retries + 1)

    def write_file(self, path, data :str):
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, 'w') as f:
            f.write(data)

    def write_json(self, path, data: dict):
        self.write_file(path, json.dumps(data, indent=4))

    def get_json(self, url, write=False, use_local=False):
        if use_local and self.db.request_exists(url):
            try:
                print('Using local database: ' + url)
                return json.loads(self.db.get_request(url))
            except Exception as e:
                print('Failed to read local database: ' + url)
                print(e)
                pass    

        json_data = self.get_retry(url).json()

        if write:
            self.db.insert_request(url, json_data, self.last_request)

        return json_data


class Depaginator:
    def __init__(self, api, url, index=0, pageSize=50):
        self.api = api
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
        return self.api.get_json(new_url, True, True)

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