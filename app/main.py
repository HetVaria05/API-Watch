"""
main.py - FastAPI application entry point.

Creates and configures the FastAPI app, registers all routes,
sets up CORS for the frontend, and serves the frontend static files.
"""

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
import os

from app.database import create_tables
from app.routes import requests, history, collections, monitoring, reports

# Create the FastAPI application
app = FastAPI(
    title="APIWatch",
    description="API Testing & Monitoring Tool",
    version="1.0.0",
)

# Allow the frontend (served from file:// or localhost) to call the API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, restrict this to your domain
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register all route modules
app.include_router(requests.router)
app.include_router(history.router)
app.include_router(collections.router)
app.include_router(monitoring.router)
app.include_router(reports.router)


@app.on_event("startup")
def startup_event():
    """Create database tables when the app starts."""
    create_tables()


@app.get("/health")
def health_check():
    """Simple health check endpoint."""
    return {"status": "ok", "app": "APIWatch"}


# Serve the frontend static files
FRONTEND_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "frontend")

if os.path.isdir(FRONTEND_DIR):
    app.mount("/static", StaticFiles(directory=FRONTEND_DIR), name="static")

    @app.get("/")
    def serve_frontend():
        """Serve the main HTML frontend page."""
        return FileResponse(os.path.join(FRONTEND_DIR, "index.html"))
