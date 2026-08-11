from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Boolean, Text
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
from nongzi.database import Base


class Warehouse(Base):
    __tablename__ = "warehouse"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(50), nullable=False)
    shelf_code = Column(String(20), nullable=True, default="")
    is_default = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    inventories = relationship("Inventory", back_populates="warehouse")
    inventory_batches = relationship("InventoryBatch", back_populates="warehouse")


class Inventory(Base):
    __tablename__ = "inventory"

    id = Column(Integer, primary_key=True, autoincrement=True)
    product_id = Column(Integer, ForeignKey("product.id"), nullable=False)
    warehouse_id = Column(Integer, ForeignKey("warehouse.id"), nullable=False)
    quantity = Column(Float, nullable=False, default=0.0)
    available_quantity = Column(Float, nullable=False, default=0.0)
    cost_price = Column(Float, nullable=True, default=None)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc),
                        onupdate=lambda: datetime.now(timezone.utc))

    product = relationship("Product", back_populates="inventories")
    warehouse = relationship("Warehouse", back_populates="inventories")


class InventoryBatch(Base):
    __tablename__ = "inventory_batch"

    id = Column(Integer, primary_key=True, autoincrement=True)
    product_id = Column(Integer, ForeignKey("product.id"), nullable=False)
    warehouse_id = Column(Integer, ForeignKey("warehouse.id"), nullable=False)
    batch_no = Column(String(50), nullable=False)
    quantity = Column(Float, nullable=False, default=0.0)
    available_quantity = Column(Float, nullable=False, default=0.0)
    prod_date = Column(DateTime, nullable=True)
    expiry_date = Column(DateTime, nullable=True)
    purchase_item_id = Column(Integer, ForeignKey("purchase_item.id"), nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc),
                        onupdate=lambda: datetime.now(timezone.utc))

    product = relationship("Product", back_populates="inventory_batches")
    warehouse = relationship("Warehouse", back_populates="inventory_batches")
    purchase_item = relationship("PurchaseItem", back_populates="inventory_batches")

class StockCount(Base):
    """盘点单"""
    __tablename__ = "stock_count"

    id = Column(Integer, primary_key=True, autoincrement=True)
    order_no = Column(String(50), unique=True, nullable=False)
    count_date = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
    counter_name = Column(String(50), nullable=True, default="")
    scope_type = Column(String(20), nullable=False, default="all")  # all / category / product
    scope_value = Column(Integer, nullable=True)  # category_id or product_id
    status = Column(String(20), nullable=False, default="in_progress")  # in_progress / completed
    notes = Column(Text, nullable=True, default="")
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    items = relationship("StockCountItem", back_populates="stock_count", cascade="all, delete-orphan")


class StockCountItem(Base):
    """盘点明细"""
    __tablename__ = "stock_count_item"

    id = Column(Integer, primary_key=True, autoincrement=True)
    count_id = Column(Integer, ForeignKey("stock_count.id"), nullable=False)
    product_id = Column(Integer, ForeignKey("product.id"), nullable=False)
    system_quantity = Column(Float, nullable=False, default=0.0)
    actual_quantity = Column(Float, nullable=True, default=None)
    difference = Column(Float, nullable=True, default=None)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    stock_count = relationship("StockCount", back_populates="items")
    product = relationship("Product")


class WriteOff(Base):
    """报损单"""
    __tablename__ = "write_off"

    id = Column(Integer, primary_key=True, autoincrement=True)
    order_no = Column(String(50), unique=True, nullable=False)
    product_id = Column(Integer, ForeignKey("product.id"), nullable=False)
    warehouse_id = Column(Integer, ForeignKey("warehouse.id"), nullable=False)
    batch_id = Column(Integer, ForeignKey("inventory_batch.id"), nullable=True)
    quantity = Column(Float, nullable=False)
    reason = Column(String(50), nullable=False)  # expired / damaged / other
    notes = Column(Text, nullable=True, default="")
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    product = relationship("Product")
    warehouse = relationship("Warehouse")
    batch = relationship("InventoryBatch")

