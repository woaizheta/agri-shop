import enum
from sqlalchemy import Column, Integer, String, Float, Text, Boolean, DateTime
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
from nongzi.database import Base


class CustomerTag(str, enum.Enum):
    FARMER = "farmer"
    MAJOR_FARMER = "major_farmer"
    COOPERATIVE = "cooperative"


class Supplier(Base):
    __tablename__ = "supplier"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), nullable=False)
    credit_code = Column(String(18), nullable=True, default="")
    contact = Column(String(50), nullable=True, default="")
    phone = Column(String(20), nullable=True, default="")
    address = Column(String(200), nullable=True, default="")
    pesticide_lic_no = Column(String(50), nullable=True, default="")
    note = Column(Text, nullable=True, default="")
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc),
                        onupdate=lambda: datetime.now(timezone.utc))

    purchase_orders = relationship("PurchaseOrder", back_populates="supplier")
    ap_transactions = relationship("APTransaction", back_populates="supplier")


class Customer(Base):
    __tablename__ = "customer"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(50), nullable=False)
    phone = Column(String(20), nullable=False)
    id_card = Column(String(18), nullable=True, default="")
    address = Column(String(200), nullable=True, default="")
    tag = Column(String(20), nullable=False, default="farmer")
    crops = Column(Text, nullable=True, default="")
    farm_area = Column(Float, nullable=True, default=None)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc),
                        onupdate=lambda: datetime.now(timezone.utc))

    sale_orders = relationship("SaleOrder", back_populates="customer")
    ar_transactions = relationship("ARTransaction", back_populates="customer")

    @property
    def tag_display(self) -> str:
        labels = {"farmer": "??", "major_farmer": "????", "cooperative": "???"}
        return labels.get(self.tag, "??")

    @property
    def credit_balance(self) -> float:
        """??????????????"""
        from nongzi.database import SessionLocal
        db = SessionLocal()
        try:
            from nongzi.models.finance import ARTransaction
            transactions = db.query(ARTransaction).filter(
                ARTransaction.customer_id == self.id
            ).all()
            balance = sum(
                t.amount if t.type == "debit" else -t.amount
                for t in transactions
            )
            return balance
        finally:
            db.close()
