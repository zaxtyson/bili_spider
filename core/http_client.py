import asyncio
import os
from typing import Optional

from aiohttp import ClientSession, ClientTimeout, AsyncResolver, TCPConnector
import config
import time
from utils.log import logger
from utils.useragent import get_random_ua
from core.proxy_pool import ProxyPool

__all__ = ["client"]

if os.name == "nt":
    # https://stackoverflow.com/questions/63653556/raise-notimplementederror-notimplementederror
    logger.info(f"Change eventloop policy: WindowsSelectorEventLoopPolicy")
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())


class HttpSession:

    def __init__(self):
        self._session: Optional[ClientSession] = None
        self._proxy_pool = ProxyPool()

        # https://docs.aiohttp.org/en/stable/client_quickstart.html#timeouts
        self._timeout = ClientTimeout(
            total=config.HTTP_CLIENT.get("timeout").get("total"),
            sock_connect=config.HTTP_CLIENT.get("timeout").get("connect")
        )
        self._dns_server = config.HTTP_CLIENT.get("dns_server")
        self._enable_proxy_pool = config.PROXY_POOL.get("enable")

    async def init(self, loop):
        if self._dns_server:
            logger.info(f"Use custom DNS server: {self._dns_server}")

        # use async dns resolver
        resolver = AsyncResolver(nameservers=self._dns_server)
        con = TCPConnector(ttl_dns_cache=300, resolver=resolver)
        self._session = ClientSession(loop=loop, connector=con)

    async def close(self):
        if self._session:
            await self._session.close()
        if self._enable_proxy_pool:
            self._proxy_pool.stop()

    def wait_proxy_pool_available(self):
        if not self._enable_proxy_pool:
            logger.info("ProxyPool is not enable")
            return

        self._proxy_pool.setDaemon(True)
        self._proxy_pool.start()
        while not self._proxy_pool.has_available_proxy():
            logger.info("Waiting for proxy available...")
            time.sleep(1)

    def _set_request_args(self, kwargs: dict):
        if self._enable_proxy_pool:
            kwargs.setdefault("proxy", self._proxy_pool.get_random_proxy())
        # set timeout for per connection
        kwargs.setdefault("timeout", self._timeout)
        # ignore ssl error
        kwargs.setdefault("ssl", False)
        # set user-agent if user not specify this filed
        if headers := kwargs.get("headers"):
            headers.setdefault("User-Agent", get_random_ua())
        else:
            kwargs.setdefault("headers", {"User-Agent": get_random_ua()})

    def do(self, method: str, url: str, **kwargs):
        self._set_request_args(kwargs)
        logger.debug(f"{method} {url} {kwargs=}")
        if method == "HEAD":
            return self._session.head(url, **kwargs)
        elif method == "GET":
            return self._session.get(url, **kwargs)
        elif method == "POST":
            return self._session.post(url, **kwargs)
        else:
            logger.error(f"Method not support: {method}")
            return None

    def head(self, url: str, **kwargs):
        return self.do("HEAD", url, **kwargs)

    def get(self, url: str, **kwargs):
        return self.do("GET", url, **kwargs)

    def post(self, url: str, **kwargs):
        return self.do("POST", url, **kwargs)

    async def get_json_data(self, url: str, **kwargs) -> dict:
        for _ in range(config.HTTP_CLIENT.get("retry_times")):
            try:
                async with self.get(url, **kwargs) as r:
                    if not r or r.status != 200:
                        continue
                    rsp_json = await r.json(content_type=None)
                    if rsp_json["code"] in [0, 88214]:
                        return rsp_json["data"]
                    elif rsp_json["code"] == -412: # request ban
                        # await asyncio.sleep(1)
                        continue
                    else:
                        logger.error(f"Error, {rsp_json=}")
                        return {}
            except Exception as e:
                logger.exception(e)
                return {}
        logger.error(f"Failed to get {url} {kwargs=}")
        return {}


# global async http session
client = HttpSession()
