from rarbg import Rarbg
from SQL import SQL
from functions import print_with_time, send_email
import time
from torrent_project import torrent_project
from iptorrents import Iptorrents
from torrent_galaxy import torrent_galaxy


class Tracker:
    def __init__(self):
        self.sql = SQL()
        self.rarbg = Rarbg()
        self.iptorrents = Iptorrents()
        self.is_iptorrents_valid = self.iptorrents.is_cookie_valid()
        self.checked_titles = None

    def start(self):
        if not self.is_iptorrents_valid:
            print_with_time("Iptorrents cookie not valid! It will be excluded from the scan!")

        while True:
            # Try to connect to database. Go on even if that fails as each sql function checks connection first.
            self.sql.connect()

            # the first time the loop runs, get a list of titles that was previously scanned
            if self.checked_titles is None:
                self.checked_titles = self.sql.get_previously_checked_titles()

            print_with_time("Starting the scan from the trackers...")

            # Scan trackers for new releases
            self.update_found_releases()

            print_with_time("All releases are updated... Starting the scan for found requests...")

            # Now check if any requests are found, and if so, send mails
            self.check_for_found_requests()
            print_with_time("Scan ended...")

            # Close the database connection.
            try:
                if self.sql.db is not None:
                    self.sql.db.close()
            except Exception as e:
                print_with_time("Failed to close connection. Error: " + str(e))
            finally:
                self.sql.db = None

            print("")
            time.sleep(10)

    # Function that detects found requests and informs users
    def check_for_found_requests(self):
        # get each unique request grouped by user, title, season and episode
        requests_with_user_data = self.sql.get_requests_with_user_data()
        for request in requests_with_user_data:
            # each request has tid, season, episode, uid, email, title_name, user_name, language
            try:
                vafr = self.sql.get_requested_versions_and_found_releases(request["tid"], request["season"],
                                                                          request["episode"], request["uid"])
                # vafr is a dict containing of two lists: requested_formats and found_releases
                # and each element of found_releases is a dict
                # now check if any of the found formats matches with requested formats
                if self.check_for_requested_formats(vafr["requested_formats"],
                                                    [release["format"] for release in vafr["found_releases"]]):
                    season = request["season"]
                    episode = request["episode"]

                    # add the season and episode info to the beginning of the title if they are not -1
                    title = f'(S{request["season"]:02}E{episode:02}) {request["title_name"]}' if episode != -1 \
                        else f'(S{season:02}) {request["title_name"]}' if season != -1 else request["title_name"]

                    # create html template for email
                    html = self.create_html_body(request["user_name"], title, vafr["requested_formats"],
                                                 vafr["found_releases"], request["language"])

                    # try to send an email to inform the user, if it is successful, delete the request
                    subject = f'"{title}" Torrent Bulundu!' if request["language"] == 'tr' \
                        else f'"{title}" Torrent Found!'

                    try:
                        send_email(html, subject, request["email"])
                        self.sql.delete_request(request["tid"], season, episode, request["uid"])
                    except Exception as e:
                        print_with_time(f"Failed to send mail to {request['email']}. Error: {str(e)}")

                    time.sleep(2)
            except Exception as e:
                print_with_time("Error processing a found request. Error: " + str(e))

    # this function replaces the dynamic info from email.html file to create an html template for email
    @staticmethod
    def create_html_body(user_name, title, requested_formats, found_releases, language):
        with open("email.html", "r", encoding="utf-8") as f:
            html = f.read()

        salut = f'Merhaba {user_name}, "{title}" yapımı için yeni sürümler tespit edildi.' if language == 'tr' \
            else f'Hello {user_name}, we have detected new releases for the title "{title}".'

        file_name_text = 'Dosya Adı' if language == 'tr' else 'File Name'
        html = html.replace("replace_salut", salut).replace("replace_file_name", file_name_text)
        rows = []

        for release in found_releases:
            if release["format"] in requested_formats:
                for file_name in release["file_names"]:
                    rows.append(f"<tr><td><h5>{release['tracker']}</h5></td>" +
                                f"<td><h5>{file_name}</h5></td></tr>")

        html = html.replace("replace_rows", "".join(rows))
        return html

    # if any of the found formats is requested, returns True
    @staticmethod
    def check_for_requested_formats(requested_formats, found_formats):
        for found_format in found_formats:
            if found_format in requested_formats:
                return True
        return False

    # get current releases from trackers, if there new releases, update the database
    def update_found_releases(self):
        # get each requested title id, ignores season and episode information
        titles_to_check = self.sql.get_titles_to_check()
        print_with_time(f"{len(titles_to_check)} requests to check...")

        for index, title in enumerate(titles_to_check):
            print_with_time(f'{index + 1}/{len(titles_to_check)} being checked...')

            # if the title was checked previously, don't scan after the first 2 pages in trackers
            if title not in self.checked_titles:
                max_page = 1000
                self.checked_titles.append(title)

            else:
                max_page = 2

            # since rarbg api can return empty list sometimes, it will be checked up to 3 times
            rarbg_results = []

            for _ in range(3):
                rarbg_results = self.rarbg.get_release_list(title)

                if len(rarbg_results) != 0:
                    break

                time.sleep(3)

            trackers = {
                "rarbg": self.process_release_list(rarbg_results),
                "tproject": self.process_release_list(torrent_project(title)),
                "tgalaxy": self.process_release_list(torrent_galaxy(max_page, title))
            }

            if self.is_iptorrents_valid:
                trackers.update({"ipt": self.process_release_list(self.iptorrents.get_release_list(max_page, title))})

            for tracker in trackers:
                current_releases = trackers[tracker]
                if len(current_releases) != 0:
                    previous_releases = self.sql.get_found_releases(tracker, title)
                    releases = self.combine_releases(previous_releases, current_releases)
                    if releases != previous_releases:
                        self.sql.update_found_releases(tracker, title, releases)

            time.sleep(5)

    # combines previous and current releases into one dict
    @staticmethod
    def combine_releases(previous, current):
        releases = {}

        for release in previous:
            releases.update({release: previous[release].copy()})

        for version in current:
            if version not in releases:
                releases.update({version: current[version]})
            else:
                for release in current[version]:
                    if release not in releases[version]:
                        releases[version].append(release)

        return releases

    # function that detects release types based on keywords
    @staticmethod
    def process_release_list(releases):
        keywords = {
            "_4k": [" 2160p ", " hdr ", " uhd "],
            "_3D": [" 3d ", " hsbs ", " h-sbs ", "half-sbs", "half sbs", " h-ou ", "half-ou", " half ou "],
            "remux": [" remux "],
            "bdrip": ["bdrip"],
            "brrip": ["brrip"],
            "webdl": ["webdl", "web-dl"],
            "webrip": ["webrip", "web-rip", " web "],
            "ts": [" ts ", "hd-ts", "hdts", " cam ", "camrip", "cam-rip"],
            "bluray": ["bluray"],
            "hdtv": ["hdtv"],
            "dvdrip": ["dvdrip", "dvd-rip", " dvd9 ", " dvd5 ", "dvd-r"],
            "dvdscr": ["dvdscr", "dvd-scr"],
            "hdrip": ["hdrip"]
        }

        # add different combinations of keywords by replacing spaces with special characters
        for keyword in keywords:
            for key in keywords[keyword].copy():
                if " " in key:
                    keywords[keyword].append("_" + key.strip(" ") + "_")
                    keywords[keyword].append("-" + key.strip(" ") + "-")
                    keywords[keyword].append("." + key.strip(" ") + ".")

        matches = {}

        for release in releases:
            is_match_found = False
            for keyword in keywords:
                if is_match_found:
                    break

                for tag in keywords[keyword]:
                    if tag in release.lower():
                        if keyword not in matches:
                            matches.update({keyword: []})

                        matches[keyword].append(release)
                        is_match_found = True
                        break

            # if none of the keywords are found in the file name, it will be categorized as unknown
            if not is_match_found:
                if "unk" not in matches:
                    matches.update({"unk": []})

                matches["unk"].append(release)

        return matches
