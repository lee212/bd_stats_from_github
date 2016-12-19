import requests
import sys
import json
from pprint import pprint
import re
import time
import datetime
from stdlib_list import stdlib_list
import os
import math
import yaml
import utils
import urllib

class surveyGitHub(object):

    conf_file = "config.yml"
    raw_data = {}

    action = "search"
    target = "repositories"
    query = ""

    result = {}
    result['items'] = {}
    result['page'] = 1
    result['pages'] = 1

    res = { 'merged': 
            { 'total_count': 0,
                'items' : {} },
            'keyword': {},
            'created_at' : str(datetime.datetime.now())
            }

    def __init__(self):
        self.conf = self.get_conf()
        self.check_git_token()

    def set_query(self, string):
        self.query = string

    def load_inputs(self, yaml_path):
        with open(yaml_path, "r") as inputs:
            inputs = yaml.load(inputs)
        self.inputs = inputs

    def get_conf(self):
        with open(self.conf_file, 'r') as config_file:
            conf = yaml.load(config_file)
        return conf

    def check_git_token(self, conf=None):
        if not conf:
            conf = self.conf
        if not conf['git_token']:
            print ("no authorization for git api. set git_token in configuration")
            time.sleep(3)
            return False
        return True

    def request_api(self, url, loop=True):
        conf = self.conf
        headers = {'Authorization': 'token ' + conf['git_token']}
        if conf['debugging'] in [ 'INFO', 'DEBUG']:
            print(url)
        r = requests.get(url, headers=headers)
        if (r.status_code != 200 and r.headers['X-RateLimit-Remaining'] == '0' and
                loop):
            if conf['debugging'] in [ 'DEBUG', 'WARNING']:
                print(r)
            time.sleep(60)
            return self.request_api(url, False)
        data = (json.loads(r.text))
        return data

    def get_total_pages(self, searched_data=None):
        if not searched_data:
            searched_data = self.raw_data
        pages = int(math.ceil(searched_data['total_count'] * 1.0 /self.conf['per_page']))
        return pages

    def generate_repo_url(self, page=1):
        conf = self.conf
        repo_url = (
                "{0}/{1}/{2}?q={3}&sort={4}&page={5}&per_page={6}".format(conf['api_addr'],
                    self.action, self.target, self.query, conf['sort'], page,
                    conf['per_page']))
        return repo_url

    def recent_activities(self):

        res = self.res
        
        cnt = 0
        # multiple keywords for search item
        for keyword in self.inputs['keywords']:
            self.query = urllib.quote_plus(keyword)
            # date query from config.yml
            self.query += "+" + self.conf['Recent']
            url1 = self.generate_repo_url()
            ret1 = self.request_api(url1)
            res['keyword'][keyword] = { 'total_count' : ret1['total_count'],
                    'items': ret1['items'] }

            for item in ret1['items']:
                # count duplicate
                if item['full_name'] in res['merged']['items'].keys():
                    cnt += 1
                res['merged']['items'][item['full_name']] = item
        return res

    def retrieve_py_modules(self, items):
        """ Find 'import *' keywords in python files """

        repos = items['merged']['items']
        for full_name, item in repos.iteritems():
            if not item:
                continue
            repo = item['full_name']
            target = "code"
            lang = "Python"
            query = "import+in:file+language:{0}+repo:{1}".format(lang, repo)
            url = ("{0}/{1}/{2}?q={3}".format(self.conf['api_addr'],
                self.action, target, query))
            codes_searched = self.request_api(url)
            repos[repo]['packages'] = set()
            for code in codes_searched['items']:
                contents = self.get_file_contents(code)
                packages = self.get_module_names(contents)
                repos[repo]['packages'].update(packages)
            repos[repo]['packages'] = list(repos[repo])
        return items

    def get_file_contents(self, item):

        c_url = item['repository']['contents_url']
        contents_url = c_url.replace('/{+path}', item['path'])
        contents = self.request_api(contents_url)
        try:
            decoded_contents = contents['content'].decode('base64')
            return decoded_contents
        except KeyError as e:
            return []

    def get_module_names(self, contents):
        package1 = re.findall("import (.*)$", contents, re.M)
        package2 = re.findall("from (.*) import .*$", contents, re.M)

        packages = package1 + package2
        package_names = []
        for package in packages:
            # import x, [y, z]
            if not isinstance(package, tuple):

                is_comment = package.find("#")
                if is_comment > 0:
                    package = package[:is_comment]
                package_names += package.split(',')
        tmp = []
        for package in package_names:
            module_name_only = package.split('.')[0]
            module_name_only = module_name_only.split(" as ")[0]
            module_name_only = module_name_only.strip()
            if not utils.check_stdlibs(module_name_only):
                tmp.append(module_name_only)

        package_names = set(tmp)
        return package_names
 
    def language_preference(self):
        res = {}
        stat = { 'all' : [] }
        for keyword in self.inputs['keywords']:
            self.query = urllib.quote_plus(keyword)
            url1 = self.generate_repo_url()
            ret1 = self.request_api(url1)
            try:
                res[keyword]['count'] = ret1['total_count']
            except KeyError as e:
                res[keyword] = { 'count' : ret1['total_count'] }

            for lang in self.conf['languages']:
                self.query = (urllib.quote_plus(keyword) + "+language:" +
                urllib.quote_plus(lang))
                url2 = self.generate_repo_url()
                ret2 = self.request_api(url2)
                res[keyword][lang] = ret2['total_count']
                try:
                    res[lang]['all'].append(ret2['total_count'] * 1.0 /
                            ret1['total_count'])
                except KeyError as e:
                    res[lang] = {}
                    res[lang]['all'] = [(ret2['total_count'] * 1.0 /
                        ret1['total_count'])]
            stat['all'].append(ret1['total_count'])
        for lang in self.conf['languages']:
            res[lang]['avg'] = utils.mean(res[lang]['all'])
        stat['avg'] = utils.mean(stat['all'])

        res.update(stat)
        return res

    def run_survey(self):

        repo_url = self.generate_repo_url()
        list_of_repo_first_slice = self.request_api(repo_url)

        result = self.result
        result['created_at'] = str(datetime.datetime.now())
        result['query_url'] = repo_url
        result['items'] = list_of_repo_first_slice['items']
        result['total_count'] = list_of_repo_first_slice['total_count']
        result['pages'] = self.get_total_pages(list_of_repo_first_slice)
        result = self.get_all_items(result, repo_url)
        result_packages = self.get_python_packages_from_ipynb(result)
        self.save_file(result_packages)

    def get_python_packages_from_ipynb(self, data):

        cnt=0
        res = {}
        for i in data['items']:
            #pprint (i)
            # u'url': u'https://api.github.com/repos/linanqiu/word2vec-sentiments',
            cnt+=1
            m = re.search("(.*)repos/(.*)",i['url'])
            if not m:
                continue
            repo = m.group(2)
            res[repo] = {}
            # meta data
            res[repo]['name'] = i['name']
            res[repo]['description'] = i['description']
            res[repo]['created_at'] = i['created_at']
            res[repo]['pushed_at'] = i['pushed_at']
            res[repo]['forks_count'] = i['forks_count']
            res[repo]['watchers_count'] = i['watchers_count']
            res[repo]['html_url'] = i['html_url']

            target = "code"
            query = "nbformat+language:\"Jupyter Notebook\""
            url = ("{0}/{1}/{2}?q={3}".format(self.conf['api_addr'],
                self.action, target, query + "+repo:" + repo))
            codes_searched = self.request_api(url)
            if codes_searched['items']:
                res[repo]['packages'] = []
                for j in codes_searched['items']:
                    res[repo][j['path']] = {}
                    c_url = j['repository']['contents_url']
                    contents_url = c_url.replace('/{+path}', j['path'])
                    contents = self.request_api(contents_url)
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
                            package = package[:package.find("#")]
                            package_names = package_names + package.split(',')
                        # from x import y
                        else:
                            tmp = list(package)
                            tmp[1] = tmp[1][:tmp[1].find('\\n')]
                            tmp[1] = tmp[1][:tmp[1].find('#')]
                            package = tuple(tmp)
                            package_names.append(package[0]) 
                        packages_cleaned.append(package)
                    tmp = []
                    for package in package_names:
                        module_name_only = package.split('.')[0]
                        module_name_only = module_name_only.split(" as ")[0]
                        module_name_only = module_name_only.strip()
                        if not utils.check_stdlibs(module_name_only):
                            tmp.append(module_name_only)

                    package_names = set(tmp)
                    res[repo][j['path']]['raw'] = packages_cleaned
                    res[repo][j['path']]['packages'] = list(package_names)
                    res[repo]['packages'] = (list(set(res[repo]['packages'] +
                        list(package_names))))
        return res

    # github api returns up to 100 items
    # this function collects rest of items
    def get_all_items(self, result, repo_url):
        if result['total_count'] > self.conf['per_page']:
        # Be careful with this option because the search size increases as a number of
        # pages is increased
            while result['page'] <= result['pages']:
                result['page'] += 1
                repo_url = self.generate_repo_url(result['page'])
                ret = self.request_api(repo_url)
                result['items'] = result['items'] + ret['items']
        return result

    def save_file(self, data=None):
        if not data:
            data = self.result
        name = (self.query.split("+")[0] + "." + time.strftime("%Y%m%d-%H%M%S")
                + ".yml")

        with open(name, 'w') as outfile:
            json.dump(data, outfile, indent=4, sort_keys=True)

if __name__ == "__main__":
    packages = surveyGitHub()
    #packages.set_query(sys.argv[1])
    #packages.run_survey()
    packages.load_inputs(sys.argv[1])
    #ret = packages.language_preference()
    #pprint (ret)
    ret = packages.recent_activities()
    #pprint(ret)
    packages.save_file(ret)
    ret2 = packages.retrieve_py_modules(ret)
    packages.save_file(ret2)
