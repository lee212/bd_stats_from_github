import requests
import sys
import json
from pprint import pprint
import re
import time
import datetime
from stdlib_list import stdlib_list

libs = stdlib_list(str(sys.version_info[0]) + "." + str(sys.version_info[1]))

api_addr = "api.github.com"
token = '9efd098dd8f3212923799f762f900eeb558335e7'
action = "search"
target = "repositories"
sort = "stars"
query=sys.argv[1]

res = {}
res['created_at'] = str(datetime.datetime.now())

headers = {'Authorization': 'token ' + token}
full_url = ("https://{0}/{1}/{2}?q={3}&sort={4}".format(api_addr, action,
    target, query, sort))
#print (full_url)
res['query_url'] = full_url

r = requests.get("https://{0}/{1}/{2}?q={3}&sort={4}".format(api_addr, action,
    target, query, sort), headers=headers)
list_of_repo = (json.loads(r.text))

res['total_count'] = list_of_repo['total_count']
res['items'] = {}
for i in list_of_repo['items']:
    #pprint (i)
    # u'url': u'https://api.github.com/repos/linanqiu/word2vec-sentiments',
    m = re.search("(.*)repos/(.*)",i['url'])
    if m:
        repo = m.group(2)
        res['items'][repo] = {}
        # meta data
        res['items'][repo]['name'] = i['name']
        res['items'][repo]['description'] = i['description']
        res['items'][repo]['created_at'] = i['created_at']
        res['items'][repo]['pushed_at'] = i['pushed_at']
        res['items'][repo]['forks_count'] = i['forks_count']
        res['items'][repo]['watchers_count'] = i['watchers_count']
        res['items'][repo]['html_url'] = i['html_url']

        r2 = requests.get("https://{0}/{1}/{2}?q={3}".format(api_addr, action,
            "code", "nbformat+language:\"Jupyter Notebook\"" + "+repo:" + repo),
            headers=headers)
        if r2.status_code != 200 and r2.headers['X-RateLimit-Remaining'] == '0':
            time.sleep(60)
            r2 = requests.get("https://{0}/{1}/{2}?q={3}".format(api_addr,
                action, "code", "nbformat+language:\"Jupyter Notebook\"" +
                "+repo:" + repo), headers=headers)
        codes_searched = json.loads(r2.text)
        #pprint (codes)
        if codes_searched['items']:
            res['items'][repo]['packages'] = []
            for j in codes_searched['items']:
                res['items'][repo][j['path']] = {}
                c_url = j['repository']['contents_url']
                contents_url = c_url.replace('/{+path}', j['path'])
                r3 = requests.get(contents_url, headers=headers)
                if (r3.status_code != 200 and 
                   r3.headers['X-RateLimit-Remaining'] == '0'):
                    time.sleep(60)
                    r3 = requests.get(contents_url, headers=headers)
                contents = json.loads(r3.text)
                try:
                    decoded_contents = contents['content'].decode('base64')
                except KeyError as e:
                    continue
                #pprint(decoded_contents)
                package1 = re.findall("\"\t*import (.*)$", decoded_contents, re.M)
                package2 = re.findall("\"\t*from (.*) import (.*)$", decoded_contents, re.M)
                #pprint(package1)
                #pprint(package2)
                packages = package1 + package2
                packages_cleaned = []
                package_names = []
                for package in packages:
                    # import x, [y, z]
                    if not isinstance(package, tuple):
                        package = package[:package.find("\\n")]
                        package_names = package_names + package.split(',')
                    # from x import y
                    else:
                        tmp = list(package)
                        tmp[1] = tmp[1][:tmp[1].find('\\n')]
                        package = tuple(tmp)
                        package_names.append(package[0]) 
                    packages_cleaned.append(package)
                tmp = []
                for package in package_names:
                    module_name_only = package.split('.')[0]
                    module_name_only = module_name_only.split(" as ")[0]
                    module_name_only = module_name_only.strip()
                    if not module_name_only in libs:
                        tmp.append(module_name_only)

                package_names = set(tmp)
                res['items'][repo][j['path']]['raw'] = packages_cleaned
                res['items'][repo][j['path']]['packages'] = list(package_names)
                res['items'][repo]['packages'] = list(set(res['items'][repo]['packages'] +
                    list(package_names)))
#pprint(res)
name = query.split("+")[0] + "." + time.strftime("%Y%m%d-%H%M%S") + ".yml"
with open(name, 'w') as outfile:
    json.dump(res, outfile, indent=4, sort_keys=True)
