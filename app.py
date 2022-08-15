from spider.up_info import UpInfoSpider
import asyncio
import signal
from utils.statistics import statistics
from concurrent.futures import ProcessPoolExecutor, as_completed, ThreadPoolExecutor, wait
import os
from utils.log import logger


def spider_task(mid_range):
    spider = UpInfoSpider()
    start, end = mid_range
    asyncio.run(spider.run_with_range(start, end))


def main():
    # total_mid = 703223210
    cpu_cores = os.cpu_count()
    logger.info(f"ProcessPoolExecutor workers={cpu_cores}")
    with ProcessPoolExecutor(cpu_cores) as executor:
        executor.map(spider_task, [(1000, 2000), (2000, 3000)])


if __name__ == "__main__":
    statistics.run()
    main()
    statistics.stop()
