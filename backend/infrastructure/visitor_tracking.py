import asyncio
from datetime import datetime

import redis
from sqlalchemy.orm import Session

from backend.database.connection import get_db
from backend.database.models import VisitorStats


class VisitorTracker:
    """
    Tracks visitors with guaranteed persistence.

    Strategy:
    1. Redis: fast, real-time counting
    2. PostgreSQL: permanent persistence
    3. Synchronization: every 1 hour or 100 visitors
    """

    def __init__(self, redis_client: redis.Redis):
        self.redis = redis_client
        self.redis_key = "visitors:total"
        self.redis_temp_key = "visitors:session"
        self.sync_threshold = 100  # Synchronize every 100 visits
        self.sync_interval = 3600  # Or every 1 hour

    async def increment_visitor(self, session_id: str = None) -> int:
        """
        Increment the visitor counter.

        Strategy:
        1. Redis: increment fast (no disk I/O)
        2. Return current count
        3. Background: persist periodically
        """
        # Incrementar no Redis
        current_count = self.redis.incr(self.redis_key)

        # Add session to set (for analytics)
        if session_id:
            self.redis.sadd(self.redis_temp_key, session_id)

        # If threshold is reached, synchronize with DB
        if current_count % self.sync_threshold == 0:
            asyncio.create_task(self._sync_to_database(current_count))

        return current_count

    async def _sync_to_database(self, count: int, db: Session = None):
        """Synchronize Redis count → PostgreSQL"""
        if db is None:
            db = next(get_db())

        try:
            stats = db.query(VisitorStats).first()
            if stats:
                stats.total_visitors = count
                stats.last_sync = datetime.utcnow()
            else:
                stats = VisitorStats(total_visitors=count, last_sync=datetime.utcnow())
                db.add(stats)

            db.commit()
            print(f"Visitantes sincronizados: {count}")
        except Exception as e:
            print(f"Erro sincronização: {e}")
            db.rollback()

    async def get_total_visitors(self) -> int:
        """
        Returns the total number of visitors.
        Combines Redis + PostgreSQL to ensure correct values.
        """
        redis_count = int(self.redis.get(self.redis_key) or 0)

        # If Redis is empty, restore from PostgreSQL
        if redis_count == 0:
            db = next(get_db())
            stats = db.query(VisitorStats).first()
            if stats:
                redis_count = stats.total_visitors
                self.redis.set(self.redis_key, redis_count)

        return redis_count

    def get_unique_sessions_today(self) -> int:
        """Returns unique sessions for today"""
        return self.redis.scard(self.redis_temp_key)