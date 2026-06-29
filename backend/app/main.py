from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.routes import api_router

app = FastAPI(title="Agent Backend Engine")

# Explicitly defining matching origins found inside your working setup
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://localhost:3000",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Connect all routes structured under /api
app.include_router(api_router)
