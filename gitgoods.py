#!/usr/bin/env python
""" 
Git Goods

Authored by @rx13 in 09/2018, 
  Pre-pub comments updates in 02/2020

There is no versioning yet, this was the first proto.

A small utility script written to quickly search for
  a time-relative appearance of specific keywords in
  files containing provided domain names.

This utility doesn't account for many items as it was
  intended to be run regularly, and looking back only 
  over a small period of time.

What it does:
    * Takes domain, keyword and/or date inputs, and 
    * Forms an in-file code query then
    * Returns related contents in 3 timestamped formats:
        * keyword-highlighted output to run screen
        * file-match list with filenames
        * matched-keyword file content 
        (same data as keyword highlight output)

Known failure situations that don't notify you:
    * invalid oauth token
    * various other error code returns from github

Known conditions where there's a notification, but it
  does not handle automatically the response:
    * rate limiting (Default limit varies; warns at 10)
    * pagination
"""

import os
import re
import sys
import json
import time
import urllib
import argparse
import datetime
import requests

#v3 api
def gitQuery():
    burl = "https://api.github.com"
    turl = "/search/code"
    headers = {
        'Accept': "application/vnd.github.v3+json",
        'Authorization': "token {}".format(token)
    }
    params = {
        'q': 'in:file "{}" "{}"'.format(args["domain.tld"], args["keyword"]),
        'sort': "indexed"
    }
    if datecheck != None:
        print("Using only repositories pushed since "+datecheck)
        params["q"] = params["q"]+" pushed:"+datecheck
    req = requests.get(burl+turl, params=params, headers=headers)
    limit = req.headers["X-RateLimit-Limit"] if "X-RateLimit-Limit" in req.headers else ""
    remain = req.headers["X-RateLimit-Remaining"] if "X-RateLimit-Remaining" in req.headers else None
    resetat = req.headers["X-RateLimit-Reset"] if "X-RateLimit-Reset" in req.headers else None
    if remain != None and int(remain) < 10:
        limitText = "(of {})".format(limit) if limit != None else ""
        resetText = " Resets at {}".format(datetime.datetime.fromtimestamp(float(resetat))) if resetat != None else ""
        print("WARNING: {}{} queries remaining before rate limit hit.{}".format(remain, limitText, resetText))
    if req.ok:
        return req.json()
    else:
        return {}

if __name__ == "__main__":
    token = None
    runtime = time.time()
    bpath = 'matched_files'
    tokenFile = 'oauth.token'

    try:
        token = open(tokenFile, 'r').read()[:40]
        if not os.path.isdir(bpath):
            os.mkdir(bpath, 0770)
    except Exception as e:
        print(e)
        print("\n\nPaste your authorization token (API key) into file: '{}'".format(tokenFile))
        sys.exit(1)

    parser = argparse.ArgumentParser(description="A github utility to identify leaks for a given domain and keyword")
    parser.add_argument('domain.tld', help="Should be a domain you're searching for content on (example.com)")
    parser.add_argument('keyword', help="Should be a keyword you are interested in ('password' or 'secret')")
    parser.add_argument('date', nargs="?", default="", help="Optional parameter, checks only new repositories pushed since date YYYY-MM-DD")
    args = vars(parser.parse_args())

    args["domain.tld"] = args["domain.tld"].replace('"', '')
    args["keyword"] = args["keyword"].replace('"', '')
    rexchk = re.compile(r'(%s)|(%s)' % (args["domain.tld"], args["keyword"]), re.IGNORECASE)
    datecheck = None
    filelist = open('{}_{}_{}_fileurls.txt'.format(args["domain.tld"], args["keyword"], runtime), 'w+')
    matchlist = open('{}_{}_{}_matches.txt'.format(args["domain.tld"], args["keyword"], runtime), 'w+')

    if len(args["date"]) > 1:
        try:
            if re.match(r'^[>=]?[\d]{4}-[\d]{2}-[\d]{2}$', args["date"]):
                datecheck = args["date"]
            else:
                raise Exception("hell")
        except:
            print("Check the formatting of the datecheck field for errors")
            sys.exit(1)

    gitTotal = 0
    results = gitQuery()
    print(results)
    if "total_count" in results:
        gitTotal = results["total_count"]
    if "items" in results:
        for entry in results['items']:
            fn = '{}/{}'.format(entry['repository']['full_name'].encode('utf-8'), entry['path'].encode('utf-8'))
            rawfile = entry['html_url'].replace('//github.com', '//raw.githubusercontent.com').replace('/blob/', '/')
            filelist.write(rawfile+"\n")
            contents = requests.get(rawfile)
            fn = fn.replace('/', '+')
            if contents.ok:
                prevline = ""
                writenext = False
                with open(os.path.join(bpath, fn), 'w+') as f:
                    f.write(contents.text.encode('utf-8'))
                for line in list(contents.text.replace('\r','').split('\n')):
                    line = line.encode('utf-8')
                    if writenext:
                        matchlist.write(line+"\n")
                        writenext = False
                    match = rexchk.search(line)
                    if match:
                        fline = line
                        uniq = []
                        for inst in [inst for inst in match.groups() if inst != None]:
                            if inst not in uniq:
                                uniq.append(inst)
                                fline = fline.replace(inst, '\x1b[0;31;40m'+inst+'\x1b[0m')
                        matchlist.write(prevline+line+"\n")
                        writenext = True
                        print(fline)
                    prevline = line+"\n"
                print('---+++---+++---+++---+++---+++---+++---+\n\n')
        print("Total items -- in GitHub: {} , Returned: {}".format(gitTotal, len(results["items"])))
    else:
        print("No items returned. (Likely a request failure)")
    matchlist.close()
    filelist.close()