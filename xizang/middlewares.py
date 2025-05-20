# Define here the models for your spider middleware
#
# See documentation in:
# https://docs.scrapy.org/en/latest/topics/spider-middleware.html
import time
import re
from scrapy import signals
from fake_useragent import UserAgent

# useful for handling different item types with a single interface


from selenium import webdriver
from scrapy.http import HtmlResponse
from selenium.webdriver.common.by import By
from selenium.webdriver.support.select import Select

import random
import base64

class RandomUseProxyWithProbabilityMiddleware:
    def __init__(self, proxy_url, proxy_auth, proxy_probability):
        self.proxy_url = proxy_url
        self.proxy_auth = proxy_auth
        self.proxy_probability = proxy_probability  # 走代理的概率 (0~1)

        if self.proxy_auth:
            self.encoded_auth = base64.b64encode(self.proxy_auth.encode()).decode()
        else:
            self.encoded_auth = None

    @classmethod
    def from_crawler(cls, crawler):
        return cls(
            proxy_url=crawler.settings.get('PROXY_URL'),
            proxy_auth=crawler.settings.get('PROXY_AUTH'),
            proxy_probability=crawler.settings.getfloat('PROXY_PROBABILITY', 0.5)  # 默认50%
        )

    def process_request(self, request, spider):
        if random.random() < self.proxy_probability:
            # 走代理
            request.meta['proxy'] = self.proxy_url
            if self.encoded_auth:
                request.headers['Proxy-Authorization'] = f'Basic {self.encoded_auth}'
            spider.logger.debug(f"Using proxy {self.proxy_url}")
        else:
            # 不使用代理，直连
            spider.logger.debug("Using local network (no proxy)")


class SimulateSearch(object):
    def __init__(self):
        self.driver = None

    def process_request(self, request, spider):
        if spider.name == "bid_list":
            options = webdriver.ChromeOptions()
            options.add_argument('--headless')  # 无头模式
            self.driver = webdriver.Chrome()
            try:
                self.driver.get(request.url)
                self.driver.implicitly_wait(30)

                self.driver.find_element(By.ID, 'choose_time_02').click()
                # 定位 <select> 元素
                select_elem = self.driver.find_element(By.ID, "provinceId")
                select = Select(select_elem)
                 # 按 value 属性选择
                select.select_by_value("540000")  # 540000 西藏
                self.driver.find_element(By.ID, "choose_stage_0102").click()
                self.driver.find_element(By.ID, "searchButton").click()
                self.driver.implicitly_wait(60)
                return HtmlResponse(
                    url=self.driver.current_url,
                    body=self.driver.page_source.encode('utf-8'),
                    encoding='utf-8',
                    request=request
                )
            except Exception as e:
                print(e)
                return HtmlResponse(url=request.url, status=500, request=request)

    def spider_closed(self, spider):
        self.driver.quit()

class SeleniumMiddleware(object):
    company_url_pattern = r'^https://ggzy\.xizang\.gov\.cn/ztxx_(\d+)\.jhtml$'
    def process_request(self, request, spider):
        if re.match(request.url, self.company_url_pattern):
            options = webdriver.FirefoxOptions()
            options.add_argument('--headless')  # 无头模式
            self.driver = webdriver.Firefox(options=options)
            try:
                self.driver.get(request.url)
                # 等待页面加载完成
                time.sleep(3)
                # 返回处理后的页面
                return HtmlResponse(
                    url=self.driver.current_url,
                    body=self.driver.page_source.encode('utf-8'),
                    encoding='utf-8',
                    request=request
                )
            except Exception as e:
                spider.logger.error(f"Selenium Error: {str(e)}")
                return HtmlResponse(url=request.url, status=500, request=request)
        if request.meta.get('click_actions'):
            options = webdriver.FirefoxOptions()
            options.add_argument('--headless')  # 无头模式
            self.driver = webdriver.Firefox(options=options)
            try:
                self.driver.get(request.url)
                for action in request.meta['click_actions']:
                    button = action['selector']
                    selector_type = action['selector_type']
                    delay = action['delay']
                        # 执行点击操作
                    if selector_type == 'xpath':
                        self.driver.find_element(By.XPATH, value=button).click()
                    else:
                        self.driver.find_element(By.CSS_SELECTOR, value=button).click()
                    time.sleep(delay)
                    # 返回处理后的页面
                return HtmlResponse(
                    url=self.driver.current_url,
                    body=self.driver.page_source.encode('utf-8'),
                    encoding='utf-8',
                    request=request
                )
            except Exception as e:
                    spider.logger.error(f"Selenium Error: {str(e)}")
                    return HtmlResponse(url=request.url, status=500, request=request)

    def spider_closed(self):
        self.driver.quit()


