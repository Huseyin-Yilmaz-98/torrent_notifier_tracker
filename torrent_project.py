import requests
from bs4 import BeautifulSoup as bs
from functions import print_with_time


# takes movie id as argument, returns a list of the detected releases,
# if an error occurs, returns an empty list but prints the error
def torrent_project(movie_id):
    headers = {
        "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/" +
                  "webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9",
        "accept-language": "en-US,en;q=0.9,es;q=0.8",
        "sec-fetch-dest": "document",
        "sec-fetch-mode": "navigate",
        "sec-fetch-site": "none",
        "sec-fetch-user": "?1",
        "upgrade-insecure-requests": "1",
        "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36" +
                      " (KHTML, like Gecko) Chrome/85.0.4183.102 Safari/537.36"
    }

    url = "https://torrentproject2.com/?t=" + str(movie_id)

    try:
        response = requests.get(url, headers=headers, timeout=15)
    except Exception as e:
        print_with_time("Error connecting to " + url + " - Error: " + str(e))
        return []

    try:
        soup = bs(response.content, "html.parser")
    except Exception as e:
        print_with_time("Error parsing from " + url + " Error: " + str(e))
        return []

    main_content = soup.find_all("div", id="main_content")
    if len(main_content) == 0:
        print_with_time("Main content couldn't be parsed from " + url)
        return []

    main_content = main_content[0]

    table = main_content.find_all("div", class_="tt")
    if len(table) == 0:
        print_with_time("Table couldn't be parsed from " + url)
        return []

    table = table[0]

    releases = []
    rows = table.find_all("div")
    for row in rows:
        if row.get("class"):
            continue
        a = row.find_all("a")
        if len(a) != 0:
            releases.append(a[0].text)

    return releases
