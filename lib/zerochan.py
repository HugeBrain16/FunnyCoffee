"""Zerochan scraper"""

import requests
import random
import json
from bs4 import BeautifulSoup as BSoup
from typing import List

from lib import cache

BASE_URL = "https://www.zerochan.net"


def get_total_posts() -> int:
    req = requests.get(BASE_URL, params={"p": 1})

    if req.status_code == 200:
        soup = BSoup(req.text, "html.parser")

        content = soup.find("div", {"id": "content"})
        images_total = content.find("p")

        total = ""

        for c in images_total.text:
            if c.isnumeric():
                total += c

    return int(total) if total else 0


def get_random(limit: int = 1) -> List[str]:
    result = []
    config = json.load(open("config.json", "r", encoding="UTF-8"))

    if config["enableCaching"]:
        cdat = cache.get(".cache", "zerochan_TotalPost")

        if cdat:
            total = cdat.data
        else:
            total = get_total_posts()
            cdat = cache.Cache("zerochan_TotalPost", total)
            cache.store(".cache", cdat)
    else:
        total = get_total_posts()

    while len(result) < limit:
        res = requests.get(f"{BASE_URL}/{random.randint(2, total)}")

        if res.status_code == 200:
            soup = BSoup(res.text, "html.parser")
            content_large = soup.find("div", {"id": "large"})
            image = content_large.find("img")

            if image:
                result.append(image["src"])

    return result
