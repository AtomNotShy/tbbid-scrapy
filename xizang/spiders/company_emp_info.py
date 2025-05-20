import scrapy
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from urllib.parse import quote
from xizang.items import CompanyItem, EmployeeItem

import time
import logging

class CompanyEmpInfoSpider(scrapy.Spider):
    name = 'company_emp_info'
    allowed_domains = ['221.13.83.27']
    custom_settings = {
        'ITEM_PIPELINES': {
            'xizang.pipelines.CompanyEmployee.CompanyEmployeePipeline': 300,
        }
    }
    def __init__(self, *args, **kwargs):
        super(CompanyEmpInfoSpider, self).__init__(*args, **kwargs)
        # 数据库连接
        self.engine = create_engine('postgresql://atom:qwerasdf@localhost:5432/data')
        self.Session = sessionmaker(bind=self.engine)
        self.session = self.Session()
        
    def start_requests(self):
        # 查询需要获取信息的公司
        query = text("""
            SELECT DISTINCT bidder_name 
            FROM bid 
            WHERE bidder_name NOT IN (SELECT name FROM company_info)
            AND bidder_name != ''
        """)
        
        companies = self.session.execute(query).fetchall()
        self.logger.info(f"Found {len(companies)} companies to process")
        
        for company in companies:
            company_item = CompanyItem()
            company_item["name"] = company[0] # company name
            # 构建搜索URL
            search_url = f'http://221.13.83.27:8010/outside/corps?keywords={quote(company_item["name"])}'
            yield scrapy.Request(
                url=search_url,
                callback=self.parse_search_result,
                meta={'company_item': company_item}
            )
    
    def parse_search_result(self, response):
        company_item = response.meta['company_item']
        # 获取公司代码
        corp_code = response.xpath('//*[@id="tab1"]/div[2]/div[1]/div[2]/table/tbody/tr/td[4]/text()').get()
        
        if corp_code:
            company_item['corp_code'] = corp_code
            # 构建详情页URL
            detail_url = f'http://221.13.83.27:8010/outside/corpdetail?corpcode={corp_code}'
            yield scrapy.Request(
                url=detail_url,
                callback=self.parse_company_detail,
                meta={
                    'company_item': company_item
                }
            )
            # 获取当前毫秒级时间戳
            timestamp_ms = int(time.time() * 1000)
            # 查询注册建造师
            emp_url = f'http://221.13.83.27:8010/outside/corplistbypersonreg?corpcode={corp_code}&pageIndex=1&_={timestamp_ms}'
            yield scrapy.Request(url=emp_url, callback=self.parse_employee, meta={'company_item': company_item})

            # 查询安全员
            security_emp_url = f'http://221.13.83.27:8010/outside/corplistbypostclass?corpcode={corp_code}&pageIndex=1&_={timestamp_ms}'
            yield scrapy.Request(url=security_emp_url, callback=self.parse_security, meta={'company_item': company_item})
        else:
            self.logger.warning(f"No company code found for {company_item['name']}")


    def parse_company_detail(self, response):
        company_item = response.meta['company_item']
        company_item['corp'] = response.xpath('//td[contains(text(), "法人姓名")]/following-sibling::td[1]/text()').get()
        company_item['corp_asset'] = response.xpath('//td[contains(text(), "注册资本")]/following-sibling::td[1]/text()').get()
        company_item['reg_address'] = response.xpath(
            '//td[contains(text(), "经营地址")]/following-sibling::td[1]/text()').get()
        company_item['valid_date'] = response.xpath(
            '//td[contains(text(), "报送有效期")]/following-sibling::td[1]/text()').get()
        qualifications_list = response.xpath('//*[@id="file1"]/div/table/tbody/tr/td[3]/text()').getall()
        # 只保留包含“承包一级”、“承包贰级”或“承包三级”的条目，并去重
        keywords = {"工程施工", "工程专业", "承包贰级","承包壹级"}
        filtered_qua = list({
            q for q in qualifications_list if any(kw in q for kw in keywords)
        })
        company_item['qualifications'] = filtered_qua
        yield company_item

    def parse_employee(self, response):
        company_item = response.meta['company_item']
        corp_code = company_item['corp_code']
        person_list = response.xpath('//tbody/tr')
        if len(person_list) == 0:
            logging.info(f"No jianzaoshi employee found for {company_item['name']}")
        for person in person_list:
            employee_item = EmployeeItem()
            employee_item['corp_code'] = corp_code
            if not person.xpath('./td[2]//a/text()').get():
                continue
            employee_item['name'] = person.xpath('./td[2]//a/text()').get().strip()
            employee_item['major'] = person.xpath('./td[7]/text()').get().strip().split('、')
            employee_item['corp_code'] = corp_code
            employee_item['cert_code'] = person.xpath('./td[3]/text()').get()
            employee_item['role'] = person.xpath('./td[4]/text()').get()
            employee_item['valid_date'] = person.xpath('./td[6]/text()').get()
            yield employee_item
        page_nums = response.xpath('//*[@class="page-item page-num"]//text()').extract()
        if len(page_nums) == 0:
            logging.info(f"No other pages found for {company_item['name']}")
            return None
        timestamp_ms = int(time.time() * 1000)
        if response.meta.get('seen'):
            return None
        for num in page_nums:
            next_url = f'http://221.13.83.27:8010/outside/corplistbypersonreg?corpcode={corp_code}&pageIndex={num}&_={timestamp_ms}'
            yield scrapy.Request(url=next_url,
                                 callback=self.parse_employee,
                                 meta={
                                     'company_item': company_item,
                                     'seen': True
                                 })

    def parse_security(self, response):
        company_item = response.meta['company_item']
        corp_code = company_item['corp_code']
        person_list = response.xpath('//tbody/tr')
        if len(person_list) == 0:
            logging.info(f"No security employee found for {company_item['name']}")
        for person in person_list:
            employee_item = EmployeeItem()
            employee_item['corp_code'] = corp_code
            if not person.xpath('./td[2]/text()').get():
                logging.info(f"No security employee found for {company_item['name']}")
                continue
            employee_item['name'] = person.xpath('./td[2]/text()').get().strip()
            employee_item['cert_code'] = person.xpath('./td[5]/text()').get()
            employee_item['valid_date'] = person.xpath('./td[7]/text()').get()
            if 'B' in employee_item['cert_code']:
                employee_item['role'] = '安全员B'
            elif 'C' in employee_item['cert_code']:
                employee_item['role'] = '安全员C'
            else:
                continue

            yield employee_item
        page_nums = response.xpath('//*[@class="page-item page-num"]//text()').extract()
        if len(page_nums) == 0:
            logging.info(f"No other pages found for {company_item['name']}")
            return None
        if response.meta.get('seen'):
            return None
        timestamp_ms = int(time.time() * 1000)
        for num in page_nums:
            next_url = f'http://221.13.83.27:8010/outside/corplistbypostclass?corpcode={corp_code}&pageIndex={num}&_={timestamp_ms}'
            yield scrapy.Request(url=next_url, callback=self.parse_security, meta={'company_item': company_item, 'seen': True})

    def closed(self, reason):
        self.session.close() 