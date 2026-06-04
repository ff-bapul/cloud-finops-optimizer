from fastapi import FastAPI, Depends, HTTPException, Security
from fastapi.security.api_key import APIKeyHeader
from fastapi.middleware.cors import CORSMiddleware
import os

from app.database.database import engine, Base, SessionLocal
from app.api.endpoints import router
from app.database.seed import seed_rules

API_KEY = os.environ.get("API_KEY", "my-super-secret-api-key-123")
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)

async def get_api_key(api_key_header: str = Security(api_key_header)):
    if api_key_header == API_KEY:
        return api_key_header
    raise HTTPException(status_code=403, detail="Could not validate API KEY")

# Automatically create all tables on startup
Base.metadata.create_all(bind=engine)

# Seed default rules
db = SessionLocal()
seed_rules(db)
db.close()

app = FastAPI(
    title="Cloud Cost Optimizer & Remediation Engine",
    description="API for ingesting billing data, evaluating optimization rules, and generating remediations.",
    version="1.0.0"
)

# Setup CORS to allow Streamlit dashboard requests
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router, prefix="/api", dependencies=[Depends(get_api_key)])

@app.get("/")
def root():
    return {"message": "Cloud Cost Optimizer API is running. Access /docs for Swagger UI."}
