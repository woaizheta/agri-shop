from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Boolean, Text
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
from nongzi.database import Base


class PurchaseOrder(Base):
    __tablename__ = "purchase_order"

    id = Column(Integer, primary_key=True, autoincrement=True)
    order_no = Column(String(30), unique=True, nullable=False)
    supplier_id = Column(Integer, ForeignKey("supplier.id"), nullable=False)
    total_amount = Column(Float, nullable=False, default=0.0)
    order_date = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
    status = Column(String(20), nullable=False, default="confirmed")
    note = Column(Text, nullable=True, default="")
    is_reversed = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc),
                        onupdate=lambda: datetime.now(timezone.utc))

    supplier = relationship("Supplier", back_populates="purchase_orders")
    items = relationship("PurchaseItem", back_populates="order",
                         cascade="all, delete-orphan")


class PurchaseItem(Base):
    __tablename__ = "purchase_item"

    id = Column(Integer, primary_key=True, autoincrement=True)
    order_id = Column(Integer, ForeignKey("purchase_order.id"), nullable=False)
    product_id = Column(Integer, ForeignKey("product.id"), nullable=False)
    batch_no = Column(String(50), nullable=True, default="")
    quantity = Column(Float, nullable=False)
    unit_price = Column(Float, nullable=False)
    amount = Column(Float, nullable=False)
    prod_date = Column(DateTime, nullable=True)
    expiry_date = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    order = relationship("PurchaseOrder", back_populates="items")
    product = relationship("Product", back_populates="purchase_items")
    inventory_batches = relationship("InventoryBatch", back_populates="purchase_item")
