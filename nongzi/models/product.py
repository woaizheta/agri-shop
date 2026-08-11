import enum
from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
from nongzi.database import Base


class ToxicityLevel(str, enum.Enum):
    NONE = """ + '""' + @"""
    LOW = "低毒"
    MEDIUM = "中等毒"
    HIGH = "高毒"
    EXTREME = "剧毒"


RESTRICTED_TOXICITY_LEVELS = [ToxicityLevel.HIGH, ToxicityLevel.EXTREME]


class Category(Base):
    __tablename__ = "category"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(50), nullable=False)
    parent_id = Column(Integer, ForeignKey("category.id"), nullable=True)
    sort_order = Column(Integer, default=0)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    parent = relationship("Category", remote_side=[id], backref="children")
    products = relationship("Product", back_populates="category")


class Product(Base):
    __tablename__ = "product"

    id = Column(Integer, primary_key=True, autoincrement=True)
    code = Column(String(30), unique=True, nullable=False)
    generic_name = Column(String(100), nullable=False)
    trade_name = Column(String(100), nullable=True, default="")
    barcode = Column(String(50), nullable=True, default="")
    spec = Column(String(50), nullable=True, default="")
    formulation = Column(String(50), nullable=True, default="")
    content = Column(String(50), nullable=True, default="")
    toxicity = Column(String(10), nullable=True, default="")
    reg_cert_no = Column(String(50), nullable=True, default="")
    produce_lic_no = Column(String(50), nullable=True, default="")
    manufacturer = Column(String(100), nullable=True, default="")
    brand = Column(String(50), nullable=True, default="")
    base_unit = Column(String(10), nullable=False)
    split_unit = Column(String(10), nullable=True, default="")
    conversion_rate = Column(Float, nullable=True, default=None)
    ref_cost = Column(Float, nullable=True, default=None)
    retail_price = Column(Float, nullable=True, default=None)
    wholesale_price = Column(Float, nullable=True, default=None)
    member_price = Column(Float, nullable=True, default=None)
    is_active = Column(Boolean, default=True)
    is_restricted = Column(Boolean, default=False)
    restricted_max_quantity = Column(Float, nullable=True, default=None)
    stock_min = Column(Float, nullable=True, default=None)
    stock_max = Column(Float, nullable=True, default=None)
    category_id = Column(Integer, ForeignKey("category.id"), nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc),
                        onupdate=lambda: datetime.now(timezone.utc))

    category = relationship("Category", back_populates="products")
    inventories = relationship("Inventory", back_populates="product")
    inventory_batches = relationship("InventoryBatch", back_populates="product")
    purchase_items = relationship("PurchaseItem", back_populates="product")
    sale_items = relationship("SaleItem", back_populates="product")