class RandomUserAgent(object):
    def process_request(self, request, spider):
        ua = UserAgent()
        user_agent = ua.random
        request.headers['User-Agent'] = user_agent

        # Add more realistic headers to avoid detection
        request.headers['Accept'] = 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7'
        request.headers['Accept-Language'] = 'zh-CN,zh;q=0.9,en;q=0.8'
        request.headers['Accept-Encoding'] = 'gzip, deflate, br'
        request.headers['Connection'] = 'keep-alive'
        request.headers['Upgrade-Insecure-Requests'] = '1'
        request.headers['Sec-Fetch-Dest'] = 'document'
        request.headers['Sec-Fetch-Mode'] = 'navigate'
        request.headers['Sec-Fetch-Site'] = 'none'
        request.headers['Sec-Fetch-User'] = '?1'

        # Add a referer for requests to ggzy.gov.cn
        if 'ggzy.gov.cn' in request.url:
            request.headers['Referer'] = 'https://www.ggzy.gov.cn/'


class XizangSpiderMiddleware:
    # Not all methods need to be defined. If a method is not defined,
    # scrapy acts as if the spider middleware does not modify the
    # passed objects.

    @classmethod
    def from_crawler(cls, crawler):
        # This method is used by Scrapy to create your spiders.
        s = cls()
        crawler.signals.connect(s.spider_opened, signal=signals.spider_opened)
        return s

    def process_spider_input(self, response, spider):
        # Called for each response that goes through the spider
        # middleware and into the spider.

        # Should return None or raise an exception.
        return None

    def process_spider_output(self, response, result, spider):
        # Called with the results returned from the Spider, after
        # it has processed the response.

        # Must return an iterable of Request, or item objects.
        for i in result:
            yield i

    def process_spider_exception(self, response, exception, spider):
        # Called when a spider or process_spider_input() method
        # (from other spider middleware) raises an exception.

        # Should return either None or an iterable of Request or item objects.
        pass

    def process_start_requests(self, start_requests, spider):
        # Called with the start requests of the spider, and works
        # similarly to the process_spider_output() method, except
        # that it doesn’t have a response associated.

        # Must return only requests (not items).
        for r in start_requests:
            yield r

    def spider_opened(self, spider):
        spider.logger.info("Spider opened: %s" % spider.name)


class XizangDownloaderMiddleware:
    # Not all methods need to be defined. If a method is not defined,
    # scrapy acts as if the downloader middleware does not modify the
    # passed objects.

    @classmethod
    def from_crawler(cls, crawler):
        # This method is used by Scrapy to create your spiders.
        s = cls()
        crawler.signals.connect(s.spider_opened, signal=signals.spider_opened)
        return s

    def process_request(self, request, spider):
        # Called for each request that goes through the downloader
        # middleware.

        # Must either:
        # - return None: continue processing this request
        # - or return a Response object
        # - or return a Request object
        # - or raise IgnoreRequest: process_exception() methods of
        #   installed downloader middleware will be called
        return None

    def process_response(self, request, response, spider):
        # Called with the response returned from the downloader.

        # Must either;
        # - return a Response object
        # - return a Request object
        # - or raise IgnoreRequest
        return response

    def process_exception(self, request, exception, spider):
        # Called when a download handler or a process_request()
        # (from other downloader middleware) raises an exception.

        # Must either:
        # - return None: continue processing this exception
        # - return a Response object: stops process_exception() chain
        # - return a Request object: stops process_exception() chain
        pass

    def spider_opened(self, spider):
        spider.logger.info("Spider opened: %s" % spider.name)
