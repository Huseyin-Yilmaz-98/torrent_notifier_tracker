import mysql.connector
import json
from functions import print_with_time


class SQL:
    def __init__(self, infofile="info.json"):
        self.infofile = infofile
        self.db = None

    # function to connect to database, returns true or false depending on success
    def connect(self):
        try:
            if self.db is not None:
                self.db.close()
        except Exception as e:
            print_with_time("Previous connection could not be closed. Skipping this step. Error: " + str(e))

        # try to get database info from the info file, if something goes wrong, return false
        try:
            with open(self.infofile, "r", encoding="utf-8") as f:
                info = json.load(f)["database"]
        except Exception as e:
            print_with_time("Failed to get database info from file... Error " + str(e))
            return False

        # try to connect to database, if something goes wrong, return false, otherwise return true
        try:
            self.db = mysql.connector.connect(
                host=info["host"],
                user=info["user"],
                password=info["password"],
                database=info["database"]
            )
            print_with_time("Connected to database...")
            return True
        except Exception as e:
            print_with_time("Failed to connect to database... Error: " + str(e))
            return False

    # takes a cursor object and closes it
    @staticmethod
    def destroy_cursor(cursor):
        try:
            cursor.close()
        except Exception as e:
            print_with_time("Failed to destroy cursor. Error: " + str(e))

    # returns a cursor, if something goes wrong, tries one more time and returns None
    def check_connection_and_create_cursor(self, counter=0):
        if counter == 1:
            self.connect()

        try:
            cursor = self.db.cursor()
            return cursor
        except Exception as e:
            if counter == 0:
                print_with_time("Failed to create cursor. Will try one more time. Error: " + str(e))
                return self.check_connection_and_create_cursor(1)
            else:
                print_with_time("Failed to create cursor for a second time! Error: " + str(e))
                return None

    # gets all requested titles from the database and returns a list, if something goes wrong, returns an empty list
    # each element of the list is a string
    def get_titles_to_check(self):
        titles = []

        cursor = self.check_connection_and_create_cursor()
        if cursor is None:
            print_with_time("Couldn't get titles to check, returning empty list.")
            return titles

        try:
            cursor.execute("SELECT DISTINCT tid FROM requests")
            results = cursor.fetchall()
            for result in results:
                titles.append(result[0])

        except Exception as e:
            print_with_time("Failed to get title list from database. Returning a partial list. Error: " + str(e))

        finally:
            self.destroy_cursor(cursor)
            return titles

    # returns a list of previously checked titles
    def get_previously_checked_titles(self):
        titles = []

        cursor = self.check_connection_and_create_cursor()
        if cursor is None:
            print_with_time("Couldn't get previously checked titles, returning empty list.")
            return titles

        try:
            cursor.execute("SELECT DISTINCT tid FROM found_releases")
            results = cursor.fetchall()
            for result in results:
                titles.append(result[0])

        except Exception as e:
            print_with_time("Failed to get checked title list from database."+
                            "Returning a partial list. Error: " + str(e))

        finally:
            self.destroy_cursor(cursor)
            return titles

    def get_found_releases(self, tracker_id, title_id):
        releases = {}
        cursor = self.check_connection_and_create_cursor()
        if cursor is None:
            print_with_time("Couldn't get found releases, returning empty dict.")
            return releases

        try:
            cursor.execute("SELECT vid,file_names FROM found_releases WHERE tracker_id= %s AND tid=%s",
                           (tracker_id, title_id,))
            results = cursor.fetchall()
            for result in results:
                releases.update({result[0]: json.loads(result[1])})

        except Exception as e:
            print_with_time("Failed to get found releases from database. Returning a partial dict. Error: " + str(e))

        finally:
            self.destroy_cursor(cursor)
            return releases

    def update_found_releases(self, tracker_id, title_id, releases):
        cursor = self.check_connection_and_create_cursor()
        if cursor is None:
            print_with_time("Couldn't update found releases...")
            return

        try:
            cursor.execute("DELETE FROM found_releases WHERE tracker_id=%s AND tid=%s", (tracker_id, title_id))
            cursor.executemany("INSERT INTO found_releases(tracker_id,tid,file_names,vid) VALUES(%s,%s,%s,%s)",
                               [[tracker_id, title_id, json.dumps(releases[release]), release] for release in releases])
            self.db.commit()
            self.destroy_cursor(cursor)

        except Exception as e:
            print_with_time("Failed to update found releases. Error: " + str(e))
            self.destroy_cursor(cursor)

    def get_requests_with_user_data(self):
        requests = []
        cursor = self.check_connection_and_create_cursor()
        if cursor is None:
            print_with_time("Couldn't get requests with user data...")
            return requests

        try:
            cursor.execute("""SELECT DISTINCT requests.tid,requests.season,requests.episode,titles.name,
            users.email,requests.uid,users.name,users.language FROM requests JOIN titles ON requests.tid=titles.tid
            JOIN users ON requests.uid=users.uid""")
            results = cursor.fetchall()

            for result in results:
                requests.append({
                    "tid": result[0], "season": result[1], "episode": result[2], "title_name": result[3],
                    "email": result[4], "uid": result[5], "user_name": result[6], "language": result[7]
                })

        except Exception as e:
            print_with_time("Failed to get requests with user data. Returning a partial list. Error: " + str(e))

        finally:
            self.destroy_cursor(cursor)
            return requests

    @staticmethod
    def filter_by_season_and_episode(file_names_old, season, episode):
        if episode != -1:
            texts_to_search = [f'_s{season:02}e{episode:02}_']
        elif season != -1:
            texts_to_search = [f'_s{season:02}_', f'_season_{season}_', f'_season_{season:02}_']
        else:
            return file_names_old

        file_names = []

        for file_name in file_names_old:
            is_matched = False
            for text in texts_to_search:
                if is_matched:
                    break
                if text in file_name.lower().replace(" ", "_").replace(".", "_").replace("-", "_"):
                    file_names.append(file_name)
                    is_matched = True

        return file_names

    def get_requested_versions_and_found_releases(self, tid, season, episode, uid):
        data = {"requested_formats": [], "found_releases": []}
        cursor = self.check_connection_and_create_cursor()
        if cursor is None:
            print_with_time("Couldn't get requested versions and found releases...")
            return data

        try:
            cursor.execute("""SELECT vid FROM requests WHERE tid=%s
            AND season=%s AND episode=%s AND uid=%s""", (tid, season, episode, uid))
            results = cursor.fetchall()

            for result in results:
                data["requested_formats"].append(result[0])

            if len(data["requested_formats"]) > 0:
                cursor.execute("""SELECT trackers.name, vid, file_names FROM found_releases
                JOIN trackers ON found_releases.tracker_id=trackers.tracker_id
                WHERE tid=%s""", (tid,))
                results = cursor.fetchall()
                for result in results:
                    file_names = self.filter_by_season_and_episode(json.loads(result[2]), season, episode)
                    if len(file_names) > 0:
                        data["found_releases"].append({
                            "tracker": result[0],
                            "format": result[1],
                            "file_names": file_names
                        })

        except Exception as e:
            print_with_time("Failed to get requested versions and found releases. Error: " + str(e))

        finally:
            self.destroy_cursor(cursor)
            return data

    def delete_request(self, tid, season, episode, uid):
        cursor = self.check_connection_and_create_cursor()
        if cursor is None:
            print_with_time("Couldn't delete request from database... Will try again...")
            self.delete_request(tid, season, episode, uid)

        try:
            cursor.execute("""DELETE FROM requests WHERE tid=%s AND season=%s AND episode=%s AND uid=%s""",
                           (tid, season, episode, uid))
            self.db.commit()
            self.destroy_cursor(cursor)
        except Exception as e:
            print_with_time("Couldn't delete request from database... Will try again. Error: " + str(e))
            self.destroy_cursor(cursor)
            self.delete_request(tid, season, episode, uid)
