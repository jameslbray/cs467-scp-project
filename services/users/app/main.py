from fastapi import FastAPI

# Create FastAPI application
app = FastAPI(
    title="User Service API",
    description="Service for managing user authentication and profiles",
    version="0.1.0",
)

@app.get("/")
async def root():
    """Root endpoint that returns a welcome message."""
    return {
        "message": "Welcome to the User Service API",
        "service": "user-service",
        "status": "operational"
    }

@app.get("/health")
async def health_check():
    """Health check endpoint for the service."""
    return {"status": "healthy"}
