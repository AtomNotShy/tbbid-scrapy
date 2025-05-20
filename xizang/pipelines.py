# Define your item pipelines here
#
# Don't forget to add your pipeline to the ITEM_PIPELINES setting
# See: https://docs.scrapy.org/en/latest/topics/item-pipeline.html


import logging
from datetime import datetime

# useful for handling different item types with a single interface
import psycopg2
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from itemadapter import ItemAdapter

from xizang.settings import DATA_BASE_PARAMS
from xizang.models.models import create_tables, CompanyInfo, EmployeeInfo


def get_province_from_usci(usci_code):
    """
    根据统一社会信用代码解析注册地省级/直辖市名称
    :param usci_code: 统一社会信用代码（字符串）
    :return: 省级/直辖市名称 或错误提示
    """
    # 内置行政区划代码（示例数据，需自行补充完整）
    province_codes = {
        "11": "北京市", "12": "天津市", "13": "河北省", "14": "山西省", "15": "内蒙古自治区",
        "21": "辽宁省", "22": "吉林省", "23": "黑龙江省", "31": "上海市", "32": "江苏省",
        "33": "浙江省", "34": "安徽省", "35": "福建省", "36": "江西省", "37": "山东省",
        "41": "河南省", "42": "湖北省", "43": "湖南省", "44": "广东省", "45": "广西壮族自治区",
        "46": "海南省", "50": "重庆市", "51": "四川省", "52": "贵州省", "53": "云南省",
        "54": "西藏自治区", "61": "陕西省", "62": "甘肃省", "63": "青海省", "64": "宁夏回族自治区",
        "65": "新疆维吾尔自治区"
    }

    try:
        # 基础校验
        if len(usci_code) != 18:
            print("错误：统一社会信用代码长度必须为18位")
            return ''

        # 提取行政区划代码前两位（省级代码）
        region_code = usci_code[2:4]

        # 查询映射表
        province = province_codes.get(region_code, None)
        if province:
            return province
        else:
            print(f"未知行政区划代码：{region_code}（请更新数据）")
            return ''

    except Exception as e:
        print(f"代码解析错误：{str(e)}")
        return ''





