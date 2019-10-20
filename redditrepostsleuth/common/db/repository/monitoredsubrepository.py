from typing import List

from redditrepostsleuth.common.model.db.databasemodels import MonitoredSub


class MonitoredSubRepository:
    def __init__(self, db_session):
        self.db_session = db_session

    def get_all(self, limit: int = None) -> List[MonitoredSub]:
        return self.db_session.query(MonitoredSub).limit(limit).all()

    def get_by_sub(self, sub: str) -> MonitoredSub:
        return self.db_session.query(MonitoredSub).filter(MonitoredSub.name == sub).first()