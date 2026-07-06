from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routers import predictions
from dotenv import load_dotenv
import os

load_dotenv()

app = FastAPI(
    title="MSparq Intelligence API",
    description="AI/ML Intelligence Layer for MSparq School OS",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        os.getenv("MSPARQ_APP_URL", "http://localhost:3001"),
        "https://msparq.vercel.app",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(predictions.router)

@app.get("/")
async def root():
    return {
        "service": "MSparq Intelligence API",
        "version": "1.0.0",
        "status": "running"
    }

@app.get("/health")
async def health():
    return {"status": "healthy"}