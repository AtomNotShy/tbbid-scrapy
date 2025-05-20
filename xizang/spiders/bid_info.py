import logging
import re
import scrapy
import json

from bs4 import BeautifulSoup

from xizang.items import ProjectItem, BidItem, BidSectionItem, BidRankItem
from datetime import datetime, timedelta
from scrapy.exceptions import CloseSpider
from xizang.constants import company_qualifications, professional_titles
from w3lib.url import add_or_replace_parameter
import pytz

from readability import Document
from lxml import html

#  "https://ggzy.xizang.gov.cn/api/attach/download?attachId=8a8b98fb967bb8dd01968145f2c948db"


# 中文数字映射表（简体 + 繁体）
digit_map = {
    '零': 0, '〇': 0,
    '一': 1, '壹': 1,
    '二': 2, '贰': 2, '貳': 2,
    '三': 3, '叁': 3, '參': 3,
    '四': 4, '肆': 4,
    '五': 5, '伍': 5,
    '六': 6, '陆': 6, '陸': 6,
    '七': 7, '柒': 7,
    '八': 8, '捌': 8,
    '九': 9, '玖': 9,
    '十': 10, '拾': 10
}

def chinese_to_arabic(chinese: str) -> int:
    """
    支持简体和繁体中文数字转阿拉伯数字（1~99）
    """
    if not chinese:
        return None

    total = 0
    if '十' in chinese or '拾' in chinese:
        chinese = chinese.replace('拾', '十')  # 统一处理
        parts = chinese.split('十')
        if parts[0] == '':
            total += 10  # 如"十一"
        else:
            total += digit_map.get(parts[0], 0) * 10

        if len(parts) > 1 and parts[1]:
            total += digit_map.get(parts[1], 0)
    else:
        # 没有"十"的情况：如"三"、"九"
        total = 0
        for ch in chinese:
            if ch in digit_map:
                total = total * 10 + digit_map[ch]
            else:
                return None
    return total

def extract_section_number_str(title: str) -> str:
    """提取标段号并格式化为三位字符串，如 '021'"""
    # 阿拉伯数字形式
    match_digit = re.search(r'项目\((\d+)标段\)', title)
    if match_digit:
        return f"{int(match_digit.group(1)):03d}"

    # 中文数字形式
    match_chinese = re.search(r'总承包(.*?)标段', title)
    if match_chinese:
        chinese_num = match_chinese.group(1)
        num = chinese_to_arabic(chinese_num)
        if num is not None:
            return f"{num:03d}"

    return '001'


def is_number(s):
    try:
        float(s)
        return True
    except (TypeError, ValueError):
        return False


def extract_url_from_click(click_url):
    base_url = 'https://www.ggzy.gov.cn/information'
    m = re.search(
        r"showDetail\(\s*[^,]+,\s*'[^']*',\s*'([^']*)'\s*\)",
        click_url
    )
    if m:
        url = m.group(1)
        return base_url + url
    else:
        return None

def extract_funding_source(text: str) -> str:
    # 匹配"资金来源"或"资金来自"后面的内容，直到遇到"招标人"或"项目"或"."等标点符号
    pattern = r"(?:资金来源|资金来自)[：:\s]*([^，。；\n]*?)(?=，招标人|，项目|。|；|$)"
    match = re.search(pattern, text)
    if match:
        return match.group(1).strip()
    return ""

def extract_duration(text: str) -> str:
    # 匹配"工期"或"计划工期"后面的内容，包括括号内的信息
    pattern = r"(?:计划)?工期[：:\s]*([\d一二三四五六七八九十百]+[年月天日]{1,2}(?:（[\d一二三四五六七八九十百]+[日历天日]{1,2}）)?)"
    match = re.search(pattern, text)
    if match:
        return match.group(1)
    return ""

# 公司资质
def extract_construction_qualification(text: str) -> list:
    # 构建明确的工程类型正则（用"|"分隔）
    categories = company_qualifications
    category_pattern = "|".join(categories)
    # 完整正则：匹配"某类工程施工总承包X级"
    pattern = rf"(?:{category_pattern})施工总承包[一二三四五六七八九十壹贰叁肆伍陆柒捌玖拾特]+级"
    return re.findall(pattern, text)


