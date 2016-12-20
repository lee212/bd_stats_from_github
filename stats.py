import json
import sys
from pprint import pprint
import datetime
from collections import Counter
import utils
import os

class Statistics(object):

    name = ""

    packages = Counter()
    packages_cnt = 0
    raw_data = None

    recent_days = [ 30, 60, 90, 180, 365 ]
    packages_recent = {}

    def __init__(self):
        for day in self.recent_days:
            day = str(day)
            self.packages_recent[day] = { 'total': 0,
                    'average': 0,
                    'package_count': [],
                    'packages': [],
                    'top20': [] }

    def read_file(self, name):

        try: 
            self.name = os.path.basename(name).split('.')[0]
        except:
            pass
        with open(name, 'r') as datafile:
            data = json.load(datafile)
            self.raw_data = data
            return data

    def is_in_timeframe(self, date_n_time, days):
        orig = datetime.datetime.strptime(date_n_time, '%Y-%m-%dT%H:%M:%SZ')
        check = datetime.datetime.now() + datetime.timedelta(-1 * days)
        return orig >= check

    def pick_close_day(self, date_n_time, days_list=None):
        if not days_list:
            days_list = self.recent_days
        orig = datetime.datetime.strptime(date_n_time, '%Y-%m-%dT%H:%M:%SZ')
        diff = datetime.datetime.now() - orig
        return min(days_list, key=lambda x:abs(x - diff.days))

    def count_package_occurrences(self, data=None):
        if not data:
            data = self.raw_data

        # for combined list of multiple keywords search
        if 'merged' in data:
            data = data['merged']

        packages = []
        for repo_name, v in data['items'].iteritems():
            if not 'packages' in v:
                continue
            # create a large list to include all packages
            packages += v['packages']

        c = Counter(packages)
        self.packages_cnt = sum(c.values())
        self.packages = c
        return c.most_common()

    def trends(self, data=None):
        return self.count_package_occurrences_over_days(data)

    def count_package_occurrences_over_days(self, data=None):
        if not data:
            data = self.raw_data

        # for combined list of multiple keywords search
        if 'merged' in data:
            data = data['merged']

        for k, v in data['items'].iteritems():
            if not 'packages' in v:
                continue
            day = str(self.pick_close_day(v['created_at']))
            self.packages_recent[day]['packages'] += v['packages']
            self.packages_recent[day]['package_count'].append(len(v['packages']))

        for day, val in self.packages_recent.iteritems():
            c = Counter(self.packages_recent[day]['packages'])
            self.packages_recent[day]['total'] = sum(c.values())
            self.packages_recent[day]['average'] = \
            utils.mean(self.packages_recent[day]['package_count'])
            self.packages_recent[day]['top20'] = c.most_common(20)

        return self.packages_recent

stat = Statistics()
data = stat.read_file(sys.argv[1])
res = stat.count_package_occurrences(data)
utils.save_json_to_file(res, stat.name + '.count_packages')
res2 = stat.count_package_occurrences_over_days()
utils.save_json_to_file(res2, stat.name + '.count_packages_timeframe')
