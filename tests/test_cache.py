import asyncio
import unittest

from lib import cache


class TestCache(unittest.TestCase):
    def test_cache_store(self):
        self.cache = cache.MemCacheManager()
        name = "__test__store"
        data = cache.Cache(name, None)

        self.cache.store(data)
        self.assertTrue(self.cache.has_cache(name))

    def test_cache_remove(self):
        self.cache = cache.MemCacheManager()
        name = "__test__remove"
        data = cache.Cache(name, None)

        self.cache.store(data)
        self.assertTrue(self.cache.has_cache(name))
        self.cache.remove(name)
        self.assertFalse(self.cache.has_cache(name))

    def test_cache_exp(self):
        self.cache = cache.MemCacheManager()
        name = "__test__exp"
        data = cache.Cache(name, None, 0.1)
        self.cache.store(data)
        self.assertTrue(self.cache.has_cache(name))

        async def main():
            loop = asyncio.get_running_loop()

            while loop.is_running():
                if not self.cache.has_cache(name):
                    break

                await asyncio.sleep(1)

        loop = asyncio.new_event_loop()
        loop.create_task(self.cache.update())
        loop.run_until_complete(main())

        self.assertFalse(self.cache.has_cache(name))

    def test_cache_noexp(self):
        self.cache = cache.MemCacheManager()
        name = "__test__noexp"
        data = cache.Cache(name, None, 0)
        self.cache.store(data)
        self.assertTrue(self.cache.has_cache(name))

        async def main():
            timeout = 5
            timeout_c = 0

            while self.cache.has_cache(name) and timeout_c < timeout:
                timeout_c += 1
                await asyncio.sleep(1)

        loop = asyncio.new_event_loop()
        loop.create_task(self.cache.update())
        loop.run_until_complete(main())

        self.assertTrue(self.cache.has_cache(name))
