from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime
import logging

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 创建基类
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
    district_show = Column(String)
    lot_size = Column(Integer)
    company_req = Column(String)
    person_req = Column(String)
    construction_funds = Column(String)
    project_duration = Column(String)
    crawl_time = Column(DateTime, default=datetime.now)

def test_db_connection():
    """测试数据库连接"""
    try:
        # 创建数据库连接
        engine = create_engine('postgresql://atom:qwerasdf@localhost:5432/data')
        # 测试连接
        with engine.connect() as conn:
            logger.info("数据库连接成功")
        return engine
    except Exception as e:
        logger.error(f"数据库连接失败: {str(e)}")
        raise

def test_create_tables(engine):
    """测试创建表"""
    try:
        Base.metadata.create_all(engine)
        logger.info("表创建成功")
    except Exception as e:
        logger.error(f"表创建失败: {str(e)}")
        raise

def test_save_project(engine):
    """测试保存项目数据"""
    Session = sessionmaker(bind=engine)
    session = Session()
    
    try:
        # 创建测试数据
        test_project = Project(
            project_id="TEST001",
            title="测试项目",
            time_show=datetime.now(),
            platform_name="测试平台",
            classify_show="测试分类",
            url="http://test.com",
            district_show="测试地区",
            lot_size=1,
            company_req="测试公司要求",
            person_req="测试人员要求",
            construction_funds="测试资金",
            project_duration="测试工期"
        )
        
        # 保存数据
        session.add(test_project)
        session.commit()
        logger.info("测试项目保存成功")
        
        # 验证数据是否保存成功
        saved_project = session.query(Project).filter_by(project_id="TEST001").first()
        if saved_project:
            logger.info(f"验证成功，找到项目: {saved_project.title}")
            # 打印项目详情
            logger.info(f"项目详情: {vars(saved_project)}")
        else:
            logger.error("验证失败，未找到保存的项目")
            
    except Exception as e:
        session.rollback()
        logger.error(f"保存项目失败: {str(e)}")
        raise
    finally:
        session.close()

def test_query_all_projects(engine):
    """测试查询所有项目"""
    Session = sessionmaker(bind=engine)
    session = Session()
    
    try:
        projects = session.query(Project).all()
        logger.info(f"数据库中共有 {len(projects)} 个项目")
        for project in projects:
            logger.info(f"项目ID: {project.project_id}, 标题: {project.title}")
    except Exception as e:
        logger.error(f"查询项目失败: {str(e)}")
        raise
    finally:
        session.close()

def main():
    """主函数"""
    try:
        # 测试数据库连接
        engine = test_db_connection()
        
        # 测试创建表
        test_create_tables(engine)
        
        # 测试保存项目
        test_save_project(engine)
        
        # 测试查询所有项目
        test_query_all_projects(engine)
        
        logger.info("所有测试完成")
        
    except Exception as e:
        logger.error(f"测试过程中出现错误: {str(e)}")
        raise

if __name__ == "__main__":
    main() 