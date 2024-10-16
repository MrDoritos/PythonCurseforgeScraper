# Python Curseforge Scraper

## You must supply an api key in the file `api_key.txt` or as the argument `-k (api_key)`

## Description

Simple python script to scrape API data from curseforge.com, directly from the API. Outputs data to a sqlite3 database. Caches requests and follows rate limits.

`python3 ./main.py --help`<br/>
`./main.py --help`<br/>

Default arguments are fully functional.

## TO-DO

* File storage of addon files and images into buckets or a folder structure. Minecraft alone will require 12TB or more, native deduplication is desirable.</br>
* Experimental interface for the archival audience