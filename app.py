from spider.up_info import UpInfoSpider
import asyncio


if __name__ == "__main__":
    spider = UpInfoSpider()
    seed_mids = {241371636, 26080061, 14889417, 364686664, 399056194}
    try:
        asyncio.run(spider.run_with_mids(seed_mids))
    except KeyboardInterrupt:
        pass
    print("finished")
