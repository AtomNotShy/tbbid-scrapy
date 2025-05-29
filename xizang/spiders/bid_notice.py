from xizang.items import ProjectItem, BidSectionItem
from xizang.utils.util import analyse_notice, extract_section_number_str
import scrapy
from scrapy.http import JsonRequest
import json
import logging
import secrets
import os


def parse_cookie_string(cookie_str):
    """
    Convert a raw cookie string into a Python dictionary.
    """
    cookies = {}
    for pair in cookie_str.strip().split(';'):
        if '=' in pair:
            key, value = pair.strip().split('=', 1)
            cookies[key] = value
    return cookies


class BidNoticeSpider(scrapy.Spider):
    """从西藏公共交易中心获取最近招标公告，以补足全国交易中心时间延长"""
    name = 'bid_notice'
    cookie = """
    _site_id_cookie=22; _trs_uv=ma0ofmnp_3522_lfzl; SESSION=NjI1ZWMwY2YtODYzYS00YzQxLTgwZTMtZjM3OTNlMzk4ZGZh; arialoadData=true; ariauseGraymode=false; JIDENTITY=a5334105-8fd4-4340-9924-e3fbf071ceff; token=07ab36e0da904b9b84bfb10876023d1b; G3_SESSION_V=MmEyOTYwNDktZjFiYy00N2Q5LWI1NmItMzgwN2EwN2QwYzZh
           """

    custom_settings = {
        'ITEM_PIPELINES': {
            'xizang.pipelines.bidSaver.BidSaverPipeline': 300,
        }
    }
    total_projects = 0
    def start_requests(self):
        rand_param = secrets.token_hex(6)
        body =  {"page": 1, "pageSize": 100, "searchName": "", "registerStatus": ""}
        url = f'https://ggzy.xizang.gov.cn/api/gbEnroll/queryList?random={rand_param}'
        yield JsonRequest(
            url=url, 
            data=body, 
            callback=self.parse, 
            method='POST',
            cookies=parse_cookie_string(self.cookie)
        )

    def parse_notice(self, response):
        if response.status != 200:
            logging.warning(f'error:{response.message}')
        project = response.meta.get('project')
        res = json.loads(response.text)
        project['session_size'] = len(res['data']['listData'])
        for item in res['data']['listData']:
            html_text = item['txt']
            project['districtShow'] = self.parse_city(item['areaNo'])
            self.total_projects +=1
            yield analyse_notice(html_text, project)

    def parse(self, response):
        res = json.loads(response.text)
        if not res['success']:
            logging.error(f"整体库打开失败:{res['message']}")
            return
        data = res['data']
        for item in data['data']:
            project = ProjectItem()
            bid_section = BidSectionItem()
            project['title'] = item['tenderProjectName']
            project['project_id'] = item['tenderProjectCode']
            project['timeShow'] = item['publishTime']

            bid_section['project_id'] = project['project_id']
            bid_section['section_id'] = extract_section_number_str(item['bidSectionName'])
            bid_section['section_name'] = item['bidSectionName'] + bid_section['section_id']
            yield bid_section

            url = 'https://ggzy.xizang.gov.cn/personalitySearch/initDetailbyProjectCode'
            body = {"projectCode": project['project_id'], "path": "jyxxgcgg", "sId": 22}
            yield JsonRequest(
                url=url,
                data=body,
                cookies=parse_cookie_string(self.cookie),
                callback=self.parse_notice,
                method='POST',
                meta={'project': project}
            )
        # 翻页请求暂时屏蔽，暂时获取前 100个
        # total = data['pageBean']['endNo']
        # cur_page = data['pageBean']['page']
        # if cur_page <= total and cur_page < 2: # 暂时只爬取前8页作为数据同步
        #     cur_page += 1
        #     print(f'第{cur_page}页')
        #     rand_param = secrets.token_hex(6)
        #     body = {"page": cur_page, "pageSize": 10, "searchName": "", "registerStatus": ""}
        #     url = f'https://ggzy.xizang.gov.cn/api/gbEnroll/queryList?random={rand_param}'
        #     yield JsonRequest(
        #         url=url,
        #         data=body,
        #         callback=self.parse,
        #         method='POST',
        #         cookies=parse_cookie_string(self.cookie)
        #     )

    def parse_city(self, area_code):
        if len(area_code) > 4:
            area_code = area_code[:4]
        # 获取当前脚本文件所在目录
        base_dir = os.path.dirname(os.path.abspath(__file__))
        cities_path = os.path.join(base_dir, '..', 'cities.json')
        with open(cities_path, encoding='utf-8') as f:
            city_dic = json.load(f)
        for city in city_dic:
            if city['code'] == area_code:
                return city['name']
        return ''

    def closed(self, reason):
        logging.info(f'共更新项目:{self.total_projects}')
