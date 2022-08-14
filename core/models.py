from dataclasses import dataclass
from dataclasses_json import dataclass_json
from typing import List


@dataclass
class BaseUserInfo:
    # http://api.bilibili.com/x/space/acc/info?mid=10086
    mid: int
    name: str
    sex: str  # 男/女/保密
    avatar_url: str  # 头像链接
    sign: str # 个人签名
    level: int  # 等级 0-6
    vip_type: int  # 0普通用户，1月度大会员，2年度大会员
    offical_type: int  # 认证类型, 0:未认证, 1 2 7 9:个人认证, 3 4 5 6:机构认证
    offical_title: str  # 认证信息
    # tags: List[str]  # 用户的 tag
    is_banned: bool  # 账号是否封禁
    school: str  # 学校
    birthday: str  # 生日 MM-DD
    hard_vip: bool  # 是否硬核会员


@dataclass
class RelationInfo:
    # http://api.bilibili.com/x/relation/stat?vmid=10086
    following: int  # 关注了多少用户
    follower: int  # 粉丝数


@dataclass
class ChargeInfo:
    # https://api.bilibili.com/x/ugcpay-rank/elec/month/up?up_mid=10086
    enable: bool  # 是否未开通充电功能
    total: int  # 充电总人数
    month: int  # 本月充电人数


@dataclass
class SubmitVideoDetails:
    # http://api.bilibili.com/x/space/arc/search?mid=14110780 (&pn=1&ps=1000)

    @dataclass
    class VideoPartitionInfo:
        tid: int  # 分区id
        count: int  # 该分区下投稿的视频数量

    @dataclass
    class VideoInfo:
        avid: int  # 稿件 avid
        bvid: str  # 稿件 bvid
        comments: int  # 视频评论数
        plays: int  # 视频播放数
        danmaku: int  # 视频弹幕数
        tid: int  # 视频所属分区id
        created: int  # 视频创建时间戳
        title: str  # 视频标题
        # desc: str  # 视频简介
        duration: int  # 视频时长, 秒
        is_union: bool  # 是否合作视频

    total_videos: int  # 投稿视频总数
    total_plays: int  # 视频总播放量
    total_comments: int  # 视频总评论数
    total_danmaku: int  # 视频总弹幕数
    partition: List[VideoPartitionInfo]  # 投稿视频分区统计
    videos: List[VideoInfo]  # 投稿视频信息

@dataclass_json
@dataclass
class UpInfo:
    base: BaseUserInfo
    relation: RelationInfo
    charge: ChargeInfo
    video: SubmitVideoDetails
