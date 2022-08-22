import random
from datetime import datetime, timedelta
import asyncio
from aiohttp import ClientSession, AsyncResolver, TCPConnector

import config
from utils.log import logger
from typing import List


class Proxy:

    def __init__(self, ip: str, port: int, expire_time: datetime):
        self._ip = ip
        self._port = port
        self._expire_time = expire_time
        self._ban_times = 0
        self._reuse_time = datetime.now()
        self._valid_flag = True
        self._ban_strategy = {
            1: 30, # seconds
            2: 60,
            3: 120
        }

    def get_proxy(self) -> str:
        return f"http://{self._ip}:{self._port}"

    def is_available(self) -> bool:
        return self.is_valid() and datetime.now() > self._reuse_time

    def is_valid(self) -> bool:
        return self._valid_flag and datetime.now() < self._expire_time

    def mark_as_invalid(self, reason: str = ""):
        self._valid_flag = False
        logger.debug(f"Proxy {self.get_proxy()} is marked as invalid: {reason}")

    def rate_limit(self):
        self._reuse_time = datetime.now() + timedelta(milliseconds=10)

    def add_ban_times(self):
        self._ban_times += 1
        wait_time = self._ban_strategy.get(self._ban_times, 60)
        self._reuse_time = datetime.now() + timedelta(seconds=wait_time)
        logger.debug(
            f"Proxy {self.get_proxy()} is ban, it will reuse at {self._reuse_time}")


class ProxyPool:

    def __init__(self):
        self._lock = None
        self._cond = None
        self._proxies: List[Proxy] = []
        self._session = None
        self._bg_update_proxy_task = None
        self._sources_type = config.PROXY_POOL["type"]

    async def __load_from_file(self):
        proxies = []
        path = config.PROXY_POOL["file"]["path"]
        with open(path, "r") as f:
            for host in f:
                ip, port = host.split(":")
                proxy = Proxy(ip, int(port), "2099-01-01 00:00:00")
                proxies.append(proxy)
            logger.info(f"Load {len(proxies)} from file {path}")

        async with self._cond:
            self._proxies = proxies
            self._cond.notify_all()

    async def __init(self):
        self._lock = asyncio.Lock()  # lock in current loop
        self._cond = asyncio.Condition(self._lock)

        con = TCPConnector(ttl_dns_cache=300, resolver=AsyncResolver())
        self._session = ClientSession(connector=con)

    async def __zhima_fetch_new_proxies(self) -> List[Proxy]:
        async with self._session.get(config.PROXY_POOL["zhima"]["api"]) as rsp:
            if rsp.status != 200:
                return []
            rsp_json = await rsp.json(content_type=None)
            if not rsp_json["data"]:
                logger.warning(
                    f"ProxyPool fetch new proxies failed: {rsp_json['msg']}")
                return []
            proxies = []
            for item in rsp_json["data"]:
                expire_time = datetime.strptime(
                    item["expire_time"], "%Y-%m-%d %H:%M:%S")
                proxies.append(Proxy(item["ip"], item["port"], expire_time))
            return proxies

    async def __juliang_fetch_new_proxies(self) -> List[Proxy]:
        async with self._session.get(config.PROXY_POOL["juliang"]["api"]) as rsp:
            if rsp.status != 200:
                return []
            rsp_json = await rsp.json(content_type=None)
            if not rsp_json["data"]:
                logger.warning(
                    f"ProxyPool fetch new proxies failed: {rsp_json['msg']}")
                return []
            proxies = []
            for item in rsp_json["data"]["proxy_list"]:
                # item: "117.27.118.94:53471,205"
                host, expired_sec = item.split(",")
                ip, port = host.split(":")
                expire_time = datetime.now() + timedelta(seconds=int(expired_sec))
                proxies.append(Proxy(ip, int(port), expire_time))
            return proxies

    async def __available_proxies_nums(self) -> int:
        async with self._lock:
            count = 0
            for proxy in self._proxies:
                if proxy.is_available():
                    count += 1
            logger.info(f"Available proxies num: {count}")
            return count

    async def __update_proxies(self):
        pool_size = 1
        if self._sources_type == "zhima":
            pool_size = config.PROXY_POOL["zhima"]["pool_size"]
        elif self._sources_type == "juliang":
            pool_size = config.PROXY_POOL["juliang"]["pool_size"]

        if await self.__available_proxies_nums() >= pool_size:
            return

        for _ in range(3):
            if self._sources_type == "zhima":
                proxies = await self.__zhima_fetch_new_proxies()
            elif self._sources_type == "juliang":
                proxies = await self.__juliang_fetch_new_proxies()

            if len(proxies) == 0:
                continue

            async with self._cond:
                self._proxies.extend(proxies)
                logger.info(
                    f"ProxyPool add {len(proxies)} proxy, total: {len(self._proxies)}")
                self._cond.notify_all()
            break

    async def __check_proxies(self):
        valid_proxies = []
        drop_count = 0
        async with self._lock:
            for proxy in self._proxies:
                if proxy.is_valid():
                    valid_proxies.append(proxy)
                else:
                    drop_count += 1
            if drop_count > 0:
                self._proxies = valid_proxies
                logger.info(
                    f"ProxyPool remove {drop_count} invalid proxies")

    async def get_random_proxy(self) -> Proxy:
        async with self._cond:
            while True:
                available_proxies = [
                    p for p in self._proxies if p.is_available()]
                if len(available_proxies) > 0:
                    return random.choice(available_proxies)
                await self._cond.wait()

    async def __run(self) -> None:
        if self._sources_type == "file":
            await self.__load_from_file()
            return

        logger.info("Update proxy task running...")
        await self.__init()
        while True:
            await self.__update_proxies()
            await self.__check_proxies()
            await asyncio.sleep(1.1)

    def start_update_proxy_task(self):
        self._bg_update_proxy_task = asyncio.create_task(self.__run())

    def stop(self):
        if not self._bg_update_proxy_task.cancelled():
            self._bg_update_proxy_task.cancel()
            logger.info("Update proxy task stopped")

# =========== for test =============


async def consumer(pool: ProxyPool):
    while True:
        print("Waiting for proxy")
        proxy = await pool.get_random_proxy()
        print("Got random proxy: ", proxy)
        await asyncio.sleep(0.5)


async def main():
    pool = ProxyPool()
    pool.start_update_proxy_task()
    await consumer(pool)

if __name__ == '__main__':
    asyncio.run(main())
