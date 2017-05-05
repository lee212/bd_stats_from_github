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

def show_depends(name, option=None):
        
    res = apt_rdepends(name, "depends")
    if option == "flat":
        d_name_only = []
        for k, v in res.iteritems():
           d_name_only += [ x[0] for x in v['depends'] ]
        return Counter(d_name_only)
    else:
        return res

def show_rdepends(name):
    return apt_rdepends(name, "reverse")

def apt_rdepends(name, q):
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

    if q == "reverse":
        option = "-r"
        keyname = "rdepends"
        search_keyword = "  Reverse Depends: "
    else:
        option = "depends"
        keyname = "depends"
        search_keyword = "  Depends: "

    FNULL = open(os.devnull, 'w')
    res = subprocess.Popen("apt-rdepends %s %s" % (option, name), shell=True,
            stdout=subprocess.PIPE, stderr=FNULL).stdout.read()
    new_d = {}
    p_node = ''
    for u in res.split("\n"):
        if u[:2] != "  ":
            p_node = u
            continue

        if u[:len(search_keyword)] == search_keyword:
            #pprint("-"+u[0:19]+"-")
            if u.find(":")>0:
                tmp = u.split(":",1)
                name_and_version = tmp[1].strip().split(' ',1)
                if not p_node in new_d:
                    new_d[p_node] = { keyname: [] }
                new_d[p_node][keyname].append(name_and_version)
    return new_d

def get_names(depends):
    depends = list(set([ x.split()[0] for x in depends.split(",")]))
    return depends

def stats_in_csv(file_or_path, option):
    a = Counter()

    if os.path.isdir(file_or_path):
        onlyfiles = [f for f in listdir(file_or_path) if isfile(join(file_or_path, f))]
        mypath = file_or_path
    else:
        onlyfiles = [file_or_path]
        mypath = ''

    # TEMPORAL CODE FOR DEPENDENCIES
    tmp_depends = []
    for filename in onlyfiles:
        full_path = mypath + filename
        res = load_json(full_path)
        name = filename.split(".")[0]
        if option:
            packages = res['result'][option]
            c = Counter()
            t_l = []
            for df_fullpath, dps in packages.iteritems():
                tmp = Counter(dps)
                c += tmp
                lib_names = list(set(list(tmp.elements())))
                t_l += lib_names
                #for i in lib_names:
                #    tmp_depends.append([df_fullpath, i, tmp[i]])
            frequent_c = Counter(t_l)
            #pprint(c.most_common())
            #print "==================="
            #pprint(frequent_c.most_common())
            #print (len(packages))
            dockerfile_cnt = len(packages)
            package_info = {}
            for k in set(frequent_c.elements()):
                if k in ['debconf', 'libc6','libcomerr2','libgcc1','libx11-6','zlib1g']:
                    continue
                info = aptcache_show(k)
                package_info[k] = info
                try:
                    size= info['Size']
                except KeyError as e:
                    # 'virtual packages'
                    # https://www.debian.org/doc/packaging-manuals/virtual-package-names-list.txt
                    size= ''

                tmp_depends.append([name, k , size, c[k],frequent_c[k],
                    dockerfile_cnt])
            package_stat = {}
            for x in frequent_c.most_common():
                perc = round(x[1]/(dockerfile_cnt*1.0),1)
                try:
                    package_stat[perc].append(x[0])
                except:
                    package_stat[perc] = [x[0]]
            image_stat = []
            for df_fullpath, dps in packages.iteritems():
                total_lib_size_in_image = 0
                ddd = {}
                for x in range(1,11):
                    do = round(x * 0.1,1)
                    ddd[do] = 0
                #print (ddd)
                for p in dps:
                    #print p
                    try:
                        psize = int(package_info[p]['Size'])
                    except:
                        psize = 0
                    if psize == 0:
                        continue
                    total_lib_size_in_image += psize
                    #print psize, total_lib_size_in_image
                    m = frequent_c[p]
                    perc = round(m/(dockerfile_cnt*1.0),1)
                    while perc > 0.0:
                        ddd[perc] += -1 * psize
                        perc-=0.1
                        perc = round(perc,1)
                    #pprint(ddd)
                #sys.exit()
                for x in ddd:
                    image_stat.append([df_fullpath, x, ddd[x], total_lib_size_in_image])
            for k,v in package_stat.iteritems():
                asize = 0
                for k1 in v:
                    try:
                        psize = int(package_info[k1]['Size'])
                    except:
                        psize = 0
                    asize+=psize

                print "%s, %s, %d" % (k, asize, len(v))

            return (image_stat)
            continue
        else:
            packages = res['result']['dockerfiles']['packages']
        c = Counter(packages)
        a += c

    if len(tmp_depends) > 0:
        return tmp_depends

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
    opt = None
    if len(sys.argv) == 3:
        opt = sys.argv[2]
    a = stats_in_csv(mypath, opt)
    for i in a:
        ddd=",".join(str(x) for x in i)
        print (ddd)

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
