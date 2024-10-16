#!/bin/python3

import json
import sqlite3
import importlib
import os
import datetime

sqlh = importlib.import_module("sqlite_helper")
config = importlib.import_module("config")

def sizeof_fmt(num, suffix="B"):
    for unit in ("", "Ki", "Mi", "Gi", "Ti", "Pi", "Ei", "Zi"):
        if abs(num) < 1024.0:
            return f"{num:3.1f}{unit}{suffix}"
        num /= 1024.0
    return f"{num:.1f}Yi{suffix}"

def get_filepath(filename):
    return f'{config.output_dir}/{filename}'

if not os.path.isfile(config.db_filepath):
    print(f"Need path to database (from args: {config.db_filepath})")
    exit(1)

db = sqlh.Sqlite_helper(config.db_filepath, dry_run=True)

slug_counts = dict()
slug_files = dict()
classid_slug = dict()
scrape_info_dump = None

mod_json_dump_path = get_filepath('dump_mod_json.txt')
source_dump_path = get_filepath('dump_source_urls.txt')
file_url_dump_path = get_filepath('dump_file_urls.txt')
all_urls_dump_path = get_filepath('dump_all_urls.txt')
scrape_info_dump_path = get_filepath('dump_scrape_info.txt')

def save_scrape_info():
    global scrape_info_dump
    # Write scrape info

    db_stat = os.stat(config.db_filepath)
    scrape_info_dump = open(scrape_info_dump_path, 'a')

    scrape_info_dump.write(
    f"""
[{datetime.datetime.fromtimestamp(db_stat.st_mtime)}] Scrape info dump
Database file: {config.db_filepath}
\tSize: {sizeof_fmt(db_stat.st_size)} ({db_stat.st_size} bytes)
\tLast modified: {datetime.datetime.fromtimestamp(db_stat.st_mtime)}
\tLast accessed: {datetime.datetime.fromtimestamp(db_stat.st_atime)}
\tLast change: {datetime.datetime.fromtimestamp(db_stat.st_ctime)}""")

    db.cur.execute("SELECT tbl_name FROM sqlite_master WHERE type='table'")

    tables = db.cur.fetchall()

    scrape_info_dump.write("\nTables:")

    for table in tables:
        db.cur.execute(f"SELECT count(*) FROM {table[0]}")
        scrape_info_dump.write(f"\n\t{table[0]}: {db.cur.fetchone()[0]} entries")
        total_bytes = 0
        db.cur.execute(f"SELECT * FROM {table[0]}")
        for row in db.cur:
            total_bytes += sum([len(str(x)) for x in row])
        scrape_info_dump.write(f" ({sizeof_fmt(total_bytes)})")

def save_primary_categories():
    # Save each primary category to files

    print("Saving primary category files")

    db.cur.execute("SELECT * FROM categories")

    for row in db.cur:
        classid_slug[row[0]] = row[2]

    db.cur.execute("SELECT * FROM mods")

    with (open(mod_json_dump_path, 'w') as json_dump,
        open(source_dump_path, 'w') as source_dump):
        for row in db.cur:
            json_dump.write(f'{row[5]}\n')
            json_data = json.loads(row[5])
            classid = json_data['classId']
            links = json_data.get('links', None)

            if links:
                srcUrl = links.get('sourceUrl', None)
                if srcUrl not in [None, 'null', '', 'None']:
                    source_dump.write(f'{json_data["slug"]},{srcUrl}\n')

            primary_category = None

            if classid not in classid_slug:
                classid = 0
                primary_category = "various"
            else:
                primary_category = classid_slug[classid]

            if slug_files.get(primary_category, 0)==0:
                filepath = f'{config.output_dir}/{classid}_{primary_category}.txt'
                slug_files[primary_category] = open(filepath, 'w')

            v = slug_counts.get(primary_category, 0)
            slug_counts[primary_category] = v + 1

            slug_files[primary_category].write(f'{json_data["id"]},{json_data["slug"]}\n')

    for primary_category in slug_files:
        slug_files[primary_category].close()

    print("slug_counts:", slug_counts)
    scrape_info_dump.write(f"\nPrimary category counts: {slug_counts}")

def approximate_file_count():
    # Approximate file count

    print("Approximating file count")

    ideal_file_count = 0
    api_entry_count = 0

    db.cur.execute("SELECT * FROM api")

    for api_raw in db.cur:
        if 'files' in api_raw[0]:
            json_data = json.loads(api_raw[2])
            api_entry_count += 1
            ideal_file_count += len(json_data['data'])

    print("Theoretical file count:", ideal_file_count, "API entry count:", api_entry_count)
    scrape_info_dump.write(f"\nTheoretical file count: {ideal_file_count} API entry count: {api_entry_count}")

def save_file_urls():
    # Save file urls to a download list

    print("Saving download links")

    file_url_count = 0
    file_url_size = 0

    db.cur.execute("SELECT * FROM files")

    with open(file_url_dump_path, 'w') as file_url_dump:
        for row in db.cur:
            json_data = json.loads(row[5])
            
            file_url_count += 1
            file_url_size += json_data["fileLength"]

            file_url_dump.write(f'{json_data["id"]},{json_data["downloadUrl"]}\n')

    print(f"File download URL count: {file_url_count} ({sizeof_fmt(file_url_size)})")
    scrape_info_dump.write(f"\nFile download URL count: {file_url_count} ({sizeof_fmt(file_url_size)})")

def save_all_urls():
    # Save all urls to a list

    print("Saving all urls")

    all_url_count = 0

    with open(all_urls_dump_path, 'w') as all_urls_dump:
        iter = db.con.cursor()

        iter.execute("SELECT * FROM categories")

        for row in iter:
            json_data = json.loads(row[4])
            all_urls_dump.write(f"category,{json_data['id']},{json_data['slug']},iconUrl,,{json_data['iconUrl']}\n")
            all_url_count += 1

        iter.execute("SELECT * FROM games")

        for row in iter:
            json_data = json.loads(row[3])
            prefix = f"game,{json_data['id']},{json_data['slug']},"
            assets = json_data['assets']
            all_urls_dump.write(prefix + f"iconUrl,,{assets['iconUrl']}\n")
            all_urls_dump.write(prefix + f"tileUrl,,{assets['tileUrl']}\n")
            all_urls_dump.write(prefix + f"coverUrl,,{assets['coverUrl']}\n")
            all_url_count += 3

        iter.execute("SELECT * FROM mods")

        for row in iter:
            json_data = json.loads(row[5])
            prefix = f"mod,{json_data['id']},{json_data['slug']},"
            logo = json_data['logo']
            for author in json_data['authors']:
                if 'avatarUrl' in author:
                    all_urls_dump.write(prefix + f"author,{author['id']},{author['avatarUrl']}\n")
                    all_url_count += 1

            for screenshot in json_data['screenshots']:
                all_urls_dump.write(prefix + f"screenshot,{screenshot['id']},{screenshot['url']}\n")
                all_urls_dump.write(prefix + f"screenshot,{screenshot['id']},{screenshot['thumbnailUrl']}\n")
                all_url_count += 2

            if logo:
                all_urls_dump.write(prefix + f"logo,{logo['id']},{logo['url']}\n")
                all_urls_dump.write(prefix + f"logo,{logo['id']},{logo['thumbnailUrl']}\n")
                all_url_count += 2
    
    print("Additional URL count:", all_url_count)
    scrape_info_dump.write(f"\nAdditional URL count: {all_url_count}")

save_scrape_info()
save_primary_categories()
approximate_file_count()
save_file_urls()
save_all_urls()

print("Done")