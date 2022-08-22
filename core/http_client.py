import asyncio
import os
from typing import Optional

from aiohttp import ClientSession, ClientTimeout, AsyncResolver, TCPConnector
from aiohttp.client_exceptions import ClientConnectionError, ClientHttpProxyError
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

        if not self._enable_proxy_pool:
            logger.info("ProxyPool is not enable")
        else:
            logger.info("ProxyPool is enabled")
            self._proxy_pool = ProxyPool()
            self._proxy_pool.start_update_proxy_task()

    async def close(self):
        if self._session:
            await self._session.close()
            logger.info("HttpClient session is closed")
        if self._enable_proxy_pool:
            self._proxy_pool.stop()
            logger.info("HttpClient proxy pool is stopped")

    def __set_request_args(self, kwargs: dict):
        # set timeout for per connection
        kwargs.setdefault("timeout", self._timeout)
        # ignore ssl error
        kwargs.setdefault("ssl", False)
        # set user-agent if user not specify this filed
        if headers := kwargs.get("headers"):
            headers.setdefault("User-Agent", get_random_ua())
        else:
            kwargs.setdefault("headers", {"User-Agent": get_random_ua()})

    async def get_json_data(self, url: str, **kwargs) -> Optional[dict]:
        retry_times = config.HTTP_CLIENT.get("retry_times")
        for _ in range(retry_times):
            proxy = None
            if self._enable_proxy_pool:
                proxy = await self._proxy_pool.get_random_proxy()
                kwargs.setdefault("proxy", proxy.get_proxy())
            self.__set_request_args(kwargs)
            try:
                async with self._session.get(url, **kwargs) as r:
                    if not r or r.status != 200:  # 412
                        if proxy:
                            proxy.add_ban_times()
                        continue
                    rsp_json = await r.json(content_type=None)
                    code = rsp_json["code"]
                    if code == 0:
                        return rsp_json["data"]
                    elif code == 88214:  # up主未开通充电
                        return {}
                    elif code == -412:  # request ban
                        proxy.add_ban_times()
                        continue
                    else:
                        logger.debug(f"Error, {url=}, {kwargs=} {rsp_json=}")
                        return None
            except (ClientConnectionError, ClientHttpProxyError) as e:
                if proxy:
                    proxy.mark_as_invalid(e)
            except asyncio.exceptions.TimeoutError as e:  # e is ""
                if proxy:
                    proxy.mark_as_invalid("Timeout")
            except Exception as e:
                logger.exception(e)
                return None  # break retry

        # failed, usually 412
        logger.debug(f"Failed to get {url} {kwargs=}, {retry_times=}")
        return None
