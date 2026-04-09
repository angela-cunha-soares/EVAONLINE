"""
Database Utils Helper

Helpers for database operations in tests.
"""

from sqlalchemy import text
from sqlalchemy.orm import Session


class DatabaseUtils:
    """Helpers for database operations in testing."""

    @staticmethod
    def truncate_table(session: Session, table_name: str):
        """
        Truncate table (remove all records).

        Args:
            session: SQLAlchemy session
            table_name: Table name
        """
        session.execute(text(f"TRUNCATE TABLE {table_name} CASCADE"))
        session.commit()

    @staticmethod
    def count_rows(session: Session, table_name: str) -> int:
        """
        Count the number of records in a table.

        Args:
            session: SQLAlchemy session
            table_name: Table name

        Returns:
            Number of records
        """
        result = session.execute(text(f"SELECT COUNT(*) FROM {table_name}"))
        return result.scalar()

    @staticmethod
    def table_exists(session: Session, table_name: str) -> bool:
        """
        Check if table exists.

        Args:
            session: SQLAlchemy session
            table_name: Table name

        Returns:
            True if table exists
        """
        result = session.execute(
            text(
                """
                SELECT EXISTS (
                    SELECT FROM information_schema.tables
                    WHERE table_schema = 'public'
                    AND table_name = :table_name
                )
            """
            ),
            {"table_name": table_name},
        )
        return result.scalar()

    @staticmethod
    def index_exists(session: Session, index_name: str) -> bool:
        """
        Check if index exists.

        Args:
            session: SQLAlchemy session
            index_name: Index name

        Returns:
            True if index exists
        """
        result = session.execute(
            text(
                """
                SELECT EXISTS (
                    SELECT FROM pg_indexes
                    WHERE indexname = :index_name
                )
            """
            ),
            {"index_name": index_name},
        )
        return result.scalar()
