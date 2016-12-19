from stdlib_list import stdlib_list
import sys
import operator

def check_stdlibs(module_name):
    libs = stdlib_list(str(sys.version_info[0]) + "." + str(sys.version_info[1]))
    return (module_name in libs)

def mean(n):
    return float(sum(n)) / max(len(n), 1)

def sort_dict(self, val, reverse=True):
    val_sorted = sorted(val.items(), key=operator.itemgetter(1),
        reverse=reverse)
    return val_sorted

