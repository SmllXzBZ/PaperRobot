import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__)) + '/'
LOG_PATH = BASE_DIR + '/log/run.log'
KEEP_PATH = BASE_DIR + '/log/keep.log'
FAIL_PATH = BASE_DIR + '/log/fails.txt'
DATA_DIR = BASE_DIR + '/data/'
COOKIE_PATH = DATA_DIR + '/cookies.json'
SLEEP_TIME = 0.5
MAX_RETRY_TIMES = 3
DEBUG = False
S_THRESHOLD = 0.85 #相似度匹配算法阈值

HEADERS = {"Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
           "Upgrade-Insecure-Requests": "1",
           "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.14; rv:86.0) Gecko/20100101 Firefox/86.0",
           "Connection": "close", "Accept-Language": "zh-CN,zh;q=0.8,zh-TW;q=0.7,zh-HK;q=0.5,en-US;q=0.3,en;q=0.2",
           "Accept-Encoding": "gzip, deflate"}

USERNAME = 'tsinghua1'
PASSWORD = 'helloworld'

PROXIES = {
    # 'http':'http:127.0.0.1:8080',
    # 'https':'http:127.0.0.1:8080'
    }

# 会议数据库
LIB = {
    "ccs": "CCS",
    "uss": "Usenix_Security",
    "sp": "S&P",
    "ndss": "NDSS",
    "dsn": "DSN",
    "raid": "RAID",
    "imc": "IMC",
    "asiaccs": "ASIACCS",
    "acsac": "ACSAC",
    "sigcomm": "SIGCOMM",
}

# 需要忽略每个会议自身的bibtex
IGNORE = [
    "Dependable Systems and Networks",
    "IEEE Symposium on Security and Privacy",
]

# scihub地址
SCIHUBS = [
    "https://sci-hub.ee/",
    "https://sci-hub.se/",
    "https://sci-hub.st/",
    "https://sci-hub.do/",
    # "https://sci-hub.ren/",
    # "https://sci-hub.ai/"
]
