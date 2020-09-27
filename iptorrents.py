import requests
import json
from functions import print_with_time
from bs4 import BeautifulSoup as bs
import time


class Iptorrents:
    def __init__(self):
        self.username, self.password, cookie = self.get_info()
        self.headers = {
            "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image" +
                      "/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9",
            "accept-language": "en-US,en;q=0.9,es;q=0.8",
            "cache-control": "max-age=0",
            "cookie": cookie,
            "sec-fetch-dest": "document",
            "sec-fetch-mode": "navigate",
            "sec-fetch-site": "none",
            "sec-fetch-user": "?1",
            "upgrade-insecure-requests": "1",
            "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36" +
                          "(KHTML, like Gecko) Chrome/85.0.4183.121 Safari/537.36"
        }
        self.session = requests.Session()

    # reads username, password and cookie info from info.json
    @staticmethod
    def get_info():
        with open("info.json", "r", encoding="utf-8") as f:
            iptorrents = json.load(f)["iptorrents"]
        return iptorrents["username"], iptorrents["password"], iptorrents["cookie"]

    # returns true or false depending on whether the cookie is still valid
    def is_cookie_valid(self):
        response = self.session.get("https://www.iptorrents.com/topics", headers=self.headers)
        return "checking_browser" not in response.text

    # tries to relogin with the cureent cookies, probably will fail
    def login(self):
        try:
            self.session.post("https://www.iptorrents.com/do-login.php", data={
                "username": self.username,
                "password": self.password
            }, headers=self.headers, allow_redirects=True)
        except Exception as e:
            print_with_time("Error trying to login to iptorrents. Error: " + str(e))

    # gets a list of the releases from the page, this is a recursive function,
    # first time it's called a movie_id is provided and the search is done based on that movie_id,
    # if there are multiple pages, the function calls itself with a link this time and adds the results,
    # otherwise returns the results from the current page
    def get_release_list(self, pages_left, movie_id=None, link=None):
        url = f"https://www.iptorrents.com/t?q={movie_id}&qf=#torrents" if movie_id is not None else link

        try:
            response = self.session.get(url, headers=self.headers)
        except Exception as e:
            print_with_time("Error loading page. Error: " + str(e))
            return []

        # if the string "checking_browser" is found on the page,
        # the cookies are no longer valid and there is nothing to do in this case,
        # will return an empty list
        if "checking_browser" in response.text:
            print_with_time("Iptorrents cookie no longer valid! Captcha found!")
            return []

        # if the string "/lout.php" not found in the page, we are no longer logged in
        # and will try to log in again, if that fails, will return an empty list
        if "/lout.php" not in response.text:
            self.login()
            time.sleep(1)
            try:
                response = self.session.get(url, headers=self.headers)
            except Exception as e:
                print_with_time("Error loading page. Error: " + str(e))
                return []

            if "/lout.php" not in response.text:
                print_with_time("Not logged in to iptorrents!")
                return []

        # this means there was no error, simply no results
        if "No Torrents Found!" in response.text:
            return []

        try:
            soup = bs(response.content, "html.parser")
        except Exception as e:
            print_with_time("Error parsing iptorrents page. Error: " + str(e))
            return []

        table = soup.find("table", id="torrents")

        if table is None:
            print_with_time("No tables found in: " + str(url))
            return []

        rows = table.find_all("tr")

        if len(rows) <= 1:
            print_with_time("Less than 1 row in: " + str(url))
            return []

        file_names = []

        # the first row is the table head,
        # therefore the rows will be processed starting from the second row
        for row in rows[1:]:
            name_link = row.find("a", class_="hv")
            if name_link is not None:
                file_names.append(name_link.text)

        # if there is a next page, will add the results from it to the current file names and return
        if len(soup.find_all("i", class_="fa-angle-right")) > 0 and pages_left > 0:
            pagination = soup.find("div", class_="pagination")
            if pagination is not None:
                singles = pagination.find_all("div", class_="single")
                for single in singles:
                    if "Next" in str(single):
                        try:
                            url = "https://www.iptorrents.com/t" + single.find("a")["href"]
                            time.sleep(3)
                            return self.get_release_list(pages_left - 1, link=url) + file_names
                        except Exception as e:
                            print_with_time("Error getting the next page url! Error: " + str(e))

        # if there are no more pages, return the file names from this page
        return file_names
