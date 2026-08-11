from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Boolean
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
from nongzi.database import Base


class SaleOrder(Base):
    __tablename__ = "sale_order"

    id = Column(Integer, primary_key=True, autoincrement=True)
    order_no = Column(String(30), unique=True, nullable=False)
    customer_id = Column(Integer, ForeignKey("customer.id"), nullable=True)
    total_amount = Column(Float, nullable=False, default=0.0)
    payment_method = Column(String(20), nullable=False, default="cash")
    is_paid = Column(Boolean, default=True)
    paid_amount = Column(Float, nullable=False, default=0.0)
    order_date = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
    is_reversed = Column(Boolean, default=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc),
                        onupdate=lambda: datetime.now(timezone.utc))

    customer = relationship("Customer", back_populates="sale_orders")
    items = relationship("SaleItem", back_populates="order",
                         cascade="all, delete-orphan")
    restricted_sales = relationship("RestrictedSale", back_populates="sale_order")


class SaleItem(Base):
    __tablename__ = "sale_item"

    id = Column(Integer, primary_key=True, autoincrement=True)
    order_id = Column(Integer, ForeignKey("sale_order.id"), nullable=False)
    product_id = Column(Integer, ForeignKey("product.id"), nullable=False)
    batch_id = Column(Integer, ForeignKey("inventory_batch.id"), nullable=True)
    quantity = Column(Float, nullable=False)
    unit_price = Column(Float, nullable=False)
    amount = Column(Float, nullable=False)
    cost_price_at_sale = Column(Float, nullable=True, default=None)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    order = relationship("SaleOrder", back_populates="items")
    product = relationship("Product", back_populates="sale_items")


class RestrictedSale(Base):
    __tablename__ = "restricted_sale"

    id = Column(Integer, primary_key=True, autoincrement=True)
    sale_order_id = Column(Integer, ForeignKey("sale_order.id"), nullable=False)
    product_id = Column(Integer, ForeignKey("product.id"), nullable=False)
    buyer_name = Column(String(50), nullable=False)
    buyer_id_card = Column(String(18), nullable=False)
    buyer_phone = Column(String(20), nullable=False)
    usage_purpose = Column(String(200), nullable=True, default="")
    usage_crop = Column(String(100), nullable=True, default="")
    quantity = Column(Float, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    sale_order = relationship("SaleOrder", back_populates="restricted_sales")
