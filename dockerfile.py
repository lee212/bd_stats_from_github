# res = search $tool in dockerfile
# for i in res
#     content = read(i.dockerfile)
#     packages = collect package names
#
import re
import sys
import os
import urllib
from pprint import pprint
from search import searchRepo
import utils
import requests

class searchDockerfileInCode(searchRepo):
    """This searches dockerfiles from 'code', not repositories"""

    default_search = "language:Dockerfile"
    search_api_limit = 1000

    repo_info_tokeep = [
            'created_at',
            'pushed_at',
            'updated_at',
            'language',
            'fork_count',
            'stargazers_count',
            'watchers_count',
            'owner'
            ]
       
    def search(self, page=1):
        self.result = {} # RESET
        self.target = "code"
        # search code size limit: 384kb
        # ref: https://developer.github.com/v3/search/#search-code
        #self.query = "from+in:file+language:Dockerfile+size:>383"
        for keyword in self.inputs['keywords']:
            if keyword.find(self.default_search) > 0:
                self.query = keyword
            else:
                self.query = urllib.quote_plus(keyword) + "+" + \
                        self.default_search

            url = self.get_api_url(page)
            ret = self.request_api(url)
            self.raw_data = ret
            for item in ret['items']:
                repo_name = item['repository']['full_name']
                filepath = item['path']
                contents = self.get_file_contents(item)
                #tmp=repo_name.replace("/","_")
                #with open(tmp, 'w') as file:
                #        file.write(contents)
                #continue
                instructions = self.read_dockerfile(contents)
                key = os.path.abspath("/" + repo_name + "/" + filepath)
                file_path = os.path.abspath("/" + filepath)
                if not repo_name in self.result:
                    self.result[repo_name] = { 
                            'dockerfile': { file_path: None }
                            }
                self.result[repo_name]['dockerfile'][file_path] = \
                        instructions

        return self.result

    def retrieve_dockerhub(self, repos):
        for repo_name in repos:
            contents = self.get_dockerfile_from_dockerhub(repo_name)
            if not contents:
                continue
            instructions = self.read_dockerfile(contents)
            file_path = self.dockerhub_path(repo_name)
            if not repo_name in self.result:
                self.result[repo_name] = { 
                        'dockerfile': { file_path: None }
                        }
                self.result[repo_name]['dockerfile'][file_path] = \
                        instructions

        return self.result

    def dockerhub_path(self, repo_name):
        if repo_name.find("/") < 0:
            is_official_repo = True
            repo_addr = repo_name
        else:
            repo_addr = "r/%s" % repo_name
        repo_addr = ('http://hub.docker.com/%s/~/dockerfile/' % repo_addr)
        return repo_addr

    def get_dockerfile_from_dockerhub(self, repo_name):
        repo_addr = self.dockerhub_path(repo_name)
        raw = requests.get(repo_addr)
        raw_contents = raw.text
        raw_contents = raw_contents.encode("ascii","ignore")
        is_found = raw_contents.find('RepoDetailsDockerfileStore')
        if is_found > 0:
            found = \
                    re.match(".*dockerfile\":\"([^}]*)\".*",raw_contents[is_found:])
            if found:
                result = found.group(1)
                return result
        return None

    def search_all(self):
        res = self.search()
        if self.raw_data['total_count'] > self.conf['per_page']:
            page = 1
            pages = self.get_total_pages(self.raw_data)
            while page <= pages:
                page += 1
                temp = self.search(page)
                res.update(temp)
                if self.search_api_limit <= page * self.conf['per_page']:
                    break
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
        #content = content.encode("ascii","ignore")
        content = re.sub(r'\\\n\s+', "", content)
        for inst in instructions.keys():
            res = re.findall(inst + " (.*)", content)
            if res:
                instructions[inst] = [x.strip() for x in res]
        return instructions

    def get_repo(self):
        self.action = "repos"
        temp = {}
        for k, v in self.result.iteritems():
            repo_name = k
            self.target = repo_name
            url = self.get_api_url()
            repo_info = self.request_api(url)
            for i in repo_info.keys():
                if i in self.repo_info_tokeep:
                    temp[i] = repo_info[i]

            self.result[k]['repo'] = temp
            temp = {}

    def get_readme(self):
        self.action = "repos"
        for k, v in self.result.iteritems():
            repo_name = k
            self.target = repo_name + "/readme"
            url = self.get_api_url()
            readme = self.request_api(url)
            self.result[k]['readme'] = readme

    def get_repo_names_as_inputs(self, func):
        #self.inputs = utils.yaml_load(yaml_path)
        repo_names = eval("self.inputs" + func)
        self.inputs['keywords'] = [ "repo:" + x for x in repo_names ]

    def get_repo_names_from_dockerhub(self):
        ret = self.search_dockerhub()
        return ret

    def is_official_image(self, name):

        url = "//api.github.com/repos/docker-library/official-images/contents/library"
        return

    def update_name(self, name=None):
        """name is used to store a file"""
        if not name:
            name = ".dockerfile"
        self.name = self.name + name

if __name__ == "__main__":
    dockerfiles = searchDockerfileInCode()
    dockerfiles.get_inputs(sys.argv[1])
    if sys.argv[2] == "from_repo":
        dockerfiles.get_repo_names_as_inputs("['result']['merged_items']['items'].keys()")
    elif sys.argv[2] == "from_dockerhub":
        ret = dockerfiles.get_repo_names_from_dockerhub()
        res = dockerfiles.retrieve_dockerhub(ret['items'])
        pprint (res)

        sys.exit()
    res = dockerfiles.search_all()
    dockerfiles.get_repo()
    dockerfiles.get_readme()
    dockerfiles.update_name()
    dockerfiles.save_file()
