import requests
import random
from typing import List

from lib import cache
from lib import utils

BASE_URL = "https://rule34.xxx/index.php"


def get_latest_post_id() -> int:
    req = requests.get(
        BASE_URL, params={"page": "dapi", "q": "index", "s": "post", "json": 1}
    )

    if req.text.strip():
        return req.json()[0]["id"]


def get_random_from_query(query: str, limit: int = 1) -> List[int]:
    result = []

    req = requests.get(
        BASE_URL,
        params={"page": "dapi", "q": "index", "s": "post", "json": 1, "tags": query},
    )
    if req.text.strip():
        while len(result) < limit:
            post = random.choice(req.json())
            result.append(post["file_url"])

    return result


def get_random(limit: int = 1) -> List[int]:
    result = []
    config = utils.load_config()

    if config["enableCaching"]:
        cdat = cache.get(".cache", "rule34_LatestPostId")

        if cdat:
            lpostid = cdat.data
        else:
            lpostid = get_latest_post_id()
            cdat = cache.Cache("rule34_LatestPostId", lpostid)
            cache.store(".cache", cdat)
    else:
        lpostid = get_latest_post_id()

    while len(result) < limit:
        id = random.randint(1, lpostid)

        req = requests.get(
            BASE_URL,
            params={"page": "dapi", "q": "index", "s": "post", "id": id, "json": 1},
        )
        if req.text.strip():
            result.append(req.json()[0]["file_url"])

    return result
