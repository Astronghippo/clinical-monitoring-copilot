from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.routes import analyses, datasets, findings, protocols

app = FastAPI(title="Clinical Monitoring Copilot")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in settings.cors_origins.split(",")],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


app.include_router(protocols.router)
app.include_router(datasets.router)
app.include_router(analyses.router)
app.include_router(findings.router)
