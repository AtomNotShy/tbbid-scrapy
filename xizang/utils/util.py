import re

from bs4 import BeautifulSoup

from xizang.constants import company_qualifications, professional_titles

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
        return -1

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
                return -1
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
        if num == -1:
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
    pattern = r"(?:资金来源|资金来自)[：:\s]*([^\n，。；]*)(?:（资金来源）)?"
    match = re.search(pattern, text)
    if match:
        # 去除括号内容和多余空白
        result = re.sub(r"（.*?）", "", match.group(1)).strip()
        return result
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
    # 匹配"一级建造师"、"二级建造师"、"注册建造师"等
    match = re.search(r'([一二三壹贰叁]级)?建造师', text)
    if match:
        return match.group(0)
    return ""

def remove_script_tags(html_content):
    soup = BeautifulSoup(html_content, "html.parser")

    # 移除所有 <script> 标签
    for script in soup.find_all("script"):
        script.decompose()

    return str(soup)


def analyse_notice(html_text, project):
    """解析招标公告-网页"""
    pure_text = remove_script_tags(html_text)
    construction_funds = extract_funding_source(pure_text)
    project_duration = extract_duration(pure_text)
    company_req = extract_construction_qualification(pure_text)
    person_req = extract_profession_and_level(pure_text)

    project['notice_content'] = pure_text
    project['company_req'] = company_req
    project['person_req'] = person_req
    project['construction_funds'] = construction_funds
    project['project_duration'] = project_duration

    return project
