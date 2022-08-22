# Logger
LOG_APPENDER = [
    "console",
    "file"
]


# Config for aiohttp
HTTP_CLIENT = {
    "retry_times": 5,
    "dns_server": [],
    "timeout": {
        "total": 10,
        "connect": 5
    }
}

# Spider filter strategies
SPIDER_FILTER = {
    "min_follower": 10000
}

# spider config
SPIDER_CONFIG = {
    "parallel_co_tasks": 300,
    "save_path": "data/up_info.dat"
}

PROXY_POOL = {
    "enable": True,
    "type": "juliang",  # "file"/"zhima"/"juliang"
    "file": {
        "path": "data/proxies"
    },
    "zhima": {
        # https://http.zhimaruanjian.com/getapi/
        "pool_size": 100,  # per cpu
        "api": "http://webapi.http.zhimacangku.com/getip?num=10&type=2&pro=&city=0&yys=0&port=1&time=1&ts=1&ys=0&cs=0&lb=1&sb=0&pb=4&mr=1&regions="
    },
    "juliang": {
        # https://www.juliangip.com/
        "pool_size": 5000,
        "api": "http://v2.api.juliangip.com/unlimited/getips?ip_remain=1&num=20&pt=1&result_type=json&trade_no=5633051359267008&sign=1f8eabbf3663a4cac67d59135f0faadf"
    }
}

# Hdfs
HDFS = {
    # "host": "http://bigdata.zaxtyson.cn:50070/",
    "host": "http://localhost:50070/",
    "root_path": "/user/bigdata"  # without '/' suffix
}
