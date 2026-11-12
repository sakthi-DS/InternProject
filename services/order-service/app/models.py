
"""
Database models for Order Service
"""

import enum

from sqlalchemy import (
    Column,
    Integer,
    String,
    DateTime,
    Float,
    ForeignKey,
    Enum,
)
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship

from .database import Base



class OrderStatus(enum.Enum):
    """Order status enumeration"""

    PENDING = "PENDING"
    CONFIRMED = "CONFIRMED"
    PROCESSING = "PROCESSING"
    SHIPPED = "SHIPPED"
    DELIVERED = "DELIVERED"
    CANCELLED = "CANCELLED"
    FAILED = "FAILED"

class Order(Base):
    """Order model"""

    __tablename__ = "orders"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, nullable=False, index=True)
    total_amount = Column(Float, nullable=False)

    status = Column(
        Enum(OrderStatus, name="orderstatus"),
        default=OrderStatus.PENDING,
        nullable=True,
    )

    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
    )

    updated_at = Column(
        DateTime(timezone=True),
        onupdate=func.now(),
    )

    items = relationship(
        "OrderItem",
        back_populates="order",
    )

    def __repr__(self):
        return (
            f"<Order(id={self.id}, "
            f"user_id={self.user_id}, "
            f"status='{self.status}')>"
        )


class OrderItem(Base):
    """Order item model"""

    __tablename__ = "order_items"

    id = Column(Integer, primary_key=True, index=True)

    order_id = Column(
        Integer,
        ForeignKey("orders.id"),
        nullable=False,
    )

    product_name = Column(String, nullable=False)
    quantity = Column(Integer, nullable=False)
    price = Column(Float, nullable=False)

    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
    )

    # Relationship to order
    order = relationship(
        "Order",
        back_populates="items",
    )

    def __repr__(self):
        return (
            f"<OrderItem(id={self.id}, "
            f"product='{self.product_name}', "
            f"quantity={self.quantity})>"
        )
