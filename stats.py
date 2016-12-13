import json
import sys
from pprint import pprint
import operator
import datetime
import collections

filename=sys.argv[1]
with open(filename, 'r') as datafile:
    res = json.load(datafile)

packages = {}
num_packages = []

recent = [ 30, 60, 90, 180, 365 ]
new = {}

def check_date(source, val):
    orig = datetime.datetime.strptime(source, '%Y-%m-%dT%H:%M:%SZ')
    check = datetime.datetime.now() + datetime.timedelta(-1 * val)
    return orig >= check

for k,v in res['items'].iteritems():
    if not 'packages' in v:
        continue

    num_packages.append(len(v['packages']))
    for i in v['packages']:
        try:
            packages[i] += 1
        except KeyError:
            packages[i] = 1

    # last 30, 60, 90 , 180, 365 days
    for j in recent:
        if check_date(v['created_at'], j):
            try:
                new[str(j)]['count'] += 1
                new[str(j)]['packages'] += v['packages']
            except:
                new[str(j)] = { 'count' : 1,
                                'packages' : v['packages'] }

def sort_dict(val):
    val_sorted = sorted(val.items(), key=operator.itemgetter(1),
        reverse=True)
    return val_sorted


for j in recent:
    pack = new[str(j)]['packages']
    pack_sorted = sort_dict(dict(collections.Counter(pack)))
    new[str(j)]['packages'] = pack_sorted
    new[str(j)]['packages'] = pack_sorted[:10]

packages_sorted = sorted(packages.items(), key=operator.itemgetter(1),
        reverse=True)

def mean(n):
    return float(sum(n)) / max(len(n), 1)

popular_packages_over_50 = [ x for x in packages_sorted if (x[1] /
    float(len(packages_sorted))) > 0.5 ]

res = { 'total': len(packages_sorted),
        'average': mean(num_packages),
        'min': min(num_packages),
        'max': max(num_packages),
        'over50%': popular_packages_over_50}

pprint (packages_sorted)
pprint (res)
pprint (new)


