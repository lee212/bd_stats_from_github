from pprint import pprint
from search import searchRepo
from collections import Counter

class fetchRepo(searchRepo):

    conf_file = "config.gitlab.yml"
    special_query = ""

    def fetch_all(self):
        result = {}
        self.action = "projects"
        self.target = ""
        self.query = None
        url = self.get_api_url()
        res = self.request_api(url)
        c = Counter()

        page = 1
        total_pages = int(self.raw_response.headers['X-Total-Pages'])
        while page <= total_pages:
            for item in res:
                unique = item['path_with_namespace']
                self.target=item['id']
                self.special_query = "/repository/tree?recursive=True"
                url1 = self.get_api_url()
                try:
                    res1 = self.request_api(url1)
                    ext = self.count_extension(res1)
                    req = self.read_requirements(res1)
                    packages = self.get_py_packages(req)
                    readme = self.find_readme_rst(res1)
                except:
                    continue
                result[unique] = {
                        'packages': packages,
                        'readme': readme,
                        'extensions': ext.most_common()
                        }
                c += Counter(packages)
            page += 1
            self.action = "projects"
            self.target = ""
            self.query = None
            self.special_query = ""
            url = self.get_api_url(page)
            res = self.request_api(url)
        self.result = {
                'items': result,
                'total_count': len(result),
                'total_packages': c.most_common()
                }
        return self.result 

    def get_py_packages(self, data):
        res = []
        for item in data:
            l = item.split("\n")
            l = [ x.split("=")[0] for x in l ]
            res += l
        tmp = set(res)
        res = list(tmp)
        res = filter(None, res)
        return res

    def get_file(self, path):
        q = "/repository/files?ref=master&file_path="
        self.special_query = q + path
        url = self.get_api_url()
        res = self.request_api(url)
        content = res['content'].decode('base64')
        return content

    def find_readme_rst(self, data):
        return self.find_files('README.rst', data)

    def read_requirements(self, data):
        return self.find_files('requirements.txt', data)

    def find_files(self, search_name, data):
        l = []
        for fileitem in data:
            name = fileitem['name']
            path = fileitem['path']
            if name == search_name:
                content = self.get_file(path)
                l.append(content)
        return l

    def count_extension(self, data):
        l = []
        for fileitem in data:
            name = fileitem['name']
            tmp = name.rfind(".")
            if tmp != -1:
                ext = name[tmp+1:]
                l.append(ext)
            ext = ""
        c = Counter(l)
        return c

if __name__ == "__main__":
    stat = fetchRepo()
    stat.name="fall16"
    res = stat.fetch_all()
    stat.save_file()
