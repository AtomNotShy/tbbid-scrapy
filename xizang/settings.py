# Scrapy settings for xizang project
#
# For simplicity, this file contains only settings considered important or
# commonly used. You can find more settings consulting the documentation:
#
#     https://docs.scrapy.org/en/latest/topics/settings.html
#     https://docs.scrapy.org/en/latest/topics/downloader-middleware.html
#     https://docs.scrapy.org/en/latest/topics/spider-middleware.html

BOT_NAME = "xizang"

SPIDER_MODULES = ["xizang.spiders"]
NEWSPIDER_MODULE = "xizang.spiders"


# Crawl responsibly by identifying yourself (and your website) on the user-agent
#USER_AGENT = "xizang (+http://www.yourdomain.com)"

# Obey robots.txt rules
# ROBOTSTXT_OBEY = True

# Configure maximum concurrent requests performed by Scrapy (default: 16)
CONCURRENT_REQUESTS = 8  # 增加并发请求数，但不要太高以避免被封

# Configure a delay for requests for the same website
DOWNLOAD_DELAY = 2  # 降低延迟，但仍保持合理间隔

# The download delay setting will honor only one of:
CONCURRENT_REQUESTS_PER_DOMAIN = 4  # 限制每个域名的并发请求数
CONCURRENT_REQUESTS_PER_IP = 4      # 限制每个IP的并发请求数

# Disable cookies (enabled by default)
#COOKIES_ENABLED = False

# Disable Telnet Console (enabled by default)
#TELNETCONSOLE_ENABLED = False

# Override the default request headers:
#DEFAULT_REQUEST_HEADERS = {
#    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
#    "Accept-Language": "en",
#}

# Enable or disable spider middlewares
# See https://docs.scrapy.org/en/latest/topics/spider-middleware.html
SPIDER_MIDDLEWARES = {
   "xizang.middlewares.RandomUserAgent": 543
}


# Enable or disable downloader middlewares
# See https://docs.scrapy.org/en/latest/topics/downloader-middleware.html

DOWNLOADER_MIDDLEWARES = {
    # 'scrapy.downloadermiddlewares.httpproxy.HttpProxyMiddleware': 110,
    # 'xizang.middlewares.RandomUseProxyWithProbabilityMiddleware': 100,
    'xizang.middlewares.SeleniumMiddleware': 800,
   # 'xizang.middlewares.SimulateSearch': 800

}
SELENIUM_DRIVER_NAME = 'chrome'

# Enable or disable extensions
# See https://docs.scrapy.org/en/latest/topics/extensions.html
#EXTENSIONS = {
#    "scrapy.extensions.telnet.TelnetConsole": None,
#}

# Enable and configure the AutoThrottle extension
AUTOTHROTTLE_ENABLED = True
AUTOTHROTTLE_START_DELAY = 2
AUTOTHROTTLE_MAX_DELAY = 30
AUTOTHROTTLE_TARGET_CONCURRENCY = 2.0
AUTOTHROTTLE_DEBUG = False  # 启用调试模式以查看节流情况

# Configure retry settings
RETRY_ENABLED = True
RETRY_TIMES = 3  # 重试次数
RETRY_HTTP_CODES = [403, 500, 502, 503, 504, 522, 524, 408, 429]  # 需要重试的HTTP状态码

# Allow 403 responses to be processed
HTTPERROR_ALLOWED_CODES = [403]

# Configure item pipelines
ITEM_PIPELINES = {
    # 'xizang.pipelines.bidSaver.BidSaverPipeline': 300,
}

# Configure logging
LOG_LEVEL = 'INFO'  # 设置日志级别
LOG_FILE = 'bid_crawl.log'  # 将日志保存到文件
LOG_ENCODING = 'utf-8'

# Configure memory usage
MEMUSAGE_ENABLED = True
MEMUSAGE_LIMIT_MB = 2048  # 限制内存使用为2GB
MEMUSAGE_WARNING_MB = 1536  # 内存使用超过1.5GB时发出警告

# Configure database connection pool
DB_MAX_CONNECTIONS = 10  # 数据库连接池最大连接数
DB_STALE_TIMEOUT = 300  # 连接超时时间（秒）

# Set settings whose default value is deprecated to a future-proof value
TWISTED_REACTOR = "twisted.internet.asyncioreactor.AsyncioSelectorReactor"
FEED_EXPORT_ENCODING = "utf-8"


DATA_BASE_PARAMS = {
    'host': 'localhost',
    'port': 5432,
    'dbname': 'data',
    'user': 'atom',
    'passwd': 'qwerasdf.'
}



PROXY_URL = 'http://47.108.227.93:3128'  # 你的Squid代理地址
PROXY_AUTH = 'myproxyuser:myproxypass'  # 代理用户名:密码

PROXY_PROBABILITY = 0.7  # 使用代理的概率

# PostgreSQL 配置
POSTGRES_URL = 'postgresql://atom:qwerasdf.@localhost:5432/data'  # 根据实际情况修改
