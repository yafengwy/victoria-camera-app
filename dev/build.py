import json,re,sys
src=open('src/index.html').read()
imgs=open('mock_images.json').read()
import datetime,zoneinfo
stamp=datetime.datetime.now(zoneinfo.ZoneInfo('America/Los_Angeles')).strftime('%m-%d %H:%M:%S')
import os
ver=open('ver.txt').read().strip() if os.path.exists('ver.txt') else '1.1.0'
if 'release' in sys.argv:
    # second and third numbers go 1..10, then roll over: 1.2.10 -> 1.3.1, 1.10.10 -> 2.1.1 (1.1.50 -> 1.2.1)
    a=[int(x) for x in ver.split('.')]; a[2]+=1
    if a[2]>10: a[2]=1; a[1]+=1
    if a[1]>10: a[1]=1; a[0]+=1
    ver='.'.join(map(str,a)); open('ver.txt','w').write(ver+'\n')
open('preview.html','w').write(src.replace('/*MOCK_IMAGES*/{}',imgs).replace('__BUILD__',stamp).replace('__VER__',ver))
open('version.txt','w').write(ver+'\n')
