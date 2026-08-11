from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
from nongzi.database import Base


class ARTransaction(Base):
    __tablename__ = "ar_transaction"

    id = Column(Integer, primary_key=True, autoincrement=True)
    customer_id = Column(Integer, ForeignKey("customer.id"), nullable=False)
    sale_order_id = Column(Integer, ForeignKey("sale_order.id"), nullable=True)
    type = Column(String(20), nullable=False)
    amount = Column(Float, nullable=False)
    balance_after = Column(Float, nullable=False, default=0.0)
    note = Column(Text, nullable=True, default="")
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    customer = relationship("Customer", back_populates="ar_transactions")


class APTransaction(Base):
    __tablename__ = "ap_transaction"

    id = Column(Integer, primary_key=True, autoincrement=True)
    supplier_id = Column(Integer, ForeignKey("supplier.id"), nullable=False)
    purchase_order_id = Column(Integer, ForeignKey("purchase_order.id"), nullable=True)
    type = Column(String(20), nullable=False)
    amount = Column(Float, nullable=False)
    balance_after = Column(Float, nullable=False, default=0.0)
    note = Column(Text, nullable=True, default="")
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    supplier = relationship("Supplier", back_populates="ap_transactions")


class Expense(Base):
    __tablename__ = "expense"

    id = Column(Integer, primary_key=True, autoincrement=True)
    category = Column(String(20), nullable=False)
    amount = Column(Float, nullable=False)
    expense_date = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
    note = Column(Text, nullable=True, default="")
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
