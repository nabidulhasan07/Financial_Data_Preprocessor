import os
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

from .api.routes import router

app = FastAPI(
    title="Financial Data Preprocessor API",
    version="0.1.0",
    description="API for the Financial Data Preprocessor application.",
)

cors_origins = [
    origin.strip()
    for origin in os.getenv("CORS_ORIGINS", "http://127.0.0.1:5173,http://localhost:5173").split(",")
    if origin.strip()
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router, prefix="/api")

# In production, the Docker image includes the Vite build beside the backend.
# The local development workflow continues to use Vite's /api proxy.
frontend_dist = Path(__file__).resolve().parents[2] / "frontend" / "dist"
frontend_index = frontend_dist / "index.html"


@app.get("/{path:path}", include_in_schema=False)
def serve_frontend(path: str):
    if path == "" and frontend_index.is_file():
        return FileResponse(frontend_index)
    if path.startswith("api/"):
        raise HTTPException(status_code=404, detail="Not found")
    requested_file = (frontend_dist / path).resolve()
    try:
        requested_file.relative_to(frontend_dist.resolve())
    except ValueError as error:
        raise HTTPException(status_code=404, detail="Not found") from error
    if requested_file.is_file():
        return FileResponse(requested_file)
    if frontend_index.is_file():
        return FileResponse(frontend_index)
    raise HTTPException(status_code=404, detail="Frontend build not found")