# 人员资质
def extract_profession_and_level(text):
    # 定义等级模式（例如：一级、二级、叁级等，包含"以上"）
    level_pattern = r"(一级|二级|叁级|贰级|四级|五级|以上|含.*?级)"

    # 将专业名构建成正则表达式
    professional_pattern = "|".join([re.escape(prof) for prof in professional_titles])

    # 定义匹配专业和等级的正则表达式
    pattern = rf"((?<=：)|(?<=要求))(.+?({professional_pattern})专业.*?({level_pattern})?.*?注册建造师执业资格)"

    # 使用正则表达式查找匹配项
    matches = re.findall(pattern, text)

    # 提取匹配的专业和等级
    result = ""
    for match in matches:
        profession = match[2]  # 匹配到的专业
        level = match[3] if match[3] else "未指定"  # 匹配到的等级，如果没有匹配到则返回"未指定"
        result += profession + level

    return result

class BidInfoSpider(scrapy.Spider):
    name = "bid_info"
    allowed_domains = ["deal.ggzy.gov.cn", "ggzy.gov.cn"]
    shanghai_tz = pytz.timezone('Asia/Shanghai')

    custom_settings = {
        'ITEM_PIPELINES': {
            'xizang.pipelines.bidSaver.BidSaverPipeline': 300,
        }
    }

    # 0101招标 0102 开标 0103 结果 0104澄清
    def __init__(self, start_date=None, end_date=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.duration = 10
        # 获取当前日期
        today = datetime.now()
        # 默认开始日期为当前日期减去7天
        default_start_date = today - timedelta(days=self.duration)
        default_end_date = today
        # 处理开始日期参数
        if start_date:
            try:
                self.start_date = datetime.strptime(start_date, '%Y-%m-%d')
            except ValueError:
                self.logger.warning(f"无效的开始日期格式: {start_date}，使用默认日期(当前日期减7天)")
                self.start_date = default_start_date
        else:
            # 如果入参为空则使用默认当日时间减7天
            self.start_date = default_start_date

        # 处理结束日期参数
        if end_date:
            try:
                self.end_date = datetime.strptime(end_date, '%Y-%m-%d')
            except ValueError:
                self.logger.warning(f"无效的结束日期格式: {end_date}，使用当前日期")
                self.end_date = default_end_date
        else:
            self.end_date = default_end_date

        # 初始化进度计数器
        self.total_projects = 0
        self.processed_projects = 0
        self.total_lots = 0
        self.processed_lots = 0
        self.total_bids = 0
        self.processed_bids = 0

    def start_requests(self):
        # 日期已在__init__中设置，这里直接使用
        url = (f"https://deal.ggzy.gov.cn/ds/deal/dealList_find.jsp?"
               f"TIMEBEGIN_SHOW={self.start_date.strftime('%Y-%m-%d')}&"
               f"TIMEEND_SHOW={self.end_date.strftime('%Y-%m-%d')}&"
               f"TIMEBEGIN={self.start_date.strftime('%Y-%m-%d')}&"
               f"TIMEEND={self.end_date.strftime('%Y-%m-%d')}&"
               f"SOURCE_TYPE=1&DEAL_TIME=06&DEAL_CLASSIFY=01&DEAL_STAGE=0101&"
               f"DEAL_PROVINCE=540000&DEAL_CITY=0&DEAL_PLATFORM=0&"
               f"BID_PLATFORM=0&DEAL_TRADE=0&isShowAll=1&PAGENUMBER=1&FINDTXT=")

        self.logger.info(f'scrawl from: {self.start_date.strftime("%Y-%m-%d")} to {self.end_date.strftime("%Y-%m-%d")}')
        yield scrapy.Request(url=url, callback=self.parse, method='POST')

    def parse(self, response):
        try:
            data = json.loads(response.text)

            if 'data' not in data:
                self.logger.error(f"Unexpected response structure: {data}")
                return None

            self.total_projects = len(data['data'])
            self.logger.info(f"processing projects: {self.total_projects}, processed: {self.processed_projects}")

            n = 0
            for item in reversed(data['data']):

                title = item['title']
                if '设计项目' in item or '监理' in title or '造价咨询' in title:
                    self.logger.debug('skip other types')
                    continue
                # n += 1
                # if n > 2: return
                # 创建并填充 ProjectItem

                project_item = ProjectItem()
                if title.endswith("招标公告"):
                    title = title[:-4]

                project_item['title'] = title
                project_item['timeShow'] = item['timeShow']
                project_item['platformName'] = item['platformName']
                project_item['classifyShow'] = item['classifyShow']
                project_item['url'] = item['url']
                project_item['districtShow'] = item['districtShow']
                
                # 发送请求处理项目详情
                self.logger.info(f"Requesting project details for: {title}")
                yield scrapy.Request(
                    url=item['url'],
                    callback=self.parse_stages,
                    meta={'project_item': project_item},
                    dont_filter=True  # 确保请求不被过滤
                )
                # return None

            cur_page = data['currentpage'] + 1
            while cur_page <= data['ttlpage']:
                cur_page += 1
                url = add_or_replace_parameter(response.url, 'PAGENUMBER', str(cur_page))
                yield scrapy.Request(url=url, callback=self.parse, method='POST')

        except json.JSONDecodeError:
            self.logger.error("响应不是有效的JSON格式")
            CloseSpider("响应不是有效的JSON格式")

    def parse_stages(self, response):
        logging.debug('开始分析四个阶段')
        project_item = response.meta['project_item']
        try:
            project_item['project_id'] = response.xpath("//*[@class='p_o']/span[1]/text()").get().split('：')[1]
        except IndexError:
            logging.error('get project id error!')
            return None
        notice_first = response.xpath('//*[@id="div_0101"]/ul/li/a/@onclick').extract_first()
        if not notice_first:
            logging.info(f'{project_item["title"]}: notice is empty, skip.')
            return None

        section_list = response.xpath('//*[@id="div_0102"]/ul/li/a/@onclick').extract()
        section_name_list = response.xpath('//*[@id="div_0102"]/ul/li/a/text()').extract()

        if not section_list:
            logging.debug('标段为空')

        project_item['session_size'] = len(section_list)

        url = extract_url_from_click(notice_first)
        if url:
            project_item['url'] = url
            logging.debug( f'开始处理{project_item["title"]}的招标公告。')
            yield scrapy.Request(url=url, callback=self.parse_notice, meta={'project_item': project_item})


        logging.debug('开始开标记录标段')
        for n, section in enumerate(section_list):
            bid_section_item = BidSectionItem()
            try:
                section_id = extract_section_number_str(section_name_list[n])
            except IndexError:
                logging.warning('')
                section_id = '001'

            url = extract_url_from_click(section)
            if not url:
                continue

            bid_section_item['project_id'] = project_item['project_id']
            bid_section_item['section_id'] = section_id
            bid_section_item['section_name'] = project_item['title'] + section_id
            bid_section_item['session_size'] = project_item['session_size']
            yield scrapy.Request(url=url, callback=self.parse_bids, meta={'bid_section_item': bid_section_item})


        result_list = response.xpath('//*[@id="div_0104"]/ul/li/a/@onclick').extract()
        logging.debug('开始解析候选人')
        for result in result_list:
            url = extract_url_from_click(result)
            if url:
                yield scrapy.Request(url=url, callback=self.parse_results, meta={'project_item': project_item})

    def remove_script_tags(self,html_content):
        soup = BeautifulSoup(html_content, "html.parser")

        # 移除所有 <script> 标签
        for script in soup.find_all("script"):
            script.decompose()

        return str(soup)

    def parse_notice(self, response):
        project_item = response.meta['project_item']
        project_item['notice_content'] = self.remove_script_tags(response.text)
        html_text = response.text
        # 用 readability 提取正文
        doc = Document(html_text)
        content_html = doc.summary()  # 提取的是 HTML 格式正文
        # 可进一步用 lxml 解析出纯文本
        content_tree = html.fromstring(content_html)
        pure_text = content_tree.text_content()

        construction_funds = extract_funding_source(pure_text)
        project_duration = extract_duration(pure_text)
        company_req = extract_construction_qualification(pure_text)
        person_req = extract_profession_and_level(pure_text)

        project_item['company_req'] = company_req
        project_item['person_req'] = person_req
        project_item['construction_funds'] = construction_funds
        project_item['project_duration'] = project_duration
        logging.debug(f'project content:{dict(project_item)}')
        self.processed_projects += 1
        yield project_item

    def get_control_price(self, response):
        th_list = response.xpath('//table//thead//tr[1]/th')
        index = 0
        for i, th in enumerate(th_list):
            text = th.xpath('string(.)').get()
            if '控制价' in text:
                index = i
                break

        node_list = response.xpath(f'//table//table//tr')
        logging.debug(f'index:{index}')
        for node in node_list:
            price = node.xpath(f'./td[{index}]/text()').get()
            if is_number(price):
                return float(price)
        return 0

    def parse_bids(self, response):
        logging.debug('开始解析竞标详情')
        bid_section_item = response.meta['bid_section_item']
        # bid_section_item['section_name'] = response.xpath('//*[@class="h4_o"]/text()').get().strip()


        bid_open_time = response.xpath('//*[@class="p_o"]/span[1]/text()').get().split('：')
        if len(bid_open_time) > 1 and bid_open_time[0] != '开标时间':
            self.logger. error(f'获取 {bid_section_item["section_name"]} 开标时间有误')
            yield bid_section_item
            return None

        bid_section_item['info_source'] = response.xpath('//*[@id="platformName"]/text()').get() # 信息来源
        bid_section_item['bid_open_time'] = bid_open_time[-1]
        rows = response.xpath('//*[@class="detail_Table"]/tr[4]/td/table//tr')
        bid_section_item['bid_size'] = len(rows)
        self.total_bids += len(rows)
        self.processed_lots += 1

        self.logger.info(f"process: project {self.processed_projects}/{self.total_projects}, "
                        f"session {self.processed_lots}/{self.total_lots}, "
                        f"bids {self.processed_bids}/{self.total_bids}")

        control_price = self.get_control_price(response)
        bid_section_item['lot_ctl_amt'] = control_price
        yield bid_section_item

        for row in rows:
            bidder_name = row.xpath('./td[1]/text()').get()
            if not bidder_name:   #如果名字为空说明不是数据，跳过
                yield bid_section_item
                continue

            bid_item = BidItem()
            bid_item['section_name'] = bid_section_item['section_name']
            bid_item['section_id'] = bid_section_item['section_id']
            bid_item['bid_open_time'] = bid_section_item['bid_open_time']
            bid_item['project_id'] = bid_section_item['project_id']
            bid_amt = row.xpath('./td[2]/text()').get()
            if is_number(bid_amt):
                bid_item['bid_amount'] = float(bid_amt)
            else:
                bid_item['bid_amount'] = 0

            if bidder_name:
                bid_item['bidder_name'] = bidder_name.strip()

            self.processed_bids += 1
            yield bid_item


    def parse_results(self, response):
        logging.debug('开始解招标结果')
        project_item = response.meta['project_item']

        if '标候选人公示' in response.xpath('//*[@class="h4_o"]/text()').get():
            return self.parse_candidates(response, project_item)


    def parse_candidates(self, response, project_item):
        logging.debug('开始解析候选人')
        res_nodes = response.xpath('//*[@id="mycontent"]//tbody/tr')
        if not res_nodes:
            logging.debug('候选人解析为空！')
            return None

        project_name = project_item['title']
        project_id = project_item['project_id']
        company_list = response.xpath('//*[@id="mycontent"]//tbody/tr/td[2]/text()').extract()
        filtered_company_list = []
        manager_list = []
        manager_list_org = response.xpath('//*[@id="mycontent"]//tbody/tr/td[3]/text()').extract()
        win_amt = []
        if len(manager_list_org) != len(company_list):
            logging.error(f'公司名单长度{len(company_list)}和其他元素长度{len(manager_list_org)}不一致')
            return None

        for i in range(0, len(company_list), 12):
            filtered_company_list.append(company_list[i])  # 只取第一名

            if i > len(manager_list_org):
                win_amt.append('')
            else:
                win_amt.append(manager_list_org[i])  # 取投标价格

            if (i+3) > len(manager_list_org):
                manager_list.append('')
            else:
                manager_list.append(manager_list_org[i+3])  # 取排名第一的经理


        project_keyword = project_name[0:4]
        section_name_list = response.xpath(f'//*[@id="mycontent"]/div/div/div/div[2]/p[contains(text(), "{project_keyword}")]').extract()
        logging.debug(f'section_name_list: {len(section_name_list)}')
        open_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        try:
            open_time = response.xpath('//*[@class="p_o"]/span[contains(text(), "发布时间")]/text()').get().strip().split('：')[1]
        except IndexError as e:
            logging.debug(f'get open_time error: {e}')
        for i in range(0, len(section_name_list)):
            bid_rank = BidRankItem()
            bid_rank['project_id'] = project_id
            section_id = extract_section_number_str(section_name_list[i])
            bid_rank['section_name'] = project_name + section_id
            bid_rank['section_id'] = section_id
            bid_rank['bidder_name'] = filtered_company_list[i]
            bid_rank['rank'] = 1  #  排名
            bid_rank['manager_name'] = manager_list[i]
            bid_rank['win_amt'] = win_amt[i]
            bid_rank['open_time'] = open_time
            yield bid_rank