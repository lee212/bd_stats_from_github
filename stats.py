import json
import sys
from pprint import pprint
import datetime
from collections import Counter
import utils
import os
import copy
from docker_official_images import dockerOfficialImages

class Statistics(object):

    name = ""
    raw_data = None
    top_ranks = 20
    sort_by = "stargazers_count" # | 'watchers_count', 'forks_count'

    package = {
            'total_count': 0,
            'average': 0.0,
            'numbers': [],
            'list': [],
            'most_common': []
            }

    language = { 
            'counts': [],
            'total_counts': [],
            'percentage': 0.0,
            'keywords': []
            }

    # TODO: list contributors
    example = { 
            'full_name': "",
            'description': "",
            'language': "",
            'created_at': "",
            'pushed_at': "",
            'forks_count': 0,
            'watchers_count': 0,
            'stargazers_count': 0,
            }

    dockerfile = {
            'total_counts': 0,
            'baseimages': [],
            'baseos': [],
            'packages': [],
            }

    base_os = {
            'ubuntu':{ 'version': {}, 'total_count':0 },
            'centos':{ 'version': {}, 'total_count':0 },
            'fedora':{ 'version': {}, 'total_count':0 },
            'debian':{ 'version': {}, 'total_count':0 },
            'alpine':{ 'version': {}, 'total_count':0 },
            'busybox':{ 'version': {}, 'total_count':0 },
            }

    result = {
            'packages': copy.deepcopy(package),
            'languages': {},
            'examples': [],
            'dockerfiles': copy.deepcopy(dockerfile),
            }

    recent_days = [ 30, 60, 90, 180, 365 ]
    recent = copy.deepcopy(result)

    def __init__(self):
        self.init_package_recent_days()

    def init_package_recent_days(self):
        """Create package dictionary per day defined in recent_days"""
        self.recent['packages_in_days'] = {}
        for day in self.recent_days:
            self.recent['packages_in_days'][str(day)] = \
            copy.deepcopy(self.package)

    def read_file(self, name):
        """Read yaml file and set name from the filename"""
        with open(name, 'r') as datafile:
            data = json.load(datafile)
            self.raw_data = data
            self.set_name(name)
            return data

        return None

    def set_name(self, filepath):
        """Read a name from file"""
        try: 
            self.name = os.path.basename(filepath).split('.')[0]
            return self.name
        except:
            return None

    def is_in_timeframe(self, date_n_time, day):
        """Return true or false after comparing whether date_n_time is in day"""
        orig = datetime.datetime.strptime(date_n_time, '%Y-%m-%dT%H:%M:%SZ')
        check = datetime.datetime.now() + datetime.timedelta(-1 * day)
        return orig >= check

    def pick_close_day(self, date_n_time, days_list=None):
        """Return a close time window from input date

        Args:
            date_n_time (str): YYYY-MM-DDThh:mm:ssZ
            days_list (list): time window in days

        Returns:
            int: close day from the list
        """

        if not days_list:
            days_list = self.recent_days
        orig = datetime.datetime.strptime(date_n_time, '%Y-%m-%dT%H:%M:%SZ')
        diff = datetime.datetime.now() - orig
        return min(days_list, key=lambda x:abs(x - diff.days))

    def count_package_occurrences(self, data=None, where="recent", n=None):
        """Return occurrences of packages"""

        if not data:
            data = self.raw_data

        # for combined list of multiple keywords search
        try:
            data = data[where]['merged_items']
        except KeyError as e:
            return None

        if not n:
            n = self.top_ranks

        packages = []
        numbers = []
        for repo_name, v in data['items'].iteritems():
            if not 'packages' in v:
                continue
            # create a large list to include all packages
            packages += v['packages']
            numbers.append(len(v['packages']))

        c = Counter(packages)
        self.result['packages']['total_count'] = sum(c.values())
        #self.result['packages']['list'] = list(c)
        #self.result['packages']['numbers'] = numbers
        self.result['packages']['average'] = utils.mean(numbers)
        self.result['packages']['most_common'] = c.most_common(self.top_ranks)
        return c.most_common(n)

    def trends(self, data=None):
        return self.count_package_occurrences_in_days(data)

    def count_package_occurrences_in_days(self, data=None, where="recent",
            n=None):
        if not data:
            data = self.raw_data

        # for combined list of multiple keywords search
        try:
            data = data[where]['merged_items']
        except KeyError as e:
            return None

        if not n:
            n = self.top_ranks

        packages_recent_days = self.recent['packages_in_days']
        for k, v in data['items'].iteritems():
            if not 'packages' in v:
                continue
            for day in self.recent_days:
                if not self.is_in_timeframe(v['created_at'], day):
                    continue
                #day = str(self.pick_close_day(v['created_at']))
                day = str(day)
                packages_recent_days[day]['list'] += v['packages']
                packages_recent_days[day]['numbers'].append(len(v['packages']))

        for day, v in packages_recent_days.iteritems():
            c = Counter(v['list'])
            v['total_count'] = sum(c.values())
            v['average'] = utils.mean(v['numbers'])
            v['most_common'] = c.most_common(n)
            # not to store in files for the following items
            v['list'] = []
            v['numbers'] = []

        return packages_recent_days

    def baseimage_dockerfile(self, n=None):
        data = self.raw_data['result']
        baseimage = []

        if not n:
            n = self.top_ranks

        for k,v in data.iteritems():
            repo_name = k
            dockerfiles = v['dockerfile']
            for k1, v1 in dockerfiles.iteritems():
                filepath = k1
                baseimage += v1['FROM']

        c = Counter(baseimage)
        self.result['dockerfiles']['baseimages'] = c.most_common(n)
        self.result['dockerfiles']['total_counts'] = len(data)
        baseos = self.get_baseimage_os(c.most_common())
        self.result['dockerfiles']['baseos'] = baseos
        return c

    def get_baseimage_os(self, image_list):
        for i in image_list:
            name = i[0]
            count = i[1]
            try:
                os_name, os_version = name.split(":")
            except ValueError as e:
                os_name = name
                os_version = "default"

            if os_name in self.base_os:
                self.base_os[os_name]['version'][os_version] = count
                self.base_os[os_name]['total_count'] += count

        return self.base_os

    def language_distribution_from_all(self, order='descending'):
        data = self.language_distribution(False)
        order = True if order == 'descending' else False
        sorted_data = sorted(data.items(), key=lambda x: x[1]['percentage'],
                reverse=order)
        return sorted_data

    def language_distribution_from_recent(self, order='descending'):
        """TBD - language distribuion is not collected for recent days in
        current search.py"""
        data = self.language_distribution()
        order = True if order == 'descending' else False
        sorted_data = sorted(data.items(), key=lambda x: x[1]['percentage'],
                reverse=order)
        return sorted_data

    def language_distribution(self, is_recent=True):
        data = self.raw_data

        if is_recent == True:
            period = 'recent'
            result = self.recent['languages']
        else:
            period = 'result'
            result = self.result['languages']

        try:
            sdata = data[period]['search_keywords']
            data = data[period]['merged_items']['language_in']
        except KeyError as e:
            return None

        for kw, val in sdata.iteritems():
            tc_for_kw = val['total_count']
            for lang, val2 in val['language_in'].iteritems():
                tc_for_lang = val2['total_count']
                percent_for_lang = (tc_for_lang * 1.0 / tc_for_kw)
                if not lang in result:
                    result[lang] = copy.deepcopy(self.language)
                result[lang]['counts'].append(tc_for_lang)
                result[lang]['total_counts'].append(tc_for_kw)
                result[lang]['keywords'].append(kw)
                result[lang]['percentage'] = \
                        utils.mean([result[lang]['percentage'], percent_for_lang])
                #print kw, lang, val2['total_count'], val['total_count']
        return result

    def examples_from_all_activities(self, n=None, order='descending'):
        return self.get_examples_over_period(n, order, False)

    def examples_from_recent_activities(self, n=None, order='descending'):
        return self.get_examples_over_period(n, order)

    def get_examples_over_period(self, n=None, order='descending', is_recent=True):
        data = self.raw_data

        if is_recent == True:
            period = 'recent' 
            result = self.recent['examples']
        else:
            period = 'result'
            result = self.result['examples']

        if not n:
            n = self.top_ranks

        try:
            data = data[period]['merged_items']
        except KeyError as e:
            return none

        order = True if order == 'descending' else False

        sorted_data = sorted(data['items'].items(), 
                key=lambda x: x[1][self.sort_by], reverse=order)

        cnt = 0
        for item in sorted_data:
            if cnt > n:
                break
            name = item[0]
            value = item[1]
            example = copy.deepcopy(self.example)
            for k, v in example.iteritems():
                example[k] = value[k]
            result.append(example)
            cnt += 1

        return result

    def language_count(self):
        data = self.raw_data

        keywords = data['result']
        summary = {
                'language_percentage': {},
                'total_count':0
                }
        l_sum = summary['language_percentage']
        for keyword, value in keywords.iteritems():
            c = Counter(value['language_count'])
            tmp = dict (c.most_common(15))
            t_cnt = sum(c.values())
            summary['total_count'] = utils.mean([t_cnt, summary['total_count']])

            for k, v in tmp.iteritems():
                perc =  v * 1.0 / t_cnt
                if k in l_sum:
                    l_sum[k] = utils.mean([l_sum[k], perc])
                else:
                    l_sum[k] = perc

        c3 = Counter(l_sum)
        summary['language_percentage'] = c3.most_common()
        self.result = summary
            # total coverage over 90% is expected
            #c2 = Counter(tmp)
            #par = (sum(c2.values()))
            #print par*1.0/sum(c.values())

    def save_file(self, data=None):
        """ Store json to yaml """
        name = (self.name + ".stats")
        data = { 
                "result": self.result,
                "recent": self.recent 
                }
        utils.save_json_to_file(data, name)
   
if __name__ == "__main__":

    stat = Statistics()
    data = stat.read_file(sys.argv[2])
    if sys.argv[1] == "ks" or sys.argv[1] == "keyword_search":
        res = stat.language_distribution_from_all()
        #print(res)
        res2 = stat.examples_from_all_activities()
        #print(res2[:10])
        res2 = stat.examples_from_recent_activities()
        #pprint(res2[:10])
        res = stat.count_package_occurrences()
        #pprint(res)

        # To discover new projects, filter repos with active one from statistics
        # https://developer.github.com/v3/repos/statistics/
        res2 = stat.count_package_occurrences_in_days()
        #for k,v in res2.iteritems():
        #    print k, v['average']
        #    pprint(v['most_common'])
        stat.save_file()
    elif sys.argv[1] == "df" or sys.argv[1] == "dockerfile":
        c = stat.baseimage_dockerfile()
        stat.save_file()
    elif sys.argv[1] == 'lc' or sys.argv[1] == 'language_count':
        c = stat.language_count()
        stat.save_file()

