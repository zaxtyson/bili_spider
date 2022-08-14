
# Config for aiohttp
HTTP_CLIENT = {
    "retry_times": 5,
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
    "pool_size": 3,
    "api": "http://http.tiqu.letecs.com/getip3?num=1&type=2&pro=110000&city=110200&yys=0&port=1&pack=122571&ts=1&ys=0&cs=1&lb=4&sb=0&pb=45&mr=1&regions=&gm=4"
}

# Hdfs
HDFS = {
    # "host": "http://bigdata.zaxtyson.cn:50070/",
    "host": "http://localhost:50070/",
    "root_path": "/user/bigdata"  # without '/' suffix
}
