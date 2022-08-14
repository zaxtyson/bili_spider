import config
from core.http_client import client
from core.models import *
from utils.log import logger
from typing import Optional
import math
from core.storage import storage
import time
import asyncio
from utils.misc import record_failed_mid

class UpInfoSpider:
    
    async def get_base_user_info(self, mid: int) -> BaseUserInfo:
        api = "http://api.bilibili.com/x/space/acc/info"
        data = await client.get_json_data(api, params={"mid": mid})
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
        # await asyncio.sleep(0.05) # ban ip
        api = "http://api.bilibili.com/x/relation/stat"
        data = await client.get_json_data(api, params={"vmid": mid})
        if not data:
            await record_failed_mid(mid)
            return None
        
        return RelationInfo(
            follower=data["follower"],
            following=data["following"]
        )
    
    async def get_charge_info(self, mid: int) -> ChargeInfo:
        api = "https://api.bilibili.com/x/ugcpay-rank/elec/month/up"
        data = await client.get_json_data(api, params={"up_mid": mid})
        if not data: # user has not enabled the charging feature
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
    
    async def get_video_nums(self, mid: int) -> SubmitVideoDetails:
        api = "http://api.bilibili.com/x/space/arc/search"
        data = await client.get_json_data(api, params={"mid": mid, "pn": 1, "ps": 1})
        return data["page"]["count"]
        
    async def get_one_page_videos(self, mid:int, page:int, page_size:int):
        api = "http://api.bilibili.com/x/space/arc/search"
        return await client.get_json_data(api, params={"mid": mid, "pn": page, "ps": page_size})
    
    async def get_submit_video_details(self, mid: int) -> SubmitVideoDetails:
        total_videos = await self.get_video_nums(mid)
        pages = math.ceil(total_videos / 50)
        tlist = []
        videos = []
        total_plays = 0
        total_comments = 0
        total_danmaku = 0
        for pn in range(1, pages+1):
            data = await self.get_one_page_videos(mid, pn, 50)
            if not tlist:
                for part in data["list"]["tlist"].values():
                    tlist.append(SubmitVideoDetails.VideoPartitionInfo(tid=part["tid"], count=part["count"]))

            for video in data["list"]["vlist"]:
                total_plays += video["play"] if type(video["play"]) == int else 0 
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
                    duration=sum(map(int, video["length"].split(":"))), # "127:31" min:sec
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
    
    async def get_up_info(self, mid: int) -> Optional[UpInfo]:
        relation = await self.get_relation_info(mid)
        if not relation:
            return None
        if relation.follower < config.SPIDER_FILTER["min_follower"]:
            logger.info(f"Drop {mid=}, {relation=}")
            return None
        
        base_info = await self.get_base_user_info(mid)
        charge_info = await self.get_charge_info(mid)
        video_detials = await self.get_submit_video_details(mid)
        logger.info(f"Save {mid=}, name={base_info.name}, {relation=}")
        return UpInfo(
            base=base_info,
            relation=relation,
            charge=charge_info,
            video=video_detials
        )
        
    
    async def run(self, mid_start, mid_end):
        # max = 703223210
        start = time.perf_counter()
        for mid in range(mid_start, mid_end):
            try:
                info = await self.get_up_info(mid)
                if not info:
                    continue
                await storage.write(info.to_json(ensure_ascii=False), "./data/up_info.dat")
            except Exception as e:
                logger.exception(e)
            except KeyboardInterrupt:
                break
        
        end = time.perf_counter()
        print(f"Time cost: {end-start:.4f} seconds")
        