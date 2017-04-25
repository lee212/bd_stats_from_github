import json
import sys
import subprocess
import os
from os import listdir
from os.path import isfile, join
from pprint import pprint
from collections import Counter

mypath=sys.argv[1]
onlyfiles = [f for f in listdir(mypath) if isfile(join(mypath, f))]

def load_json(filename):

    with open(filename) as data_file:    
        data = json.load(data_file)
    return data

def show_dpkg(name):
    FNULL = open(os.devnull, 'w')
    res = subprocess.Popen("dpkg -s %s" % name, shell=True,
            stdout=subprocess.PIPE, stderr=FNULL).stdout.read()
    new_l = []
    for u in res.split("\n"):
        if u.find(":")>0:
            new_l.append(u.split(":",1))
    new_d = dict(new_l)
    return new_d

def get_names(depends):
    depends = list(set([ x.split()[0] for x in depends.split(",")]))
    return depends

a = Counter()
for filename in onlyfiles:
    full_path = mypath + filename
    res = load_json(full_path)
    packages = res['result']['dockerfiles']['packages']
    c = Counter(packages)
    a += c

li = a.most_common(50)
for i in li:
    info = show_dpkg(i[0])
    try:
        desc = info['Description']
        depends = info['Depends']
        size = info['Installed-Size']
        priority = info['Priority']
        depends_names = get_names(depends)
    except KeyError as e: 
        continue
    size_all = 0
    for j in depends_names:
        info_d = show_dpkg(j)
        try:
            #print info_d['Package'], info_d['Installed-Size']
            size_all += int(info_d['Installed-Size'])
        except KeyError as e:
            continue

    print "%s & %s & %s & %s (%s) & %s \\\\ \\hline" % (i[0], desc,
            ", ".join(depends_names), size, size_all, priority)

total_count = sum(a.values())
print total_count
re = a.most_common()
top_count = 0
for i,b in re:
    if b == 1:
        continue
    top_count += b
print top_count * 1.0 / total_count
