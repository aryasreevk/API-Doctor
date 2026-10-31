
from fastapi import FastAPI

from backend.routes.api_routes import router
from backend.database import engine, Base

# Import model so SQLAlchemy registers the table
from backend.models.history import APIHistory

from fastapi.middleware.cors import CORSMiddleware

# Create database tables
Base.metadata.create_all(bind=engine)


app = FastAPI(
    title="API Doctor",
    description="AI-powered API debugging and diagnostic platform",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://127.0.0.1:5500", "http://localhost:5500"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register API routes
app.include_router(
    router,
    prefix="/api",
    tags=["API Testing"]
)


@app.get("/")
def home():
    return {
        "application": "API Doctor",
        "message": "Welcome to API Doctor!",
        "status": "Running"
    }


@app.get("/health")
def health_check():
    return {
        "status": "healthy",
        "application": "API Doctor",
        "database": "initialized"
    }
