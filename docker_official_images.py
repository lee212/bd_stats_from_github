from search import searchRepo
from pprint import pprint

class dockerOfficialImages(searchRepo):

    repo = "docker-library/official-images"
    path = "library"

    def __init__(self):
        self.conf = self.get_conf()
        self.check_git_token()
        self.names = self.read_official_images()

    def read_official_images(self):
        """Name only"""

        names = []
        self.action = "repos"
        self.target = self.repo + "/contents/" + self.path
        url = self.get_api_url()
        res = self.request_api(url)
        for i in res:
            names.append(i['name'])
        return names

def test():
    test = dockerOfficialImages()
    pprint (test.names)

if __name__ == "__main__":
    pass
    # test()
