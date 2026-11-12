
"""
Pydantic schemas for Order Service
"""

from pydantic import BaseModel, Field
from datetime import datetime
from typing import List, Optional
import enum


# Order status enum
class OrderStatus(str, enum.Enum):
    PENDING = "PENDING"
    CONFIRMED = "CONFIRMED"
    PROCESSING = "PROCESSING"
    SHIPPED = "SHIPPED"
    DELIVERED = "DELIVERED"
    CANCELLED = "CANCELLED"
    FAILED = "FAILED"


# Schema for creating an order item
class OrderItemCreate(BaseModel):
    product_name: str = Field(..., min_length=1, max_length=200)
    quantity: int = Field(..., gt=0)
    price: float = Field(..., gt=0)


# Schema for order item response
class OrderItemResponse(OrderItemCreate):
    id: int
    order_id: int
    created_at: datetime

    class Config:
        from_attributes = True


# Schema for creating an order
class OrderCreate(BaseModel):
    items: List[OrderItemCreate] = Field(..., min_items=1)


# Schema for order response
class OrderResponse(BaseModel):
    id: int
    user_id: int
    total_amount: float
    status: OrderStatus
    created_at: datetime
    updated_at: Optional[datetime] = None
    items: List[OrderItemResponse] = []

    class Config:
        from_attributes = True
