import scrapy
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from urllib.parse import quote
from xizang.items import CompanyItem, EmployeeItem, PersonPerformanceItem
from xizang.settings import POSTGRES_URL
import time
import logging


class CompanyEmpInfoSpider(scrapy.Spider):
    """在西藏信息查询网站，查询西藏公司及员工信息"""

    name = 'company_emp_info'  # scrapy crawl company_emp_info
    allowed_domains = ['221.13.83.27']
    base_url = 'http://221.13.83.27:8010'
    custom_settings = {
        'ITEM_PIPELINES': {
            'xizang.pipelines.CompanyEmployee.CompanyEmployeePipeline': 300,
        }
    }
    def __init__(self, *args, **kwargs):
        super(CompanyEmpInfoSpider, self).__init__(*args, **kwargs)
        # 数据库连接
        self.engine = create_engine(POSTGRES_URL)
        self.Session = sessionmaker(bind=self.engine)
        self.session = self.Session()
        
    def start_requests(self):
        # 查询需要获取信息的公司
        query = text("""
            SELECT bidder_name
            FROM (
                SELECT DISTINCT bidder_name
                FROM bid
                WHERE bidder_name NOT IN (SELECT name FROM company_info)
                  AND bidder_name != ''
            ) AS sub
            ORDER BY RANDOM()
            LIMIT 400;
        """)
        
        companies = self.session.execute(query).fetchall()
        self.logger.info(f"Found {len(companies)} companies to process")
        
        # 使用生成器处理公司列表
        for name in self.expand_companies(companies):
            company_item = CompanyItem()
            company_item["name"] = name # company name
            # 构建搜索URL
            search_url = f'{self.base_url}/outside/corps?keywords={quote(company_item["name"])}'
            logging.info(f'开始爬取{company_item["name"]}')
            yield scrapy.Request(
                url=search_url,
                callback=self.parse_search_result,
                meta={'company_item': company_item}
            )

    def expand_companies(self, companies):
        """展开包含分号的公司名称，生成器返回公司名称"""
        for company in companies:
            name = company[0] if company and len(company) > 0 else ""
            if ';' in name:
                # 分割并逐个返回公司名称
                names = name.split(';')
                for single_name in names:
                    cleaned_name = single_name.strip()
                    if cleaned_name:  # 只返回非空名称
                        yield cleaned_name
            else:
                cleaned_name = name.strip()
                if cleaned_name:  # 只返回非空名称
                    yield cleaned_name

    def parse_search_result(self, response):
        company_item = response.meta['company_item']
        # 获取公司代码
        corp_code = response.xpath('//*[@id="tab1"]/div[2]/div[1]/div[2]/table/tbody/tr/td[4]/text()').get()
        
        if corp_code:
            company_item['corp_code'] = corp_code
            # 构建详情页URL
            detail_url = f'{self.base_url}/outside/corpdetail?corpcode={corp_code}'
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
            emp_url = f'{self.base_url}/outside/corplistbypersonreg?corpcode={corp_code}&pageIndex=1&_={timestamp_ms}'
            yield scrapy.Request(url=emp_url, callback=self.parse_employee, meta={'company_item': company_item})

            # 查询安全员
            security_emp_url = f'{self.base_url}/outside/corplistbypostclass?corpcode={corp_code}&pageIndex=1&_={timestamp_ms}'
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
        # 只保留包含"承包一级"、"承包贰级"或"承包三级"的条目，并去重
        keywords = {"工程施工", "工程专业", "承包贰级","承包壹级"}
        filtered_qua = list({
            q for q in qualifications_list if any(kw in q for kw in keywords)
        })
        company_item['qualifications'] = filtered_qua
        others = response.xpath("//*[@class='tooltip-bottom']/text()").get()
        if others:
            company_item['others'] = others.strip()
        logging.info(f'公司信息获取完成：{company_item["name"]}')
        yield company_item

    def parse_employee_perform(self, response):
        employee = response.meta['employee']
        perform = response.meta['perform']
        logging.info(f'获取{employee["name"]}员工,个人业绩')
        #'http://221.13.83.27:8010/outside/_viewpersonperformancedetail/20558'

        project_name = response.xpath('string(//td[contains(text(), "项目名称")]/following-sibling::td[1])').get().strip()
        record_id = response.xpath('string(//td[contains(text(), "个人业绩记录编号")]/following-sibling::td[1])').get().strip()
        company_id = response.xpath('string(//td[contains(text(), "企业业绩记录编号")]/following-sibling::td[1])').get().strip()

        id_number = response.xpath('string(//td[contains(text(), "人员证件号码")]/following-sibling::td[1])').get().strip()
        if id_number:
            employee['id_number'] = id_number
            yield employee
        perform['project_name'] = project_name
        perform['record_id'] = record_id
        perform['company_id'] = company_id

        yield perform

    def parse_employee_detail(self, response):
        employee = response.meta['employee']
        logging.info(f'开始解析员工{employee["name"]}详情')
        birth_date = response.xpath(
            'string(//td[contains(text(), "出生日期")]/following-sibling::td[1])').get().strip()
        if birth_date:
            employee['birth_date'] = birth_date

        # 如果业绩栏为空则直接返回员工信息
        cols = response.xpath('//tbody/tr').extract()
        if not cols:
            logging.info('业绩为空')
            yield employee
            return
        detail_urls = response.xpath('//tbody/tr/td[6]/a/@data-details').extract()
        data_levels = response.xpath('//tbody/tr/td[2]/text()').extract()
        roles = response.xpath('//tbody/tr/td[5]/text()').extract()

        timestamp_ms = int(time.time() * 1000)
        
        for role,url,level in zip(roles,detail_urls,data_levels):
            if url is None or role != '项目经理':
                continue
            perform = PersonPerformanceItem()
            perform["name"] = employee['name']
            perform["corp_code"] = employee['corp_code']
            perform['corp_name'] = employee['corp_name']
            perform['data_level'] = level
            perform['role'] = '项目经理'
            url = self.base_url + url + f'?_={timestamp_ms}'
            yield scrapy.Request(
                url=url,
                callback=self.parse_employee_perform,
                meta={
                    'employee': employee,
                    'perform': perform
                }
            )

    def parse_employee(self, response):
        company_item = response.meta['company_item']
        corp_code = company_item['corp_code']
        person_list = response.xpath('//tbody/tr')
        if len(person_list) == 0:
            logging.warning(f"{company_item['name']}：无项目经理")

        timestamp_ms = int(time.time() * 1000)
        logging.info(f'获取{company_item["name"]}员工信息')
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
            # 添加公司名称用于个人业绩记录
            employee_item['corp_name'] = company_item['name']
            url = person.xpath('./td[2]//a/@href').get()
            logging.info(f'开始分析员工：{employee_item["name"]}')
            if url.startswith('/outside/persondetail'):
                new_url = url.replace('/outside/persondetail', '/outside/listpersonperformance')
                perform_url = self.base_url + new_url + f'&_={timestamp_ms}'
                yield scrapy.Request(
                    url=perform_url,
                    callback=self.parse_employee_detail,
                    meta={'employee': employee_item}
                )
            else:
                logging.warning(f'员工：{employee_item["name"]}：无个人详情')
                yield employee_item
        page_nums = response.xpath('//*[@class="page-item page-num"]//text()').extract()
        if len(page_nums) == 0:
            logging.info(f"No other pages found for {company_item['name']}")
            return None
        timestamp_ms = int(time.time() * 1000)
        if response.meta.get('seen'):
            return None
        for num in page_nums:
            next_url = f'{self.base_url}/outside/corplistbypersonreg?corpcode={corp_code}&pageIndex={num}&_={timestamp_ms}'
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
            next_url = f'{self.base_url}/outside/corplistbypostclass?corpcode={corp_code}&pageIndex={num}&_={timestamp_ms}'
            yield scrapy.Request(url=next_url, callback=self.parse_security, meta={'company_item': company_item, 'seen': True})

    def closed(self, reason):
        self.session.close() 