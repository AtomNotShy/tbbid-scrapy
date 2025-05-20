import scrapy
from xizang.items import CompanyItem
from datetime import datetime, timedelta
from scrapy.exceptions import CloseSpider
import re

class CompanyListSpider(scrapy.Spider):
    name = "corp_list"
    allowed_domains = ["ggzy.xizang.gov.cn"]

    def __init__(self, duration=1, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.duration = int(duration)  # Convert string to integer
        time_end = datetime.today().strftime('%Y-%m-%d %H:%M:%S')
        time_begin = (datetime.today() - timedelta(days=self.duration)).strftime('%Y-%m-%d')
        start_url = f"https://ggzy.xizang.gov.cn/search/queryContents.jhtml?title=&channelId=3528&inDates={self.duration}&timeBegin={time_begin}&timeEnd={time_end}"
        self.start_url = start_url
    
    def start_requests(self):
        yield scrapy.Request(url=self.start_url, callback=self.parse)

    def parse(self, response):
        node_list = response.xpath('//*[@class="detail_content_right_box_content_ul"]/li')
        if not node_list:
            return None
        end_date = (datetime.today() - timedelta(days=self.duration)).date()  # 爬虫截止日期
        cur_date = None
        self.logger.info(f'爬虫截止日期: {end_date}')
        for li in node_list:
            item = CompanyItem()
            onclick_js = li.xpath('.//p[@onclick]/@onclick').extract_first()
            url = onclick_js.split("'")[1]  # 分割字符串提取路径
            item['link'] = response.urljoin(url)  # 转换为完整 URL
            # 提取公司名称（第二个 span 的文本）
            item['name'] = li.xpath('.//span[2]/text()').extract_first()
            # 提取日期（第二个 p 的文本）
            item['date'] = li.xpath('./p[2]/text()').extract_first()
            cur_date = datetime.strptime(item['date'], "%Y-%m-%d").date()  # 4.12

            if cur_date <= end_date:
                raise CloseSpider(f"搜索日期:[{datetime.today().strftime('%Y-%m-%d')}, {end_date}],搜索结束!")
            yield scrapy.Request(url=item['link'], callback=self.parse_detail, meta={'item': item})

        count = int(re.search(r'count: (\d+)', response.text).group(1))
        page_limit = int(re.search(r'limit: (\d+)', response.text).group(1))
        page_num = count // page_limit + 1
        self.logger.info(f'total items: {count}, page limit: {page_limit}, page number: {page_num}')
        print(f'total items: {count}, page limit: {page_limit}, page number: {page_num}')
        n = 1
        while n <= page_num:
            n += 1
            next_url = f'https://ggzy.xizang.gov.cn/search/queryContents_{n}.jhtml'
            self.logger.info(f'current page:{n}, expected page:{page_num}, next_url:{next_url}')
            yield scrapy.Request(url=next_url, callback=self.parse)

    def parse_detail(self, response):
        item = response.meta['item']
        content_table = response.xpath('//*[@class="content-text"]/div/div/table')

        item['corp'] = content_table.xpath('./tr[1]/td[2]/text()').extract_first()
        item['corp_code'] = content_table.xpath('./tr[1]/td[4]/text()').extract_first()

        item['corp_role'] = content_table.xpath('./tr[2]/td[2]/text()').extract_first()
        item['corp_name'] = content_table.xpath('./tr[2]/td[4]/text()').extract_first()

        item['corp_type'] = content_table.xpath('./tr[3]/td[2]/text()').extract_first()
        item['corp_asset'] = content_table.xpath('./tr[3]/td[4]/text()').extract_first()

        item['agent_type'] = content_table.xpath('./tr[4]/td[2]/text()').extract_first()
        item['location'] = content_table.xpath('./tr[4]/td[4]/text()').extract_first()

        item['city'] = content_table.xpath('./tr[5]/td[2]/text()').extract_first()

        return item

