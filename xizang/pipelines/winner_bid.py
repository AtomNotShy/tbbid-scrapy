from itemadapter import ItemAdapter
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from xizang.models.models import create_tables, WinnerBidInfo
from datetime import datetime
from xizang.settings import POSTGRES_URL

class WinnerBidPipeline:
    def __init__(self, db_url):
        self.engine = create_engine(db_url)
        self.Session = sessionmaker(bind=self.engine)
        create_tables(self.engine)

    @classmethod
    def from_crawler(cls, crawler):
        return cls(
            db_url=crawler.settings.get('POSTGRES_URL', 'postgresql://atom:qwerasdf@localhost:5432/data')
        )

    def process_item(self, item, spider):
        if item.__class__.__name__ != 'BidWinItem':
            return item
        session = self.Session()
        adapter = ItemAdapter(item)
        try:
            # 检查 corp_code 是否存在
            corp_code = adapter.get('corp_code')
            project_name = adapter.get('project_name')
            if not corp_code or not project_name:
                spider.logger.error(f"BidWinItem 缺少 corp_code 或 project_name: {dict(adapter)}")
                return item

            # 查找是否已存在该中标信息（可根据 corp_code + project_name 判断唯一性）
            existing = session.query(WinnerBidInfo).filter_by(corp_code=corp_code, project_name=project_name).first()
            if existing:
                # 更新字段
                existing.bidder_name = adapter.get('bidder_name')
                existing.area_code = adapter.get('area_code')
                existing.win_amt = adapter.get('win_amt')
                existing.create_time = self._parse_datetime(adapter.get('create_time'))
                existing.tender_org_name = adapter.get('tender_org_name')
                existing.tos = adapter.get('tos')
                existing.url = adapter.get('url')
                existing.notice_content = adapter.get('notice_content')
            else:
                # 新建
                winner = WinnerBidInfo(
                    project_name=project_name,
                    corp_code=corp_code,
                    bidder_name=adapter.get('bidder_name'),
                    area_code=adapter.get('area_code'),
                    win_amt=adapter.get('win_amt'),
                    create_time=self._parse_datetime(adapter.get('create_time')),
                    tender_org_name=adapter.get('tender_org_name'),
                    tos=adapter.get('tos'),
                    url=adapter.get('url'),
                    notice_content=adapter.get('notice_content')
                )
                session.add(winner)
            session.commit()
        except Exception as e:
            session.rollback()
            spider.logger.error(f"保存 WinnerBidInfo 失败: {e}")
            raise
        finally:
            session.close()
        return item

    def _parse_datetime(self, value):
        if isinstance(value, datetime):
            return value
        if isinstance(value, str):
            for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d", "%Y/%m/%d %H:%M:%S", "%Y/%m/%d"):
                try:
                    return datetime.strptime(value, fmt)
                except Exception:
                    continue
        return None
