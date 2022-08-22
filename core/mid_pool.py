from typing import Set
import asyncio
from utils.log import logger
import random
import signal
import json

__all__ = ["MidPool"]


class MidPool:

    def __init__(self) -> None:
        self._mid_to_process = set()
        self._mid_processed = set()
        self._mid_failed = set()
        self._bg_retry_task = None
        self._lock = None
        self._cond = None
        self._file = "data/mid_pool.json"

    def init(self, loop=None):
        if loop:
            self._lock = asyncio.Lock(loop)
        else:
            self._lock = asyncio.Lock()  # use current running loop
        self._cond = asyncio.Condition(self._lock)

        # load history data
        self.__load()

        # start background task
        self._bg_retry_task = asyncio.create_task(
            self.__failed_mid_retry_task())
        self._bg_retry_task.set_name("FailedMidRetryTask")

    def __load(self):
        logger.info(f"Load MidPool history from file: {self._file}")
        with open(self._file, "r") as f:
            data = json.load(f)
            self._mid_to_process = set(data["mid_to_process"])
            self._mid_processed = set(data["mid_processed"])
            self._mid_failed = set(data["mid_failed"])

    def __dump(self):
        logger.info(f"Dump MidPool history to file: {self._file}")
        with open(self._file, "w+") as f:
            data = {
                "mid_to_process": list(self._mid_to_process),
                "mid_processed": list(self._mid_processed),
                "mid_failed": list(self._mid_failed)
            }
            json.dump(data, f)

    def stop(self):
        logger.info("Stop MidPool...")
        if not self._bg_retry_task.cancelled():
            self._bg_retry_task.cancel()
        self.__dump()

    async def add_processed_mid(self, mid: int):
        async with self._cond:
            logger.debug(f"Add a proceed {mid=}")
            self._mid_processed.add(mid)

    async def add_mid_set(self, mids: Set[int]):
        async with self._cond:
            to_process = mids - self._mid_processed - self._mid_failed
            if len(to_process) > 0:
                self._mid_to_process.update(to_process)
                logger.info(
                    f"Add {len(to_process)} mid(s), total {len(self._mid_to_process)} mid(s) to process")
                self._cond.notify_all()

    async def add_failed_mid(self, mid: int):
        async with self._lock:
            logger.warning(f"Add failed {mid=}")
            self._mid_failed.add(mid)

    async def __failed_mid_retry_task(self):
        logger.info("Scan failed mid set task running...")
        while True:
            await asyncio.sleep(10)
            logger.info("Scan falied mid set...")
            async with self._cond:
                if len(self._mid_failed) > 0:
                    logger.info(
                        f"Add {len(self._mid_failed)} failed mid(s) to retry list")
                    self._mid_to_process.update(self._mid_failed)
                    self._mid_failed.clear()
                    self._cond.notify_all()

    async def get_mid(self) -> int:
        async with self._cond:
            while len(self._mid_to_process) == 0:
                logger.info("Wait a mid...")
                await self._cond.wait()
            return self._mid_to_process.pop()

# ============ for test ===============


if __name__ == "__main__":
    mid_pool = MidPool()

    def gen_random_mid():
        return random.randint(9000, 10000)

    def gen_random_mid_set():
        mids = set()
        for _ in range(100):
            mids.add(gen_random_mid())
        return mids

    async def single_task(tid: int):
        while True:
            logger.info(f"[{tid}] Try to get a mid...")
            mid = await mid_pool.get_mid()
            logger.info(f"[{tid}] Got a mid {mid}")
            await asyncio.sleep(0.1)
            # simulate do filter
            if mid < 9100:
                logger.info(f"[{tid}] Drop mid {mid}")
            elif 9600 < mid < 9650:
                logger.error(f"Process {mid=} failed!")
                await mid_pool.add_failed_mid(mid)  # failed!
            else:
                # get info of mid...
                # get following of mid
                await mid_pool.add_mid_set(gen_random_mid_set())

    async def parallel_task():
        co_tasks = [single_task(i) for i in range(100)]
        await asyncio.gather(
            *co_tasks
        )

    task = None
    stop_task = False

    def sig_handler(signum, frame):
        global task
        global stop_task
        logger.info(f"Recv signal: {signum}")
        mid_pool.stop()
        if not task.cancelled():
            task.cancel()
        stop_task = True
        print("Task canceled")

    async def main():
        global task
        mid_pool.init()
        seed_mid = 9800
        await mid_pool.add_mid(seed_mid)
        task = asyncio.create_task(parallel_task())
        while not stop_task:
            await asyncio.sleep(1)

    signal.signal(signal.SIGINT, sig_handler)
    asyncio.run(main())
    print("finished")
