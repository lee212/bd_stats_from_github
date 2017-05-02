import json
import sys
import subprocess
import os
from os import listdir
from os.path import isfile, join
from pprint import pprint
from collections import Counter

def load_json(filename):

    with open(filename) as data_file:    
        data = json.load(data_file)
    return data

def aptcache_show(name):
    FNULL = open(os.devnull, 'w')
    res = subprocess.Popen("apt-cache show %s" % name, shell=True,
            stdout=subprocess.PIPE, stderr=FNULL).stdout.read()
    new_l = []
    for u in res.split("\n"):
        if u.find(":")>0:
            new_l.append(u.split(":",1))
    new_d = dict(new_l)
    return new_d

def show_rdepends(name):
    """ Sample:

    build-essential
      Reverse Depends: abi-compliance-checker (1.99.9-2)
      Reverse Depends: blends-dev (0.6.92.3ubuntu1)
      Reverse Depends: critcl (3.1.9-1)
      ...
    dkms
      Reverse Depends: acpi-call-dkms (>= 1.1.0-2)
      Reverse Depends: asic0x-dkms (>= 1.0.1-1)

    Return: dict
    e.g.

    { 'abc': { 'rdepends': [[ 'xyz', '(>= 1.0.0)' ],
                            [ '...', '(ubuntu1.0.1)' ]]
                            }
                            }
    """
    FNULL = open(os.devnull, 'w')
    res = subprocess.Popen("apt-rdepends -r %s" % name, shell=True,
            stdout=subprocess.PIPE, stderr=FNULL).stdout.read()
    new_d = {}
    p_node = ''
    for u in res.split("\n"):
        if u[0:19] == "  Reverse Depends: ":
            #pprint("-"+u[0:19]+"-")
            if u.find(":")>0:
                tmp = u.split(":",1)
                name_and_version = tmp[1].strip().split(' ',1)
                new_d[p_node]['rdepends'].append(name_and_version)
        else:
            p_node = u
            new_d[p_node] = { 'rdepends': [] }
            continue
    return new_d

def get_names(depends):
    depends = list(set([ x.split()[0] for x in depends.split(",")]))
    return depends

def stats_in_csv(file_or_path):
    a = Counter()

    if os.path.isdir(file_or_path):
        onlyfiles = [f for f in listdir(file_or_path) if isfile(join(file_or_path, f))]
        mypath = file_or_path
    else:
        onlyfiles = [file_or_path]
        mypath = ''

    for filename in onlyfiles:
        full_path = mypath + filename
        res = load_json(full_path)
        packages = res['result']['dockerfiles']['packages']
        c = Counter(packages)
        a += c

    li = a.most_common(50)
    for i in li:
        package_name = i[0]
        info = aptcache_show(package_name)
        rinfo = show_rdepends(package_name)
        depends_cnt = rdepends_cnt = 0
        depends_names = ""
        size = 0
        size_all = 0
        priority = ""
        try:
            desc = info['Description-en'] # dpkg has 'Description'
            if 'Depends' in info:
                depends = info['Depends']
                depends_names = get_names(depends)
                depends_cnt = len(depends_names)
            rdepends_cnt = len(rinfo[package_name]['rdepends'])
            size = info['Size'] # Not Installed-Size
            priority = info['Priority']
            section = info['Section']
        except KeyError as e: 
            continue
        for j in depends_names:
            info_d = aptcache_show(j)
            try:
                #print info_d['Package'], info_d['Installed-Size']
                size_all += int(info_d['Size'])
            except KeyError as e:
                continue

        # in latex table
        print ("%s & %s & %s & %s & %s & %s & %s (%s) & %s \\\\ \\hline" %
                (package_name, desc, section, depends_cnt, rdepends_cnt, 
                ", ".join(depends_names), size, size_all, priority))

    return a

if __name__ == "__main__":

    mypath=sys.argv[1]
    a = stats_in_csv(mypath)
    total_count = sum(a.values())
    re = a.most_common()
    top_count = 0
    for i,b in re:
        if b == 1:
            continue
        top_count += b
    print ("total number of packages: %s" % total_count)
    print ("Percentage of 1+ used packages: %s" % (top_count * 1.0 /
        total_count))
