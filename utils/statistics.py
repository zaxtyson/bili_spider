from utils.log import logger
import time
from threading import Thread
from multiprocessing import Queue

__all__ = ["statistics"]


class Statistics:

    def __init__(self):
        self._failed_mid_queue = Queue(1000)
        self._accept_mid_queue = Queue(1000)
        self._failed_mid_file = "data/failed_mid.dat"
        self._accept_mid_file = "data/accept_mid.dat"
        self._dump_thread = None
        self._stop = False  # use atomic<bool> to avoid datarace

    def record_failed_mid(self, mid: int):
        logger.info(f"Record failed {mid=}")
        self._failed_mid_queue.put(mid)

    def record_accept_mid(self, mid: int):
        logger.info(f"Record accept {mid=}")
        self._accept_mid_queue.put(mid)

    def _dump(self):
        logger.debug(f"Dump task running...")
        if self._failed_mid_queue.qsize() != 0:
            failed_mids = []
            while not self._failed_mid_queue.empty():
                failed_mids.append(self._failed_mid_queue.get())
            with open(self._failed_mid_file, 'a+') as f:
                f.write("\n".join(map(str, failed_mids)) + "\n")
                logger.info(
                    f"Dump failed {len(failed_mids)} mid(s) to file: {self._failed_mid_file}")

        if not self._accept_mid_queue.empty():
            accept_mids = []
            while not self._accept_mid_queue.empty():
                accept_mids.append(self._accept_mid_queue.get())
            with open(self._accept_mid_file, 'a+') as f:
                f.write("\n".join(map(str, accept_mids)) + "\n")
                logger.info(
                    f"Dump accept {len(accept_mids)} mid(s) to file: {self._accept_mid_file}")

    def _dump_with_interval(self, interval: float):
        logger.info("Statistics dump thread running")
        while not self._stop:
            time.sleep(interval)
            self._dump()

    def run(self):
        self._dump_thread = Thread(
            name="StatisticsDumpThread", target=self._dump_with_interval, args=(3,))
        self._dump_thread.setDaemon(True)
        self._dump_thread.start()

    def stop(self):
        self._stop = True
        self._dump()
        # self._dump_thread.join()
        logger.info("Statistics stopped")


# global statistics
statistics = Statistics()


def producer():
    while True:
        statistics.record_failed_mid(11111)
        statistics.record_accept_mid(22222)
        # time.sleep(0.001)


if __name__ == "__main__":
    statistics.run()
    Thread(target=producer, daemon=True).start()
    time.sleep(3)
    statistics.stop()
