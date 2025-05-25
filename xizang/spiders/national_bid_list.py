import scrapy
import json
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from xizang.items import BidWinItem,CompanyItem
from xizang.settings import POSTGRES_URL

class NationalBidListSpider(scrapy.Spider):
    """在公共交易中心查公司全国业绩"""
    name = 'national_bid_list'
    allowed_domains = ['ggzy.gov.cn']
    start_url = 'https://data.ggzy.gov.cn/yjcx/index/bid_list'
    bid_show = 'https://data.ggzy.gov.cn/yjcx/index/bid_show'
    custom_settings = {
        'ITEM_PIPELINES': {
            'xizang.pipelines.winner_bid.WinnerBidPipeline': 350
        }
    }

    def __init__(self, *args, **kwargs):
        super(NationalBidListSpider, self).__init__(*args, **kwargs)
        # 数据库连接
        self.engine = create_engine(POSTGRES_URL)
        self.Session = sessionmaker(bind=self.engine)
        self.session = self.Session()

    def start_requests(self):
        query = text("SELECT corp_code, name FROM company_info WHERE name != 'Temporary Company' ORDER BY RANDOM() LIMIT 400;")
        companies = self.session.execute(query).fetchall()
        self.logger.info(f"Found {len(companies)} companies to process")
        for row in companies:
            body = {"uniscid": row[0], "page": 1, "tos": '01'}  # tos 01 代表工程建设
            company = CompanyItem()
            company['corp_code'] = row[0]
            company['name'] = row[1]
            yield scrapy.Request(
                url=self.start_url,
                method='POST',
                body=json.dumps(body),  # 关键：用 json.dumps 转成字符串
                callback=self.parse,
                meta={'company': company}
            )

    def parse(self, response):
        company = response.meta['company']
        data = json.loads(response.text)
        total = int(data['total'])
        bid_list = data.get("data",[])
        if total is None or total <= 0:
            self.logger.debug(f'total is not valid, {total}')
            return
        if bid_list is None or len(bid_list) == 0:
            self.logger.debug('bid_list is not valid')
            return
        for bid in bid_list:
            item = BidWinItem()
            item["project_name"] = bid["project_name"]
            item["bidder_name"] = company["name"]
            item['corp_code'] = company["corp_code"]
            item["win_amt"] = bid["bid_price"]
            item["create_time"] = bid["create_time"]
            item['tos'] = bid["tos"]
            item['area_code'] = bid["area_code"]
            item['tender_org_name'] = bid["tender_org_name"]
            body = {"id": bid["id"]}
            yield scrapy.Request(
                url=self.bid_show,
                method='POST',
                body=json.dumps(body),
                callback=self.parse_detail,
                meta={'item': item}
            )

        cur_page = data.get("page")
        rows = data.get("rows")
        total_page = int(total) // rows + 1
        while cur_page <= total_page:
            cur_page += 1
            body = {"uniscid": company["corp_code"], "page": cur_page, "tos": ''}  # tos 1 代表工程建设
            yield scrapy.Request(
                url=self.start_url,
                method='POST',
                body=json.dumps(body),  # 关键：用 json.dumps 转成字符串
                callback=self.parse,
                meta={'company': company}
            )

    def parse_detail(self, response):
        res = json.loads(response.text)
        data = res.get("data")
        item = response.meta.get("item")
        if data is None or len(data) == 0:
            yield item
        item['url'] = data.get("url")
        item['notice_content'] = data.get("content")
        yield item









