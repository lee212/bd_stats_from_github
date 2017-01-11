# res = search $tool in dockerfile
# for i in res
#     content = read(i.dockerfile)
#     packages = collect package names
#
import re
import sys
import os
from pprint import pprint
from search import searchRepo
from dockerfile_parse import DockerfileParser

class searchDockerfile(searchRepo):
       
    def __init(self):
        self.conf = self.get_conf()
        self.check_git_token()

    def search(self, page=1):
        self.result = {} # RESET
        self.target = "code"
        # search code size limit: 384kb
        # ref: https://developer.github.com/v3/search/#search-code
        self.query = "from+in:file+language:Dockerfile+size:>383"
        url = self.get_api_url(page)
        ret = self.request_api(url)
        self.raw_data = ret
        for item in ret['items']:

            contents = self.get_file_contents(item)
            instructions = self.read_dockerfile(contents)
            key = os.path.abspath("/" + item['repository']['full_name'] + "/" +
                    item['path'])
            file_path = os.path.abspath("/" + item['path'])
            if not item['repository']['full_name'] in self.result:
                self.result[item['repository']['full_name']] = { 
                        file_path: None
                        }
            self.result[item['repository']['full_name']][file_path] = \
                    instructions

        return self.result

    def search_all(self):
        res = self.search()
        if self.raw_data['total_count'] > self.conf['per_page']:
            page = 1
            pages = self.get_total_pages(self.raw_data)
            while page <= pages:
                page += 1
                temp = self.search(page)
                res.update(temp)
        self.result = res
        return res

    def read_dockerfile(self, content):
        instructions = {
                "FROM": [],
                "MAINTAINER": [],
                "RUN": [],
                "CMD": [],
                "LABEL": [],
                "EXPOSE": [],
                "ENV": [],
                "ADD": [],
                "COPY": [],
                "ENTRYPOINT": [],
                "VOLUMN": [],
                "USER": [],
                "WORKDIR": [],
                "ARG": [],
                "ONBUILD": [],
                "STOPSIGNAL": [],
                "HEALTHCHECK": [],
                "SHELL": [],
                }

        # patch for multi lines
        content = re.sub(r'\\\n\s+', "", content)
        for inst in instructions.keys():
            res = re.findall(inst + " (.*)", content)
            if res:
                instructions[inst] = res
        return instructions

if __name__ == "__main__":
    dockerfiles = searchDockerfile()
    dockerfiles.get_inputs(sys.argv[1])
    res = dockerfiles.search_all()
    dockerfiles.save_file()
