#!/bin/python3

import os

api_url = 'https://api.curseforge.com/v1'
output_dir = './curseforge'
api_key_file = './api_key.txt'

os.makedirs(output_dir, exist_ok=True)