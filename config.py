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
    "parallel_co_tasks": 500,
    "save_path": "data/up_info_test.dat"
}

PROXY_POOL = {
    "enable": False,
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
        "pool_size": 2000,
        "api": "http://v2.api.juliangip.com/dynamic/getips?ip_remain=1&num=10&pt=1&result_type=json&trade_no=1786806280220473&sign=cf797a634332a12c9478d0d9086daa32"
    }
}

# Hdfs
HDFS = {
    # "host": "http://bigdata.zaxtyson.cn:50070/",
    "host": "http://localhost:50070/",
    "root_path": "/user/bigdata"  # without '/' suffix
}
