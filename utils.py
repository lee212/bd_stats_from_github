from stdlib_list import stdlib_list
import sys
import operator
import time
import json

def check_stdlibs(module_name):
    libs = stdlib_list(str(sys.version_info[0]) + "." + str(sys.version_info[1]))
    return (module_name in libs)

def mean(n):
    return float(sum(n)) / max(len(n), 1)

def sort_dict(self, val, reverse=True):
    val_sorted = sorted(val.items(), key=operator.itemgetter(1),
        reverse=reverse)
    return val_sorted


def save_json_to_file(data, filename):
    name = (filename + "." + time.strftime("%Y%m%d-%H%M%S")
            + ".yml")
    with open(name, 'w') as outfile:
        json.dump(data, outfile, indent=4, sort_keys=True)
