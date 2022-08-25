import config
from core.http_client import HttpClient
from core.mid_pool import MidPool
from core.models import *
from utils.log import logger
from typing import Optional, Set
import math
import asyncio
from core.storage import storage


class UpInfoSpider:

    def __init__(self):
        self._client = HttpClient()
        self._mid_pool = MidPool()
        self._save_path = config.SPIDER_CONFIG.get("save_path")
        self._parallel_co_tasks = config.SPIDER_CONFIG.get("parallel_co_tasks")

    async def get_base_user_info(self, mid: int) -> Optional[BaseUserInfo]:
        api = "http://api.bilibili.com/x/space/acc/info"
        if data := await self._client.get_json_data(api, params={"mid": mid}):
            return BaseUserInfo(
                mid=mid,
                name=data["name"],
                sex=data["sex"],
                sign=data["sign"],
                avatar_url=data["face"],
                level=data["level"],
                vip_type=data["vip"]["type"],
                offical_type=data["official"]["role"],
                offical_title=data["official"]["title"],
                is_banned=bool(data["silence"]),
                school=data["school"]["name"] if data["school"] else "未知",
                birthday=data["birthday"],
                hard_vip=bool(data["is_senior_member"])
            )

    async def get_relation_info(self, mid: int) -> Optional[RelationInfo]:
        api = "http://api.bilibili.com/x/relation/stat"
        if data := await self._client.get_json_data(api, params={"vmid": mid}):
            return RelationInfo(
                follower=data["follower"],
                following=data["following"]
            )

    async def get_charge_info(self, mid: int) -> Optional[ChargeInfo]:
        api = "https://api.bilibili.com/x/ugcpay-rank/elec/month/up"
        data = await self._client.get_json_data(api, params={"up_mid": mid})
        if data is None:
            return None
        if not data:  # user has not enabled the charging feature
            return ChargeInfo(
                enable=False,
                month=0,
                total=0
            )
        else:
            return ChargeInfo(
                enable=True,
                month=data["count"],
                total=data["total_count"],
            )

    async def __get_video_nums(self, mid: int):
        api = "http://api.bilibili.com/x/space/arc/search"
        data = await self._client.get_json_data(api, params={"mid": mid, "pn": 1, "ps": 1})
        return data["page"]["count"] if data else None

    async def __get_one_page_videos(self, mid: int, page: int, page_size: int):
        api = "http://api.bilibili.com/x/space/arc/search"
        return await self._client.get_json_data(api, params={"mid": mid, "pn": page, "ps": page_size})

    async def get_submit_video_details(self, mid: int) -> Optional[SubmitVideoDetails]:
        total_videos = await self.__get_video_nums(mid)
        if total_videos is None:
            return None

        pages = math.ceil(total_videos / 50)
        tlist = []
        videos = []
        total_plays = 0
        total_comments = 0
        total_danmaku = 0
        for pn in range(1, pages+1):
            data = await self.__get_one_page_videos(mid, pn, 50)
            if data is None:
                return None

            if not tlist:
                for part in data["list"]["tlist"].values():
                    tlist.append(SubmitVideoDetails.VideoPartitionInfo(
                        tid=part["tid"], count=part["count"]))

            for video in data["list"]["vlist"]:
                total_plays += video["play"] if type(
                    video["play"]) == int else 0
                total_comments += video["comment"]
                total_danmaku += video["video_review"]
                videos.append(SubmitVideoDetails.VideoInfo(
                    avid=video["aid"],
                    bvid=video["bvid"],
                    title=video["title"],
                    # desc=video["description"],
                    comments=video["comment"],
                    plays=video["play"],
                    danmaku=video["video_review"],
                    tid=video["typeid"],
                    created=video["created"],
                    # "127:31" min:sec
                    duration=sum(map(int, video["length"].split(":"))),
                    is_union=bool(video["is_union_video"])
                ))

        return SubmitVideoDetails(
            total_videos=total_videos,
            total_plays=total_plays,
            total_comments=total_comments,
            total_danmaku=total_danmaku,
            partition=tlist,
            videos=videos
        )

    async def __get_one_page_followings(self, mid: int, page: int, page_size: int) -> Set[int]:
        api = "https://api.bilibili.com/x/relation/followings"
        followings = set()
        data = await self._client.get_json_data(api, params={"vmid": mid, "pn": page, "ps": page_size})
        if not data:
            return followings
        for item in data["list"]:
            followings.add(item["mid"])
        return followings

    async def get_followings(self, mid: int) -> Set[int]:
        max_page = 5  # we can get only 5 pages data without login
        page_size = 50  # default
        total_followings = set()
        for page in range(1, max_page+1):
            followings = await self.__get_one_page_followings(mid, page, page_size)
            total_followings.update(followings)
            # total followings < 50, only 1 page
            if len(followings) < page_size:
                break
        return total_followings

    async def get_up_info(self, mid: int) -> Optional[UpInfo]:
        relation = await self.get_relation_info(mid)
        if not relation:
            await self._mid_pool.add_failed_mid(mid)
            return None

        if relation.follower < config.SPIDER_FILTER["min_follower"]:
            logger.info(f"Drop {mid=}, {relation=}")
            await self._mid_pool.add_processed_mid(mid)  # dropping data also considered successful
            return None

        base_info = await self.get_base_user_info(mid)
        charge_info = await self.get_charge_info(mid)
        video_detials = await self.get_submit_video_details(mid)

        if not all([base_info, charge_info, video_detials]):
            await self._mid_pool.add_failed_mid(mid)
            return None

        logger.info(f"Accept {mid=}, name={base_info.name}, {relation=}")
        await self._mid_pool.add_processed_mid(mid)
        return UpInfo(
            base=base_info,
            relation=relation,
            charge=charge_info,
            video=video_detials
        )

    async def process_up_info(self, mid: int):
        try:
            # find up's followings
            followings = await self.get_followings(mid)
            await self._mid_pool.add_mid_set(followings)
            # fetch up details and save to disk
            info = await self.get_up_info(mid)
            if not info: # dropped
                return
            await storage.write(info.to_json(ensure_ascii=False), self._save_path)
        except Exception as e:
            await self._mid_pool.add_failed_mid(mid)
            logger.exception(e)

    async def __single_spider_task(self, tid: int):
        while True:
            logger.debug(f"[{tid}] try to fetch a mid")
            mid = await self._mid_pool.get_mid()
            logger.debug(f"[{tid}] start process up info, {mid=}")
            await self.process_up_info(mid)
            logger.debug(f"[{tid}] process finished, {mid=}")

    async def __parallel_spider_task(self):
        tasks = [self.__single_spider_task(i) for i in range(self._parallel_co_tasks)]
        await asyncio.gather(*tasks)

    async def run_with_mids(self, mids: Set[int]):
        self._mid_pool.init()
        await self._mid_pool.add_mid_set(mids)  # seed mids
        await self._client.init()
        
        task = None
        try:
            task = asyncio.create_task(self.__parallel_spider_task())
            while True:
                await asyncio.sleep(1)
        except KeyboardInterrupt:
            task.cancel()
        finally:
            await self._client.close()
            self._mid_pool.stop()
