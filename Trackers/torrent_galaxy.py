import requests
from bs4 import BeautifulSoup as bs
from functions import print_with_time
import time


# returns an empty list if something goes wrong, this function is recursive,
# it will call itself until it reaches the last page in the results and add the results together
def torrent_galaxy(max_page, movie_id, page=0):
    headers = {
        "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36" +
                      " (KHTML, like Gecko) Chrome/85.0.4183.102 Safari/537.36"
    }

    url = f"https://torrentgalaxy.to/torrents.php?parent_cat=&search={movie_id}&sort=id&order=desc&page={page}"

    try:
        response = requests.get(url, headers=headers, timeout=15)
    except Exception as e:
        print_with_time("Error connecting to " + url + "  Error: " + str(e))
        return []

    if "No results found..." in response.text:
        return []

    try:
        soup = bs(response.content, "html.parser")
    except Exception as e:
        print_with_time("Error parsing from " + url + " Error: " + str(e))
        return []

    table = soup.find("div", class_="tgxtable")

    if table is None:
        print_with_time("No tables found in: " + str(url))
        return []

    rows = table.find_all("div", class_="tgxtablerow")

    file_names = []

    for row in rows:
        try:
            file_names.append(row.find_all("div", class_="tgxtablecell")[3].find("b").text)
        except Exception as e:
            print_with_time("Error getting the file name from a row in torrent galaxy. Error: " + str(e))

    # if it is the first page, check for any further results, otherwise just return the current list
    if page == 0:
        try:
            page_items = soup.find("ul", class_="pagination").find_all("li", class_="page-item")
            last_page = int(page_items[len(page_items) - 2].find("a").text.split(" ")[0])

            for page in range(1, min(last_page, max_page)):
                time.sleep(3)
                file_names += torrent_galaxy(max_page, movie_id, page)

        except Exception as e:
            print_with_time("Error getting the last page number from torrent galaxy. Error: " + str(e))

    return file_names
