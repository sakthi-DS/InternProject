"""
User Service - FastAPI Microservice
Handles user registration, authentication, and profile management
"""

from fastapi import FastAPI, HTTPException, Depends, status, Request
from fastapi.responses import Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from sqlalchemy.orm import Session
from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST

import structlog
import time

from .database import engine, SessionLocal, Base
from .models import User
from .schemas import UserCreate, UserResponse, UserLogin, Token
from .auth import create_access_token, verify_token, get_password_hash, verify_password
from .config import settings

# Create tables
Base.metadata.create_all(bind=engine)

# Initialize FastAPI app
# Initialize FastAPI app
app = FastAPI(
    title="User Service",
    description="Microservice for user management and authentication",
    version="1.0.0",
    docs_url="/users/docs",
    redoc_url="/users/redoc",
    openapi_url="/users/openapi.json"
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
# Prometheus Metrics

REQUEST_COUNT = Counter(
    'user_service_requests_total',
    'Total HTTP requests received by User Service',
    ['method', 'endpoint', 'status_code']
)

REQUEST_DURATION = Histogram(
    'user_service_request_duration_seconds',
    'HTTP request processing duration in seconds',
    ['method', 'endpoint'],
    buckets=(0.005, 0.01, 0.025, 0.05, 0.1,
             0.25, 0.5, 1.0, 2.5, 5.0, 10.0)
)

# Security
security = HTTPBearer()

# Dependency to get database session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Dependency to get current user
async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
):
    token = credentials.credentials
    payload = verify_token(token)
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials"
        )
    
    user = db.query(User).filter(User.id == payload.get("sub")).first()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found"
        )
    return user



@app.middleware("http")
async def add_process_time_header(request: Request, call_next):

    # Don't count Prometheus scraping requests
    if request.url.path == "/metrics":
        return await call_next(request)

    start_time = time.perf_counter()

    status_code = 500

    try:
        response = await call_next(request)
        status_code = response.status_code

        return response

    finally:

        process_time = time.perf_counter() - start_time

        # Get the FastAPI route template
        route = request.scope.get("route")

        endpoint = (
            route.path
            if route is not None
            else "unmatched"
        )

        # Count HTTP requests
        REQUEST_COUNT.labels(
            method=request.method,
            endpoint=endpoint,
            status_code=str(status_code)
        ).inc()

        # Measure request duration
        REQUEST_DURATION.labels(
            method=request.method,
            endpoint=endpoint
        ).observe(process_time)

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "service": "user-service"}

@app.get("/metrics")
async def metrics():
    """Prometheus metrics endpoint"""
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)

@app.post("/users", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register_user(user: UserCreate, db: Session = Depends(get_db)):
    """Register a new user"""
    logger.info("Registering new user", email=user.email)
    
    # Check if user already exists
    db_user = db.query(User).filter(User.email == user.email).first()
    if db_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    # Create new user
    hashed_password = get_password_hash(user.password)
    db_user = User(
        email=user.email,
        username=user.username,
        full_name=user.full_name,
        hashed_password=hashed_password
    )
    
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    
    logger.info("User registered successfully", user_id=db_user.id)
    return db_user

@app.post("/users/login", response_model=Token)
async def login_user(user_login: UserLogin, db: Session = Depends(get_db)):
    """Authenticate user and return access token"""
    logger.info("User login attempt", email=user_login.email)
    
    # Find user by email
    db_user = db.query(User).filter(User.email == user_login.email).first()
    if not db_user or not verify_password(user_login.password, db_user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password"
        )
    
    # Create access token
    access_token = create_access_token(data={"sub": str(db_user.id)})
    
    logger.info("User logged in successfully", user_id=db_user.id)
    return {"access_token": access_token, "token_type": "bearer"}

@app.get("/users/me", response_model=UserResponse)
async def get_current_user_profile(current_user: User = Depends(get_current_user)):
    """Get current user profile"""
    return current_user

@app.get("/users/{user_id}", response_model=UserResponse)
async def get_user(user_id: int, db: Session = Depends(get_db)):
    """Get user by ID"""
    db_user = db.query(User).filter(User.id == user_id).first()
    if db_user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    return db_user

@app.get("/users", response_model=list[UserResponse])
async def list_users(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    """List all users with pagination"""
    users = db.query(User).offset(skip).limit(limit).all()
    return users

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
