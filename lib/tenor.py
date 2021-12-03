"""Tenor API Wrapper"""

from typing import Optional
import requests

BASE = "https://g.tenor.com/v1"


def search_gif(query: str, api_key: str, limit: int = 5) -> Optional[dict]:
    """search for gif"""
    req = requests.get(
        BASE + "/search", params={"key": api_key, "q": query, "limit": limit}
    )
    if req.status_code == 200:
        return req.json()

    return {}
