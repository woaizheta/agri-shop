from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean
from datetime import datetime, timezone
from nongzi.database import Base
import hashlib


class User(Base):
    __tablename__ = "user"

    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(50), unique=True, nullable=False)
    password_hash = Column(String(128), nullable=False)
    role = Column(String(20), nullable=False, default="admin")
    display_name = Column(String(50), nullable=True, default="")
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    @staticmethod
    def hash_password(password: str, salt: str = "nongzi_salt") -> str:
        return hashlib.sha256(f"{salt}{password}".encode()).hexdigest()

    def check_password(self, password: str, salt: str = "nongzi_salt") -> bool:
        return self.password_hash == self.hash_password(password, salt)


class OperationLog(Base):
    __tablename__ = "operation_log"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, nullable=True)
    action = Column(String(50), nullable=False)
    target_type = Column(String(50), nullable=True, default="")
    target_id = Column(Integer, nullable=True)
    detail = Column(Text, nullable=True, default="")
    ip_address = Column(String(50), nullable=True, default="")
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

class SystemConfig(Base):
    __tablename__ = "system_config"

    id = Column(Integer, primary_key=True, autoincrement=True)
    key = Column(String(50), unique=True, nullable=False)
    value = Column(Text, nullable=True, default="")
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
