#!/bin/bash

# run specifically for 24/7 devices

# crontab every day at 2 am
# 0 2 * * *

#screen, start detached
scrcmd=screen -dmR -S curse -X stuff
waitformore='\; exec $SHELL'
runnow='\n'

# low priority
nicecmd='nice -n 10'

# more info, more api use
morecmd='--scrape-descriptions --scrape-changelogs --scrape-game-versions'

# with available bucket (a lot of storage)
bucketcmd='--download-media --download-files'

# morecmd and bucketcmd
allcmd='--download-all'

# just replicate current api (low storage), cache is 80% of the database
# maybe combine with compression of some kind, I won't be doing that though
nocachecmd='--store-option=none --cache-option=none'

$scrcmd '$nicecmd ./main.py -w 10000 $morecmd $waitformore' $runnow