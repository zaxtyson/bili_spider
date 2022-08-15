import random
from datetime import datetime
import asyncio
from aiohttp import ClientSession, AsyncResolver, TCPConnector

import config
from utils.log import logger
from typing import List


class ProxyPool:

    def __init__(self):
        self._lock = asyncio.Lock()
        self._stop = False
        self._proxies = []
        self._session = None

    async def _init(self):
        con = TCPConnector(ttl_dns_cache=300, resolver=AsyncResolver())
        self._session = ClientSession(connector=con)

    async def _fetch_new_proxies(self) -> List[dict]:
        async with self._session.get(config.PROXY_POOL.get("api")) as rsp:
            if rsp.status != 200:
                return []
            rsp_json = await rsp.json(content_type=None)
            if not rsp_json["data"]:
                logger.warning(
                    f"ProxyPool fetch new proxies failed: {rsp_json['msg']}")
                return []
            proxies = []
            for item in rsp_json["data"]:
                host = f"{item['ip']}:{item['port']}"
                proxies.append({
                    "host": host,
                    "http": f"http://{host}",
                    "https": f"http://{host}",
                    "expire_time": datetime.strptime(item["expire_time"], "%Y-%m-%d %H:%M:%S")
                })
            return proxies

    async def _update_proxies(self):
        async with self._lock:
            if len(self._proxies) >= config.PROXY_POOL.get("pool_size"):
                return

        for _ in range(3):
            proxies = await self._fetch_new_proxies()
            if len(proxies) == 0:
                continue

            async with self._lock:
                self._proxies.extend(proxies)
                logger.info(
                    f"ProxyPool add {len(proxies)} proxy, total: {len(self._proxies)}")
            break

    async def _check_proxies(self):
        available_proxies = list(
            filter(lambda proxy: proxy["expire_time"] > datetime.now(), self._proxies))
        async with self._lock:
            drop_count = len(self._proxies) - len(available_proxies)
            if drop_count > 0:
                self._proxies = available_proxies
                logger.info(
                    f"ProxyPool remove {drop_count} unavailable proxies")

    async def remove_proxy(self, host: str):
        available_proxies = list(
            filter(lambda proxy: proxy["host"] != host, self._proxies))
        async with self._lock:
            self._proxies = available_proxies
        logger.info(f"ProxyPool remove {host}")

    async def get_random_proxy(self) -> str:
        while True:
            async with self._lock:
                if self._proxies:
                    proxy = random.choice(self._proxies)
                    return proxy["http"]
            await asyncio.sleep(1)  # wait available proxy

    def stop(self):
        self._stop = True

    async def run(self) -> None:
        await self._init()
        while not self._stop:
            await self._update_proxies()
            await self._check_proxies()
            await asyncio.sleep(3)


async def consumer(pool: ProxyPool):
    while True:
        print("Waiting for proxy")
        proxy = await pool.get_random_proxy()
        print("Got random proxy: ", proxy)
        await asyncio.sleep(0.5)


async def main():
    pool = ProxyPool()
    await asyncio.gather(
        pool.run(),
        consumer(pool)
    )

if __name__ == '__main__':
    asyncio.run(main())
