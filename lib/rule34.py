"""lewd stuff ( ͡° ͜ʖ ͡°)..."""

import requests
import random
from typing import List

BASE_URL = "https://rule34.xxx/index.php"


def get_latest_post_id() -> int:
    req = requests.get(
        BASE_URL, params={"page": "dapi", "q": "index", "s": "post", "json": 1}
    )

    if req.status_code == 200:
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

    while len(result) < limit:
        id = random.randint(1, get_latest_post_id())

        req = requests.get(
            BASE_URL,
            params={"page": "dapi", "q": "index", "s": "post", "id": id, "json": 1},
        )
        if req.status_code == 200:
            result.append(req.json()[0]["file_url"])

    return result
