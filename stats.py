import json
import sys
from pprint import pprint
import datetime
from collections import Counter
import utils
import os
import copy

class Statistics(object):

    name = ""
    raw_data = None
    top_ranks = 20
    sort_by = "stargazers_count" # | 'watchers_count', 'forks_count'

    recent_days = [ 30, 60, 90, 180, 365 ]
    package = {
            'total_count': 0,
            'average': 0.0,
            'numbers': [],
            'list': [],
            'most_common': []
            }

    language = { 
            'total_count': 0,
            'percentage': 0.0
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

    result = {
            'packages': copy.deepcopy(package),
            'packages_recent_days': {},
            'languages': {},
            'examples': []
            }


    def __init__(self):
        self.init_package_recent_days()

    def init_package_recent_days(self):
        """Create package dictionary per day defined in recent_days"""
        for day in self.recent_days:
            self.result['packages_recent_days'][str(day)] = \
            copy.deepcopy(self.package)

    def read_file(self, name):
        """Read yaml file and set name from the filename"""
        with open(name, 'r') as datafile:
            data = json.load(datafile)
            self.raw_data = data
            self.set_name(name)
            return data

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
        self.result['packages']['list'] = list(c)
        self.result['packages']['numbers'] = numbers
        self.result['packages']['average'] = utils.mean(numbers)
        self.result['packages']['most_common'] = c.most_common(self.top_ranks)
        return c.most_common(n)

    def trends(self, data=None):
        return self.count_package_occurrences_over_days(data)

    def count_package_occurrences_over_days(self, data=None, where="recent",
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

        packages_recent_days = self.result['packages_recent_days']
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

        return packages_recent_days

    def language_distribution(self):
        data = self.raw_data
        result = self.result['languages']

        try:
            sdata = data['result']['search_keywords']
            data = data['result']['merged_items']['language_in']
        except KeyError as e:
            return None

        for kw, val in sdata.iteritems():
            for lang, val2 in val['language_in'].iteritems():
                percent_for_lang = (val2['total_count'] * 1.0 /
                val['total_count'])
                try:
                    result[lang]['percentage'] = \
                    utils.mean([result[lang]['percentage'], percent_for_lang])
                except KeyError as e:
                    result[lang] = { 'percentage': percent_for_lang }
                #print kw, lang, val2['total_count'], val['total_count']
        return result

    def recent_activities(self, n=None, order='descending'):
        data = self.raw_data

        if not n:
            n = self.top_ranks

        try:
            data = data['recent']['merged_items']
        except KeyError as e:
            return none

        order = True if order == 'descending' else False

        sorted_data = sorted(data['items'].items(), 
                key=lambda x: x[1][self.sort_by], reverse=order)

        for item in sorted_data:
            name = item[0]
            value = item[1]
            example = copy.deepcopy(self.example)
            for k, v in example.iteritems():
                example[k] = value[k]
            self.result['examples'].append(example)

        return self.result['examples']

    def save_file(self, data=None):
        """ Store json to yaml """
        name = (self.name + ".stats")
        utils.save_json_to_file(self.result, name)
    
stat = Statistics()
data = stat.read_file(sys.argv[1])
res = stat.language_distribution()
pprint(res)
res2 = stat.recent_activities()
pprint(res2[:10])
res = stat.count_package_occurrences()
pprint(res)

# To discover new projects, filter repos with active one from statistics
# https://developer.github.com/v3/repos/statistics/
res2 = stat.count_package_occurrences_over_days()
for k,v in res2.iteritems():
    print k, v['average']
    pprint(v['most_common'])
stat.save_file()
