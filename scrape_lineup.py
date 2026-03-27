from bs4 import BeautifulSoup as bs
import requests

def load_lineup(url):

    headers = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
    }
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    soup = bs(response.text,"html.parser")
    return soup



url = 'https://clashfinder.com/m/2ktrees2026/'


trees = load_lineup(url)

match = trees.find(
    "span",
    class_="actNm",
    string=lambda text: text and "bronx" in text.lower()
)

if match:
    act = match.find_parent(class_="act")
    print(act.name, act.get("class"))
    print(act.get_text(" ", strip=True))
    print("-----")

    el = act.parent
    for _ in range(6):
        if el is None:
            break
        print(el.name, el.get("class"), el.get("id"))
        print(el.get_text(" ", strip=True)[:200])
        print("-----")
        el = el.parent
