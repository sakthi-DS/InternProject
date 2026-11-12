
"""
Order Service - FastAPI Microservice
Handles order placement, tracking, and management
"""

from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.openapi.docs import get_swagger_ui_html
from sqlalchemy.orm import Session
from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST
from fastapi.responses import Response
from typing import List
import structlog
import time

from .database import engine, SessionLocal, Base
from .models import Order, OrderItem, OrderStatus
from .schemas import OrderCreate, OrderResponse
from .auth import verify_token
from .config import settings


# Create database tables
Base.metadata.create_all(bind=engine)
print("Registered tables:", Base.metadata.tables.keys())
print("Database enum labels:", Order.__table__.c.status.type.enums)


# Initialize FastAPI application
app = FastAPI(
    title="Order Service",
    description="Microservice for order placement, tracking, and management",
    version="1.0.0",
    docs_url="/orders/docs",
    redoc_url="/orders/redoc",
    openapi_url="/orders/openapi.json"
)


# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Initialize logging
logger = structlog.get_logger()


# Prometheus metrics
REQUEST_COUNT = Counter(
    "order_service_requests_total",
    "Total requests",
    ["method", "endpoint"]
)

REQUEST_DURATION = Histogram(
    "order_service_request_duration_seconds",
    "Request duration"
)


# Security
security = HTTPBearer()


# Database dependency
def get_db():
    db = SessionLocal()

    try:
        yield db
    finally:
        db.close()


# Authentication dependency
async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    token = credentials.credentials

    payload = verify_token(token)

    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials"
        )

    return payload.get("sub")


# Verify user exists through User Service
async def verify_user_exists(user_id: int) -> bool:
    import httpx

    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{settings.user_service_url}/users/{user_id}"
            )

            return response.status_code == 200

    except Exception as e:
        logger.error(
            "Failed to verify user",
            user_id=user_id,
            error=str(e)
        )

        return False


# Request processing time and metrics middleware
@app.middleware("http")
async def add_process_time_header(request, call_next):

    start_time = time.time()

    response = await call_next(request)

    process_time = time.time() - start_time

    REQUEST_COUNT.labels(
        method=request.method,
        endpoint=request.url.path
    ).inc()

    REQUEST_DURATION.observe(process_time)

    response.headers["X-Process-Time"] = str(process_time)

    return response


# Swagger documentation
@app.get("/docs", include_in_schema=False)
async def custom_swagger_ui_html():

    return get_swagger_ui_html(
        openapi_url=app.openapi_url,
        title=f"{app.title} - Swagger UI"
    )


# Health check
@app.get("/health")
async def health_check():

    return {
        "status": "healthy",
        "service": "order-service"
    }


# Prometheus metrics
@app.get("/metrics")
async def metrics():

    return Response(
        generate_latest(),
        media_type=CONTENT_TYPE_LATEST
    )


# Create order
@app.post(
    "/orders",
    response_model=OrderResponse,
    status_code=status.HTTP_201_CREATED
)
async def create_order(
    order: OrderCreate,
    current_user_id: str = Depends(get_current_user),
    db: Session = Depends(get_db)
):

    user_id = int(current_user_id)

    logger.info("Creating new order", user_id=user_id)

    # Verify user exists
    if not await verify_user_exists(user_id):

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User not found"
        )

    # Calculate total amount
    total_amount = sum(
        item.price * item.quantity
        for item in order.items
    )

    try:
        # Create order
        db_order = Order(
            user_id=user_id,
            total_amount=total_amount,
            status=OrderStatus.PENDING
        )

        db.add(db_order)
        db.flush()

        # Create order items
        for item_data in order.items:

            db_item = OrderItem(
                order_id=db_order.id,
                product_name=item_data.product_name,
                quantity=item_data.quantity,
                price=item_data.price
            )

            db.add(db_item)

        # No payment service used.
        # Confirm order after saving order and items.
        db_order.status = OrderStatus.CONFIRMED

        db.commit()
        db.refresh(db_order)

        logger.info(
            "Order created",
            order_id=db_order.id,
            status=db_order.status
        )

        return db_order

    except Exception as e:
        db.rollback()

        logger.error(
            "Failed to create order",
            user_id=user_id,
            error=str(e)
        )

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create order"
        )


# Get order by ID
@app.get(
    "/orders/{order_id}",
    response_model=OrderResponse
)
async def get_order(
    order_id: int,
    current_user_id: str = Depends(get_current_user),
    db: Session = Depends(get_db)
):

    user_id = int(current_user_id)

    db_order = db.query(Order).filter(
        Order.id == order_id,
        Order.user_id == user_id
    ).first()

    if db_order is None:

        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Order not found"
        )

    return db_order


# List orders
@app.get(
    "/orders",
    response_model=List[OrderResponse]
)
async def list_orders(
    skip: int = 0,
    limit: int = 100,
    current_user_id: str = Depends(get_current_user),
    db: Session = Depends(get_db)
):

    user_id = int(current_user_id)

    orders = db.query(Order).filter(
        Order.user_id == user_id
    ).offset(skip).limit(limit).all()

    return orders


# Update order status
@app.patch("/orders/{order_id}/status")
async def update_order_status(
    order_id: int,
    new_status: OrderStatus,
    current_user_id: str = Depends(get_current_user),
    db: Session = Depends(get_db)
):

    user_id = int(current_user_id)

    db_order = db.query(Order).filter(
        Order.id == order_id,
        Order.user_id == user_id
    ).first()

    if db_order is None:

        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Order not found"
        )

    try:
        db_order.status = new_status

        db.commit()

        logger.info(
            "Order status updated",
            order_id=order_id,
            status=new_status
        )

        return {
            "message": "Order status updated successfully"
        }

    except Exception as e:
        db.rollback()

        logger.error(
            "Failed to update order status",
            order_id=order_id,
            error=str(e)
        )

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update order status"
        )


# Run application directly
if __name__ == "__main__":

    import uvicorn

    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8002
    )
