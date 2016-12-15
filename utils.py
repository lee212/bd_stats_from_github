from stdlib_list import stdlib_list
import sys

def check_stdlibs(module_name):
    libs = stdlib_list(str(sys.version_info[0]) + "." + str(sys.version_info[1]))
    return (module_name in libs)
