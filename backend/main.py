from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from database import engine, Base
from models import Account, Post, Statistics, Pattern
from routes import router
from ivadi_routes import router as ivadi_router
from analyzer_routes import router as analyzer_router
from client_routes import router as client_router
from settings_routes import router as settings_router
from opportunity_routes import router as opportunity_router
from youtube_routes import router as youtube_router
from shorts_factory_routes import router as shorts_factory_router
from grok_video_routes import router as grok_video_router
from auth_routes import router as auth_router
from dotenv import load_dotenv
import os

load_dotenv()

Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Factory API",
    description="VK Content Factory API",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)
app.include_router(ivadi_router)
app.include_router(analyzer_router)
app.include_router(client_router)
app.include_router(settings_router)
app.include_router(opportunity_router)
app.include_router(youtube_router)
app.include_router(shorts_factory_router)
app.include_router(grok_video_router)
app.include_router(auth_router)

@app.get("/api/health")
def health_check():
    return {"status": "ok"}

import os as _os
_os.makedirs("/root/factory/backend/static", exist_ok=True)
app.mount("/static", StaticFiles(directory="/root/factory/backend/static"), name="static_files")
app.mount("/", StaticFiles(directory="/root/factory/backend", html=True), name="static")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
