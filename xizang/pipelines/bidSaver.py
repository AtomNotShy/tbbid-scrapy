from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from itemadapter import ItemAdapter
from datetime import datetime
from scrapy.exceptions import DropItem
from xizang.models.models import Project, BidSection, Bid, BidRank

Base = declarative_base()

class BidSaverPipeline:
    def __init__(self, db_url):
        self.engine = create_engine(db_url)
        self.Session = sessionmaker(bind=self.engine)
        Base.metadata.create_all(self.engine)
        self.project_cache = set()  # 缓存已存在的project_id
        self.pending_projects = {}  # 存储待处理的project信息
        self.pending_items = []  # 存储待处理的非ProjectItem

    @classmethod
    def from_crawler(cls, crawler):
        return cls(
            db_url=crawler.settings.get('POSTGRES_URL', 'postgresql://atom:qwerasdf@localhost:5432/data')
        )

    def open_spider(self, spider):
        # 在爬虫开始时加载已存在的project_id
        session = self.Session()
        try:
            existing_projects = session.query(Project.project_id).all()
            self.project_cache = {p[0] for p in existing_projects}
            spider.logger.info(f"Loaded {len(self.project_cache)} existing projects into cache")
            spider.logger.debug(f"Project cache contents: {self.project_cache}")
        finally:
            session.close()

    def process_item(self, item, spider):
        adapter = ItemAdapter(item)
        project_id = adapter.get('project_id')
        
        if not project_id:
            spider.logger.error("Item missing project_id")
            raise DropItem("Item missing project_id")

        # 如果是ProjectItem，立即处理
        if item.__class__.__name__ == 'ProjectItem':
            spider.logger.info(f"Processing ProjectItem with project_id: {project_id}")
            return self._process_project_item(item, spider)
        
        # 如果不是ProjectItem，检查project是否存在
        if project_id not in self.project_cache:
            # 将item加入待处理队列
            self.pending_items.append(item)
            spider.logger.debug(f"Project {project_id} not found in cache, item queued for later processing")
            spider.logger.debug(f"Current project cache num: {len(self.project_cache)}")
            return item
            
        # 处理其他类型的item
        return self._process_other_item(item, spider)

    def _process_project_item(self, item, spider):
        session = self.Session()
        adapter = ItemAdapter(item)
        project_id = adapter['project_id']
        
        try:
            spider.logger.info(f"Processing ProjectItem with project_id: {project_id}")
            # spider.logger.info(f"ProjectItem data: {dict(adapter)}")
            
            # 检查必要字段
            required_fields = ['title', 'timeShow', 'project_id', 'notice_content']
            missing_fields = [field for field in required_fields if not adapter.get(field)]
            if missing_fields:
                spider.logger.error(f"ProjectItem missing required fields: {missing_fields}")
                raise DropItem(f"ProjectItem missing required fields: {missing_fields}")
            
            # 转换时间字段
            time_show = adapter['timeShow']
            if isinstance(time_show, str):
                try:
                    time_show = datetime.strptime(time_show, '%Y-%m-%d %H:%M:%S')
                except ValueError:
                    spider.logger.warning(f"Invalid time format for project {project_id}: {time_show}")
                    time_show = None
            
            # 创建项目实例
            project = Project(
                project_id=project_id,
                title=adapter['title'],
                time_show=time_show,
                platform_name=adapter.get('platform_name',''),
                classify_show=adapter.get('classifyShow',''),
                url=adapter.get('url',''),
                notice_content=adapter.get('notice_content', ''),
                district_show=adapter.get('districtShow',''),
                session_size=adapter.get('session_size', 0),
                company_req=adapter.get('company_req', ''),
                person_req=adapter.get('person_req', ''),
                construction_funds=adapter.get('construction_funds', ''),
                project_duration=adapter.get('project_duration', ''),
                stage=1  # 设置初始状态为1
            )
            
            # 检查是否已存在
            existing_project = session.query(Project).filter_by(project_id=project_id).first()
            if existing_project:
                spider.logger.info(f"Updating existing project: {project_id}")
                for key, value in vars(project).items():
                    if not key.startswith('_'):
                        setattr(existing_project, key, value)
            else:
                spider.logger.info(f"Creating new project: {project_id}")
                session.add(project)
            
            # 提交事务
            session.commit()
            spider.logger.info(f"Successfully committed project {project_id}")
            
            # 验证保存是否成功
            saved_project = session.query(Project).filter_by(project_id=project_id).first()
            if saved_project:
                spider.logger.info(f"Successfully saved project {project_id}")
                self.project_cache.add(project_id)
                spider.logger.info(f"Added project {project_id} to cache. Cache size: {len(self.project_cache)}")
            else:
                spider.logger.error(f"Failed to save project {project_id}")
                raise Exception(f"Failed to save project {project_id}")
            
            # 处理待处理的items
            self._process_pending_items(spider)
            
        except Exception as e:
            session.rollback()
            spider.logger.error(f'Error saving project to database: {str(e)}')
            spider.logger.exception(e)  # 添加完整的异常堆栈
            raise e
        finally:
            session.close()
            
        return item

    def _process_other_item(self, item, spider):
        session = self.Session()
        adapter = ItemAdapter(item)
        project_id = adapter['project_id']
        
        try:
            if item.__class__.__name__ == 'BidSectionItem':
                return self._process_bid_section(item, spider)
            elif item.__class__.__name__ == 'BidItem':
                return self._process_bid(item, spider)
            elif item.__class__.__name__ == 'BidRankItem':
                return self._process_bid_rank(item, spider)
        except Exception as e:
            session.rollback()
            spider.logger.error(f'Error processing item: {str(e)}')
            raise e
        finally:
            session.close()
            
        return item

    def _process_pending_items(self, spider):
        """处理待处理的items"""
        if not self.pending_items:
            return
            
        spider.logger.info(f"Processing {len(self.pending_items)} pending items")
        items_to_process = self.pending_items.copy()
        self.pending_items.clear()
        
        for item in items_to_process:
            self._process_other_item(item, spider)

    def _process_bid_section(self, item, spider):
        session = self.Session()
        adapter = ItemAdapter(item)
        project_id = adapter['project_id']
        
        try:
            # 检查项目是否存在
            project = session.query(Project).filter_by(project_id=project_id).first()
            if not project:
                spider.logger.debug(f"Project {project_id} not found, queuing bid section for later processing")
                self.pending_items.append(item)
                return item

            # 检查是否已存在相同的标段
            existing_section = session.query(BidSection).filter_by(
                project_id=project_id,
                section_id=adapter['section_id']
            ).first()

            if existing_section:
                # 更新现有记录
                spider.logger.debug(f"Updating existing bid section: {adapter['section_name']}")
                for key, value in adapter.items():
                    if hasattr(existing_section, key):
                        setattr(existing_section, key, value)
                session.add(existing_section)
            else:
                # 创建新记录
                spider.logger.debug(f"Creating new bid section: {adapter['section_name']}")
                bid_section = BidSection(
                    project_id=project_id,
                    section_id=adapter.get('section_id', '001'),
                    section_name=adapter.get('section_name', ''),
                    session_size=adapter.get('session_size',0),
                    lot_ctl_amt=adapter.get('lot_ctl_amt',0),
                    bid_size=adapter.get('bid_size'),
                    bid_open_time=adapter.get('bid_open_time'),
                    info_source=adapter.get('info_source'),
                    status=adapter.get('status', 'pending'),
                    winning_bidder=adapter.get('winning_bidder'),
                    winning_amount=adapter.get('winning_amount'),
                    winning_time=adapter.get('winning_time')
                )
                session.add(bid_section)

            # 更新项目状态为2
            project.stage = 2
            session.add(project)
            session.commit()
            spider.logger.debug(f"Successfully saved bid section: {adapter['section_name']}")
            
        except Exception as e:
            session.rollback()
            spider.logger.error(f'Error saving bid section: {str(e)}')
            raise e
        finally:
            session.close()
            
        return item

    def _process_bid(self, item, spider):
        session = self.Session()
        adapter = ItemAdapter(item)
        project_id = adapter['project_id']
        
        try:
            
            # Check if project exists
            project = session.query(Project).filter_by(project_id=project_id).first()
            if not project:
                spider.logger.debug(f"Project {project_id} not found, queuing bid for later processing")
                self.pending_items.append(item)
                return item
            
            # Check if bid section exists, create if it doesn't
            existing_section = session.query(BidSection).filter_by(
                project_id=project_id,
                section_id=adapter['section_id']
            ).first()
            
            if not existing_section:
                spider.logger.debug(f"Creating missing bid section for bid: {adapter['section_name']}")
                bid_section = BidSection(
                    project_id=project_id,
                    section_id=adapter['section_id'],
                    section_name=adapter['section_name'],
                    status='pending'
                )
                session.add(bid_section)
                session.commit()
            
            existing_bid = session.query(Bid).filter_by(
                project_id=project_id,
                section_id=adapter['section_id'],
                bidder_name=adapter['bidder_name']
            ).first()

            if existing_bid:
                # 更新字段
                existing_bid.section_name = adapter['section_name']
                existing_bid.bid_amount = adapter['bid_amount']
                existing_bid.bid_open_time = adapter['bid_open_time']
                session.add(existing_bid)
            else:
                bid = Bid(
                    project_id=project_id,
                    section_id=adapter['section_id'],
                    section_name=adapter['section_name'],
                    bidder_name=adapter['bidder_name'],
                    bid_amount=adapter['bid_amount'],
                    bid_open_time=adapter['bid_open_time'],
                )
                session.add(bid)
            session.commit()
            spider.logger.debug(f"Successfully saved bid for project {project_id}")
            
        except Exception as e:
            session.rollback()
            spider.logger.error(f'Error saving bid: {str(e)}')
            raise e
        finally:
            session.close()
            
        return item

    def _process_bid_rank(self, item, spider):
        session = self.Session()
        adapter = ItemAdapter(item)
        project_id = adapter['project_id']
        
        try:
            spider.logger.debug(f"Processing BidRankItem with project_id: {project_id}")
            
            # 检查项目是否存在
            project = session.query(Project).filter_by(project_id=project_id).first()
            if not project:
                spider.logger.info(f"Project {project_id} not found, queuing bid rank for later processing")
                self.pending_items.append(item)
                return item
            
            # 先查找是否已存在
            existing_bid_rank = session.query(BidRank).filter_by(
                project_id=project_id,
                section_id=adapter['section_id'],
                rank=adapter['rank']
            ).first()

            if existing_bid_rank:
                # 更新字段
                existing_bid_rank.section_name = adapter['section_name']
                existing_bid_rank.bidder_name = adapter['bidder_name']
                existing_bid_rank.manager_name = adapter['manager_name']
                existing_bid_rank.win_amt = adapter.get('win_amt')
                session.add(existing_bid_rank)
                session.flush()
            else:
                # 新建
                bid_rank = BidRank(
                    project_id=project_id,
                    section_name=adapter['section_name'],
                    section_id=adapter['section_id'],
                    bidder_name=adapter['bidder_name'],
                    rank=adapter['rank'],
                    manager_name=adapter['manager_name'],
                    win_amt=adapter.get('win_amt'),
                    open_time=adapter.get('open_time')
                )
                session.add(bid_rank)
                session.flush()
            
            # 检查并创建bid_section（如果不存在）
            bid_section = session.query(BidSection).filter_by(
                project_id=project_id,
                section_id=adapter['section_id']
            ).first()
            
            if not bid_section:
                spider.logger.info(f"Creating missing bid section for project {project_id}, section {adapter['section_id']}")
                bid_section = BidSection(
                    project_id=project_id,
                    section_id=adapter['section_id'],
                    section_name=adapter['section_name'],
                    status='pending'
                )
                session.add(bid_section)
                session.flush()
            
            # 更新中标信息
            bid_section.winning_bidder = adapter['bidder_name']
            bid_section.winning_amount = adapter.get('win_amt')
            bid_section.winning_time = datetime.now()
            
            # 更新状态
            if adapter['rank'] == 1:  # 如果是第一名
                bid_section.status = 'completed'  # 已完成
            elif adapter['rank'] == 2:
                bid_section.status = 'second'  # 第二名
            elif adapter['rank'] == 3:
                bid_section.status = 'third'  # 第三名
            else:
                bid_section.status = 'pending'  # 其他名次
            
            session.add(bid_section)
            spider.logger.debug(f"Updated bid section status to {bid_section.status} for section {adapter['section_id']}")
            
            # 更新项目状态为3
            project.stage = 3
            session.add(project)
            
            # 提交所有更改
            session.commit()
            spider.logger.debug(f"Successfully saved bid rank and updated bid section for project {project_id}")
            
        except Exception as e:
            session.rollback()
            spider.logger.error(f'Error saving bid rank: {str(e)}')
            raise e
        finally:
            session.close()
            
        return item
