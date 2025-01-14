# Python Curseforge Scraper

## You must supply an api key in the file `api_key.txt` or as the argument `-k (api_key)`

## Description

Python script for scraping API data from curseforge.com. Outputs API data to a sqlite database with another sqlite database for file storage. The program caches requests, follows rate limits, maintains historical data and captures everything.

`python3 ./main.py --help`<br/>

Default arguments are fully functional although no CDN content is saved without `--download-all` (`-a`)

## Scrape info

There is an additional script for extracting miscellaneous information and URL lists.

`python3 ./print_scrape_info.py`<br/>

## TO-DO

* Minecraft alone will require 12TB or more, native deduplication and/or compression is desirable within the file bucket.</br>
* Experimental interface for the archival audience

#### Past attempts which should be ignored

* <sub>[https://github.com/MrDoritos/CurseforgeMirrorer](CurseforgeMirrorer)</sub><br/>
* <sub>[https://github.com/MrDoritos/CurseforgeScraper](CurseforgeScraper)</sub>
