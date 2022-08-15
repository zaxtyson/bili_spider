import asyncio
import os
from typing import Optional

from aiohttp import ClientSession, ClientTimeout, AsyncResolver, TCPConnector
from aiohttp.client_exceptions import ClientProxyConnectionError
import config
from utils.log import logger
from utils.useragent import get_random_ua
from core.proxy_pool import ProxyPool

__all__ = ["HttpClient"]

if os.name == "nt":
    # https://stackoverflow.com/questions/63653556/raise-notimplementederror-notimplementederror
    logger.info(f"Change eventloop policy: WindowsSelectorEventLoopPolicy")
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())


class HttpClient:

    def __init__(self):
        self._session: Optional[ClientSession] = None
        self._proxy_pool = None

        # https://docs.aiohttp.org/en/stable/client_quickstart.html#timeouts
        self._timeout = ClientTimeout(
            total=config.HTTP_CLIENT.get("timeout").get("total"),
            sock_connect=config.HTTP_CLIENT.get("timeout").get("connect")
        )
        self._dns_server = config.HTTP_CLIENT.get("dns_server")
        self._enable_proxy_pool = config.PROXY_POOL.get("enable")

    async def init(self):
        if self._dns_server:
            logger.info(f"Use custom DNS server: {self._dns_server}")

        # use async dns resolver
        resolver = AsyncResolver(nameservers=self._dns_server)
        con = TCPConnector(ttl_dns_cache=300, resolver=resolver)
        self._session = ClientSession(connector=con)

        self._proxy_pool = ProxyPool()
        if not self._enable_proxy_pool:
            logger.info("ProxyPool is not enable")
        else:
            logger.info("ProxyPool is enabled")
            asyncio.create_task(self._proxy_pool.run())

    async def close(self):
        if self._session:
            await self._session.close()
            logger.info("HttpClient session is closed")
        if self._enable_proxy_pool:
            self._proxy_pool.stop()
            logger.info("HttpClient proxy pool is closed")

    async def _set_request_args(self, kwargs: dict):
        if self._enable_proxy_pool:
            kwargs.setdefault("proxy", await self._proxy_pool.get_random_proxy())
        # set timeout for per connection
        kwargs.setdefault("timeout", self._timeout)
        # ignore ssl error
        kwargs.setdefault("ssl", False)
        # set user-agent if user not specify this filed
        if headers := kwargs.get("headers"):
            headers.setdefault("User-Agent", get_random_ua())
        else:
            kwargs.setdefault("headers", {"User-Agent": get_random_ua()})

    async def do(self, method: str, url: str, **kwargs):
        await self._set_request_args(kwargs)
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

    async def head(self, url: str, **kwargs):
        return await self.do("HEAD", url, **kwargs)

    async def get(self, url: str, **kwargs):
        return await self.do("GET", url, **kwargs)

    async def post(self, url: str, **kwargs):
        return await self.do("POST", url, **kwargs)

    async def get_json_data(self, url: str, **kwargs) -> Optional[dict]:
        rsp_json = {}
        last_status = 0
        for _ in range(config.HTTP_CLIENT.get("retry_times")):
            try:
                async with (await self.get(url, **kwargs)) as r:
                    if not r or r.status != 200:
                        last_status = r.status  # 412
                        continue
                    rsp_json = await r.json(content_type=None)
                    code = rsp_json["code"]
                    if code == 0:
                        return rsp_json["data"]
                    elif code == 88214:  # up主未开通充电
                        return {}
                    elif code == -412:  # request ban
                        continue
                    else:
                        logger.debug(f"Error, {rsp_json=}")
                        return None
            except ClientProxyConnectionError as e:
                host = f"{e._conn_key.host}:{e._conn_key.port}"
                logger.info(e)
                await self._proxy_pool.remove_proxy(host)
            except asyncio.exceptions.TimeoutError as e:
                logger.info(e)
            except Exception as e:
                logger.debug(f"Error, {rsp_json=}")
                logger.exception(e)
                return None # break retry

        # failed, usually 412
        logger.debug(
            f"Failed to get {url} {kwargs=}, {rsp_json=}, {last_status=}")
        return None
