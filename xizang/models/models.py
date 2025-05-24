from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, UniqueConstraint, ForeignKeyConstraint, ARRAY
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime, timezone


Base = declarative_base()

class Project(Base):
    __tablename__ = 'project'

    id = Column(Integer, primary_key=True)
    project_id = Column(String, unique=True, nullable=False)
    title = Column(String)
    time_show = Column(DateTime)
    platform_name = Column(String)
    classify_show = Column(String)
    url = Column(String)
    notice_content = Column(String)
    district_show = Column(String)
    session_size = Column(Integer)
    company_req = Column(String)
    person_req = Column(String)
    construction_funds = Column(String)
    project_duration = Column(String)
    crawl_time = Column(DateTime, default=datetime.now)
    stage = Column(Integer, default=1)  # 1: initial, 2: has bid sections, 3: has bid ranks
    bid_sections = relationship("BidSection", backref="project", cascade="all, delete-orphan")
    bid_ranks = relationship("BidRank", backref="project", cascade="all, delete-orphan")


class BidSection(Base):
    __tablename__ = 'bid_section'

    id = Column(Integer, primary_key=True)
    project_id = Column(String, ForeignKey('project.project_id', ondelete='CASCADE'), nullable=False)
    section_name = Column(String, nullable=False)
    section_id = Column(String, nullable=False)
    bid_size = Column(Integer)
    bid_open_time = Column(DateTime)
    info_source = Column(String)
    lot_ctl_amt = Column(Float)
    session_size = Column(Integer)
    crawl_time = Column(DateTime, default=datetime.now)
    status = Column(String)
    winning_bidder = Column(String)
    winning_amount = Column(Float)
    winning_time = Column(DateTime)
    bids = relationship("Bid", backref="bid_section", cascade="all, delete-orphan")

    __table_args__ = (
        UniqueConstraint('project_id', 'section_id', name='uix_project_section'),
    )

class Bid(Base):
    __tablename__ = 'bid'

    id = Column(Integer, primary_key=True)
    project_id = Column(String, nullable=False)
    section_id = Column(String, nullable=False)
    section_name = Column(String, nullable=False)
    bidder_name = Column(String, nullable=False)
    bid_amount = Column(Float)
    bid_open_time = Column(DateTime)
    crawl_time = Column(DateTime, default=datetime.now)

    __table_args__ = (
        UniqueConstraint('project_id', 'section_id', 'bidder_name', name='uix_project_section_bidder'),
        ForeignKeyConstraint(['project_id', 'section_id'], ['bid_section.project_id', 'bid_section.section_id'],
                             ondelete='CASCADE'),
    )


class BidRank(Base):
    __tablename__ = 'bid_rank'

    id = Column(Integer, primary_key=True)
    project_id = Column(String, ForeignKey('project.project_id', ondelete='CASCADE'), nullable=False)
    section_name = Column(String, nullable=False)
    section_id = Column(String, nullable=False)
    bidder_name = Column(String, nullable=False)
    rank = Column(Integer, nullable=False)
    manager_name = Column(String)
    win_amt = Column(Float)
    crawl_time = Column(DateTime, default=datetime.now)
    open_time = Column(DateTime)

    __table_args__ = (
        UniqueConstraint('project_id', 'section_id', 'rank', name='uix_project_section_rank'),
    )


class CompanyInfo(Base):
    __tablename__ = 'company_info'

    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)  # 公司名称
    corp_code = Column(String, unique=True, nullable=False)  # 统一社会信用代码
    corp = Column(String)  # 法人姓名
    corp_asset = Column(String)  # 注册资本
    reg_address = Column(String)  # 注册地址
    valid_date = Column(String)  # 报送有效期
    qualifications = Column(ARRAY(String))  # 资质信息
    bid_count = Column(Integer, default=1)
    win_count = Column(Integer, default=0)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    # 建立与员工的关系
    employees = relationship("EmployeeInfo", back_populates="company")

    def __repr__(self):
        return f"<CompanyInfo(name='{self.name}', corp_code='{self.corp_code}')>"


class EmployeeInfo(Base):
    __tablename__ = 'employee_info'

    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)  # 人员名称
    corp_code = Column(String, ForeignKey('company_info.corp_code',ondelete='CASCADE'), nullable=False)  # 公司代码
    role = Column(String)  # 角色
    cert_code = Column(String, unique=True)  # 注册证书编号
    major = Column(ARRAY(String))  # 注册专业
    valid_date = Column(String)  # 注册有效期
    birth_date =Column(DateTime, nullable=True)
    id_number = Column(String)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    # 建立与公司的关系
    company = relationship("CompanyInfo", back_populates="employees")

    def __repr__(self):
        return f"<EmployeeInfo(name='{self.name}', cert_code='{self.cert_code}')>"

class WinnerBidInfo(Base):
    __tablename__ = 'winner_bid_info'
    
    id = Column(Integer, primary_key=True)
    project_name = Column(String, nullable=False)
    corp_code = Column(String, ForeignKey('company_info.corp_code', ondelete='CASCADE'), nullable=False)  # 公司代码
    bidder_name = Column(String)  # 中标单位名称
    area_code = Column(String)  # 地区代码
    win_amt = Column(Float)  # 中标金额
    create_time = Column(DateTime)  # 创建时间
    tender_org_name = Column(String)  # 招标单位
    tos = Column(String)  # 类别
    url = Column(String)  # 详情页URL
    notice_content = Column(String)  # 公告内容
    
    # 添加时间戳
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), 
                       onupdate=lambda: datetime.now(timezone.utc))

    def __repr__(self):
        return f"<BidWinInfo(project_name='{self.project_name}', bidder_name='{self.bidder_name}')>"

class PersonPerformance(Base):
    __tablename__ = 'person_performance'
    id = Column(Integer, primary_key=True)


# 创建数据库表的函数
def create_tables(engine):
    Base.metadata.create_all(engine)

