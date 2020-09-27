Tracker app for [Movie-Notifier](https://www.movie-notifier.com).

Frontend app for the website can be found [here](https://github.com/Xeraphin/torrent_notifier_frontend) and backend app can be found [here](https://github.com/Xeraphin/torrent_notifier_backend).

-----------------

This app scans requested titles by users on torrent trackers and informs users when they are detected.

In order for this app to work, you need to have an info.json file in your current working directory. It looks like this:

![info](https://github.com/Xeraphin/torrent_notifier_tracker/blob/master/images/info.json..png?raw=true)

SQL functions in this app was written for a MySQL 8.0 database. Provide credentials accordingly.

Rarbg app_id can be a random string to identify your app.

The app will only scan iptorrents if a cookie from a logged in browser is provided, if you cannot provide that, fill all iptorrents field in the info.json with empty strings.

---------------------------------------------------
The database schema for this app is as follows:

![database](https://github.com/Xeraphin/torrent_notifier_tracker/blob/master/images/database.png?raw=true)

---------------------------------------------------
Trackers table is as follows:

![trackers](https://github.com/Xeraphin/torrent_notifier_tracker/blob/master/images/trackers.png?raw=true)

tracker_id columns must be as they are in the image.

-------------------------------------------------
Versions table is as follows:

![versions](https://github.com/Xeraphin/torrent_notifier_tracker/blob/master/images/versions.png?raw=true)

-------------------------------------------------

The app runs in an infinite loop.60 seconds after the last loop has ended, requested titles are fetched from the database and are scanned on the trackers. During the scan, each release is categorized by release type. After the scan has ended, the requests are fetched with user id and season and episode info. If one of the requested release types was found in one or more of the trackers, an is sent to the user.

The html template for the email is in the email.html file.

A sample email:

![email](https://github.com/Xeraphin/torrent_notifier_tracker/blob/master/images/email.png?raw=true)
