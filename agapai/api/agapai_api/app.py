from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from agapai_api.clients import authenticate_bluesky
from agapai_api.routes import router
from agapai_api.ner_routes import router as ner_router
from agapai_api.classifier import classify_post

class PostPayload(BaseModel):
    text: str


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
    authenticate_bluesky()

app.include_router(router)
app.include_router(ner_router)