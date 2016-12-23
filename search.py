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
import utils
import urllib
import copy

class searchRepo(object):

    conf_file = "config.yml"
    raw_data = {}

    name = ""
    action = "search"
    target = "repositories"
    query = ""

    result = { 
            'searched_at' : str(datetime.datetime.now()),
            'merged_items': { 
                'total_count': 0, 
                'items' : {},
                'language_in': { 
                    'all': {},
                    },
                }, 
            'search_keywords': {
                },
            }

    recent = copy.deepcopy(result)

    def __init__(self):
        self.conf = self.get_conf()
        self.check_git_token()

    def set_query(self, string):
        self.query = string

    def get_inputs(self, yaml_path):
        """Read yaml input file"""
        self.inputs = utils.yaml_load(yaml_path)
        self.set_name(yaml_path)
        self.init_search_keywords()

    def set_name(self, filepath):
        """Set a name for search from an input filename"""
        try:
            self.name = os.path.basename(filepath).split('.')[0]
        except:
            self.name = ""

    def init_search_keywords(self):
        """ Create dict data in search_keywords in case of not existing """
        for keyword in self.inputs['keywords']:
            if not keyword in self.result['search_keywords']:
                self.result['search_keywords'][keyword] = {}
            if not keyword in self.recent['search_keywords']:
                self.recent['search_keywords'][keyword] = {}

    def get_conf(self):
        """Read yaml config file"""
        return utils.yaml_load(self.conf_file)

    def check_git_token(self, conf=None):
        if not conf:
            conf = self.conf
        if not conf['git_token']:
            token = self.get_git_token_env()
            if not token:
                print ("no authorization for git api. set git_token")
                return False
            self.conf['git_token'] = token
        return True

    def get_git_token_env(self):
        return os.getenv('git_token')

    def request_api(self, url, recursive=True):
        """Call github api

        Args:
            url (str): git api url to request
            recursive (bool): boolean to call again itself

        Returns:
            dict: https response data from requests.get()

        """
        conf = self.conf
        headers = {'Authorization': 'token ' + conf['git_token']}
        if conf['debugging'] in [ 'INFO', 'DEBUG']:
            print(url)
        r = requests.get(url, headers=headers)
        if (r.status_code != 200 and r.headers['X-RateLimit-Remaining'] == '0' and
                recursive):
            if conf['debugging'] in [ 'DEBUG', 'WARNING']:
                print(r)
            time.sleep(60)
            return self.request_api(url, False)
        data = (json.loads(r.text))
        return data

    def get_api_url(self, page=1):
        """Return github api url based on settings"""
        repo_url = (
                "{0}/{1}/{2}?q={3}&sort={4}&page={5}&per_page={6}".format(
                    self.conf['api_addr'], self.action, self.target, self.query,
                    self.conf['sort'], page, self.conf['per_page']))
        return repo_url

    def get_total_pages(self, searched_data=None):
        """ Return total number of pages from 'per_page' config value and
        'total_count' searched value

        Args:
            searched_data (dict): contains 'total_count' in its dict key and value

        Returns:
            int: number of pages based on the total_count and per_page

        """
        if not searched_data:
            searched_data = self.raw_data
        pages = int(math.ceil(searched_data['total_count'] * 1.0 /self.conf['per_page']))
        return pages

    def search_with_date(self):
        """Search recent activities"""

        search_keywords = self.recent['search_keywords']
        merged_items = self.recent['merged_items']['items']
        
        duplicate = 0
        # multiple keywords for search item
        for keyword in self.inputs['keywords']:
            self.query = urllib.quote_plus(keyword)
            # date query from config.yml
            self.query += "+" + self.conf['Recent']
            url = self.get_api_url()
            ret = self.request_api(url)
            search_keywords[keyword]['total_count'] = ret['total_count']
            search_keywords[keyword]['items'] = ret['items']
            search_keywords[keyword]['query'] = self.query

            for item in ret['items']:
                # count duplicate
                if item['full_name'] in merged_items.keys():
                    duplicate += 1

                # create a unique data with key: value
                merged_items[item['full_name']] = item
        return self.recent

    def retrieve_py_modules(self, items, language="Python"):
        """ Find 'import *' keywords in python files """

        repos = items['merged_items']['items']
        for repo_full_name, item in repos.iteritems():
            if not item:
                continue
            target = "code"
            query = "import+in:file+language:{0}+repo:{1}".format(language,
                    repo_full_name)
            url = ("{0}/{1}/{2}?q={3}".format(self.conf['api_addr'],
                self.action, target, query))
            codes_searched = self.request_api(url)
            repos[repo_full_name]['packages'] = set()
            for code in codes_searched['items']:
                contents = self.get_file_contents(code)
                packages = self.get_module_names(contents)
                repos[repo_full_name]['packages'].update(packages)
            repos[repo_full_name]['packages'] = \
                    list(repos[repo_full_name]['packages'])

        return items

    def get_file_contents(self, item):
        """Retrieve file contents from github API
        
        Args:
            item (dict): searched item

        Returns:
            str: decoded file contents from github api
            
        """

        c_url = item['repository']['contents_url']
        contents_url = c_url.replace('/{+path}', item['path'])
        contents = self.request_api(contents_url)
        try:
            decoded_contents = contents['content'].decode('base64')
            return decoded_contents
        except KeyError as e:
            return ""

    def get_module_names(self, contents):
        """ Collect top module names from strings 
        
        Args:
            contents (str): file contents

        Returns:
            set: set of package names

        """
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
 
    def search_with_language(self, option='language'):
        """ Count a number of repositories per language written in """

        # count repositories per language with search keywords
        search_keywords = self.result['search_keywords']
        merged_items = self.result['merged_items']['language_in']

        # search api runs: x (keywords) * (y (languages) + 1) times
        for keyword in self.inputs['keywords']:
            self.query = urllib.quote_plus(keyword)
            url = self.get_api_url()
            ret = self.request_api(url)

            search_keywords[keyword]['total_count'] = ret['total_count']
            search_keywords[keyword]['items'] = ret['items']
            search_keywords[keyword]['query'] = self.query
            search_keywords[keyword]['language_in'] = {}

            for opt in self.conf[option]:
                self.query = urllib.quote_plus(keyword)
                self.query += ("+{0}:".format(option) + urllib.quote_plus(opt))
                url = self.get_api_url()
                ret = self.request_api(url)
                language_in = search_keywords[keyword]['language_in']
                language_in[opt] = {}
                language_in[opt]['total_count'] = ret['total_count'] 
                language_in[opt]['items'] = ret['items']
                language_in[opt]['query'] = self.query

                for item in ret['items']:
                    # create a unique data with key: value
                    try:
                        merged_items[opt]['items'][item['full_name']] = item
                    except KeyError as e:
                        merged_items[opt] = { 
                                'total_count': 0,
                                'items': {}
                                }

        return search_keywords

    def run_search(self, query):
        """Obsolete function"""
        """run search from a direct single query string"""

        self.query = query
        repo_url = self.get_api_url()
        list_of_repo_first_slice = self.request_api(repo_url)

        result = self.result
        result['total_count'] = list_of_repo_first_slice['total_count']
        result['items'] = list_of_repo_first_slice['items']
        result['query'] = self.query
        result = self.get_all_items(result)
        result_packages = self.get_python_packages_from_ipynb(result)
        self.save_file(result_packages)
        return True

    def get_python_packages_from_ipynb(self, data):
        """no guarantee working"""

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

    def get_all_items(self, data):
        """ Search all items over page limits (100) """
        if data['total_count'] > self.conf['per_page']:
        # Be careful with this option because the search size increases as a number of
        # pages is increased
            page = 1
            pages = self.get_total_pages(data)
            while page <= pages:
                page += 1
                repo_url = self.get_api_url(page=page)
                ret = self.request_api(repo_url)
                data['items'] += ret['items']
        return data

    def save_file(self, data=None):
        """ Store json to yaml """
        if not data:
            data = { 
                    'result': self.result,
                    'recent': self.recent
                    }
        name = (self.name + "." + time.strftime("%Y%m%d-%H%M%S")
                + ".yml")

        with open(name, 'w') as outfile:
            json.dump(data, outfile, indent=4, sort_keys=True)

if __name__ == "__main__":
    packages = searchRepo()
    packages.get_inputs(sys.argv[1])
    ret = packages.search_with_language()
    ret = packages.search_with_date()
    ret2 = packages.retrieve_py_modules(ret)
    packages.save_file()
