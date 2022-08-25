from core.http_client import HttpClient
import aiofiles
from utils.log import logger


class GuichuInfoSpider:

    def __init__(self):
        self._client = HttpClient()
        self._file = "data/guichu_title.txt"

    async def __get_one_page_data(self, offset: str = ""):
        api = "http://bigdata.zaxtyson.cn:8086/api/web/channel/featured/list"
        params = {"channel_id": 68, "filter_type": 0,
                  "offset": offset, "page_size": 30}
        data = await self._client.get_json_data(api, params=params)
        next_page_offset = data["offset"]
        title_list = [item["name"].strip() for item in data["list"]]
        logger.info(f"Get page {offset=}, title={len(title_list)}, {next_page_offset=}")
        return title_list, next_page_offset
    
    async def __append_to_file(self, texts):
        async with aiofiles.open(self._file, "a+", encoding="utf-8") as f:
            await f.write("\n")
            await f.write("\n".join(texts))
            await f.flush()
    
    async def __get_title(self):
        title_list, next_page_offset = await self.__get_one_page_data()
        await self.__append_to_file(title_list)
        for _ in range(300):  # 30*300
            title_list, next_page_offset = await self.__get_one_page_data(next_page_offset)
            await self.__append_to_file(title_list)

    async def run(self):
        await self._client.init()
        try:
            await self.__get_title()
        except KeyboardInterrupt:
            pass
        finally:
            await self._client.close()
