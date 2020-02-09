#!/bin/bash

# Auto-Scrape is just a wrapper script for gitgoods.py. 
#
# It loops through the domain and keyword files ... it
#   would probably be far more useful once I wrap in 
#   automatic rate limiting and pagination to gitgoods.py

if [ "$1" == "" ]; then echo "Usage: ./auto-scrape <since YYYY-MM-DD>"; exit 1; fi
sincedate="$1"
while read -r domain; do
    if [[ "$domain" =~ ^\#.*$ ]]; then
        continue
    else
        while read -r phrase; do
            echo Grabbing $domain -- $phrase
            python gitgoods.py "$domain" "$phrase" $sincedate
        done < <(cat keywords.txt)
    fi
done < <(cat domains.txt)
