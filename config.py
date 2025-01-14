#!/bin/python3

import os
import argparse
import re

api_url = 'https://api.curseforge.com/v1'
output_dir = './curseforge'
api_key_file = 'api_key.txt'
api_key = ''
dry_run = False
db_filename = 'curseforge.db'
db_filepath = ':memory:'
bucket_filename = 'bucket.db'
bucket_filepath = ':memory:'
category_filter = []
game_filter = [432]
wait_ms = 1000
retry_limit = 4
store_option = None
cache_option = None
full = False
scrape_descriptions = False
scrape_changelogs = False
scrape_game_versions = False
download_media = False
download_files = False
download_all = False

parser = argparse.ArgumentParser(
    prog="Python Curseforge Scraper",
    description="Scrape Curseforge API",
    epilog="https://github.com/MrDoritos/PythonCurseforgeScraper",
    formatter_class=argparse.ArgumentDefaultsHelpFormatter
)

parser.add_argument('-o', '--output-dir', default=output_dir, dest='o', help='directory for scraper output')
parser.add_argument('-k', '--api-key', dest='k', help='api key, ignores api_key_file')
parser.add_argument('--api-key-file', default=api_key_file, dest='kf', help='file with api key')
parser.add_argument('-u', '--api-url', default=api_url, dest='u', help='api endpoint base url')
parser.add_argument('-n', '--dry-run', action='store_true', dest='n', help='do not write to disk')
parser.add_argument('-df', '--database-filename', default=db_filename, dest='dbf', help='database connection filename')
parser.add_argument('-dp', '--database-filepath', dest='dbfp', help='full path to database connection, ignores database filename option')
parser.add_argument('-bf', '--bucket-filename', default=bucket_filename, dest='bf', help='filebucket connection filename')
parser.add_argument('-bp', '--bucket-filepath', dest='bfp', help='full path to filebucket connection, ignores bucket filename option')
parser.add_argument('-cf', '--category-filter', type=int, default=category_filter, action='extend', nargs='+', dest='cf', help='category ids to collect')
parser.add_argument('-gf', '--game-filter', type=int, default=game_filter, action='extend', nargs='+', dest='gf', help='game ids to collect')
parser.add_argument('-w', '--wait-ms', type=float, default=wait_ms, dest='w', help='wait time between requests in milliseconds')
parser.add_argument('-r', '--retry-limit', type=int, default=retry_limit, dest='r', help='number of retries for a failed request')
parser.add_argument('-t', '--stale-threshold', type=int, default=1, dest='threshold', help='Number of consecutive pages of stale data before leaving the current loop')
parser.add_argument('-s', '--store-option', default='default', choices=['none', 'default', 'all', 'last'], dest='store', help='request storage usage')
parser.add_argument('-c', '--cache-option', default='default', choices=['none', 'default', 'all', 'only'], dest='cache', help='request cache usage')
parser.add_argument('-f', '--full', action='store_true', dest='f', help='Enable when the final numbers show any discrepancies')
parser.add_argument('--scrape-descriptions', action='store_true', dest='sd', help='Scrape descriptions for each mod')
parser.add_argument('--scrape-changelogs', action='store_true', dest='sc', help='Scrape changelogs for each file')
parser.add_argument('--scrape-game-versions', action='store_true', dest='sgv', help='Scrape versions for each game')
parser.add_argument('--download-media', action='store_true', dest='dm', help='Download media/logo/image files for everything')
parser.add_argument('--download-files', action='store_true', dest='df', help='Download files')
parser.add_argument('-a', '--download-all', action='store_true', dest='da', help='Download and scrape everything')
parser.add_argument('-C', '--curl', dest='curl', help='wrapper to use api key with curl')
parser.add_argument('-pf', '--pid-file', default='curse.pid', dest='pid_file', help='Read/write program pid at this file')
parser.add_argument('-p', '--pid', dest='pid', help="Use this pid for the singleton check")
parser.add_argument('--singleton', action='store_true', default=True, dest='singleton', help='Force single instance using pid')

args = parser.parse_args()

print(args)

output_dir = args.o
api_url = args.u
api_key_file = args.kf
api_key = args.k
dry_run = args.n
category_filter = args.cf
game_filter = args.gf
db_filename = args.dbf
bucket_filename = args.bf
wait_ms = args.w
retry_limit = args.r
store_option = args.store
cache_option = args.cache
full = args.f
scrape_descriptions = args.sd
scrape_changelogs = args.sc
scrape_game_versions = args.sgv
download_media = args.dm
download_files = args.df
download_all = args.da
pid_file = args.pid_file
pid_arg = args.pid
singleton = args.singleton
threshold = args.threshold

# Stateful

def pid_check(pid):
    try:
        os.kill(pid, 0)
    except OSError:
        return False
    else:
        return True

if singleton:
    if not (pid_arg and len(pid_arg)) and not (pid_file and len(pid_file)):
            print('No pid supplied, unsafe circumstances or remove the singleton flag')
    
    if (pid_arg and len(pid_arg) and pid_check(pid_arg)):
        print('Program is already running. Pid from pid arg')
        exit(1)

    if (pid_file and len(pid_file) and os.path.isfile(pid_file)):
        pid = open(pid_file).read().strip()
        if pid_check(pid):
            print('Program is already running. Pid from pid_file arg')
            exit(1)
            
        # write current pid
        with open(pid_file, 'w') as f:
            f.write(str(os.getpid()))


if not (api_key and len(api_key)):
    if not (api_key_file and len(api_key_file)):
        print('No api_key or api_key_file')
        exit(1)

    if not os.path.isfile(api_key_file):
        print('Bad api_key_file path')
        exit(1)

    api_key = open(api_key_file).read().strip()

if not dry_run:
    os.makedirs(output_dir, exist_ok=True)
    
if not args.dbfp:
    db_filepath = output_dir + '/' + db_filename

if not args.bfp:
    bucket_filepath = output_dir + '/' + bucket_filename
    
if download_all:
    scrape_descriptions = True
    scrape_changelogs = True
    scrape_game_versions = True
    download_media = True
    download_files = True

if args.curl:
    curl_opts = 'curl '
    curl_opts += '--http1.1 -v '
    curl_opts += f'-H "x-api-key: {api_key.replace('$', '\\$')}" '
    curl_opts += '-H "Accept: application/json" '
    curl_opts += '-H "User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/87.0.4280.141 Safari/537.36 OverwolfClient/0.204.0.1" '
    curl_opts += '-H "Authorization: OAuth" '
    curl_opts += '-H "X-Twitch-Id:" '
    curl_opts += '-H "Accept-Encoding: utf-8" '
    curl_opts += args.curl
    exit(os.system(curl_opts))