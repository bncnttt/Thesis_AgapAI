from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from agapai_api.clients import client
from agapai_api.config import BLUESKY_HANDLE, BLUESKY_PASSWORD
from agapai_api.routes import router

app = FastAPI(
    title="AgapAI Data Collection Pipeline",
    description="Thesis Phase 1 Data Ingestion Engine: Verified Social Graph Mapping.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def authenticate_session():
    try:
        print(f"Attempting API login for {BLUESKY_HANDLE}...")
        client.login(BLUESKY_HANDLE, BLUESKY_PASSWORD)
        print("Login successful! Network connectivity verified.")
    except Exception as e:
        print(f"Startup Login Bypass Warning: Could not authenticate with Bluesky: {repr(e)}")


app.include_router(router)
