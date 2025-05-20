import scrapy
from xizang.items import EmployeeItem
from xizang.settings import DATA_BASE_PARAMS
import psycopg2
from w3lib.url import add_or_replace_parameter


class PersonRegListSpider(scrapy.Spider):
    name = "PersonReg"

    def start_requests(self):
        self.connect = psycopg2.connect(
            host=DATA_BASE_PARAMS['host'],
            port=DATA_BASE_PARAMS['port'],
            dbname=DATA_BASE_PARAMS['dbname'],
            user=DATA_BASE_PARAMS['user'],
            password=DATA_BASE_PARAMS['passwd']
        )
        self.cursor = self.connect.cursor()
        self.cursor.execute("SELECT COUNT(corp) FROM corp_list;")
        total = self.cursor.fetchone()[0]
        if total == 0:
            self.logger.info("待更新查找注册人员的公司为空。")
            return None
        print('corp total size: ', total)
        patch_num = 100
        for i in range(0, int(total//patch_num)+1):
            self.cursor.execute(f"SELECT corp_code FROM corp_list LIMIT {patch_num} OFFSET {100*i}")
            results = self.cursor.fetchall()
            for row in results:
                keyword = row[0]  # 替换为你要搜索的关键词
                search_url = f"http://221.13.83.27:8010/outside/corplistbypersonreg?corpcode={keyword}&pageIndex=1"
                yield scrapy.Request(url=search_url, callback=self.parse, meta={'corp_code': keyword})
 
    def parse(self, response):
        page_num = len(response.xpath('//*[@id="Personreg"]/div/div[1]/ul/li')) - 4
        corp_code = response.meta['corp_code']
        if page_num == 0:
            self.logger.warning(f'WARN: {corp_code} no employee find, page_num = {page_num}')
            return None
        
        person_list = response.xpath('/html/body/div[1]/table/tbody/tr')
        for td in person_list:
            emp = EmployeeItem()
            emp['corp_code'] = corp_code
            emp['name'] = td.xpath('./td[2]/a/text()').get().strip()
            emp['cert'] = td.xpath('./td[3]/text()').get().strip().strip()
            emp['type_level'] = td.xpath('./td[4]/text()').get().strip()
            emp['start_date'] = td.xpath('./td[5]/text()').get().strip()
            emp['end_date'] = td.xpath('./td[6]/text()').get().strip()
            emp['major'] = td.xpath('./td[7]/text()').get().strip()
            yield emp
        index = 1
        while index <= page_num:
            index += 1
            new_url = add_or_replace_parameter(response.url, 'pageIndex', str(page_num))
            yield scrapy.Request(url=new_url, callback=self.parse_other_page, meta={'corp_code': corp_code})

    def parse_other_page(self, response):
        corp_code = response.meta['corp_code']
        person_list = response.xpath('/html/body/div[1]/table/tbody/tr')

        for td in person_list:
            emp = EmployeeItem()
            emp['corp_code'] = corp_code
            emp['name'] = td.xpath('./td[2]/a/text()').get().strip()
            emp['cert'] = td.xpath('./td[3]/text()').get().strip().strip()
            emp['type_level'] = td.xpath('./td[4]/text()').get().strip()
            emp['start_date'] = td.xpath('./td[5]/text()').get().strip()
            emp['end_date'] = td.xpath('./td[6]/text()').get().strip()
            emp['major'] = td.xpath('./td[7]/text()').get().strip()
            return emp