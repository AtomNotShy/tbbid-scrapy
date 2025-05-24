# 西藏招投标信息采集系统

一个基于Scrapy的招投标信息自动化采集系统，专门用于采集西藏地区政府采购和工程招投标相关数据。

## 📋 项目概述

本项目是一个专业的招投标数据采集系统，能够自动化采集以下信息：
- **招标公告信息**：项目名称、时间、分类、地区等
- **投标企业信息**：企业资质、法人信息、注册资本等
- **员工资质信息**：建造师证书、专业等级、有效期等
- **中标结果数据**：中标企业、金额、项目经理等
- **个人业绩数据**：项目经理履历、工程业绩等

## 🏗️ 系统架构

### 核心组件
- **爬虫引擎**：基于Scrapy 2.12
- **数据存储**：PostgreSQL 数据库
- **浏览器驱动**：Selenium + Chrome (处理JavaScript渲染)
- **数据处理**：Beautiful Soup + lxml 解析HTML
- **反爬虫策略**：User-Agent轮换、请求延迟、自动限流

### 数据模型
- `Project`: 招标项目基础信息
- `BidSection`: 标段信息
- `Bid`: 投标信息
- `BidRank`: 中标排名
- `CompanyInfo`: 企业基础信息
- `EmployeeInfo`: 员工资质信息
- `PersonPerformance`: 个人业绩
- `WinnerBidInfo`: 中标结果

## 🚀 快速开始

### 环境要求
- Python 3.10+
- PostgreSQL 数据库
- Chrome 浏览器

### 安装步骤

1. **克隆项目**
```bash
git clone <repository_url>
cd xizang
```

2. **创建虚拟环境**
```bash
python -m venv .venv
source .venv/bin/activate  # Linux/Mac
# .venv\Scripts\activate  # Windows
```

3. **安装依赖**
```bash
pip install -r requirements.txt
```

4. **配置数据库**
- 创建PostgreSQL数据库
- 修改 `xizang/settings.py` 中的数据库连接参数
- 运行数据库初始化脚本：
```bash
python xizang/initDataBase.py
```

5. **配置Chrome驱动**
- 确保系统已安装Chrome浏览器
- Selenium会自动管理ChromeDriver

## 🎯 使用方法

### 主要爬虫命令

#### 1. 采集招投标信息 (主要功能)
```bash
# 采集指定日期范围的招投标信息
nohup scrapy crawl bid_info -a start_date='2025-03-01' -a end_date='2025-04-01' > bid_info.log 2>&1 &

# 采集最近7天的数据 (默认)
scrapy crawl bid_info

# 实时查看日志
tail -f bid_info.log
```

#### 2. 采集企业员工信息 (包含个人业绩)
```bash
# 采集企业员工信息及其个人业绩数据
scrapy crawl company_emp_info

# 注意：此爬虫会同时采集以下数据：
# - 企业基本信息
# - 员工资质信息（建造师、安全员等）
# - 项目经理个人业绩数据
```

#### 3. 采集企业资质信息
```bash
scrapy crawl corp_list
```

#### 4. 采集个人注册信息
```bash
scrapy crawl personreg
```

#### 5. 采集全国招投标列表
```bash
scrapy crawl national_bid_list
```

### 参数说明
- `start_date`: 开始日期 (格式: YYYY-MM-DD)
- `end_date`: 结束日期 (格式: YYYY-MM-DD)
- 如不指定日期，默认采集最近7天的数据

## ⚙️ 配置说明

### 主要配置文件

#### `xizang/settings.py`
```python
# 并发设置
CONCURRENT_REQUESTS = 8
DOWNLOAD_DELAY = 2
CONCURRENT_REQUESTS_PER_DOMAIN = 4

# 数据库配置
DATA_BASE_PARAMS = {
    'host': 'localhost',
    'port': 5432,
    'dbname': 'data',
    'user': 'atom',
    'passwd': 'qwerasdf.'
}

# Pipeline配置 (根据爬虫需要启用)
ITEM_PIPELINES = {
    'xizang.pipelines.CompanyEmployee.CompanyEmployeePipeline': 300,  # 企业员工信息
    'xizang.pipelines.PersonPerformance.PersonPerformancePipeline': 310,  # 个人业绩
    'xizang.pipelines.bidSaver.BidSaverPipeline': 300,  # 招投标信息
}

# 自动限流
AUTOTHROTTLE_ENABLED = True
AUTOTHROTTLE_START_DELAY = 2
AUTOTHROTTLE_MAX_DELAY = 30
```

