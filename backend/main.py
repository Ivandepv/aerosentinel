import asyncio
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

load_dotenv()

from database import init_db
from inference import init_engine
from collector import run_collector
from routes.aircraft import router as aircraft_router
from routes.anomalies import router as anomalies_router
from routes.websocket import router as websocket_router

READSB_URL    = os.getenv("READSB_URL",     "http://localhost:30047/data/aircraft.json")
POLL_INTERVAL = int(os.getenv("POLL_INTERVAL_SEC", "2"))
DB_PATH       = os.getenv("DB_PATH",        "./data/aerosentinel.db")
MODEL_PATH    = os.getenv("MODEL_PATH",     "../models/model.pkl")
SCALER_PATH   = os.getenv("SCALER_PATH",   "../models/scaler.pkl")
FEATURES_PATH = os.getenv("FEATURES_PATH", "../models/features.pkl")


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db(DB_PATH)
    init_engine(MODEL_PATH, SCALER_PATH, FEATURES_PATH)
    task = asyncio.create_task(run_collector(READSB_URL, POLL_INTERVAL))
    print(f"[main] collector started — polling {READSB_URL} every {POLL_INTERVAL}s")
    yield
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass


app = FastAPI(title="AeroSentinel API", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(aircraft_router)
app.include_router(anomalies_router)
app.include_router(websocket_router)


@app.get("/health")
async def health():
    return {"status": "ok"}
