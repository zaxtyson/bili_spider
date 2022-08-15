# Logger
LOG_APPENDER = [
    "console",
    "file"
]


# Config for aiohttp
HTTP_CLIENT = {
    "retry_times": 10,
    "dns_server": [],
    "timeout": {
        "total": 3600,
        "connect": 30
    }
}

# Spider filter strategies
SPIDER_FILTER = {
    "min_follower": 10000
}

# https://http.zhimaruanjian.com/getapi/
PROXY_POOL = {
    "enable": False,
    "pool_size": 5,  # per cpu
    "api": "http://webapi.http.zhimacangku.com/getip?num=2&type=2&pro=&city=0&yys=0&port=1&pack=122571&ts=1&ys=0&cs=1&lb=1&sb=0&pb=4&mr=1&regions="
}

# Hdfs
HDFS = {
    # "host": "http://bigdata.zaxtyson.cn:50070/",
    "host": "http://localhost:50070/",
    "root_path": "/user/bigdata"  # without '/' suffix
}
