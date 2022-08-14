from spider.anime import AnimeInfoSpider
from spider.guichu import GuichuInfoSpider
from spider.up_info import UpInfoSpider
from core.http_client import client
import asyncio
from concurrent.futures import ThreadPoolExecutor, as_completed


async def main():
    loop = asyncio.get_running_loop()
    await client.init(loop)
    client.wait_proxy_pool_available()

    # start spider
    # await AnimeInfoSpider().run()
    # await GuichuInfoSpider().run()
    tasks = []
    for i in range(100000, 500000, 1000):
        tasks.append(UpInfoSpider().run(i, i+1000))
    print(f"task nums={len(tasks)}")
    await asyncio.gather(*tasks)

    # close resource
    await client.close()
    # storage.wait_finish()

if __name__ == "__main__":
    # with ThreadPoolExecutor(max_workers=16) as executor:
    #     tasks = []
    #     for i in range(1, 500000, 5000):
    #         tasks.append(executor.submit(asyncio.run, main(i, i+5000)))
    #     as_completed(tasks)
    asyncio.run(main())
