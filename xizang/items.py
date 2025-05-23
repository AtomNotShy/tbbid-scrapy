# Define here the models for your scraped items
#
# See documentation in:
# https://docs.scrapy.org/en/latest/topics/items.html

import scrapy

class CompanyItem(scrapy.Item):
    name = scrapy.Field()  # 公司名字
    link = scrapy.Field()  # 公司链接
    corp = scrapy.Field()  # 法人
    corp_code = scrapy.Field()  # 统一社会信用代码
    corp_name = scrapy.Field()  # 法人名字
    corp_asset = scrapy.Field()  # 注册资本
    reg_address = scrapy.Field()  # 国别/地区
    valid_date = scrapy.Field()  # 报送有效期
    bid_success_count = scrapy.Field()  # 成交次数，默认为0
    bid_count = scrapy.Field()  # 参与投标次数，默认为0
    qualifications = scrapy.Field()


class EmployeeItem(scrapy.Item):
    name = scrapy.Field()  # 人员名称
    corp_code = scrapy.Field()  # 公司代码
    role = scrapy.Field()  # 角色
    cert_code = scrapy.Field()  # 注册证书编号
    major = scrapy.Field()  # 注册专业
    valid_date = scrapy.Field()  # 注册有效期
    id = scrapy.Field()

class PersonPerformanceItem(scrapy.Item):
    name = scrapy.Field()
    corp_code = scrapy.Field()
    corp_name = scrapy.Field()
    project_name = scrapy.Field()


class ProjectItem(scrapy.Item):
    title = scrapy.Field()
    timeShow = scrapy.Field()
    platformName = scrapy.Field()
    classifyShow = scrapy.Field()
    url = scrapy.Field()
    notice_content = scrapy.Field()
    districtShow = scrapy.Field()  # 地区
    session_size = scrapy.Field()  #标段数量
    project_id = scrapy.Field()  # 招标编号
    company_req = scrapy.Field()
    person_req = scrapy.Field()
    construction_funds = scrapy.Field()
    project_duration = scrapy.Field()


class BidSectionItem(scrapy.Item):
    project_id = scrapy.Field()
    section_name = scrapy.Field()
    section_id = scrapy.Field()
    bid_size = scrapy.Field()
    bid_open_time = scrapy.Field()
    info_source = scrapy.Field()
    lot_ctl_amt = scrapy.Field()  # 控制价
    session_size = scrapy.Field()  # 标段数量


class BidItem(scrapy.Item):
    section_name = scrapy.Field()  # 标段名字
    project_id = scrapy.Field()  # 招标编号
    section_id = scrapy.Field()
    bidder_name = scrapy.Field()
    bid_amount = scrapy.Field()
    bid_open_time = scrapy.Field()
    rank = scrapy.Field()

class BidRankItem(scrapy.Item):
    project_id = scrapy.Field()
    section_name = scrapy.Field()
    section_id = scrapy.Field()
    bidder_name = scrapy.Field()
    rank = scrapy.Field()
    manager_name = scrapy.Field()  # 项目经理
    win_amt = scrapy.Field()
    open_time = scrapy.Field()

class BidWinItem(scrapy.Item):
    bidder_name = scrapy.Field()
    corp_code = scrapy.Field()
    project_name = scrapy.Field()
    area_code = scrapy.Field()
    win_amt = scrapy.Field()
    create_time = scrapy.Field()
    tender_org_name = scrapy.Field()  # 招标单位
    tos = scrapy.Field()   # 类别
    url = scrapy.Field()
    notice_content = scrapy.Field()
