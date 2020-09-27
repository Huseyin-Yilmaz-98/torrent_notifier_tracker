import requests
from functions import print_with_time
from datetime import datetime
import time
import json

headers = {
    "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/" +
                  "537.36 (KHTML, like Gecko) Chrome/84.0.4147.105 Safari/537.36"
}


class Rarbg:
    def __init__(self):
        # app_id is a string that defines the app that makes a request to the torrentapi
        self.app_id = self.get_app_id()
        self.url = 'https://torrentapi.org/pubapi_v2.php'

        # each function checks the last request time and waits for 2 seconds if it was less than 3 seconds ago
        self.last_request_time = None
        self.token = self.get_token()

    # function that reads and returns the app_id from info.json file
    @staticmethod
    def get_app_id():
        with open("info.json", "r", encoding="utf-8") as f:
            app_id = json.load(f)["rarbg"]["app_id"]

        return app_id

    # gets the token from the api, returns None if an error occurs
    def get_token(self):
        if self.last_request_time is not None and (datetime.now() - self.last_request_time).seconds < 3:
            time.sleep(2)

        payload = {
            'app_id': self.app_id,
            'get_token': 'get_token'
        }

        try:
            response = requests.get(self.url, params=payload, headers=headers, timeout=5)
            self.last_request_time = datetime.now()
        except Exception as e:
            print_with_time("Couldn't connect to torrentapi to get token! Error: " + str(e))
            self.last_request_time = datetime.now()
            return None

        try:
            received_json = response.json()
        except Exception as e:
            print_with_time("Error converting to json to get token! Error: " + str(e))
            return None

        if 'token' not in received_json:
            print_with_time("Token not found in json!")
            return None

        return received_json['token']

    # this is a recursive funtion, it gets called for a second time if the token expired,
    # in which case the counter is 1 and if it fails again, returns an empty list
    def get_release_list(self, movie_id, counter=0):
        if self.token is None:
            self.token = self.get_token()

        if self.token is None:
            print_with_time("Attempt to get token failed for a second time, won't check!")
            return []

        if self.last_request_time is not None and (datetime.now() - self.last_request_time).seconds < 3:
            time.sleep(2)

        payload = {
            'app_id': self.app_id,
            'mode': 'search',
            'search_imdb': movie_id,
            'token': self.token,
            "limit": 100,
            "ranked": 0
        }

        try:
            response = requests.get(self.url, params=payload, headers=headers, timeout=5)
            self.last_request_time = datetime.now()
        except Exception as e:
            print_with_time("Couldn't connect to website to get release list from rarbg! Error: " + str(e))
            self.last_request_time = datetime.now()
            return []

        try:
            received_json = response.json()
        except Exception as e:
            print_with_time("Error converting to json to get release list from rarbg! Error: " + str(e))
            return []

        if 'error_code' in received_json:
            # error code 2 means the token is invalid or expired
            if received_json['error_code'] == 2:
                if counter == 1:
                    print_with_time("Token error for the second time!")
                    return []
                else:
                    self.token = self.get_token()
                    return self.get_release_list(movie_id, 1)

            # error code 20 means there were no results
            elif received_json['error_code'] == 20:
                return []

            else:
                print_with_time("Unknown error getting release list from rarbg: " + str(received_json))
                return []

        if 'torrent_results' not in received_json:
            print_with_time("Error getting release list from rarbg! movie_id= " + movie_id + " JSON: " + received_json)
            return []

        torrent_results = received_json['torrent_results']
        releases = []
        for release in torrent_results:
            if 'filename' in release:
                releases.append(release['filename'])
        return releases
