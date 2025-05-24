from itemadapter import ItemAdapter
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import IntegrityError
import logging

from xizang.models.models import create_tables, PersonPerformance, CompanyInfo
from xizang.settings import POSTGRES_URL


class PersonPerformancePipeline:
    """个人业绩数据存储Pipeline"""
    
    def __init__(self):
        # 从settings获取数据库配置
        self.engine = create_engine(POSTGRES_URL)
        self.Session = sessionmaker(bind=self.engine)
        self.session = self.Session()
        
        # 创建数据库表
        create_tables(self.engine)
        
        self.logger = logging.getLogger(__name__)

    def process_item(self, item, spider):
        """处理个人业绩Item"""
        adapter = ItemAdapter(item)

        # 只处理PersonPerformanceItem
        if item.__class__.__name__ != 'PersonPerformanceItem':
            return item

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
                    self.session.flush()  # 立即写入数据库以获取ID
                    self.logger.info(f"Created temporary company record for corp_code: {corp_code}")

            # 检查是否已存在相同的个人业绩记录
            existing_performance = self.session.query(PersonPerformance).filter_by(
                name=adapter.get('name'),
                corp_code=adapter.get('corp_code'),
                project_name=adapter.get('project_name'),
                role=adapter.get('role')
            ).first()

            if existing_performance:
                # 更新现有记录
                existing_performance.corp_name = adapter.get('corp_name')
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

            self.session.commit()

        except IntegrityError as e:
            self.session.rollback()
            self.logger.error(f"Database integrity error when processing person performance: {e}")
        except Exception as e:
            self.session.rollback()
            self.logger.error(f"Error processing person performance item: {e}")
            raise

        return item

    def close_spider(self, spider):
        """关闭爬虫时清理资源"""
        if self.session:
            self.session.close()
        self.logger.info("PersonPerformancePipeline closed") 