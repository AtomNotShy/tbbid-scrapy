from sqlalchemy import create_engine, text
from models.models import Base
from settings import POSTGRES_URL

def init_database():
    # 创建数据库连接
    engine = create_engine(POSTGRES_URL)
    
    # 删除现有表
    with engine.connect() as conn:
        conn.execute(text("DROP TABLE IF EXISTS employee_info CASCADE"))
        conn.execute(text("DROP TABLE IF EXISTS company_info CASCADE"))
        conn.commit()
    
    # 创建新表
    Base.metadata.create_all(engine)
    print("数据库表结构已重新创建")

if __name__ == "__main__":
    init_database()
    