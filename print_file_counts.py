#!/bin/python3

import importlib

sqlite_helper = importlib.import_module('sqlite_helper')
api_helper = importlib.import_module('api_helper')
config = importlib.import_module('config')

db = sqlite_helper.Sqlite_helper(config.output_dir + '/curseforge.db')
api = api_helper.Api_helper(db)

cur_2 = db.con.cursor()
cur_2.execute("SELECT * FROM mods")

total_result_count = 0
total_file_stub_count = 0

for mod_row in cur_2:
    for result in api_helper.Depaginator(api, f'/mods/{mod_row[0]}/files?'):
        total_result_count += len(result['data'])
        for file_stub in result['data']:
            total_file_stub_count += 1

print(f"Total result count: {total_result_count}")
print(f"Total file stub count: {total_file_stub_count}")