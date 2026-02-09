"""FastAPI application - Verification endpoint for interview setup."""
from fastapi import FastAPI

app = FastAPI(title="Odin AI - Staff Engineer Interview")


@app.get("/")
async def root():
    """Health check endpoint."""
    return {"status": "ok", "message": "FastAPI is working correctly"}


@app.get("/health")
async def health():
    """Health check for verification."""
    return {"status": "healthy", "framework": "FastAPI"}
