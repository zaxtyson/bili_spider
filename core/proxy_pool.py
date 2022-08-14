import random
from datetime import datetime
from threading import Thread, Lock
from time import sleep

import requests

import config
from utils.log import logger


class ProxyPool(Thread):

    def __init__(self):
        super().__init__()
        self._stop = False
        self._lock = Lock()
        self._proxies = []

    def has_available_proxy(self) -> bool:
        return len(self._proxies) > 0

    def fetch_new_proxies(self):
        resp = requests.get(config.PROXY_POOL.get("api"))
        for _ in range(3):
            if resp.status_code != 200:
                continue
            data = resp.json()["data"]
            new_proxies = []
            for item in data:
                host = f"{item['ip']}:{item['port']}"
                new_proxies.append({
                    "host": host,
                    "http": f"http://{host}",
                    "https": f"http://{host}",
                    "expire_time": datetime.strptime(item["expire_time"], "%Y-%m-%d %H:%M:%S")
                })

            if len(new_proxies) > 0:
                self._lock.acquire()
                self._proxies.extend(new_proxies)
                self._lock.release()
                logger.info(f"ProxyPool add {len(new_proxies)} proxy, total: {len(self._proxies)}")
                return

            logger.warning(f"ProxyPool fetch new proxies failed: {resp.json()['msg']}")

    def remove_proxy(self, http_proxy: str) -> None:
        logger.warning(f"Remove proxy: {http_proxy}")
        self._lock.acquire()
        self._proxies = list(filter(lambda proxy: proxy["http"] != http_proxy, self._proxies))
        self._lock.release()

    def update_proxies(self):
        valid_proxies = []
        for proxy in self._proxies:
            # proxy is unavailable
            if proxy["expire_time"] <= datetime.now():
                valid_proxies.append(proxy)
        # drop this proxy
        self._lock.acquire()
        for proxy in valid_proxies:
            self._proxies.remove(proxy)
        self._lock.release()
        if len(valid_proxies) > 0:
            logger.info(f"ProxyPool remove {len(valid_proxies)} unavailable proxies")

    def get_random_proxy(self) -> str:
        while len(self._proxies) == 0:
            sleep(1)  # wait available proxy
        self._lock.acquire()
        http_proxy = random.choice(self._proxies)["http"]
        self._lock.release()
        return http_proxy

    def stop(self):
        self._stop = True

    def run(self) -> None:
        self.fetch_new_proxies()
        while not self._stop:
            self.update_proxies()
            if len(self._proxies) < config.PROXY_POOL.get("pool_size"):
                self.fetch_new_proxies()
            sleep(3)


if __name__ == '__main__':
    pool = ProxyPool()
    pool.start()