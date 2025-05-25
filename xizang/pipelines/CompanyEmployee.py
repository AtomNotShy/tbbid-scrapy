from itemadapter import ItemAdapter
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import IntegrityError
import logging

from xizang.models.models import create_tables, CompanyInfo, EmployeeInfo, PersonPerformance
from xizang.settings import POSTGRES_URL

class CompanyEmployeePipeline:
    def __init__(self):
        self.engine = create_engine(POSTGRES_URL)
        self.Session = sessionmaker(bind=self.engine)
        self.session = self.Session()
        # 创建数据库表
        create_tables(self.engine)
        self.logger = logging.getLogger(__name__)

    def process_item(self, item, spider):
        adapter = ItemAdapter(item)

        if item.__class__.__name__ == 'EmployeeItem':
            # 检查公司是否存在
            company = self.session.query(CompanyInfo).filter_by(corp_code=adapter.get('corp_code')).first()

            if not company:
                # 创建临时公司记录
                company = CompanyInfo(
                    corp_code=adapter.get('corp_code'),
                    name='Temporary Company'
                )
                self.session.add(company)
                self.session.commit()

            # 创建或更新员工信息
            employee = self.session.query(EmployeeInfo).filter_by(cert_code=adapter.get('cert_code')).first()
            if employee:
                # 更新现有员工信息
                employee.name = adapter.get('name')
                employee.corp_code = adapter.get('corp_code')
                employee.role = adapter.get('role')
                employee.major = adapter.get('major')
                employee.valid_date = adapter.get('valid_date')
                employee.birth_date = adapter.get('birth_date')
                employee.id_number = adapter.get('id_number')
            else:
                # 创建新员工记录
                employee = EmployeeInfo(
                    name=adapter.get('name'),
                    corp_code=adapter.get('corp_code'),
                    role=adapter.get('role'),
                    cert_code=adapter.get('cert_code'),
                    major=adapter.get('major'),
                    valid_date=adapter.get('valid_date'),
                    id_number=adapter.get('id_number'),
                    birth_date=adapter.get('birth_date')
                )
                self.session.add(employee)

        elif item.__class__.__name__ == 'CompanyItem':
            # 更新公司信息
            company = self.session.query(CompanyInfo).filter_by(corp_code=adapter.get('corp_code')).first()
            if company:
                company.name = adapter.get('name')
                company.corp = adapter.get('corp')
                company.corp_asset = adapter.get('corp_asset')
                company.reg_address = adapter.get('reg_address')
                company.valid_date = adapter.get('valid_date')
                company.qualifications = adapter.get('qualifications')
                company.bid_count = adapter.get('bid_count', 0) + 1
            else:
                # 创建新公司记录
                company = CompanyInfo(
                    name=adapter.get('name'),
                    corp_code=adapter.get('corp_code'),
                    corp=adapter.get('corp'),
                    corp_asset=adapter.get('corp_asset'),
                    reg_address=adapter.get('reg_address'),
                    valid_date=adapter.get('valid_date'),
                    qualifications=adapter.get('qualifications'),
                    bid_count=1,
                    win_count=0
                )
                self.session.add(company)

        elif item.__class__.__name__ == 'PersonPerformanceItem':
            # 处理个人业绩数据
            try:
                # 检查公司是否存在
                corp_code = adapter.get('corp_code')
                if corp_code:
                    company = self.session.query(CompanyInfo).filter_by(corp_code=corp_code).first()
                    if not company:
                        # 如果公司不存在，创建临时公司记录
                        company = CompanyInfo(
                            corp_code=corp_code,
                            name=adapter.get('corp_name', 'Unknown Company')
                        )
                        self.session.add(company)
                        self.session.flush()

                # 检查是否已存在相同的个人业绩记录
                existing_performance = self.session.query(PersonPerformance).filter_by(
                    name=adapter.get('name'),
                    corp_code=adapter.get('corp_code'),
                    project_name=adapter.get('project_name'),
                    role=adapter.get('role')
                ).first()

                if existing_performance:
                    # 更新现有记录
                    existing_performance.data_level = adapter.get('data_level')
                    self.logger.debug(f"Updated person performance for {adapter.get('name')}")
                else:
                    # 创建新的个人业绩记录
                    performance = PersonPerformance(
                        name=adapter.get('name'),
                        corp_code=adapter.get('corp_code'),
                        corp_name=adapter.get('corp_name'),
                        project_name=adapter.get('project_name'),
                        data_level=adapter.get('data_level'),
                        role=adapter.get('role')
                    )
                    self.session.add(performance)
                    self.logger.debug(f"Added new person performance for {adapter.get('name')}")

            except IntegrityError as e:
                self.session.rollback()
                self.logger.error(f"Database integrity error when processing person performance: {e}")
            except Exception as e:
                self.session.rollback()
                self.logger.error(f"Error processing person performance item: {e}")
                raise

        self.session.commit()
        return item

    def close_spider(self, spider):
        self.session.close()
