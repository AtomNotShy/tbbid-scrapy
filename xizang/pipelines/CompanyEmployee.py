from itemadapter import ItemAdapter
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import logging

from xizang.models.models import create_tables, CompanyInfo, EmployeeInfo, PersonPerformance
from xizang.settings import POSTGRES_URL

class CompanyEmployeePipeline:
    def __init__(self):
        self.engine = create_engine(
            POSTGRES_URL,
            pool_size=10,
            max_overflow=20,
            pool_pre_ping=True,  # 检查连接是否有效
            pool_recycle=3600    # 1小时后回收连接
        )
        self.Session = sessionmaker(bind=self.engine)
        # 创建数据库表
        create_tables(self.engine)
        self.logger = logging.getLogger(__name__)

    def open_spider(self, spider):
        """爬虫开始时创建会话"""
        self.session = self.Session()
        self.logger.info("CompanyEmployeePipeline opened")

    def process_item(self, item, spider):
        adapter = ItemAdapter(item)
        
        try:
            if item.__class__.__name__ == 'EmployeeItem':
                self._process_employee_item(adapter)
            elif item.__class__.__name__ == 'CompanyItem':
                self._process_company_item(adapter)
            elif item.__class__.__name__ == 'PersonPerformanceItem':
                self._process_performance_item(adapter)
            
            # 统一提交
            self.session.commit()
            self.logger.debug(f"Successfully processed {item.__class__.__name__}")
            
        except Exception as e:
            self.session.rollback()
            self.logger.error(f"Error processing {item.__class__.__name__}: {e}")
            # 重新抛出异常，让Scrapy知道处理失败
            raise
        
        return item

    def _process_employee_item(self, adapter):
        """处理员工信息"""
        corp_code = adapter.get('corp_code')
        if not corp_code:
            raise ValueError("Employee item missing corp_code")
        
        # 确保公司存在
        company = self.session.query(CompanyInfo).filter_by(corp_code=corp_code).first()
        if not company:
            # 创建临时公司记录
            company = CompanyInfo(
                corp_code=corp_code,
                name=adapter.get('corp_name', 'Temporary Company')
            )
            self.session.add(company)
            self.session.flush()  # 立即写入以获取ID
            self.logger.info(f"Created temporary company: {corp_code}")

        # 处理员工信息
        cert_code = adapter.get('cert_code')
        if cert_code:
            employee = self.session.query(EmployeeInfo).filter_by(cert_code=cert_code).first()
        else:
            # 如果没有证书编号，按姓名和公司查找
            employee = self.session.query(EmployeeInfo).filter_by(
                name=adapter.get('name'),
                corp_code=corp_code
            ).first()

        if employee:
            # 更新现有员工信息
            employee.name = adapter.get('name')
            employee.corp_code = corp_code
            employee.role = adapter.get('role')
            employee.major = adapter.get('major')
            employee.valid_date = adapter.get('valid_date')
            employee.birth_date = adapter.get('birth_date')
            employee.id_number = adapter.get('id_number')
            self.logger.debug(f"Updated employee: {employee.name}")
        else:
            # 创建新员工记录
            employee = EmployeeInfo(
                name=adapter.get('name'),
                corp_code=corp_code,
                role=adapter.get('role'),
                cert_code=cert_code,
                major=adapter.get('major'),
                valid_date=adapter.get('valid_date'),
                id_number=adapter.get('id_number'),
                birth_date=adapter.get('birth_date')
            )
            self.session.add(employee)
            self.logger.debug(f"Added new employee: {adapter.get('name')}")

    def _process_company_item(self, adapter):
        """处理公司信息"""
        corp_code = adapter.get('corp_code')
        if not corp_code:
            raise ValueError("Company item missing corp_code")
        
        company = self.session.query(CompanyInfo).filter_by(corp_code=corp_code).first()
        if company:
            # 更新现有公司信息
            company.name = adapter.get('name')
            company.corp = adapter.get('corp')
            company.corp_asset = adapter.get('corp_asset')
            company.reg_address = adapter.get('reg_address')
            company.valid_date = adapter.get('valid_date')
            company.qualifications = adapter.get('qualifications')
            # 只有在有新的投标计数时才更新
            if adapter.get('bid_count') is not None:
                company.bid_count = adapter.get('bid_count', 0) + 1
            if adapter.get('others'):
                company.others = adapter.get('others')
            self.logger.debug(f"Updated company: {company.name}")
        else:
            # 创建新公司记录
            company = CompanyInfo(
                name=adapter.get('name'),
                corp_code=corp_code,
                corp=adapter.get('corp'),
                corp_asset=adapter.get('corp_asset'),
                reg_address=adapter.get('reg_address'),
                valid_date=adapter.get('valid_date'),
                qualifications=adapter.get('qualifications'),
                bid_count=adapter.get('bid_count', 1),
                win_count=0,
                others=adapter.get('others', '')
            )
            self.session.add(company)
            self.logger.debug(f"Added new company: {adapter.get('name')}")

    def _process_performance_item(self, adapter):
        """处理个人业绩信息"""
        corp_code = adapter.get('corp_code')
        if not corp_code:
            raise ValueError("Performance item missing corp_code")
        
        # 确保公司存在
        company = self.session.query(CompanyInfo).filter_by(corp_code=corp_code).first()
        if not company:
            company = CompanyInfo(
                corp_code=corp_code,
                name=adapter.get('corp_name', 'Unknown Company')
            )
            self.session.add(company)
            self.session.flush()
            self.logger.info(f"Created temporary company for performance: {corp_code}")

        # 检查是否已存在相同的个人业绩记录
        existing_performance = self.session.query(PersonPerformance).filter_by(
            name=adapter.get('name'),
            corp_code=corp_code,
            project_name=adapter.get('project_name'),
            role=adapter.get('role')
        ).first()

        if existing_performance:
            # 更新现有记录
            existing_performance.corp_name = adapter.get('corp_name')
            existing_performance.data_level = adapter.get('data_level')
            existing_performance.record_id = adapter.get('record_id')
            existing_performance.company_id = adapter.get('company_id')
            self.logger.debug(f"Updated person performance for {adapter.get('name')}")
        else:
            # 创建新的个人业绩记录
            performance = PersonPerformance(
                name=adapter.get('name'),
                corp_code=corp_code,
                corp_name=adapter.get('corp_name'),
                project_name=adapter.get('project_name'),
                data_level=adapter.get('data_level'),
                role=adapter.get('role'),
                record_id=adapter.get('record_id'),
                company_id=adapter.get('company_id')
            )
            self.session.add(performance)
            self.logger.debug(f"Added new person performance for {adapter.get('name')}")

    def close_spider(self, spider):
        """爬虫结束时清理资源"""
        if hasattr(self, 'session') and self.session:
            try:
                self.session.commit()  # 最后提交一次
            except Exception as e:
                self.logger.error(f"Error in final commit: {e}")
                self.session.rollback()
            finally:
                self.session.close()
        self.logger.info("CompanyEmployeePipeline closed")
