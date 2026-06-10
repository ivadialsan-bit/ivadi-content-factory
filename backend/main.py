from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from database import engine, Base
from models import Account, Post, Statistics, Pattern
from routes import router
from ivadi_routes import router as ivadi_router
from analyzer_routes import router as analyzer_router
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

@app.get("/api/health")
def health_check():
    return {"status": "ok"}

app.mount("/", StaticFiles(directory="/root/factory/backend", html=True), name="static")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
