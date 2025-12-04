"""Database operations using SQLAlchemy."""

import json
from pathlib import Path
from typing import Any, Dict, List

from sqlalchemy import JSON, Column, Integer, String, Text, create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import Session, sessionmaker

from cf_box.logging_config import get_logger

logger = get_logger(__name__)

Base = declarative_base()


class CloudflareAccount(Base):
    """SQLAlchemy model for Cloudflare accounts."""

    __tablename__ = "cloudflare_accounts"

    id = Column(String(255), primary_key=True)
    name = Column(String(255))
    type = Column(String(50))
    settings = Column(JSON)


class CloudflareZone(Base):
    """SQLAlchemy model for Cloudflare zones."""

    __tablename__ = "cloudflare_zones"

    id = Column(String(255), primary_key=True)
    name = Column(String(255))
    status = Column(String(50))
    account_id = Column(String(255))
    name_servers = Column(JSON)
    development_mode = Column(Integer)


class CloudflareDNSRecord(Base):
    """SQLAlchemy model for Cloudflare DNS records."""

    __tablename__ = "cloudflare_dns_records"

    id = Column(String(255), primary_key=True)
    zone_id = Column(String(255))
    zone_name = Column(String(255))
    type = Column(String(50))
    name = Column(String(255))
    content = Column(Text)
    proxied = Column(Integer)
    ttl = Column(Integer)
    created_on = Column(String(50))
    modified_on = Column(String(50))
    data = Column(JSON)


class DatabaseManager:
    """Database manager for SQLite operations."""

    def __init__(self, db_path: str = "exports/cloudflare_data.db"):
        """Initialize database manager.

        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = db_path
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)

        self.engine = create_engine(f"sqlite:///{db_path}", echo=False)
        Base.metadata.create_all(self.engine)
        self.SessionLocal = sessionmaker(bind=self.engine)

        logger.info("database_initialized", db_path=db_path)

    def get_session(self) -> Session:
        """Get a database session.

        Returns:
            SQLAlchemy session
        """
        return self.SessionLocal()

    def save_accounts(self, accounts: List[Dict[str, Any]]) -> None:
        """Save accounts to database.

        Args:
            accounts: List of account dictionaries
        """
        session = self.get_session()
        try:
            for account_data in accounts:
                account = CloudflareAccount(
                    id=account_data["id"],
                    name=account_data.get("name", ""),
                    type=account_data.get("type", ""),
                    settings=account_data.get("settings"),
                )
                session.merge(account)
            session.commit()
            logger.info("accounts_saved", count=len(accounts))
        except Exception as e:
            session.rollback()
            logger.error("save_accounts_failed", error=str(e))
            raise
        finally:
            session.close()

    def save_zones(self, zones: List[Dict[str, Any]]) -> None:
        """Save zones to database.

        Args:
            zones: List of zone dictionaries
        """
        session = self.get_session()
        try:
            for zone_data in zones:
                zone = CloudflareZone(
                    id=zone_data["id"],
                    name=zone_data.get("name", ""),
                    status=zone_data.get("status", ""),
                    account_id=zone_data.get("account", {}).get("id", ""),
                    name_servers=zone_data.get("name_servers"),
                    development_mode=zone_data.get("development_mode", 0),
                )
                session.merge(zone)
            session.commit()
            logger.info("zones_saved", count=len(zones))
        except Exception as e:
            session.rollback()
            logger.error("save_zones_failed", error=str(e))
            raise
        finally:
            session.close()

    def save_dns_records(self, dns_records: List[Dict[str, Any]]) -> None:
        """Save DNS records to database.

        Args:
            dns_records: List of DNS record dictionaries
        """
        session = self.get_session()
        try:
            for record_data in dns_records:
                record = CloudflareDNSRecord(
                    id=record_data["id"],
                    zone_id=record_data.get("zone_id", ""),
                    zone_name=record_data.get("zone_name", ""),
                    type=record_data.get("type", ""),
                    name=record_data.get("name", ""),
                    content=record_data.get("content", ""),
                    proxied=1 if record_data.get("proxied", False) else 0,
                    ttl=record_data.get("ttl", 1),
                    created_on=str(record_data.get("created_on", "")),
                    modified_on=str(record_data.get("modified_on", "")),
                    data=record_data.get("data"),
                )
                session.merge(record)
            session.commit()
            logger.info("dns_records_saved", count=len(dns_records))
        except Exception as e:
            session.rollback()
            logger.error("save_dns_records_failed", error=str(e))
            raise
        finally:
            session.close()

    def close(self) -> None:
        """Close database connection."""
        self.engine.dispose()
        logger.info("database_closed")