#### `config.yml`
```yaml
USERNAME: admin
PASSWORD: "qwer2025."
COMPRESS_STATIC: True
```

### 反爬虫策略
- **随机User-Agent**: 模拟不同浏览器访问
- **智能延迟**: 自动调节请求间隔
- **Selenium渲染**: 处理JavaScript动态内容
- **重试机制**: 自动重试失败请求

## 📊 数据采集范围

### 采集网站
- 主站：`deal.ggzy.gov.cn` (中国政府采购网)
- 备用：`ggzy.gov.cn`

### 采集内容
1. **招标公告** (类型0101)
2. **开标信息** (类型0102) 
3. **中标结果** (类型0103)
4. **澄清公告** (类型0104)

### 数据字段
- **项目信息**: 标题、时间、分类、地区、资金来源、工期
- **企业信息**: 名称、统代码、法人、资质、注册资本
- **人员信息**: 姓名、证书、专业、等级、有效期
- **投标信息**: 企业、金额、排名、项目经理

## 🔧 开发指南

### 项目结构
```
xizang/
├── xizang/
│   ├── spiders/          # 爬虫文件
│   │   ├── bid_info.py   # 主要招投标爬虫
│   │   ├── company_emp_info.py  # 企业员工信息爬虫
│   │   └── ...
│   ├── models/           # 数据模型
│   ├── pipelines/        # 数据处理管道
│   │   ├── CompanyEmployee.py   # 企业员工数据Pipeline
│   │   ├── PersonPerformance.py # 个人业绩数据Pipeline
│   │   └── bidSaver.py          # 招投标数据Pipeline
│   ├── middlewares.py    # 中间件
│   ├── items.py         # 数据结构定义
│   └── settings.py      # 配置文件
├── requirements.txt     # 依赖包
├── scrapy.cfg          # Scrapy配置
├── test_person_performance.py  # 个人业绩测试脚本
└── README.md
```

### 添加新爬虫
1. 在 `spiders/` 目录创建新的爬虫文件
2. 继承 `scrapy.Spider` 类
3. 定义 `name`、`allowed_domains`、`start_urls`
4. 实现 `parse` 方法

### 扩展数据模型
1. 在 `models/models.py` 中添加新的SQLAlchemy模型
2. 在 `items.py` 中定义对应的Scrapy Item
3. 创建对应的Pipeline处理数据

## 🧪 功能测试

### 个人业绩数据测试
```bash
# 测试个人业绩数据存储功能
python test_person_performance.py

# 该测试会检查：
# - 个人业绩记录数量统计
# - 最近采集的业绩数据
# - 按公司和角色的统计信息
# - 数据完整性验证
```

## 📝 日志监控

### 日志文件
- **主日志**: `bid_info.log`
- **级别**: INFO
- **编码**: UTF-8

### 监控指标
- 请求成功率
- 数据采集量
- 错误类型统计
- 内存使用情况

### 常见问题
1. **403错误**: 触发反爬虫，自动重试
2. **超时**: 网络问题，增加重试次数
3. **内存不足**: 调整 `MEMUSAGE_LIMIT_MB` 参数

## 🔒 数据安全

- 数据库连接加密
- 敏感信息配置文件管理
- 请求头伪装
- 访问频率控制

## 📈 性能优化

- 数据库连接池
- 并发请求控制
- 内存使用监控
- 自动限流机制

## 🤝 贡献指南

1. Fork 项目
2. 创建特性分支
3. 提交更改
4. 推送到分支
5. 创建 Pull Request

## 📄 许可证

本项目仅供学习和研究使用，请遵守相关网站的robots.txt协议。

## 🆘 技术支持

如有问题请提交Issue或联系开发团队。

---
**注意**: 使用本系统时请遵守目标网站的服务条款，合理控制访问频率，避免对服务器造成过大压力。

### 使用如下方式运行：
```bash
nohup scrapy crawl bid_info -a start_date='2025-03-01' -a end_date='2025-04-01' > bid_info.log 2>&1 &
``` 
