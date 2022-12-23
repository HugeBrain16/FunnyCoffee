import attrs
import asyncio
import datetime
import os
import shutil
import pickle
from typing import Any, List


@attrs.define
class Cache:
    name: str
    data: Any
    expired_after: int = attrs.field(default=10)
    expiration: datetime.datetime = attrs.field(init=False)

    @expiration.default
    def _expiration(self):
        return datetime.datetime.utcnow() + datetime.timedelta(
            minutes=self.expired_after
        )


def check_cache(cache: Cache):
    return all(
        (
            hasattr(cache, attr)
            for attr in ("name", "data", "expired_after", "expiration")
        )
    )


def ensure_cachedir(cachedir: str):
    if not os.path.isdir(cachedir):
        os.makedirs(cachedir)


def get_cache_names(cachedir: str) -> List[str]:
    ensure_cachedir(cachedir)
    result = []

    for cdir in os.listdir(cachedir):
        if os.path.isfile(os.path.join(cachedir, cdir, "data")):
            result.append(cdir)

    return result


def has_cache(cachedir: str, name: str) -> bool:
    ensure_cachedir(cachedir)

    return name in get_cache_names(cachedir)


def store(cachedir: str, cache: Cache):
    ensure_cachedir(cachedir)

    if cache.name in get_cache_names(cachedir):
        raise NameError(f"a cache with the name `{cache.name}` already stored.")

    os.makedirs(os.path.join(cachedir, cache.name))

    with open(os.path.join(cachedir, cache.name, "data"), "wb") as file:
        pickle.dump(cache, file, protocol=pickle.HIGHEST_PROTOCOL)


def get(cachedir: str, name: str) -> Cache:
    ensure_cachedir(cachedir)

    for cdir in get_cache_names(cachedir):
        if cdir == name:
            with open(os.path.join(cachedir, cdir, "data"), "rb") as file:
                return pickle.load(file)


def remove(cachedir, name: str):
    ensure_cachedir(cachedir)

    if has_cache(cachedir, name):
        shutil.rmtree(os.path.join(cachedir, name))
    else:
        raise ValueError(f"cache with the name `{name}` not found.")


async def update_cachedir(cachedir: str):
    while True:
        for cdir in get_cache_names(cachedir):
            cache = get(cachedir, cdir)

            if cache:
                if check_cache(cache):
                    if cache.expired_after <= 0:
                        continue

                    if datetime.datetime.utcnow() >= cache.expiration:
                        remove(cachedir, cache.name)
                else:
                    if hasattr(cache, "name"):
                        remove(cachedir, cache.name)

        await asyncio.sleep(0.1)


class MemCacheManager:
    """memory cache manager"""

    def __init__(self):
        self.caches: List[Cache] = []

    def store(self, cache: Cache):
        if cache.name in self.get_cache_names():
            raise NameError(f"a cache with the name `{cache.name}` already stored.")

        self.caches.append(cache)

    def has_cache(self, name: str) -> bool:
        return name in self.get_cache_names()

    def get_cache_names(self) -> List[str]:
        return [cache.name for cache in self.caches]

    def get(self, name: str) -> Cache:
        for cache in self.caches:
            if cache.name == name:
                return cache

    def remove(self, name: str):
        cache = self.get(name)

        if cache:
            self.caches.remove(cache)
        else:
            raise ValueError(f"cache with the name `{name}` not found.")

    async def update(self):
        """check for expired caches"""

        while True:
            for _, cache in enumerate(self.caches):
                if cache.expired_after <= 0:
                    continue

                if datetime.datetime.utcnow() >= cache.expiration:
                    self.caches.remove(cache)

            await asyncio.sleep(0.1)
