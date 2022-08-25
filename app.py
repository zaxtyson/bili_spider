from spider.up_info import UpInfoSpider
from spider.guichu import GuichuInfoSpider
import asyncio


if __name__ == "__main__":
    up_spider = UpInfoSpider()
    seed_mids = {241371636, 26080061, 14889417, 364686664, 399056194}
    guichu_spider = GuichuInfoSpider()
    try:
        asyncio.run(up_spider.run_with_mids(seed_mids))
        # asyncio.run(guichu_spider.run())
    except KeyboardInterrupt:
        pass
    print("finished")
