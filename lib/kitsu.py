"""Kitsu.io API Wrapper"""

import random
import datetime
from typing import List
from enum import Enum

import requests
import hikari

BASE = "https://kitsu.io/api/edge"


class ImageSize(Enum):
    """image size enum"""

    ORIGINAL = "original"
    SMALL = "small"
    TINY = "tiny"
    MEDIUM = "medium"
    LARGE = "large"


class ContentType(Enum):
    """content type enum"""

    ANIME = "anime"
    MANGA = "manga"


class MediaDefault(Enum):
    """media default content"""

    NOT_FOUND = "https://gcdn.pbrd.co/images/zkdbeZmdYByv.gif"


class Anime:
    """Anime content instance"""

    def __init__(self, anime_id: int):
        self.request = requests.get(BASE + "/anime/" + str(anime_id))
        self.data = self.request.json()["data"]

    def __dict__(self) -> dict:
        return self.data

    @property
    def content_id(self) -> int:
        """get content id"""
        return int(self.data["id"])

    @property
    def type(self) -> ContentType:
        """get content type"""
        return ContentType[self.data["type"]]

    @property
    def episodes(self) -> int:
        """get episode count"""
        return self.data["attributes"].get("episodeCount", 0)

    @property
    def url(self) -> str:
        """get website url"""
        return "https://kitsu.io/anime/" + str(self.content_id)

    @property
    def api_url(self) -> str:
        """get api path url"""
        return BASE + "/anime/" + str(self.content_id)

    @property
    def title(self) -> str:
        """get title"""
        return self.data["attributes"]["titles"].get("en", "-")

    @property
    def title_jp(self) -> str:
        """get japanese romaji title"""
        return self.data["attributes"]["titles"].get("en_jp", "-")

    @property
    def title_ja(self) -> str:
        """get japanese title"""
        return self.data["attributes"]["titles"].get("ja_jp", "-")

    @property
    def description(self) -> str:
        """get content description"""
        return self.data["attributes"]["description"]

    @property
    def nsfw(self) -> bool:
        """check if content is nsfw"""
        return self.data["attributes"]["nsfw"]

    @property
    def synopsis(self) -> str:
        """get synopsis"""
        return self.data["attributes"]["synopsis"]

    def get_poster_image(self, size: ImageSize = ImageSize.ORIGINAL) -> str:
        """get poster image url"""
        poster = self.data["attributes"]["posterImage"]
        if poster is not None:
            return poster.get(size.value)

        return MediaDefault.NOT_FOUND.value

    def get_cover_image(self, size: ImageSize = ImageSize.ORIGINAL) -> str:
        """get cover image url"""
        cover = self.data["attributes"]["coverImage"]
        if cover is not None:
            return cover.get(size.value)

        return MediaDefault.NOT_FOUND.value

    def genre_list(self) -> list:
        """get genre list"""
        req = requests.get(self.api_url + "/genres")

        return [
            data["attributes"]["name"].lower().capitalize()
            for data in req.json()["data"]
        ]

    def discord_embed(self, cover: bool = False):
        """create discord embed"""
        readmore = f"...\n\n[read more]({self.url})"
        embed = hikari.Embed(
            title=self.title_jp[: 256 - len("...")]
            + (
                "..."
                if len(self.title_jp) > (256 - len("..."))
                else self.title_jp[256 - len("...") :]
            ),
            url=self.url,
            color=0x87CEEB if not self.nsfw else 0xFF0000,
        )
        embed.description = self.description[: 4096 - len(readmore)] + (
            readmore
            if len(self.description) > (4096 - len(readmore))
            else self.description[4096 - len(readmore) :]
        )
        embed.set_thumbnail(self.get_poster_image(ImageSize.LARGE))
        embed.set_footer(
            text="Kitsu.io"
            + (", Content with embed color Red is NSFW" if self.nsfw else "")
        )
        if cover:
            embed.set_image(self.get_cover_image(ImageSize.LARGE))

        # fields
        embed.add_field(name="Total Episodes", value=self.episodes or "-")
        embed.add_field(
            name="Alternative Titles",
            value=f"Japanese: **{self.title_ja}**\nEnglish: **{self.title}**",
        )
        embed.add_field(name="Genres", value=", ".join(self.genre_list()) + ".")
        if self.data["attributes"]["averageRating"]:
            embed.add_field(
                name="Rating", value=self.data["attributes"]["averageRating"]
            )
        embed.add_field(
            name="Status", value=self.data["attributes"]["status"].capitalize()
        )
        embed.add_field(
            name="Year",
            value="-" if not self.data["attributes"]["startDate"] else datetime.datetime.strptime(
                self.data["attributes"]["startDate"], "%Y-%m-%d"
            ).year,
        )

        return embed


def search_anime(query: str, limit: int = 5) -> List[Anime]:
    """search anime by query"""
    req = requests.get(BASE + "/anime", params={"filter[text]": query})
    return [Anime(int(data["id"])) for data in req.json()["data"][:limit]]


def random_anime(limit: int = 5) -> List[Anime]:
    """get random anime"""
    req = requests.get(BASE + "/anime")
    result = []

    while len(result) < limit:
        random_id = random.randint(1, req.json()["meta"]["count"])
        areq = requests.get(BASE + "/anime/" + str(random_id))
        if areq.status_code == 200:
            result.append(Anime(random_id))

    return result
