import scrapy
import json

class CompanyGGJySpider(scrapy.Spider):
    name = "company_ggjy"
    start_url = 'https://data.ggzy.gov.cn/yjcx/index/bid_list'

    def start_requests(self):
        body = {
            "uniscid": "915100007316089178",
            "page": 1,
            "tos": ""
        }

        headers = {
            "Content-Type": "application/json;charset=UTF-8",
            "Accept": "application/json, text/plain, */*",
            "Origin": "https://data.ggzy.gov.cn",
            "Referer": "https://data.ggzy.gov.cn/portal_legal/companyPer.html",
            "User-Agent": "Mozilla/5.0"
        }

        yield scrapy.Request(
            url=self.start_url,
            method='POST',
            body=json.dumps(body),  # 关键：用 json.dumps 转成字符串
            headers=headers,
            callback=self.parse
        )

    def parse(self, response):
        print(response.text)